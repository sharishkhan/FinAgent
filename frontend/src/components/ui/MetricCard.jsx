export function MetricCard({ label, value, icon: Icon, detail, className = "" }) {
  return (
    <section className={`rounded-lg border border-border bg-panel p-5 shadow-panel ${className}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-muted">{label}</p>
          <p className="mt-2 text-3xl font-semibold text-foreground">{value}</p>
          {detail && <p className="mt-2 text-xs text-muted">{detail}</p>}
        </div>
        {Icon && (
          <div className="flex size-10 shrink-0 items-center justify-center rounded-md border border-border bg-panelRaised text-primary">
            <Icon size={19} aria-hidden="true" />
          </div>
        )}
      </div>
    </section>
  );
}
