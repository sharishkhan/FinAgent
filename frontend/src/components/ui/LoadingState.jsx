import { Loader2 } from "lucide-react";

export function LoadingState({ label = "Loading", description, className = "" }) {
  return (
    <div className={`flex items-center gap-3 rounded-lg border border-border bg-panelRaised/50 px-4 py-4 ${className}`} role="status">
      <Loader2 className="shrink-0 animate-spin text-primary" size={18} aria-hidden="true" />
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        {description && <p className="mt-0.5 text-sm text-muted">{description}</p>}
      </div>
    </div>
  );
}
