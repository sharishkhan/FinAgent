import { useEffect, useState } from "react";
import { CheckCircle2, Database, FileText, KeyRound, Loader2, Server, ShieldCheck, XCircle } from "lucide-react";

import { API_BASE_URL, getSettings, testConnection } from "../lib/api.js";
import { Button } from "../components/ui/Button.jsx";
import { Card, CardBody, CardHeader } from "../components/ui/Card.jsx";

function StatusRow({ icon: Icon, label, value, detail }) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-slate-50 p-4 sm:flex-row sm:items-start">
      <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-panel text-primary"><Icon size={19} aria-hidden="true" /></div>
      <div className="min-w-0"><p className="text-sm font-semibold text-slate-900">{label}</p><p className="mt-1 break-words text-sm text-foreground">{value}</p>{detail && <p className="mt-1 text-xs leading-5 text-muted">{detail}</p>}</div>
    </div>
  );
}

export function SettingsPage({ systemStatus }) {
  const [settings, setSettings] = useState(null);
  const [settingsError, setSettingsError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const statusLabel = systemStatus === "ready" ? "System Ready" : systemStatus === "offline" ? "Backend Offline" : "Checking";

  async function loadSettings() {
    setIsLoading(true);
    setSettingsError("");
    try {
      setSettings(await getSettings());
    } catch (error) {
      setSettingsError(error.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleTestConnection() {
    if (isTesting) return;
    setIsTesting(true);
    setTestResult(null);
    try {
      setTestResult(await testConnection());
    } catch (error) {
      setTestResult({ success: false, message: error.message });
    } finally {
      setIsTesting(false);
    }
  }

  useEffect(() => { loadSettings(); }, []);

  const counts = settings?.storage?.counts ?? {};
  const llm = settings?.llm;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-primary">Settings</p>
        <h1 className="mt-2 text-3xl font-semibold">Runtime configuration</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">Review non-secret application status and local configuration. API keys, environment files, and credentials are never displayed here.</p>
      </div>

      {settingsError && <div className="flex items-start gap-3 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"><XCircle className="mt-0.5 shrink-0" size={18} aria-hidden="true" /><span>{settingsError}</span></div>}

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3"><div className="flex size-10 items-center justify-center rounded-md bg-slate-100 text-primary"><KeyRound size={20} aria-hidden="true" /></div><div><h2 className="text-base font-semibold">AI connection</h2><p className="mt-1 text-sm text-muted">Backend-only AI configuration.</p></div></div>
            <Button variant="secondary" onClick={handleTestConnection} disabled={isTesting || isLoading} className="w-full sm:w-auto">{isTesting && <Loader2 className="animate-spin" size={17} aria-hidden="true" />}{isTesting ? "Testing..." : "Test connection"}</Button>
          </CardHeader>
          <CardBody className="space-y-3">
            {isLoading ? <p className="text-sm text-muted">Loading AI configuration...</p> : <><StatusRow icon={Server} label="Provider" value={llm?.provider ?? "Unavailable"} /><StatusRow icon={FileText} label="Model" value={llm?.model ?? "Unavailable"} /><StatusRow icon={KeyRound} label="API key" value={llm?.key_configured ? "Set" : "Not set"} /></>}
            {testResult && <div className={`flex items-start gap-3 rounded-md border px-4 py-3 text-sm ${testResult.success ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-red-200 bg-red-50 text-red-700"}`}>{testResult.success ? <CheckCircle2 className="mt-0.5 shrink-0" size={18} aria-hidden="true" /> : <XCircle className="mt-0.5 shrink-0" size={18} aria-hidden="true" />}<span>{testResult.success ? `Connected in ${testResult.latency_ms} ms` : testResult.message}</span></div>}
          </CardBody>
        </Card>

        <Card>
          <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div className="flex items-center gap-3"><div className="flex size-10 items-center justify-center rounded-md bg-slate-100 text-primary"><Database size={20} aria-hidden="true" /></div><div><h2 className="text-base font-semibold">Your data</h2><p className="mt-1 text-sm text-muted">Local saved content and storage.</p></div></div><Button variant="secondary" onClick={loadSettings} disabled={isLoading} className="w-full sm:w-auto">{isLoading ? "Refreshing..." : "Refresh"}</Button></CardHeader>
          <CardBody className="space-y-3"><StatusRow icon={FileText} label="Documents" value={isLoading ? "Loading..." : String(counts.documents ?? 0)} /><StatusRow icon={FileText} label="Questions" value={isLoading ? "Loading..." : String(counts.questions ?? 0)} /><StatusRow icon={FileText} label="Saved analyses" value={isLoading ? "Loading..." : String(counts.results ?? 0)} /><StatusRow icon={Database} label="Database file" value={settings?.storage?.database_path ?? "Unavailable"} /></CardBody>
        </Card>

        <Card>
          <CardHeader><div className="flex items-center gap-3"><div className="flex size-10 items-center justify-center rounded-md bg-slate-100 text-primary"><ShieldCheck size={20} aria-hidden="true" /></div><h2 className="text-base font-semibold">Privacy</h2></div></CardHeader>
          <CardBody><p className="text-sm leading-7 text-muted">Documents are stored on your computer. When you ask a question or generate a summary, only the relevant passages are sent to the Gemini AI. FinAgent explains what reports say and never gives investment advice.</p></CardBody>
        </Card>

        <Card>
          <CardHeader><div className="flex items-center gap-3"><div className="flex size-10 items-center justify-center rounded-md bg-slate-100 text-primary"><Server size={20} aria-hidden="true" /></div><h2 className="text-base font-semibold">Backend</h2></div></CardHeader>
          <CardBody className="space-y-3"><StatusRow icon={Server} label="Backend health" value={statusLabel} detail="Derived from the existing /api/health check in the application shell." /><StatusRow icon={Server} label="Frontend API base URL" value={API_BASE_URL} detail="Configured through VITE_API_BASE_URL or the local Flask default." /></CardBody>
        </Card>
      </div>
    </div>
  );
}
