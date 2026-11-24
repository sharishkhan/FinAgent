import { CheckCircle2, AlertTriangle } from "lucide-react";

import { Card, CardBody, CardHeader } from "./ui/Card.jsx";

function formatNumber(value, fractionDigits = 2) {
  return Number(value).toLocaleString("en-IN", { minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits });
}

function formatAmount(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return null;
  return formatNumber(value);
}

function formatValue(value, unit = "") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return null;
  const suffix = unit === "times" ? "x" : unit === "%" ? "%" : unit === "days" ? " days" : "";
  return `${formatNumber(value, unit === "days" ? 1 : 2)}${suffix}`;
}

function unitLabel(unit) {
  const labels = { crore: "₹ crore", lakh: "₹ lakh", million: "₹ million" };
  return labels[unit] ?? "";
}

function pageFor(metric, value) {
  return value?.page ?? metric?.inputs?.[0]?.page ?? null;
}

function ChangeChip({ value, type = "percent" }) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return null;
  const numeric = Number(value);
  const formatted = formatNumber(numeric);
  const suffix = type === "percent" ? "%" : "";
  const className = type === "increase"
    ? numeric > 0
      ? "bg-amber-100 text-amber-800"
      : numeric < 0
        ? "bg-emerald-100 text-emerald-800"
        : "bg-panelRaised text-muted"
    : numeric > 0
      ? "bg-emerald-100 text-emerald-800"
      : numeric < 0
        ? "bg-red-100 text-red-700"
        : "bg-panelRaised text-muted";
  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${className}`}>{numeric > 0 ? "+" : ""}{formatted}{suffix}</span>;
}

function ProfitChangeChip({ current, previous, change }) {
  if (current === null || current === undefined || previous === null || previous === undefined) return null;
  if (Number(previous) > 0 && Number(current) < 0) {
    return <span className="rounded-full bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700">Swung to a loss</span>;
  }
  if (Number(previous) < 0 && Number(current) < 0) return null;
  return <ChangeChip value={change} />;
}

function FigureCard({ label, value, metric, change, changeType, profitChange, page }) {
  const current = value?.current ?? metric?.current;
  const previous = value?.previous ?? metric?.previous;
  const displayCurrent = value ? formatAmount(current) : formatValue(current, metric?.unit);
  if (displayCurrent === null) return null;

  return (
    <div className="rounded-lg border border-border bg-panelRaised p-4">
      <div className="flex items-start justify-between gap-3"><p className="text-sm font-medium text-muted">{label}</p>{page && <span className="shrink-0 rounded-full bg-panel px-2.5 py-1 text-xs text-muted">Page {page}</span>}</div>
      <div className="mt-3 flex flex-wrap items-end gap-3"><p className={`text-2xl font-semibold ${Number(current) < 0 ? "text-red-700" : "text-foreground"}`}>{displayCurrent}</p>{profitChange ? <ProfitChangeChip current={current} previous={previous} change={change} /> : <ChangeChip value={change} type={changeType} />}</div>
      {previous !== null && previous !== undefined && <p className="mt-2 text-xs text-muted">was {value ? formatAmount(previous) : formatValue(previous, metric?.unit)}</p>}
      {metric?.formula && <p className="mt-3 text-xs leading-5 text-muted">{metric.formula}</p>}
    </div>
  );
}

export function KeyFigures({ financials, basis }) {
  const statements = financials?.statements ?? {};
  const basisStatements = statements[basis] ?? {};
  const profitAndLoss = basisStatements.profit_and_loss;
  const metrics = financials?.metrics?.[basis] ?? {};

  if (Object.keys(statements).length === 0) {
    return (
      <Card>
        <CardHeader><h2 className="text-base font-semibold">Key figures</h2></CardHeader>
        <CardBody><p className="text-sm font-medium text-foreground">No financial statements were recognised in this document</p>{financials?.warnings?.map((warning) => <p key={warning} className="mt-2 text-sm text-muted">{warning}</p>)}</CardBody>
      </Card>
    );
  }

  const values = profitAndLoss?.values ?? {};
  const checks = (financials?.checks ?? []).filter((check) => check.basis === basis);
  const failedChecks = checks.filter((check) => !check.ok);
  const statementUnit = profitAndLoss?.unit ?? basisStatements.balance_sheet?.unit;
  const revenue = values.revenue_from_operations;
  const profit = values.profit_for_the_year;
  const borrowings = metrics.total_borrowings;
  const debtEquity = metrics.debt_equity_ratio;
  const primaryCards = [
    { label: "Revenue from operations", value: revenue, metric: metrics.revenue_growth_pct, change: metrics.revenue_growth_pct?.current, changeType: "percent", page: pageFor(metrics.revenue_growth_pct, revenue) },
    { label: "Profit for the year", value: profit, metric: metrics.profit_change_pct, change: metrics.profit_change_pct?.current, changeType: "percent", profitChange: true, page: pageFor(metrics.profit_change_pct, profit) },
    { label: "Total borrowings", metric: borrowings, change: borrowings?.current !== null && borrowings?.previous !== null ? Number(borrowings.current) - Number(borrowings.previous) : null, changeType: "increase", page: pageFor(borrowings) },
    { label: "Debt-equity ratio", metric: debtEquity, change: debtEquity?.current !== null && debtEquity?.previous !== null ? Number(debtEquity.current) - Number(debtEquity.previous) : null, changeType: "increase", page: pageFor(debtEquity) },
  ];
  const ratioKeys = ["interest_coverage", "ebitda_margin_pct", "current_ratio", "receivable_days", "net_profit_margin_pct"];

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-base font-semibold">KEY FIGURES · {basis.toUpperCase()}{unitLabel(statementUnit) ? ` · ${unitLabel(statementUnit)}` : ""}</h2>
          {checks.length > 0 && (failedChecks.length === 0 ? <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-800"><CheckCircle2 size={13} aria-hidden="true" />Cross-checks: {checks.length} of {checks.length} passed</span> : <span title={failedChecks.map((check) => check.name).join("; ")} className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800"><AlertTriangle size={13} aria-hidden="true" />Some cross-checks failed</span>)}
        </div>
      </CardHeader>
      <CardBody className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{primaryCards.map((card) => <FigureCard key={card.label} {...card} />)}</div>
        {ratioKeys.some((key) => metrics[key]?.current !== null && metrics[key]?.current !== undefined) && <div><p className="mb-3 text-xs font-medium uppercase tracking-[0.1em] text-muted">More ratios</p><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">{ratioKeys.map((key) => { const metric = metrics[key]; const current = formatValue(metric?.current, metric?.unit); if (!metric || current === null) return null; return <div key={key} title={metric.formula} className="rounded-lg border border-border bg-panelRaised p-4"><p className="text-xs text-muted">{metric.label}</p><p className="mt-2 text-lg font-semibold text-foreground">{current}</p>{metric.previous !== null && metric.previous !== undefined && <p className="mt-1 text-xs text-muted">was {formatValue(metric.previous, metric.unit)}</p>}</div>; })}</div></div>}
      </CardBody>
    </Card>
  );
}
