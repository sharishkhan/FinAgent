import { Card, CardBody, CardHeader } from "./Card.jsx";

export function SectionCard({ icon: Icon, title, description, children, className = "" }) {
  return (
    <Card className={className}>
      {(title || description) && (
        <CardHeader>
          <div className="flex items-start gap-3">
            {Icon && (
              <div className="flex size-9 shrink-0 items-center justify-center rounded-md border border-border bg-panelRaised text-primary">
                <Icon size={18} aria-hidden="true" />
              </div>
            )}
            <div>
              {title && <h2 className="text-base font-semibold text-foreground">{title}</h2>}
              {description && <p className="mt-1 text-sm leading-5 text-muted">{description}</p>}
            </div>
          </div>
        </CardHeader>
      )}
      <CardBody>{children}</CardBody>
    </Card>
  );
}
