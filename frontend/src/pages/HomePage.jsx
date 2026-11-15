import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, BrainCircuit, Calculator, FileText, MessageSquareText, Search, ShieldCheck, Upload } from "lucide-react";

import { Button } from "../components/ui/Button.jsx";

const proofPoints = [
  { icon: FileText, title: "Every answer shows its pages", description: "See the exact pages and excerpts behind each answer." },
  { icon: Calculator, title: "Numbers are calculated in code", description: "Growth and margin figures come from verified calculations, not AI guesses." },
  { icon: ShieldCheck, title: "It won't guess", description: "Questions about other companies or investment advice are declined, and missing information is reported as missing." },
];

const workflow = [
  { icon: Upload, label: "Upload", detail: "Add a company's annual report (PDF)." },
  { icon: Search, label: "Read", detail: "Text is extracted on your computer, page by page." },
  { icon: Calculator, label: "Find & calculate", detail: "The best-matching pages are retrieved and key figures are calculated." },
  { icon: BrainCircuit, label: "Answer with proof", detail: "Each answer lists its source pages." },
];

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString();
}

function getResultTitle(result) {
  return result?.title || result?.document_filename || result?.filename || "Saved research result";
}

function Reveal({ children, reduceMotion, className = "" }) {
  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.18 }}
      transition={{ duration: reduceMotion ? 0 : 0.32, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

function ExampleMessage({ children, delay = 0, reduceMotion, className = "" }) {
  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduceMotion ? 0 : 0.24, delay: reduceMotion ? 0 : delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

function ContinueCard({ recentDocuments, savedResults, onNavigate }) {
  const latestDocument = recentDocuments[0];
  const latestResult = savedResults[0];

  return (
    <section className="rounded-lg border border-border bg-panel p-5 shadow-panel">
      <p className="text-sm font-medium text-primary">Continue where you left off</p>
      {latestDocument ? (
        <div className="mt-4">
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-md border border-border bg-panelRaised text-accent"><FileText size={19} aria-hidden="true" /></div>
            <div className="min-w-0">
              <p className="truncate text-base font-semibold text-foreground" title={latestDocument.filename ?? "Untitled report"}>{latestDocument.filename ?? "Untitled report"}</p>
              <p className="mt-1 text-sm text-muted">{latestDocument.pages ?? 0} pages</p>
            </div>
          </div>
          {latestResult && (
            <p className="mt-4 border-t border-border pt-4 text-sm text-muted">
              Latest research: <span className="font-medium text-foreground">{getResultTitle(latestResult)}</span>
              {formatDate(latestResult.created_at) && ` · ${formatDate(latestResult.created_at)}`}
            </p>
          )}
          <div className="mt-5 flex flex-col gap-2 sm:flex-row">
            <Button onClick={() => onNavigate("research")}>Ask a question <MessageSquareText size={16} aria-hidden="true" /></Button>
            <Button variant="secondary" onClick={() => onNavigate("documents")}>Open Documents</Button>
          </div>
        </div>
      ) : latestResult ? (
        <div className="mt-4">
          <p className="text-sm text-muted">Latest research: <span className="font-medium text-foreground">{getResultTitle(latestResult)}</span>{formatDate(latestResult.created_at) && ` · ${formatDate(latestResult.created_at)}`}</p>
          <Button variant="secondary" onClick={() => onNavigate("reports")} className="mt-5">Open Reports</Button>
        </div>
      ) : (
        <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-muted">No reports yet. Upload your first annual report.</p>
          <Button onClick={() => onNavigate("documents")} className="shrink-0">Upload a report <Upload size={16} aria-hidden="true" /></Button>
        </div>
      )}
    </section>
  );
}

export function HomePage({ onNavigate, recentDocuments = [], savedResults = [] }) {
  const reduceMotion = useReducedMotion();

  return (
    <div className="mx-auto max-w-7xl space-y-16 pb-6 lg:space-y-20 lg:pb-10">
      <section className="grid items-center gap-10 pt-4 lg:grid-cols-[1.02fr_0.98fr] lg:pt-10">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary"><span className="size-1.5 rounded-full bg-accent" aria-hidden="true" />Financial report research</div>
          <h2 className="mt-6 text-4xl font-semibold leading-[1.1] text-foreground sm:text-5xl">Annual reports, answered with proof.</h2>
          <p className="mt-5 max-w-xl text-lg leading-8 text-muted">FinAgent reads a company's report, calculates figures in code, and shows the exact page behind every answer. If the report doesn't say it, FinAgent says so.</p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button onClick={() => onNavigate("documents")} className="sm:min-w-40">Upload a report <ArrowRight size={17} aria-hidden="true" /></Button>
            <Button variant="secondary" onClick={() => onNavigate("research")} className="sm:min-w-40">Ask a question <MessageSquareText size={17} aria-hidden="true" /></Button>
          </div>
          <p className="mt-4 max-w-xl text-sm leading-6 text-muted">Stored on your computer. Only the passages needed for an answer are sent to the Gemini AI.</p>
        </div>

        <section className="overflow-hidden rounded-lg border border-border bg-panel shadow-panel" aria-label="Static FinAgent research example">
          <div className="border-b border-border px-5 py-4"><p className="text-sm font-semibold text-foreground">Example from a real annual report (Crompton Greaves Consumer Electricals, FY2025-26)</p></div>
          <div className="space-y-4 p-5">
            <ExampleMessage reduceMotion={reduceMotion} className="ml-auto max-w-[86%] rounded-lg bg-primary px-4 py-3 text-sm leading-6 text-slate-950">What was the debt-equity ratio?</ExampleMessage>
            <ExampleMessage reduceMotion={reduceMotion} delay={0.4} className="max-w-[92%] rounded-lg border border-border bg-panelRaised px-4 py-3 text-sm leading-6 text-foreground">The debt-equity ratio was 0.00 for 2025-26 and 0.08 for 2024-25.</ExampleMessage>
            <ExampleMessage reduceMotion={reduceMotion} delay={0.8} className="inline-flex items-center gap-2 rounded-md border border-border bg-panelRaised px-2.5 py-1.5 text-xs font-medium text-muted"><FileText size={13} className="text-accent" aria-hidden="true" />Source: PDF page 135</ExampleMessage>
            <ExampleMessage reduceMotion={reduceMotion} delay={1.2} className="ml-auto max-w-[86%] rounded-lg bg-primary px-4 py-3 text-sm leading-6 text-slate-950">What was Voltas&apos;s revenue?</ExampleMessage>
            <ExampleMessage reduceMotion={reduceMotion} delay={1.6} className="max-w-[92%] rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-800">&apos;Voltas&apos; does not appear in this report, so FinAgent won&apos;t give figures for it.</ExampleMessage>
          </div>
        </section>
      </section>

      <Reveal reduceMotion={reduceMotion}>
        <section>
          <div className="max-w-2xl"><p className="text-sm font-medium text-primary">Built to be checked.</p><h2 className="mt-2 text-2xl font-semibold text-foreground">Every conclusion stays connected to its evidence.</h2></div>
          <div className="mt-7 grid gap-4 md:grid-cols-3">
            {proofPoints.map((point) => {
              const Icon = point.icon;
              return <article key={point.title} className="rounded-lg border border-border bg-panel p-5 transition-colors hover:border-primary/35 hover:bg-panelRaised"><div className="flex size-10 items-center justify-center rounded-md border border-border bg-panelRaised text-primary"><Icon size={19} aria-hidden="true" /></div><h3 className="mt-5 text-base font-semibold text-foreground">{point.title}</h3><p className="mt-2 text-sm leading-6 text-muted">{point.description}</p></article>;
            })}
          </div>
        </section>
      </Reveal>

      <Reveal reduceMotion={reduceMotion}>
        <section className="border-y border-border py-8 sm:py-10">
          <div><p className="text-sm font-medium text-primary">How it works</p><h2 className="mt-2 text-2xl font-semibold text-foreground">From PDF to a checked answer.</h2></div>
          <ol className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {workflow.map((step, index) => {
              const Icon = step.icon;
              return <li key={step.label} className="relative flex gap-3 lg:block"><span className="flex size-9 shrink-0 items-center justify-center rounded-md border border-border bg-panelRaised text-primary"><Icon size={17} aria-hidden="true" /></span><div className="lg:mt-4"><p className="text-xs font-medium text-muted">0{index + 1}</p><h3 className="mt-1 text-sm font-semibold text-foreground">{step.label}</h3><p className="mt-1 text-sm leading-6 text-muted">{step.detail}</p></div></li>;
            })}
          </ol>
        </section>
      </Reveal>

      <Reveal reduceMotion={reduceMotion}><ContinueCard recentDocuments={recentDocuments} savedResults={savedResults} onNavigate={onNavigate} /></Reveal>
    </div>
  );
}
