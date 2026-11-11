export function Card({ children, className = "" }) {
  return (
    <section className={`rounded-lg border border-border bg-panel shadow-soft ${className}`}>
      {children}
    </section>
  );
}

export function CardHeader({ children, className = "" }) {
  return <div className={`border-b border-border px-5 py-4 ${className}`}>{children}</div>;
}

export function CardBody({ children, className = "" }) {
  return <div className={`p-5 ${className}`}>{children}</div>;
}
