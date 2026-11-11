export function EmptyState({ icon: Icon, title, description, action, className = "" }) {
  return (
    <div className={`rounded-lg border border-dashed border-border bg-panelRaised/50 px-5 py-10 text-center ${className}`}>
      {Icon && (
        <div className="mx-auto flex size-10 items-center justify-center rounded-md border border-border bg-panel text-primary">
          <Icon size={19} aria-hidden="true" />
        </div>
      )}
      <p className="mt-3 text-sm font-semibold text-foreground">{title}</p>
      {description && <p className="mx-auto mt-1 max-w-md text-sm leading-6 text-muted">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
