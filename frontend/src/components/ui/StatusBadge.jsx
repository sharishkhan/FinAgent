const statusStyles = {
  ready: "border-teal-400/25 bg-teal-400/10 text-teal-200",
  checking: "border-amber-300/25 bg-amber-300/10 text-amber-200",
  offline: "border-red-400/25 bg-red-400/10 text-red-200",
  neutral: "border-border bg-panelRaised text-muted",
};

const dotStyles = {
  ready: "bg-teal-300",
  checking: "bg-amber-300",
  offline: "bg-red-300",
  neutral: "bg-slate-400",
};

export function StatusBadge({ status = "neutral", children, className = "" }) {
  const resolvedStatus = statusStyles[status] ? status : "neutral";

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-medium ${statusStyles[resolvedStatus]} ${className}`}
    >
      <span className={`size-1.5 rounded-full ${dotStyles[resolvedStatus]}`} aria-hidden="true" />
      {children}
    </span>
  );
}
