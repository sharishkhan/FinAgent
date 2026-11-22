import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEFAULT_DATABASE_PATH = DEFAULT_DATA_DIR / "finagent.sqlite3"


class PersistenceError(Exception):
    pass


def get_database_path() -> Path:
    configured_path = os.getenv("FINAGENT_DB_PATH", "").strip()
    return Path(configured_path) if configured_path else DEFAULT_DATABASE_PATH


@contextmanager
def _connect():
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def _json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=True)


def _json_loads(value, fallback):
    if value in (None, ""):
        return fallback

    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def init_database() -> None:
    try:
        with _connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    processed_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    text TEXT NOT NULL,
                    page_texts_json TEXT NOT NULL,
                    chunks_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS question_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source_pages_json TEXT NOT NULL,
                    sources_json TEXT NOT NULL,
                    provider TEXT,
                    model TEXT,
                    disclaimer TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(document_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    result_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(document_id)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_question_history_document_id ON question_history(document_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_saved_results_document_id ON saved_results(document_id)"
            )
            connection.commit()
    except sqlite3.Error as exc:
        raise PersistenceError("Could not initialize the local database.") from exc


def save_document(document: dict) -> None:
    try:
        with _connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO documents (
                    document_id,
                    filename,
                    processed_at,
                    metadata_json,
                    response_json,
                    text,
                    page_texts_json,
                    chunks_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document["document_id"],
                    document["filename"],
                    document.get("processed_at") or datetime.now(UTC).isoformat(),
                    _json_dumps(document.get("metadata", {})),
                    _json_dumps(document.get("response", {})),
                    document.get("text", ""),
                    _json_dumps(document.get("page_texts", [])),
                    _json_dumps(document.get("chunks", [])),
                ),
            )
            connection.commit()
    except sqlite3.Error as exc:
        raise PersistenceError("Could not persist document data.") from exc


def load_documents() -> dict[str, dict]:
    documents = {}

    try:
        with _connect() as connection:
            rows = connection.execute(
                """
                SELECT document_id, filename, processed_at, metadata_json,
                       response_json, text, page_texts_json, chunks_json
                FROM documents
                ORDER BY processed_at DESC
                """
            ).fetchall()
    except sqlite3.Error as exc:
        raise PersistenceError("Could not load saved documents.") from exc

    for row in rows:
        response = _json_loads(row["response_json"], {})
        if not response:
            continue

        documents[row["document_id"]] = {
            "document_id": row["document_id"],
            "filename": row["filename"],
            "text": row["text"] or "",
            "page_texts": _json_loads(row["page_texts_json"], []),
            "chunks": _json_loads(row["chunks_json"], []),
            "processed_at": row["processed_at"],
            "metadata": _json_loads(row["metadata_json"], {}),
            "response": response,
        }

    return documents


def list_documents() -> list[dict]:
    try:
        with _connect() as connection:
            rows = connection.execute(
                """
                SELECT document_id, filename, processed_at, response_json
                FROM documents
                ORDER BY processed_at DESC
                """
            ).fetchall()
    except sqlite3.Error as exc:
        raise PersistenceError("Could not list saved documents.") from exc

    documents = []
    for row in rows:
        response = _json_loads(row["response_json"], {})
        documents.append(
            {
                "document_id": row["document_id"],
                "filename": row["filename"],
                "processed_at": row["processed_at"],
                "pages": response.get("pages"),
                "words": response.get("words"),
                "characters": response.get("characters"),
                "preview": response.get("preview"),
                "financial_topics": response.get("financial_topics", []),
            }
        )

    return documents


def save_question_history(document_id: str, payload: dict) -> int:
    created_at = datetime.now(UTC).isoformat()

    try:
        with _connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO question_history (
                    document_id,
                    question,
                    answer,
                    status,
                    source_pages_json,
                    sources_json,
                    provider,
                    model,
                    disclaimer,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    payload.get("question", ""),
                    payload.get("answer") or payload.get("message") or "",
                    payload.get("status", ""),
                    _json_dumps(payload.get("source_pages", [])),
                    _json_dumps(payload.get("sources", [])),
                    payload.get("provider"),
                    payload.get("model"),
                    payload.get("disclaimer"),
                    created_at,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)
    except sqlite3.Error as exc:
        raise PersistenceError("Could not save question history.") from exc


def list_question_history(document_id: str) -> list[dict]:
    try:
        with _connect() as connection:
            rows = connection.execute(
                """
                SELECT id, document_id, question, answer, status, source_pages_json,
                       sources_json, provider, model, disclaimer, created_at
                FROM question_history
                WHERE document_id = ?
                ORDER BY created_at DESC
                """,
                (document_id,),
            ).fetchall()
    except sqlite3.Error as exc:
        raise PersistenceError("Could not load question history.") from exc

    return [_question_row_to_dict(row) for row in rows]


def _question_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "document_id": row["document_id"],
        "question": row["question"],
        "answer": row["answer"],
        "status": row["status"],
        "source_pages": _json_loads(row["source_pages_json"], []),
        "sources": _json_loads(row["sources_json"], []),
        "provider": row["provider"],
        "model": row["model"],
        "disclaimer": row["disclaimer"],
        "created_at": row["created_at"],
    }


def save_result(document_id: str, result_type: str, title: str, status: str, payload: dict) -> int:
    created_at = datetime.now(UTC).isoformat()

    try:
        with _connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO saved_results (
                    document_id,
                    result_type,
                    title,
                    status,
                    payload_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    result_type,
                    title,
                    status,
                    _json_dumps(payload),
                    created_at,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)
    except sqlite3.Error as exc:
        raise PersistenceError("Could not save analysis result.") from exc


def list_results() -> list[dict]:
    try:
        with _connect() as connection:
            rows = connection.execute(
                """
                SELECT id, document_id, result_type, title, status, created_at
                FROM saved_results
                ORDER BY created_at DESC
                """
            ).fetchall()
    except sqlite3.Error as exc:
        raise PersistenceError("Could not list saved results.") from exc

    return [
        {
            "id": row["id"],
            "document_id": row["document_id"],
            "result_type": row["result_type"],
            "title": row["title"],
            "status": row["status"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_result(result_id: int) -> dict | None:
    try:
        with _connect() as connection:
            row = connection.execute(
                """
                SELECT id, document_id, result_type, title, status,
                       payload_json, created_at
                FROM saved_results
                WHERE id = ?
                """,
                (result_id,),
            ).fetchone()
    except sqlite3.Error as exc:
        raise PersistenceError("Could not load saved result.") from exc

    if row is None:
        return None

    return {
        "id": row["id"],
        "document_id": row["document_id"],
        "result_type": row["result_type"],
        "title": row["title"],
        "status": row["status"],
        "payload": _json_loads(row["payload_json"], {}),
        "created_at": row["created_at"],
    }


def delete_document(document_id: str) -> dict | None:
    """Delete a document together with its questions and saved results.

    All three deletes happen in ONE transaction: either everything is removed or
    nothing is. Returns how many questions/results were removed, or None if the
    document does not exist.
    """
    try:
        with _connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM documents WHERE document_id = ?", (document_id,)
            ).fetchone()
            if exists is None:
                return None

            questions = connection.execute(
                "DELETE FROM question_history WHERE document_id = ?", (document_id,)
            ).rowcount
            results = connection.execute(
                "DELETE FROM saved_results WHERE document_id = ?", (document_id,)
            ).rowcount
            connection.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
            connection.commit()
            return {"questions": questions, "results": results}
    except sqlite3.Error as exc:
        raise PersistenceError("Could not delete the document.") from exc


def delete_result(result_id: int) -> bool:
    """Delete one saved result. Returns False if it does not exist."""
    try:
        with _connect() as connection:
            deleted = connection.execute(
                "DELETE FROM saved_results WHERE id = ?", (result_id,)
            ).rowcount
            connection.commit()
            return deleted > 0
    except sqlite3.Error as exc:
        raise PersistenceError("Could not delete the saved result.") from exc


def get_storage_counts() -> dict:
    try:
        with _connect() as connection:
            return {
                "documents": connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
                "questions": connection.execute("SELECT COUNT(*) FROM question_history").fetchone()[0],
                "results": connection.execute("SELECT COUNT(*) FROM saved_results").fetchone()[0],
            }
    except sqlite3.Error as exc:
        raise PersistenceError("Could not read storage counts.") from exc
