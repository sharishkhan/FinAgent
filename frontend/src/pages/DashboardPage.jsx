import { ArrowUpRight, FileText, FolderOpen, PieChart, Upload } from "lucide-react";

import { Button } from "../components/ui/Button.jsx";
import { Card, CardBody, CardHeader } from "../components/ui/Card.jsx";
import { MetricCard } from "../components/ui/MetricCard.jsx";

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

  function getResearchTitle(result) {
    return result.title || result.document_filename || result.filename || "Saved research";
  }

  return (
    <div className="space-y-5">
      <section className="flex flex-col gap-4 border-b border-border pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium text-primary">Workspace overview</p>
          <p className="mt-1 text-sm text-muted">Recent documents, research, and saved analysis outputs.</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button onClick={() => onNavigate("documents")} className="w-full sm:w-auto">
            <Upload size={17} aria-hidden="true" />
            Upload Document
          </Button>
          <Button variant="secondary" onClick={() => onNavigate("analysis")} className="w-full sm:w-auto">
            <PieChart size={17} aria-hidden="true" />
            Run Analysis
          </Button>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {stats.map((stat) => {
          return (
            <MetricCard
              key={stat.label}
              label={stat.label}
              value={resultsLoading && stat.label !== "Documents" ? "..." : stat.value}
              icon={stat.icon}
            />
          );
        })}
      </section>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold">Recent documents</h2>
            <p className="mt-1 text-sm text-muted">Latest uploaded financial documents.</p>
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
                <div key={document.document_id ?? document.filename} className="flex min-w-0 flex-col gap-2 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="truncate font-medium" title={document.filename ?? "Untitled document"}>{document.filename ?? "Untitled document"}</p>
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
            <h2 className="text-base font-semibold">Recent research</h2>
            <p className="mt-1 text-sm text-muted">Saved summaries and analysis.</p>
          </div>
          <Button variant="ghost" onClick={() => onNavigate("reports")} aria-label="Open history">
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
                <div key={result.id} className="flex min-w-0 flex-col gap-2 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="truncate font-medium" title={getResearchTitle(result)}>{getResearchTitle(result)}</p>
                    <p className="truncate text-sm text-muted" title={result.document_filename ?? result.filename ?? ""}>
                      {result.document_filename ?? result.filename ?? `${result.result_type} · ${result.status}`}
                    </p>
                  </div>
                  <p className="text-sm text-muted">{new Date(result.created_at).toLocaleString()}</p>
                </div>
              ))}
            </div>
          )}
        </CardBody>
        </Card>
      </div>
    </div>
  );
}
