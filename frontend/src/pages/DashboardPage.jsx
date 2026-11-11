import { ArrowUpRight, FileText, FolderOpen, PieChart, Upload } from "lucide-react";

import { Button } from "../components/ui/Button.jsx";
import { Card, CardBody, CardHeader } from "../components/ui/Card.jsx";

export function DashboardPage({
  recentDocuments,
  documentsLoading,
  documentsError,
  savedResults,
  resultsLoading,
  resultsError,
  onNavigate,
}) {
  const documentCount = recentDocuments.length;
  const analysisCount = savedResults.filter(
    (result) => result.result_type === "agent_analysis"
  ).length;
  const summaryCount = savedResults.filter(
    (result) => result.result_type === "summary"
  ).length;
  const stats = [
    { label: "Documents", value: documentCount, icon: FileText },
    { label: "Agent Analyses", value: analysisCount, icon: PieChart },
    { label: "AI Summaries", value: summaryCount, icon: FolderOpen },
  ];

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-border bg-panel px-6 py-7 shadow-soft">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div className="max-w-3xl">
            <p className="mb-2 text-sm font-medium text-primary">Assessment-ready workspace</p>
            <h1 className="text-3xl font-semibold tracking-normal text-foreground">
              Financial document intelligence, RAG, and bounded agent analysis.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
              Upload PDFs, ask source-grounded questions, generate summaries, and run approved financial calculations against persisted document evidence.
            </p>
          </div>
          <Button onClick={() => onNavigate("documents")} className="w-full md:w-auto">
            <Upload size={17} aria-hidden="true" />
            Upload Document
          </Button>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label}>
              <CardBody>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-muted">{stat.label}</p>
                    <p className="mt-2 text-3xl font-semibold">
                      {resultsLoading && stat.label !== "Documents"
                        ? "..."
                        : stat.value}
                    </p>
                  </div>
                  <div className="flex size-10 items-center justify-center rounded-md bg-slate-100 text-primary">
                    <Icon size={20} aria-hidden="true" />
                  </div>
                </div>
              </CardBody>
            </Card>
          );
        })}
      </section>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold">Recent documents</h2>
            <p className="mt-1 text-sm text-muted">Persisted PDF uploads restored from the backend.</p>
          </div>
          <Button variant="ghost" onClick={() => onNavigate("documents")} aria-label="Open documents">
            <ArrowUpRight size={18} aria-hidden="true" />
          </Button>
        </CardHeader>
        <CardBody>
          {documentsLoading ? (
            <div className="rounded-md border border-dashed border-border bg-slate-50 px-4 py-8 text-center">
              <p className="text-sm font-medium text-foreground">Loading saved documents</p>
              <p className="mt-1 text-sm text-muted">Restoring persisted document history from the backend.</p>
            </div>
          ) : documentsError ? (
            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-4 text-sm text-red-700">
              {documentsError}
            </div>
          ) : recentDocuments.length === 0 ? (
            <div className="rounded-md border border-dashed border-border bg-slate-50 px-4 py-8 text-center">
              <p className="text-sm font-medium text-foreground">No documents processed yet</p>
              <p className="mt-1 text-sm text-muted">Upload a PDF to see its extraction summary here.</p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {recentDocuments.map((document) => (
                <div key={document.document_id ?? document.filename} className="flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-medium">{document.filename}</p>
                    <p className="text-sm text-muted">{document.pages} pages · {document.words?.toLocaleString() ?? 0} words</p>
                  </div>
                  <p className="text-sm font-medium text-primary">
                    {((document.characters ?? document.characters_extracted) ?? 0).toLocaleString()} characters
                  </p>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold">Saved outputs</h2>
            <p className="mt-1 text-sm text-muted">Persisted summaries and agent analyses.</p>
          </div>
          <Button variant="ghost" onClick={() => onNavigate("reports")} aria-label="Open reports">
            <ArrowUpRight size={18} aria-hidden="true" />
          </Button>
        </CardHeader>
        <CardBody>
          {resultsLoading ? (
            <div className="rounded-md border border-dashed border-border bg-slate-50 px-4 py-8 text-center">
              <p className="text-sm font-medium text-foreground">Loading saved results</p>
              <p className="mt-1 text-sm text-muted">Restoring analysis history from SQLite.</p>
            </div>
          ) : resultsError ? (
            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-4 text-sm text-red-700">
              {resultsError}
            </div>
          ) : savedResults.length === 0 ? (
            <div className="rounded-md border border-dashed border-border bg-slate-50 px-4 py-8 text-center">
              <p className="text-sm font-medium text-foreground">No saved outputs yet</p>
              <p className="mt-1 text-sm text-muted">Generate a summary or run agent analysis to see results here.</p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {savedResults.slice(0, 5).map((result) => (
                <div key={result.id} className="flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-medium">{result.title}</p>
                    <p className="text-sm text-muted">{result.result_type} · {result.status}</p>
                  </div>
                  <p className="text-sm text-muted">{new Date(result.created_at).toLocaleString()}</p>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
