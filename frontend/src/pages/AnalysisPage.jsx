import { ArrowUpRight, BarChart3, Calculator, Clock, LineChart, Loader2, XCircle } from "lucide-react";

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

export function AnalysisPage({
  savedResults,
  resultsLoading,
  resultsError,
  onNavigate,
}) {
  const agentAnalyses = savedResults.filter(
    (result) => result.result_type === "agent_analysis"
  );
  const summaries = savedResults.filter((result) => result.result_type === "summary");

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-primary">Analysis</p>
        <h1 className="mt-2 text-3xl font-semibold">
          Financial analysis workspace
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
          This page summarizes the analysis capabilities currently implemented:
          bounded agent analysis in Research and persisted results in Reports.
        </p>
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardBody>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted">Agent Analyses</p>
                <p className="mt-2 text-3xl font-semibold">
                  {resultsLoading ? "..." : agentAnalyses.length}
                </p>
              </div>
              <div className="flex size-10 items-center justify-center rounded-md bg-slate-100 text-primary">
                <LineChart size={20} aria-hidden="true" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted">AI Summaries</p>
                <p className="mt-2 text-3xl font-semibold">
                  {resultsLoading ? "..." : summaries.length}
                </p>
              </div>
              <div className="flex size-10 items-center justify-center rounded-md bg-slate-100 text-primary">
                <BarChart3 size={20} aria-hidden="true" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted">Approved Tools</p>
                <p className="mt-2 text-3xl font-semibold">3</p>
              </div>
              <div className="flex size-10 items-center justify-center rounded-md bg-slate-100 text-primary">
                <Calculator size={20} aria-hidden="true" />
              </div>
            </div>
          </CardBody>
        </Card>
      </section>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <CardHeader>
            <h2 className="text-base font-semibold">Available workflow</h2>
            <p className="mt-1 text-sm text-muted">
              Use the implemented agent workflow without adding unsupported analytics.
            </p>
          </CardHeader>
          <CardBody className="space-y-4">
            <div className="rounded-lg border border-border bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-900">
                Bounded agent analysis
              </p>
              <p className="mt-2 text-sm leading-6 text-muted">
                Select a saved PDF, ask a financial analysis question, retrieve
                source passages, execute approved calculations, and persist the
                result.
              </p>
              <Button onClick={() => onNavigate("research")} className="mt-4 w-full sm:w-auto">
                <ArrowUpRight size={17} aria-hidden="true" />
                Open Research
              </Button>
            </div>

            <div className="rounded-lg border border-border bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-900">
                Saved result review
              </p>
              <p className="mt-2 text-sm leading-6 text-muted">
                Reopen persisted AI summaries and agent analyses from the local
                SQLite-backed results history.
              </p>
              <Button
                variant="secondary"
                onClick={() => onNavigate("reports")}
                className="mt-4 w-full sm:w-auto"
              >
                <ArrowUpRight size={17} aria-hidden="true" />
                Open Reports
              </Button>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-base font-semibold">Recent agent analyses</h2>
            <p className="mt-1 text-sm text-muted">
              Existing saved analyses only; no fake charting or simulated data.
            </p>
          </CardHeader>
          <CardBody>
            {resultsLoading ? (
              <div className="flex items-center gap-3 rounded-md border border-border bg-slate-50 px-4 py-4 text-sm text-muted">
                <Loader2 className="animate-spin text-primary" size={18} aria-hidden="true" />
                <span>Loading saved analyses...</span>
              </div>
            ) : resultsError ? (
              <div className="flex items-start gap-3 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                <XCircle className="mt-0.5 shrink-0" size={18} aria-hidden="true" />
                <span>{resultsError}</span>
              </div>
            ) : agentAnalyses.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border bg-slate-50 px-5 py-8 text-center">
                <LineChart className="mx-auto text-primary" size={24} aria-hidden="true" />
                <p className="mt-3 text-sm font-medium text-slate-800">
                  No saved agent analyses yet.
                </p>
                <p className="mt-1 text-sm text-muted">
                  Run an analysis from Research to populate this list.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {agentAnalyses.slice(0, 5).map((analysis) => (
                  <div key={analysis.id} className="rounded-lg border border-border bg-slate-50 p-4">
                    <p className="text-sm font-semibold text-slate-900">
                      {analysis.title}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted">
                      <span>{analysis.status}</span>
                      <span className="inline-flex items-center gap-1">
                        <Clock size={14} aria-hidden="true" />
                        {formatTimestamp(analysis.created_at)}
                      </span>
                    </div>
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
