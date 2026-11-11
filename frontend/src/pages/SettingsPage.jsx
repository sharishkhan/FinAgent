import { CheckCircle2, Database, FileText, Server, Settings, ShieldCheck } from "lucide-react";

import { API_BASE_URL } from "../lib/api.js";
import { Card, CardBody, CardHeader } from "../components/ui/Card.jsx";

function StatusRow({ icon: Icon, label, value, detail }) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-slate-50 p-4 sm:flex-row sm:items-start">
      <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-panel text-primary">
        <Icon size={19} aria-hidden="true" />
      </div>
      <div>
        <p className="text-sm font-semibold text-slate-900">{label}</p>
        <p className="mt-1 break-words text-sm text-foreground">{value}</p>
        {detail && <p className="mt-1 text-xs leading-5 text-muted">{detail}</p>}
      </div>
    </div>
  );
}

export function SettingsPage({ systemStatus }) {
  const statusLabel =
    systemStatus === "ready"
      ? "System Ready"
      : systemStatus === "offline"
        ? "Backend Offline"
        : "Checking";

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-primary">Settings</p>
        <h1 className="mt-2 text-3xl font-semibold">Runtime configuration</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
          Review non-secret application status and local configuration. API
          keys, environment files, and credentials are never displayed here.
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-md bg-slate-100 text-primary">
                <Settings size={20} aria-hidden="true" />
              </div>
              <div>
                <h2 className="text-base font-semibold">Application status</h2>
                <p className="mt-1 text-sm text-muted">
                  Current frontend and backend connectivity.
                </p>
              </div>
            </div>
          </CardHeader>
          <CardBody className="space-y-3">
            <StatusRow
              icon={Server}
              label="Backend health"
              value={statusLabel}
              detail="Derived from the existing /api/health check in the application shell."
            />
            <StatusRow
              icon={Server}
              label="Frontend API base URL"
              value={API_BASE_URL}
              detail="Configured through VITE_API_BASE_URL or the local Flask default."
            />
            <StatusRow
              icon={Database}
              label="Persistence"
              value="SQLite local persistence enabled"
              detail="Saved documents, question history, summaries, and agent analyses are read through backend APIs."
            />
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-base font-semibold">Implemented capabilities</h2>
            <p className="mt-1 text-sm text-muted">
              This list reflects features already present in the app.
            </p>
          </CardHeader>
          <CardBody className="space-y-3">
            <StatusRow
              icon={FileText}
              label="PDF document intelligence"
              value="Upload, extract, inspect, and reopen saved documents"
              detail="Uses Flask, PyMuPDF, and persisted extracted text."
            />
            <StatusRow
              icon={CheckCircle2}
              label="Document Q&A and summaries"
              value="RAG answers with page sources and saved AI summaries"
              detail="LLM calls remain backend-only and depend on configured provider credentials."
            />
            <StatusRow
              icon={ShieldCheck}
              label="Bounded agent analysis"
              value="Approved tools only"
              detail="The agent may retrieve document passages and run revenue-growth or profit-margin calculations from supported values."
            />
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
