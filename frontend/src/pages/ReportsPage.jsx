import { useEffect, useState } from "react";
import {
  ArrowUpRight,
  BarChart3,
  Calculator,
  CheckCircle2,
  Clock,
  FileArchive,
  FileText,
  Loader2,
  XCircle,
} from "lucide-react";

import { getSavedResult, getSavedResults } from "../lib/api.js";
import { Button } from "../components/ui/Button.jsx";
import { Card, CardBody, CardHeader } from "../components/ui/Card.jsx";

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

function getResultTitle(result) {
  return (
    result.title ||
    result.filename ||
    result.document_filename ||
    `${result.result_type ?? "Saved result"}`
  );
}

function getDocumentFilename(result, documents) {
  return (
    result.document_filename ||
    result.filename ||
    documents.find((document) => document.document_id === result.document_id)?.filename ||
    null
  );
}

function getResultSummary(result) {
  const payload = result.payload ?? result.result ?? result;

  if (typeof payload === "string") {
    return payload;
  }

  return (
    payload.summary ||
    payload.answer ||
    payload.message ||
    result.summary ||
    "No result text was returned for this saved item."
  );
}

function getResultPayload(result) {
  return result?.payload ?? result;
}

function formatNumber(value) {
  return Number(value ?? 0).toLocaleString();
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

function renderResultText(text) {
  if (!text) {
    return null;
  }

  return String(text)
    .split("\n")
    .map((line, index) => {
      const trimmed = line.trim();

      if (!trimmed) {
        return <div key={index} className="h-3" />;
      }

      if (trimmed.startsWith("#")) {
        return (
          <h3
            key={index}
            className="mt-4 text-sm font-semibold text-slate-900 first:mt-0"
          >
            {trimmed.replace(/^#+\s*/, "")}
          </h3>
        );
      }

      if (trimmed.startsWith("- ")) {
        return (
          <div
            key={index}
            className="flex gap-2 text-sm leading-7 text-slate-700"
          >
            <span className="mt-3 size-1.5 shrink-0 rounded-full bg-primary" />
            <span>{trimmed.replace(/^-\s+/, "")}</span>
          </div>
        );
      }

      return (
        <p key={index} className="text-sm leading-7 text-slate-700">
          {trimmed}
        </p>
      );
    });
}

export function ReportsPage({ recentDocuments = [] }) {
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedResult, setSelectedResult] = useState(null);
  const [selectedLoading, setSelectedLoading] = useState(false);
  const [selectedError, setSelectedError] = useState("");

  async function loadResults() {
    setIsLoading(true);
    setError("");

    try {
      const payload = await getSavedResults();
      setResults(payload.results ?? []);
    } catch (resultsError) {
      setError(resultsError.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleOpenResult(resultId) {
    if (!resultId || selectedLoading) {
      return;
    }

    setSelectedLoading(true);
    setSelectedError("");
    setSelectedResult(null);

    try {
      const payload = await getSavedResult(resultId);
      setSelectedResult(payload.result ?? payload);
    } catch (resultError) {
      setSelectedError(resultError.message);
    } finally {
      setSelectedLoading(false);
    }
  }

  useEffect(() => {
    loadResults();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-primary">Reports</p>

        <h1 className="mt-2 text-3xl font-semibold">
          Saved analysis results
        </h1>

        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Review persisted summaries and analysis outputs saved by the backend.
          This page reads existing results only; report generation remains a
          later phase.
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-md bg-slate-100 text-primary">
                <FileArchive size={20} aria-hidden="true" />
              </div>

              <div>
                <h2 className="text-base font-semibold">Saved results</h2>
                <p className="mt-1 text-sm text-muted">
                  Summaries and analysis records from SQLite.
                </p>
              </div>
            </div>

            <Button
              variant="secondary"
              onClick={loadResults}
              disabled={isLoading}
              className="w-full sm:w-auto"
            >
              {isLoading ? (
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
            {isLoading ? (
              <div className="rounded-md border border-dashed border-border bg-slate-50 px-4 py-8 text-center">
                <p className="text-sm font-medium text-foreground">
                  Loading saved results
                </p>
                <p className="mt-1 text-sm text-muted">
                  Reading persisted analysis history from the backend.
                </p>
              </div>
            ) : error ? (
              <div className="flex items-start gap-3 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                <XCircle
                  className="mt-0.5 shrink-0"
                  size={18}
                  aria-hidden="true"
                />
                <span>{error}</span>
              </div>
            ) : results.length === 0 ? (
              <div className="rounded-md border border-dashed border-border bg-slate-50 px-4 py-8 text-center">
                <p className="text-sm font-medium text-foreground">
                  No saved results yet
                </p>
                <p className="mt-1 text-sm text-muted">
                  Generate a document summary to persist a result here.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
              {results.map((result) => {
                const resultId = result.result_id ?? result.id;
                const isSelected =
                  selectedResult &&
                  (selectedResult.result_id ?? selectedResult.id) === resultId;
                const documentFilename = getDocumentFilename(result, recentDocuments);

                  return (
                    <button
                      key={resultId}
                      type="button"
                      onClick={() => handleOpenResult(resultId)}
                      className={`w-full rounded-lg border p-4 text-left transition ${
                        isSelected
                          ? "border-primary bg-emerald-50"
                          : "border-border bg-slate-50 hover:bg-slate-100"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-slate-900" title={getResultTitle(result)}>
                            {getResultTitle(result)}
                          </p>

                          <p className="truncate text-xs text-muted" title={documentFilename ?? ""}>
                            {documentFilename ?? `${result.result_type ?? "analysis"} · ${result.status ?? "saved"}`}
                          </p>
                        </div>

                        <ArrowUpRight
                          className="shrink-0 text-muted"
                          size={17}
                          aria-hidden="true"
                        />
                      </div>

                      <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted">
                        <span className="inline-flex items-center gap-1">
                          <Clock size={14} aria-hidden="true" />
                          {formatTimestamp(result.created_at)}
                        </span>

                        {documentFilename && (
                          <span className="inline-flex items-center gap-1">
                            <FileText size={14} aria-hidden="true" />
                            <span className="max-w-44 truncate" title={documentFilename}>{documentFilename}</span>
                          </span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-base font-semibold">Result detail</h2>
            <p className="mt-1 text-sm text-muted">
              Open a saved item to review the persisted output.
            </p>
          </CardHeader>

          <CardBody>
            {selectedLoading ? (
              <div className="flex items-center gap-3 rounded-md border border-border bg-slate-50 px-4 py-4 text-sm text-muted">
                <Loader2
                  className="animate-spin text-primary"
                  size={18}
                  aria-hidden="true"
                />

                <span>Loading saved result...</span>
              </div>
            ) : selectedError ? (
              <div className="flex items-start gap-3 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                <XCircle
                  className="mt-0.5 shrink-0"
                  size={18}
                  aria-hidden="true"
                />
                <span>{selectedError}</span>
              </div>
            ) : selectedResult ? (
              <ResultDetail result={selectedResult} />
            ) : (
              <div className="rounded-lg border border-dashed border-border bg-slate-50 px-5 py-8 text-center">
                <FileArchive
                  className="mx-auto text-primary"
                  size={24}
                  aria-hidden="true"
                />

                <p className="mt-3 text-sm font-medium text-slate-800">
                  Select a saved result.
                </p>

                <p className="mt-1 text-sm text-muted">
                  Persisted summaries and results will open here.
                </p>
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function ResultDetail({ result }) {
  const payload = getResultPayload(result);
  const resultType = result.result_type ?? payload?.result_type;

  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm font-semibold text-slate-900">
          {getResultTitle(result)}
        </p>

        <p className="mt-1 text-xs text-muted">
          {result.result_type ?? "analysis"} · {result.status ?? "saved"} ·{" "}
          {formatTimestamp(result.created_at)}
        </p>
      </div>

      {resultType === "agent_analysis" ? (
        <AgentAnalysisDetail payload={payload} />
      ) : (
        <SummaryDetail result={result} />
      )}
    </div>
  );
}

function SummaryDetail({ result }) {
  const summary = getResultSummary(result);

  return (
    <div className="rounded-lg border border-border bg-slate-50 px-5 py-5">
      {summary ? (
        renderResultText(summary)
      ) : (
        <p className="text-sm text-muted">
          No summary text is available for this saved result.
        </p>
      )}
    </div>
  );
}

function AgentAnalysisDetail({ payload }) {
  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-border bg-slate-50 px-5 py-5">
        {payload?.question && (
          <div className="mb-4">
            <p className="text-xs font-medium uppercase text-muted">
              Question
            </p>
            <p className="mt-1 text-sm font-semibold text-slate-900">
              {payload.question}
            </p>
          </div>
        )}

        {payload?.answer || payload?.message ? (
          <p className="whitespace-pre-wrap text-sm leading-7 text-slate-800">
            {payload.answer || payload.message}
          </p>
        ) : (
          <p className="text-sm text-muted">
            No saved answer text is available for this analysis.
          </p>
        )}

        {payload?.disclaimer && (
          <p className="mt-4 text-xs text-muted">{payload.disclaimer}</p>
        )}
      </div>

      {payload?.source_pages?.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {payload.source_pages.map((page) => (
            <span
              key={page}
              className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700"
            >
              Source: Page {page}
            </span>
          ))}
        </div>
      )}

      {payload?.findings?.length > 0 && (
        <SectionCard
          icon={BarChart3}
          title="Findings"
          description="Saved findings from the completed analysis."
        >
          <ul className="space-y-2 text-sm leading-6 text-slate-700">
            {payload.findings.map((finding, index) => (
              <li key={`${finding}-${index}`}>{finding}</li>
            ))}
          </ul>
        </SectionCard>
      )}

      {payload?.calculations?.length > 0 && (
        <SectionCard
          icon={Calculator}
          title="Calculations"
          description="Verified outputs from approved financial tools."
        >
          <div className="grid gap-3 sm:grid-cols-2">
            {payload.calculations.map((calculation, index) => (
              <div
                key={`${calculation.metric}-${index}`}
                className="rounded-lg border border-border bg-panel p-4"
              >
                <p className="text-sm font-semibold text-slate-900">
                  {calculation.metric?.replaceAll("_", " ") ?? "Calculation"}
                </p>
                <p className="mt-2 text-2xl font-semibold text-primary">
                  {getCalculationValue(calculation)}
                </p>
                {calculation.formula && (
                  <p className="mt-2 text-xs text-muted">
                    {calculation.formula}
                  </p>
                )}
                {calculation.evidence && (
                  <p className="mt-2 text-xs leading-5 text-muted">
                    {calculation.evidence}
                  </p>
                )}
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {payload?.tools_executed?.length > 0 && (
        <SectionCard
          icon={BarChart3}
          title="Tools executed"
          description="Actual tool trace persisted with this result."
        >
          <div className="space-y-3">
            {payload.tools_executed.map((tool, index) => (
              <div
                key={`${tool.tool}-${index}`}
                className="rounded-lg border border-border bg-panel p-4"
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
          </div>
        </SectionCard>
      )}

      {payload?.limitations?.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3">
          <p className="text-sm font-semibold text-amber-900">Limitations</p>
          <ul className="mt-2 space-y-1 text-sm text-amber-800">
            {payload.limitations.map((limitation, index) => (
              <li key={`${limitation}-${index}`}>{limitation}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function SectionCard({ icon: Icon, title, description, children }) {
  return (
    <div className="rounded-lg border border-border bg-slate-50 p-4">
      <div className="mb-3 flex items-center gap-3">
        <div className="flex size-9 items-center justify-center rounded-md bg-panel text-primary">
          <Icon size={18} aria-hidden="true" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
          <p className="mt-1 text-xs text-muted">{description}</p>
        </div>
      </div>
      {children}
    </div>
  );
}
