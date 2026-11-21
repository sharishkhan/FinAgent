import { useEffect, useRef, useState } from "react";
import {
  BarChart3,
  CheckCircle2,
  Clock,
  Database,
  FileText,
  History,
  Loader2,
  Sparkles,
  UploadCloud,
  XCircle,
} from "lucide-react";

import {
  generateSummary,
  uploadDocument,
} from "../lib/api.js";
import { Button } from "../components/ui/Button.jsx";
import { Card, CardBody, CardHeader } from "../components/ui/Card.jsx";

function formatNumber(value) {
  return Number(value ?? 0).toLocaleString();
}

function renderSummary(text) {
  if (!text) {
    return null;
  }

  return text.split("\n").map((line, index) => {
    const trimmed = line.trim();

    if (!trimmed) {
      return <div key={index} className="h-3" />;
    }

    if (trimmed.startsWith("## ")) {
      return (
        <h3
          key={index}
          className="mt-5 border-b border-border pb-2 text-base font-semibold text-slate-900 first:mt-0"
        >
          {trimmed.replace(/^##\s+/, "")}
        </h3>
      );
    }

    if (trimmed.startsWith("# ")) {
      return (
        <h2
          key={index}
          className="mt-5 text-lg font-semibold text-slate-900 first:mt-0"
        >
          {trimmed.replace(/^#\s+/, "")}
        </h2>
      );
    }

    if (trimmed.startsWith("### ")) {
      return (
        <h4
          key={index}
          className="mt-4 text-sm font-semibold text-slate-900"
        >
          {trimmed.replace(/^###\s+/, "")}
        </h4>
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

function normalizeSavedDocument(document) {
  return {
    ...document,
    success: true,
    status: "processed",
    pages: document.pages ?? 0,
    words: document.words ?? 0,
    characters: document.characters ?? 0,
    characters_extracted: document.characters ?? 0,
    text_pages: document.text_pages ?? document.pages ?? 0,
    low_text_pages: document.low_text_pages ?? [],
    page_statistics: document.page_statistics ?? [],
    financial_topics: document.financial_topics ?? [],
    preview: document.preview ?? "",
  };
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

export function DocumentsPage({
  recentDocuments,
  documentsLoading,
  documentsError,
  onDocumentProcessed,
  onRefreshDocuments,
  onRefreshResults,
  onNavigate,
}) {
  const inputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [processingStage, setProcessingStage] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState(null);
  const [summaryError, setSummaryError] = useState("");
  const [isSummarizing, setIsSummarizing] = useState(false);

  function selectFile(file) {
    setResult(null);
    setError("");

    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (
      file.type !== "application/pdf" &&
      !file.name.toLowerCase().endsWith(".pdf")
    ) {
      setSelectedFile(null);
      setError("Please choose a PDF file.");
      return;
    }

    setSelectedFile(file);
  }

  async function handleUpload() {
    if (!selectedFile) {
      setError("Select a PDF before uploading.");
      return;
    }

    setIsUploading(true);
    setProcessingStage("Uploading document and extracting text...");
    setError("");
    setResult(null);
    setSummary(null);
    setSummaryError("");

    let stageTimer;

    try {
      stageTimer = window.setTimeout(() => {
        setProcessingStage(
          "Analyzing document structure and financial topics..."
        );
      }, 500);

      const payload = await uploadDocument(selectedFile);

      setResult(payload);
      onDocumentProcessed(payload);
      onRefreshDocuments?.();
      setProcessingStage("Processing complete");
    } catch (uploadError) {
      setError(uploadError.message);
      setProcessingStage("");
    } finally {
      if (stageTimer) {
        window.clearTimeout(stageTimer);
      }

      setIsUploading(false);
    }
  }

  async function handleGenerateSummary() {
    if (!result?.document_id) {
      return;
    }

    setIsSummarizing(true);
    setSummary(null);
    setSummaryError("");

    try {
      const payload = await generateSummary(result.document_id);

      if (payload.configured === false) {
        setSummaryError(payload.message);
      } else {
        setSummary(payload);
        onRefreshResults?.();
      }
    } catch (summaryRequestError) {
      setSummaryError(summaryRequestError.message);
    } finally {
      setIsSummarizing(false);
    }
  }

  function handleOpenSavedDocument(document) {
    const normalizedDocument = normalizeSavedDocument(document);
    setResult(normalizedDocument);
    setProcessingStage("");
    setError("");
    setSummary(null);
    setSummaryError("");
  }

  useEffect(() => {
    if (!result && recentDocuments.length > 0) {
      handleOpenSavedDocument(recentDocuments[0]);
    }
  }, [recentDocuments, result]);

  const topicMax = Math.max(
    ...(result?.financial_topics ?? []).map((topic) => topic.count),
    1
  );

  const textCoverage = result?.pages
    ? Math.round((result.text_pages / result.pages) * 100)
    : 0;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-primary">Documents</p>

        <h1 className="mt-2 text-3xl font-semibold">
          Financial Document Intelligence
        </h1>

        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Upload a PDF to extract text, calculate document statistics, and
          detect financial topics with local processing.
        </p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold">Document intake</h2>

          <p className="mt-1 text-sm text-muted">
            Select one PDF for text extraction.
          </p>
        </CardHeader>

        <CardBody className="space-y-5">
          <div
            className={`flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition ${
              isDragging
                ? "border-primary bg-emerald-50"
                : "border-border bg-slate-50 hover:bg-slate-100"
            }`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => {
              event.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setIsDragging(false);
              selectFile(event.dataTransfer.files?.[0]);
            }}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                inputRef.current?.click();
              }
            }}
          >
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf,.pdf"
              className="sr-only"
              onChange={(event) => selectFile(event.target.files?.[0])}
            />

            <div className="mb-4 flex size-14 items-center justify-center rounded-md bg-panel text-primary shadow-sm">
              <FileText size={28} aria-hidden="true" />
            </div>

            <p className="text-base font-semibold">
              {selectedFile
                ? selectedFile.name
                : "Drop a PDF here or choose a file"}
            </p>

            <p className="mt-2 max-w-lg text-sm leading-6 text-muted">
              PDF only. The backend processes a temporary copy, extracts text
              with PyMuPDF, and does not send document contents to external
              APIs.
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-h-10 items-center gap-2 text-sm text-muted">
              <FileText size={17} aria-hidden="true" />

              {selectedFile
                ? `${(selectedFile.size / 1024 / 1024).toFixed(2)} MB selected`
                : "No file selected"}
            </div>

            <Button
              onClick={handleUpload}
              disabled={!selectedFile || isUploading}
              className="w-full sm:w-auto"
            >
              {isUploading ? (
                <Loader2
                  className="animate-spin"
                  size={17}
                  aria-hidden="true"
                />
              ) : (
                <UploadCloud size={17} aria-hidden="true" />
              )}

              {isUploading ? "Processing" : "Upload Document"}
            </Button>
          </div>

          {processingStage && (
            <div className="flex items-center gap-3 rounded-md border border-border bg-slate-50 px-4 py-3 text-sm text-muted">
              {isUploading ? (
                <Loader2
                  className="animate-spin text-primary"
                  size={18}
                  aria-hidden="true"
                />
              ) : (
                <CheckCircle2
                  className="text-primary"
                  size={18}
                  aria-hidden="true"
                />
              )}

              <span>{processingStage}</span>
            </div>
          )}

          {error && (
            <div className="flex items-start gap-3 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <XCircle
                className="mt-0.5 shrink-0"
                size={18}
                aria-hidden="true"
              />

              <span>{error}</span>
            </div>
          )}

          {result && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
              <div className="flex items-center gap-2 text-emerald-800">
                <CheckCircle2 size={18} aria-hidden="true" />

                <p className="font-medium">
                  Document intelligence complete
                </p>
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <div className="flex size-9 items-center justify-center rounded-md bg-slate-100 text-primary">
                <Database size={18} aria-hidden="true" />
              </div>

              <h2 className="text-base font-semibold">Saved documents</h2>
            </div>

            <p className="mt-2 text-sm text-muted">
              Persisted documents restored from the local SQLite database.
            </p>
          </div>

          <Button
            variant="secondary"
            onClick={onRefreshDocuments}
            disabled={documentsLoading}
            className="w-full sm:w-auto"
          >
            {documentsLoading ? (
              <Loader2
                className="animate-spin"
                size={17}
                aria-hidden="true"
              />
            ) : (
              <History size={17} aria-hidden="true" />
            )}
            Refresh
          </Button>
        </CardHeader>

        <CardBody>
          {documentsLoading ? (
            <div className="rounded-md border border-dashed border-border bg-slate-50 px-4 py-8 text-center">
              <p className="text-sm font-medium text-foreground">
                Loading saved documents
              </p>
              <p className="mt-1 text-sm text-muted">
                Reading persisted document metadata from the backend.
              </p>
            </div>
          ) : documentsError ? (
            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-4 text-sm text-red-700">
              {documentsError}
            </div>
          ) : recentDocuments.length === 0 ? (
            <div className="rounded-md border border-dashed border-border bg-slate-50 px-4 py-8 text-center">
              <p className="text-sm font-medium text-foreground">
                No saved documents yet
              </p>
              <p className="mt-1 text-sm text-muted">
                Upload a PDF to persist it for later sessions.
              </p>
            </div>
          ) : (
            <div className="grid gap-3 lg:grid-cols-2">
              {recentDocuments.map((document) => {
                const isSelected = result?.document_id === document.document_id;

                return (
                  <button
                    key={document.document_id}
                    type="button"
                    onClick={() => handleOpenSavedDocument(document)}
                    className={`rounded-lg border p-4 text-left transition ${
                      isSelected
                        ? "border-primary bg-emerald-50"
                        : "border-border bg-slate-50 hover:bg-slate-100"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-slate-900" title={document.filename}>
                          {document.filename}
                        </p>
                        <p className="mt-1 text-xs text-muted">
                          {formatNumber(document.pages)} pages ·{" "}
                          {formatNumber(document.words)} words
                        </p>
                      </div>

                      <span
                        className={`rounded-full px-2 py-1 text-xs font-medium ${
                          isSelected
                            ? "bg-panel text-primary"
                            : "bg-panel text-muted"
                        }`}
                      >
                        {isSelected ? "Open" : "Open"}
                      </span>
                    </div>

                    <p className="mt-3 max-h-10 overflow-hidden text-xs leading-5 text-muted">
                      {document.preview || "No preview available."}
                    </p>

                    <div className="mt-3 flex items-center gap-2 text-xs text-muted">
                      <Clock size={14} aria-hidden="true" />
                      {formatTimestamp(document.processed_at)}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </CardBody>
      </Card>

      {result && (
        <>
          {/* Main document analysis area */}
          <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
            {/* Left column */}
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <h2 className="text-base font-semibold">
                    Document Overview
                  </h2>

                  <p className="mt-1 text-sm text-muted">
                    {result.preview || "No preview available."}
                  </p>
                </CardHeader>

                <CardBody>
                  <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    <Metric label="Filename" value={result.filename} />
                    <Metric
                      label="Pages"
                      value={formatNumber(result.pages)}
                    />
                    <Metric
                      label="Words"
                      value={formatNumber(result.words)}
                    />
                    <Metric
                      label="Characters"
                      value={formatNumber(result.characters)}
                    />
                    <Metric
                      label="Text Coverage"
                      value={`${textCoverage}%`}
                    />
                    <Metric
                      label="Document ID"
                      value={result.document_id}
                    />
                  </dl>

                  {result.low_text_pages?.length > 0 && (
                    <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                      Low-text pages detected:{" "}
                      {result.low_text_pages.join(", ")}
                    </div>
                  )}
                </CardBody>
              </Card>

              <Card>
                <CardHeader>
                  <h2 className="text-base font-semibold">
                    Page Analysis
                  </h2>

                  <p className="mt-1 text-sm text-muted">
                    Page-level extraction statistics from PyMuPDF.
                  </p>
                </CardHeader>

                <CardBody>
                  <div className="max-h-80 overflow-auto rounded-md border border-border">
                    <table className="w-full text-left text-sm">
                      <thead className="sticky top-0 bg-slate-50 text-xs uppercase text-muted">
                        <tr>
                          <th className="px-4 py-3 font-medium">Page</th>
                          <th className="px-4 py-3 font-medium">Words</th>
                          <th className="px-4 py-3 font-medium">
                            Characters
                          </th>
                          <th className="px-4 py-3 font-medium">Status</th>
                        </tr>
                      </thead>

                      <tbody className="divide-y divide-border bg-panel">
                        {result.page_statistics.length > 0 ? (
                          result.page_statistics.map((page) => (
                            <tr key={page.page}>
                              <td className="px-4 py-3 font-medium">
                                Page {page.page}
                              </td>

                              <td className="px-4 py-3">
                                {formatNumber(page.words)}
                              </td>

                              <td className="px-4 py-3">
                                {formatNumber(page.characters)}
                              </td>

                              <td className="px-4 py-3">
                                <span
                                  className={`rounded-full px-2 py-1 text-xs font-medium ${
                                    page.low_text
                                      ? "bg-amber-100 text-amber-800"
                                      : "bg-emerald-100 text-emerald-800"
                                  }`}
                                >
                                  {page.low_text
                                    ? "Low text"
                                    : "Text found"}
                                </span>
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td
                              colSpan={4}
                              className="px-4 py-8 text-center text-sm text-muted"
                            >
                              Detailed page analysis is not included in this
                              saved document listing.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </CardBody>
              </Card>
            </div>

            {/* Right column */}
            <div className="space-y-6">
              <Card>
                <CardHeader className="flex items-center gap-3">
                  <div className="flex size-10 items-center justify-center rounded-md bg-slate-100 text-primary">
                    <BarChart3 size={20} aria-hidden="true" />
                  </div>

                  <div>
                    <h2 className="text-base font-semibold">
                      Detected Financial Topics
                    </h2>

                    <p className="mt-1 text-sm text-muted">
                      Local keyword counts, not an importance ranking.
                    </p>
                  </div>
                </CardHeader>

                <CardBody className="space-y-3">
                  {result.financial_topics.length === 0 ? (
                    <p className="rounded-md border border-dashed border-border bg-slate-50 px-4 py-6 text-center text-sm text-muted">
                      No configured financial topics were detected.
                    </p>
                  ) : (
                    result.financial_topics.map((topic) => (
                      <div key={topic.term} className="space-y-1">
                        <div className="flex items-center justify-between gap-3 text-sm">
                          <span className="font-medium">
                            {topic.term}
                          </span>

                          <span className="text-muted">
                            {formatNumber(topic.count)}
                          </span>
                        </div>

                        <div className="h-2 rounded-full bg-slate-100">
                          <div
                            className="h-2 rounded-full bg-primary"
                            style={{
                              width: `${Math.max(
                                (topic.count / topicMax) * 100,
                                8
                              )}%`,
                            }}
                          />
                        </div>
                      </div>
                    ))
                  )}
                </CardBody>
              </Card>
            </div>
          </div>
          <Card>
            <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-base font-semibold">Ask about this document</h2>
                <p className="mt-2 text-sm leading-6 text-muted">
                  Ask questions and see the exact pages behind each answer.
                </p>
              </div>

              <Button onClick={() => onNavigate?.("research", result.document_id)} className="w-full sm:w-auto">
                Open Ask
              </Button>
            </CardHeader>
          </Card>

          {/* Full-width AI Summary */}
          <Card>
            <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <div className="flex size-9 items-center justify-center rounded-md bg-slate-100 text-primary">
                    <Sparkles size={18} aria-hidden="true" />
                  </div>

                  <h2 className="text-base font-semibold">
                    AI Financial Summary
                  </h2>
                </div>

                <p className="mt-2 text-sm text-muted">
                  AI-generated analysis of the uploaded financial document.
                </p>
              </div>

              <Button
                onClick={handleGenerateSummary}
                disabled={isSummarizing}
                variant="secondary"
                className="w-full sm:w-auto"
              >
                {isSummarizing ? (
                  <Loader2
                    className="animate-spin"
                    size={17}
                    aria-hidden="true"
                  />
                ) : (
                  <Sparkles size={17} aria-hidden="true" />
                )}

                {isSummarizing
                  ? "Analyzing"
                  : "Generate AI Summary"}
              </Button>
            </CardHeader>

            <CardBody>
              {isSummarizing && (
                <div className="flex items-center gap-3 rounded-md border border-border bg-slate-50 px-4 py-4 text-sm text-muted">
                  <Loader2
                    className="animate-spin text-primary"
                    size={18}
                    aria-hidden="true"
                  />

                  <span>
                    Gemini is analyzing the financial document...
                  </span>
                </div>
              )}

              {summaryError && (
                <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  {summaryError}
                </div>
              )}

              {summary && (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="rounded-full bg-emerald-50 px-3 py-1 font-medium text-emerald-700">
                      {summary.provider || "AI"}
                    </span>

                    {summary.model && (
                      <span className="rounded-full bg-slate-100 px-3 py-1 text-muted">
                        {summary.model}
                      </span>
                    )}

                    <span className="text-muted">
                      {summary.disclaimer}
                    </span>
                  </div>

                  <div className="rounded-lg border border-border bg-slate-50 px-5 py-5 sm:px-6">
                    <div className="max-w-none">
                      {renderSummary(summary.summary)}
                    </div>
                  </div>
                </div>
              )}

              {!isSummarizing && !summaryError && !summary && (
                <div className="rounded-lg border border-dashed border-border bg-slate-50 px-5 py-8 text-center">
                  <Sparkles
                    className="mx-auto text-primary"
                    size={24}
                    aria-hidden="true"
                  />

                  <p className="mt-3 text-sm font-medium text-slate-800">
                    Generate an AI summary of this financial document.
                  </p>

                  <p className="mt-1 text-sm text-muted">
                    The summary is generated from the uploaded document and
                    is not investment advice.
                  </p>
                </div>
              )}
            </CardBody>
          </Card>
        </>
      )}
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-md border border-border bg-slate-50 p-3">
      <dt className="text-xs uppercase text-muted">{label}</dt>

      <dd className="mt-1 break-words text-sm font-semibold">
        {value}
      </dd>
    </div>
  );
}
