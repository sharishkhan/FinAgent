export function PageHeader({ eyebrow, title, description, actions, className = "" }) {
  return (
    <header className={`flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between ${className}`}>
      <div className="max-w-3xl">
        {eyebrow && <p className="text-sm font-medium text-primary">{eyebrow}</p>}
        <h1 className="mt-2 text-2xl font-semibold text-foreground sm:text-3xl">{title}</h1>
        {description && <p className="mt-2 text-sm leading-6 text-muted">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </header>
  );
}
