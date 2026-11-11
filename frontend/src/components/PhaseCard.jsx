import { Card, CardBody } from "./ui/Card.jsx";

export function PhaseCard({ icon: Icon, eyebrow, title, description }) {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-primary">{eyebrow}</p>
        <h1 className="mt-2 text-3xl font-semibold">{title}</h1>
      </div>
      <Card>
        <CardBody className="flex flex-col gap-5 md:flex-row md:items-center">
          <div className="flex size-14 shrink-0 items-center justify-center rounded-md bg-slate-100 text-primary">
            <Icon size={26} aria-hidden="true" />
          </div>
          <div>
            <p className="text-base font-semibold">Coming in a later phase</p>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">{description}</p>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
