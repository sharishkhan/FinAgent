export function Button({
  children,
  className = "",
  variant = "primary",
  type = "button",
  disabled = false,
  ...props
}) {
  const variants = {
    primary:
      "bg-primary text-slate-950 shadow-sm hover:bg-primaryDark focus-visible:ring-primary/30",
    secondary:
      "border border-border bg-panelRaised text-foreground hover:bg-slate-100 focus-visible:ring-primary/30",
    ghost: "text-muted hover:bg-slate-100 hover:text-foreground focus-visible:ring-primary/30",
  };

  return (
    <button
      type={type}
      disabled={disabled}
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:ring-4 disabled:cursor-not-allowed disabled:opacity-60 ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
