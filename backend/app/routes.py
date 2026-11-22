from flask import Blueprint, jsonify, request

from .services.llm_service import (
    LLMSummaryError,
    generate_document_summary,
    generate_grounded_answer,
)
from .services.agent_service import AgentAnalysisError, analyze_document_with_agent
from .services.guards import check_question_guards
from .services.pdf_service import (
    DOCUMENT_STORE,
    PDFProcessingError,
    get_processed_document,
    process_pdf_upload,
)
from .services.persistence_service import (
    PersistenceError,
    delete_document,
    delete_result,
    get_result,
    list_documents,
    list_question_history,
    list_results,
    save_question_history,
    save_result,
)
from .services.retrieval_service import RetrievalError, retrieve_relevant_chunks
from .services.sample_service import SampleDocumentError, load_sample_document
from .services.settings_service import check_llm_connection, get_settings_overview
from .services.statement_extractor import compute_metrics, extract_financial_statements

api = Blueprint("api", __name__)


@api.get("/health")
def health():
    return jsonify({"status": "ok", "service": "FinAgent backend"})


@api.get("/settings")
def settings_overview():
    try:
        return jsonify(get_settings_overview())
    except PersistenceError as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@api.post("/settings/test-connection")
def settings_test_connection():
    return jsonify(check_llm_connection())


@api.get("/documents")
def saved_documents():
    try:
        documents = list_documents()
    except PersistenceError as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    return jsonify({"success": True, "documents": documents})


@api.post("/upload")
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file was provided."}), 400

    uploaded_file = request.files["file"]

    try:
        result = process_pdf_upload(uploaded_file)
    except PDFProcessingError as exc:
        return jsonify({"success": False, "error": str(exc)}), exc.status_code

    return jsonify(result)


@api.post("/sample-document")
def load_sample():
    try:
        return jsonify(load_sample_document())
    except SampleDocumentError as exc:
        return jsonify({"success": False, "error": str(exc)}), exc.status_code
    except PDFProcessingError as exc:
        return jsonify({"success": False, "error": str(exc)}), exc.status_code
    except PersistenceError as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@api.get("/documents/<document_id>/financials")
def document_financials(document_id):
    document = get_processed_document(document_id)
    if document is None:
        return jsonify({"success": False, "error": "Document not found."}), 404

    extracted = extract_financial_statements(document)
    metrics = {basis: compute_metrics(extracted["statements"], basis) for basis in extracted["statements"]}
    return jsonify({"success": True, "document_id": document_id, **extracted, "metrics": metrics})


@api.post("/documents/<document_id>/summary")
def summarize_document(document_id):
    document = get_processed_document(document_id)
    if document is None:
        return jsonify({"success": False, "error": "Document not found or no longer available."}), 404

    try:
        result = generate_document_summary(document)
    except LLMSummaryError as exc:
        return jsonify({"success": False, "error": str(exc)}), exc.status_code

    status_code = 200 if result.get("configured") else 503
    if result.get("success"):
        try:
            result_id = save_result(
                document_id=document_id,
                result_type="summary",
                title=f"AI summary for {document['filename']}",
                status=result.get("status", "generated"),
                payload=result,
            )
            result["result_id"] = result_id
        except PersistenceError as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    return jsonify(result), status_code


@api.get("/documents/<document_id>/questions")
def document_question_history(document_id):
    document = get_processed_document(document_id)
    if document is None:
        return jsonify({"success": False, "error": "Document not found or no longer available."}), 404

    try:
        questions = list_question_history(document_id)
    except PersistenceError as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    return jsonify({"success": True, "document_id": document_id, "questions": questions})


@api.post("/documents/<document_id>/question")
def answer_document_question(document_id):
    document = get_processed_document(document_id)
    if document is None:
        return jsonify({"success": False, "error": "Document not found or no longer available."}), 404

    payload = request.get_json(silent=True) or {}
    question = payload.get("question")

    if not isinstance(question, str) or not question.strip():
        return jsonify({"success": False, "error": "A non-empty question is required."}), 400

    question = question.strip()
    if len(question) > 1000:
        return jsonify({"success": False, "error": "Question must be 1000 characters or fewer."}), 400

    guard_result = check_question_guards(document, question)
    if guard_result is not None:
        response_payload = {
            "success": True,
            "status": "insufficient_evidence",
            "document_id": document_id,
            "question": question,
            "answer": guard_result[1],
            "source_pages": [],
            "sources": [],
        }
        try:
            response_payload["history_id"] = save_question_history(document_id, response_payload)
        except PersistenceError as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

        return jsonify(response_payload)

    try:
        sources = retrieve_relevant_chunks(document, question)
    except RetrievalError as exc:
        return jsonify({"success": False, "error": str(exc)}), exc.status_code

    if not sources:
        response_payload = {
            "success": True,
            "status": "insufficient_evidence",
            "document_id": document_id,
            "question": question,
            "answer": "The uploaded document does not provide enough evidence to answer this question.",
            "source_pages": [],
            "sources": [],
        }
        try:
            response_payload["history_id"] = save_question_history(document_id, response_payload)
        except PersistenceError as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

        return jsonify(response_payload)

    source_pages = sorted({source["page"] for source in sources})

    try:
        answer_result = generate_grounded_answer(
            question=question,
            sources=sources,
            filename=document["filename"],
        )
    except LLMSummaryError as exc:
        return jsonify({"success": False, "error": str(exc)}), exc.status_code

    if not answer_result.get("configured"):
        response_payload = {
            **answer_result,
            "document_id": document_id,
            "question": question,
            "source_pages": source_pages,
            "sources": sources,
        }
        try:
            response_payload["history_id"] = save_question_history(document_id, response_payload)
        except PersistenceError as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

        return jsonify(response_payload), 503

    response_payload = {
        **answer_result,
        "document_id": document_id,
        "question": question,
        "source_pages": source_pages,
        "sources": sources,
    }
    try:
        response_payload["history_id"] = save_question_history(document_id, response_payload)
    except PersistenceError as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    return jsonify(response_payload)


@api.post("/documents/<document_id>/analyze")
def analyze_document(document_id):
    document = get_processed_document(document_id)
    if document is None:
        return jsonify({"success": False, "error": "Document not found or no longer available."}), 404

    payload = request.get_json(silent=True) or {}
    question = payload.get("question")

    try:
        result = analyze_document_with_agent(document, question)
    except AgentAnalysisError as exc:
        return jsonify({"success": False, "error": str(exc)}), exc.status_code

    status_code = 200 if result.get("configured", True) else 503
    if result.get("success") and status_code == 200:
        try:
            result_id = save_result(
                document_id=document_id,
                result_type="agent_analysis",
                title=f"Agent analysis for {document['filename']}",
                status=result.get("status", "analyzed"),
                payload=result,
            )
            result["result_id"] = result_id
        except PersistenceError as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    return jsonify(result), status_code


@api.delete("/documents/<document_id>")
def delete_saved_document(document_id):
    try:
        deleted = delete_document(document_id)
    except PersistenceError as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    if deleted is None:
        return jsonify({"success": False, "error": "Document not found."}), 404

    DOCUMENT_STORE.pop(document_id, None)
    return jsonify({"success": True, "document_id": document_id, "deleted": deleted})


@api.delete("/results/<int:result_id>")
def delete_saved_result(result_id):
    try:
        deleted = delete_result(result_id)
    except PersistenceError as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    if not deleted:
        return jsonify({"success": False, "error": "Saved result not found."}), 404

    return jsonify({"success": True, "result_id": result_id})


@api.get("/results")
def saved_results():
    try:
        results = list_results()
    except PersistenceError as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    return jsonify({"success": True, "results": results})


@api.get("/results/<int:result_id>")
def saved_result(result_id):
    try:
        result = get_result(result_id)
    except PersistenceError as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    if result is None:
        return jsonify({"success": False, "error": "Saved result not found."}), 404

    return jsonify({"success": True, "result": result})
