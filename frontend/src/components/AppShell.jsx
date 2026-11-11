import {
  BarChart3,
  FileArchive,
  FileText,
  LayoutDashboard,
  LineChart,
  Settings,
  Sparkles,
} from "lucide-react";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, state: "Available" },
  { id: "documents", label: "Documents", icon: FileText, state: "Available" },
  { id: "research", label: "Research", icon: Sparkles, state: "Available" },
  { id: "analysis", label: "Analysis", icon: LineChart, state: "Available" },
  { id: "reports", label: "Reports", icon: FileArchive, state: "Available" },
  { id: "settings", label: "Settings", icon: Settings, state: "Available" },
];

const statusCopy = {
  checking: { label: "Checking", className: "bg-amber-500" },
  ready: { label: "System Ready", className: "bg-emerald-500" },
  offline: { label: "Backend Offline", className: "bg-red-500" },
};

export function AppShell({ activePage, onNavigate, systemStatus = "checking", children }) {
  const status = statusCopy[systemStatus] ?? statusCopy.checking;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <aside className="fixed inset-y-0 left-0 hidden w-72 border-r border-border bg-panel px-4 py-5 lg:block">
        <div className="mb-8 flex items-center gap-3 px-2">
          <div className="flex size-10 items-center justify-center rounded-md bg-primary text-white">
            <BarChart3 size={22} aria-hidden="true" />
          </div>
          <div>
            <p className="text-lg font-semibold leading-6">FinAgent</p>
            <p className="text-xs text-muted">Financial Research & Analysis Assistant</p>
          </div>
        </div>

        <div className="mb-6 flex items-center gap-2 rounded-md border border-border bg-slate-50 px-3 py-2 text-xs font-medium text-muted">
          <span className={`size-2 rounded-full ${status.className}`} aria-hidden="true" />
          {status.label}
        </div>

        <nav className="space-y-1" aria-label="Main navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activePage === item.id;
            return (
              <button
                key={item.id}
                className={`flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm font-medium transition ${
                  isActive ? "bg-emerald-50 text-primary" : "text-muted hover:bg-slate-50 hover:text-foreground"
                }`}
                onClick={() => onNavigate(item.id)}
              >
                <Icon size={18} aria-hidden="true" />
                <span className="flex-1">{item.label}</span>
                <span className="text-[11px] font-medium text-muted">{item.state}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-10 border-b border-border bg-panel/95 px-4 py-3 backdrop-blur lg:hidden">
          <div className="mb-3 flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-md bg-primary text-white">
              <BarChart3 size={20} aria-hidden="true" />
            </div>
            <div>
              <p className="font-semibold leading-5">FinAgent</p>
              <p className="text-xs text-muted">{status.label}</p>
            </div>
          </div>
          <nav className="flex gap-2 overflow-x-auto pb-1" aria-label="Mobile navigation">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  className={`flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${
                    isActive ? "bg-emerald-50 text-primary" : "text-muted"
                  }`}
                  onClick={() => onNavigate(item.id)}
                >
                  <Icon size={16} aria-hidden="true" />
                  {item.label}
                </button>
              );
            })}
          </nav>
        </header>

        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
