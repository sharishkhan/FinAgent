import { useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  BrainCircuit,
  Calculator,
  CheckCircle2,
  Clock,
  FileText,
  Loader2,
  Search,
  Sparkles,
  XCircle,
} from "lucide-react";

import {
  analyzeDocument,
  getSavedResult,
  getSavedResults,
} from "../lib/api.js";
import { Button } from "../components/ui/Button.jsx";
import { Card, CardBody, CardHeader } from "../components/ui/Card.jsx";

function formatNumber(value) {
  return Number(value ?? 0).toLocaleString();
}

function formatTimestamp(value) {
  if (!value) {
    return "Unknown time";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function getAnalysisPayload(result) {
  return result?.payload ?? result;
}

function getCalculationValue(calculation) {
  if (calculation.metric === "revenue_growth") {
    return `${formatNumber(calculation.growth_percentage)}% growth`;
  }

  if (calculation.metric === "profit_margin") {
    return `${formatNumber(calculation.margin_percentage)}% margin`;
  }

  return calculation.metric ?? "Calculation";
}

export function ResearchPage({
  recentDocuments,
  documentsLoading,
  documentsError,
  onRefreshResults,
  selectedDocumentId: activeDocumentId,
  onSelectDocument,
  embedded = false,
}) {
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [question, setQuestion] = useState("");
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisError, setAnalysisError] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [savedAnalyses, setSavedAnalyses] = useState([]);
  const [savedLoading, setSavedLoading] = useState(true);
  const [savedError, setSavedError] = useState("");
  const [openingResultId, setOpeningResultId] = useState(null);

  const selectedDocument = useMemo(
    () =>
      recentDocuments.find(
        (document) => document.document_id === selectedDocumentId
      ) ?? null,
    [recentDocuments, selectedDocumentId]
  );

  async function loadSavedAnalyses() {
    setSavedLoading(true);
    setSavedError("");

    try {
      const payload = await getSavedResults();
      setSavedAnalyses(
        (payload.results ?? []).filter(
          (result) => result.result_type === "agent_analysis"
        )
      );
    } catch (loadError) {
      setSavedError(loadError.message);
    } finally {
      setSavedLoading(false);
    }
  }

  async function handleRunAnalysis() {
    const trimmedQuestion = question.trim();

    if (!selectedDocumentId) {
      setAnalysisError("Select a saved document before running analysis.");
      return;
    }

    if (!trimmedQuestion) {
      setAnalysisError("Enter a financial analysis question.");
      return;
    }

    setIsAnalyzing(true);
    setAnalysisError("");

    try {
      const payload = await analyzeDocument(selectedDocumentId, trimmedQuestion);
      setAnalysisResult(payload);
      if (payload.success && payload.configured !== false) {
        loadSavedAnalyses();
        onRefreshResults?.();
      }
    } catch (requestError) {
      setAnalysisError(requestError.message);
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function handleOpenSavedAnalysis(resultId) {
    if (!resultId || openingResultId) {
      return;
    }

    setOpeningResultId(resultId);
    setAnalysisError("");

    try {
      const payload = await getSavedResult(resultId);
      const result = payload.result ?? payload;
      const analysisPayload = getAnalysisPayload(result);
      setAnalysisResult(analysisPayload);
      const documentId = result.document_id ?? analysisPayload.document_id ?? "";
      setSelectedDocumentId(documentId);
      onSelectDocument?.(documentId);
      setQuestion(analysisPayload.question ?? "");
    } catch (requestError) {
      setAnalysisError(requestError.message);
    } finally {
      setOpeningResultId(null);
    }
  }

  function handleQuestionKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleRunAnalysis();
    }
  }

  useEffect(() => {
    loadSavedAnalyses();
  }, []);

  useEffect(() => {
    if (activeDocumentId && recentDocuments.some((document) => document.document_id === activeDocumentId)) {
      setSelectedDocumentId(activeDocumentId);
    } else if (!selectedDocumentId && recentDocuments.length > 0) {
      setSelectedDocumentId(recentDocuments[0].document_id);
    }
  }, [activeDocumentId, recentDocuments, selectedDocumentId]);

  const result = getAnalysisPayload(analysisResult);

  return (
    <div className="space-y-6">
      {!embedded && <div>
        <p className="text-sm font-medium text-primary">Analysis</p>

        <h1 className="mt-2 text-3xl font-semibold">
          Evidence-backed analysis
        </h1>

        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
          Run a bounded workflow that retrieves document evidence, executes approved financial tools, and produces a grounded answer with source pages.
        </p>
      </div>}

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="flex size-10 items-center justify-center rounded-md bg-slate-100 text-primary">
                  <BrainCircuit size={20} aria-hidden="true" />
                </div>

                <div>
                  <h2 className="text-base font-semibold">
                    Analysis request
                  </h2>

                  <p className="mt-1 text-sm text-muted">
                    Select a persisted document and ask for financial analysis.
                  </p>
                </div>
              </div>
            </CardHeader>

            <CardBody className="space-y-5">
              <div className="space-y-2">
                {!activeDocumentId && <label
                  className="text-sm font-medium text-slate-800"
                  htmlFor="agent-document"
                >
                  Document
                </label>}

                {!activeDocumentId && (documentsLoading ? (
                  <div className="rounded-md border border-dashed border-border bg-slate-50 px-4 py-5 text-sm text-muted">
                    Loading saved documents...
                  </div>
                ) : documentsError ? (
                  <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {documentsError}
                  </div>
                ) : recentDocuments.length === 0 ? (
                  <div className="rounded-md border border-dashed border-border bg-slate-50 px-4 py-6 text-center">
                    <p className="text-sm font-medium text-foreground">
                      No saved documents available
                    </p>
                    <p className="mt-1 text-sm text-muted">
                      Upload a PDF from Documents before running analysis.
                    </p>
                  </div>
                ) : (
                  <select
                    id="agent-document"
                    value={selectedDocumentId}
                    onChange={(event) => {
                      setSelectedDocumentId(event.target.value);
                      onSelectDocument?.(event.target.value);
                      setAnalysisResult(null);
                      setAnalysisError("");
                    }}
                    className="min-h-10 w-full rounded-md border border-border bg-panel px-3 py-2 text-sm shadow-sm outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10"
                  >
                    {recentDocuments.map((document) => (
                      <option
                        key={document.document_id}
                        value={document.document_id}
                      >
                        {document.filename}
                      </option>
                    ))}
                  </select>
                ))}
              </div>

              {selectedDocument && (
                <div className="grid gap-3 rounded-lg border border-border bg-slate-50 p-4 sm:grid-cols-3">
                  <Metric label="Pages" value={formatNumber(selectedDocument.pages)} />
                  <Metric label="Words" value={formatNumber(selectedDocument.words)} />
                  <Metric label="Characters" value={formatNumber(selectedDocument.characters)} />
                </div>
              )}

              <div className="space-y-2">
                <label
                  className="text-sm font-medium text-slate-800"
                  htmlFor="agent-question"
                >
                  Analysis question
                </label>

                <textarea
                  id="agent-question"
                  value={question}
                  onChange={(event) => {
                    setQuestion(event.target.value);
                    if (analysisError) {
                      setAnalysisError("");
                    }
                  }}
                  onKeyDown={handleQuestionKeyDown}
                  disabled={isAnalyzing}
                  rows={4}
                  className="min-h-32 w-full resize-y rounded-md border border-border bg-panel px-4 py-3 text-sm leading-6 text-foreground shadow-sm outline-none transition placeholder:text-muted focus:border-primary focus:ring-4 focus:ring-primary/10 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-muted"
                  placeholder="Example: Calculate revenue growth and profit margin using figures reported in this document."
                />

                <p className="text-xs text-muted">
                  Press Enter to run, or Shift+Enter for a new line.
                </p>
              </div>

              <Button
                onClick={handleRunAnalysis}
                disabled={!selectedDocumentId || !question.trim() || isAnalyzing}
                className="w-full sm:w-auto"
              >
                {isAnalyzing ? (
                  <Loader2
                    className="animate-spin"
                    size={17}
                    aria-hidden="true"
                  />
                ) : (
                  <Sparkles size={17} aria-hidden="true" />
                )}

                {isAnalyzing ? "Running Analysis" : "Run Agent Analysis"}
              </Button>

              {isAnalyzing && (
                <div className="flex items-center gap-3 rounded-md border border-border bg-slate-50 px-4 py-4 text-sm text-muted">
                  <Loader2
                    className="animate-spin text-primary"
                    size={18}
                    aria-hidden="true"
                  />
                  <span>
                    Retrieving evidence, planning approved tools, and preparing
                    the final answer...
                  </span>
                </div>
              )}

              {analysisError && (
                <div className="flex items-start gap-3 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  <XCircle
                    className="mt-0.5 shrink-0"
                    size={18}
                    aria-hidden="true"
                  />
                  <span>{analysisError}</span>
                </div>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-base font-semibold">Saved analyses</h2>
                <p className="mt-1 text-sm text-muted">
                  Reopen persisted agent outputs after refresh.
                </p>
              </div>

              <Button
                variant="secondary"
                onClick={loadSavedAnalyses}
                disabled={savedLoading}
                className="w-full sm:w-auto"
              >
                {savedLoading ? (
                  <Loader2
                    className="animate-spin"
                    size={17}
                    aria-hidden="true"
                  />
                ) : (
                  <Clock size={17} aria-hidden="true" />
                )}
                Refresh
              </Button>
            </CardHeader>

            <CardBody>
              {savedLoading ? (
                <div className="rounded-md border border-dashed border-border bg-slate-50 px-4 py-8 text-center">
                  <p className="text-sm font-medium text-foreground">
                    Loading saved analyses
                  </p>
                </div>
              ) : savedError ? (
                <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {savedError}
                </div>
              ) : savedAnalyses.length === 0 ? (
                <div className="rounded-md border border-dashed border-border bg-slate-50 px-4 py-8 text-center">
                  <p className="text-sm font-medium text-foreground">
                    No saved agent analyses yet
                  </p>
                  <p className="mt-1 text-sm text-muted">
                    Run an analysis to persist it locally.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {savedAnalyses.map((analysis) => (
                    <button
                      key={analysis.id}
                      type="button"
                      onClick={() => handleOpenSavedAnalysis(analysis.id)}
                      className="w-full rounded-lg border border-border bg-slate-50 p-4 text-left transition hover:bg-slate-100"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-slate-900">
                            {analysis.title}
                          </p>
                          <p className="mt-1 text-xs text-muted">
                            {analysis.status} · {formatTimestamp(analysis.created_at)}
                          </p>
                        </div>

                        {openingResultId === analysis.id ? (
                          <Loader2
                            className="shrink-0 animate-spin text-primary"
                            size={17}
                            aria-hidden="true"
                          />
                        ) : (
                          <FileText
                            className="shrink-0 text-muted"
                            size={17}
                            aria-hidden="true"
                          />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>
        </div>

        <AnalysisResultCard result={result} />
      </div>
    </div>
  );
}

function AnalysisResultCard({ result }) {
  if (!result) {
    return (
      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold">Agent output</h2>
          <p className="mt-1 text-sm text-muted">
            Results will show evidence, calculations, and executed tools.
          </p>
        </CardHeader>

        <CardBody>
          <div className="rounded-lg border border-dashed border-border bg-slate-50 px-5 py-10 text-center">
            <BrainCircuit
              className="mx-auto text-primary"
              size={28}
              aria-hidden="true"
            />
            <p className="mt-3 text-sm font-medium text-slate-800">
              Run a bounded financial analysis.
            </p>
            <p className="mt-1 text-sm text-muted">
              FinAgent will show the actual tools executed and source pages.
            </p>
          </div>
        </CardBody>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-base font-semibold">Agent output</h2>
            <p className="mt-1 text-sm text-muted">
              {result.provider || "Agent"} {result.model ? `· ${result.model}` : ""}
            </p>
          </div>

          <span
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              result.status === "insufficient_evidence" ||
              result.configured === false
                ? "bg-amber-100 text-amber-800"
                : "bg-emerald-100 text-emerald-800"
            }`}
          >
            {result.status ?? "analysis"}
          </span>
        </CardHeader>

        <CardBody className="space-y-5">
          <div>
            <p className="text-xs font-medium uppercase text-muted">
              Question
            </p>
            <p className="mt-1 text-sm font-semibold text-slate-900">
              {result.question}
            </p>
          </div>

          <div className="rounded-lg border border-border bg-slate-50 px-5 py-5">
            <p className="whitespace-pre-wrap text-sm leading-7 text-slate-800">
              {result.answer || result.message}
            </p>
          </div>

          {result.source_pages?.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {result.source_pages.map((page) => (
                <span
                  key={page}
                  className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700"
                >
                  Source: Page {page}
                </span>
              ))}
            </div>
          )}

          {result.disclaimer && (
            <p className="text-xs text-muted">{result.disclaimer}</p>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-md bg-slate-100 text-primary">
            <Calculator size={18} aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-base font-semibold">Calculations</h2>
            <p className="mt-1 text-sm text-muted">
              Verified outputs from approved financial tools.
            </p>
          </div>
        </CardHeader>

        <CardBody>
          {result.calculations?.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {result.calculations.map((calculation, index) => (
                <div
                  key={`${calculation.metric}-${index}`}
                  className="rounded-lg border border-border bg-slate-50 p-4"
                >
                  <p className="text-sm font-semibold text-slate-900">
                    {calculation.metric?.replaceAll("_", " ") ?? "Calculation"}
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-primary">
                    {getCalculationValue(calculation)}
                  </p>
                  <p className="mt-2 text-xs text-muted">
                    {calculation.formula}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-md border border-dashed border-border bg-slate-50 px-4 py-6 text-center text-sm text-muted">
              No supported calculation was executed for this question.
            </p>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-md bg-slate-100 text-primary">
            <BarChart3 size={18} aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-base font-semibold">Tools executed</h2>
            <p className="mt-1 text-sm text-muted">
              Actual registered tools called by the backend.
            </p>
          </div>
        </CardHeader>

        <CardBody className="space-y-3">
          {result.tools_executed?.map((tool, index) => (
            <div
              key={`${tool.tool}-${index}`}
              className="rounded-lg border border-border bg-slate-50 p-4"
            >
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-slate-900">
                  {tool.tool}
                </p>
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${
                    tool.status === "success"
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-red-100 text-red-700"
                  }`}
                >
                  {tool.status === "success" ? (
                    <CheckCircle2 size={13} aria-hidden="true" />
                  ) : (
                    <XCircle size={13} aria-hidden="true" />
                  )}
                  {tool.status}
                </span>
              </div>

              {tool.error && (
                <p className="mt-2 text-sm text-red-700">{tool.error}</p>
              )}

              {tool.output?.source_count > 0 && (
                <p className="mt-2 text-sm text-muted">
                  Retrieved {tool.output.source_count} passages from pages{" "}
                  {tool.output.source_pages?.join(", ")}.
                </p>
              )}
            </div>
          ))}

          {result.limitations?.length > 0 && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3">
              <p className="text-sm font-semibold text-amber-900">
                Limitations
              </p>
              <ul className="mt-2 space-y-1 text-sm text-amber-800">
                {result.limitations.map((limitation, index) => (
                  <li key={`${limitation}-${index}`}>{limitation}</li>
                ))}
              </ul>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div>
      <p className="text-xs uppercase text-muted">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-900">{value}</p>
    </div>
  );
}
