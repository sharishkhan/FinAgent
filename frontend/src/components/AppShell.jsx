import { useEffect, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  FileArchive,
  FileText,
  House,
  Menu,
  Moon,
  Settings,
  Sun,
  X,
} from "lucide-react";

const navigation = [
  { id: "home", label: "Home", icon: House, title: "Home" },
  { id: "documents", label: "Documents", icon: FileText, title: "Documents" },
  { id: "reports", label: "History", icon: FileArchive, title: "History" },
];

const utilityNavigation = [
  { id: "settings", label: "Settings", icon: Settings, title: "Settings" },
];

const themeStorageKey = "finagent-theme";

function getInitialTheme() {
  if (typeof window === "undefined") {
    return "dark";
  }

  return window.localStorage.getItem(themeStorageKey) === "light" ? "light" : "dark";
}

function NavButton({ item, isActive, collapsed, onNavigate }) {
  const Icon = item.icon;
  const className = `group relative flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm font-medium transition-colors duration-150 ${
    isActive
      ? "bg-primary/15 text-primary"
      : "text-muted hover:bg-panelRaised hover:text-foreground"
  } ${collapsed ? "justify-center px-2" : ""}`;

  const content = (
    <>
      <Icon className="shrink-0" size={18} aria-hidden="true" />
      {!collapsed && <span className="min-w-0 flex-1 truncate">{item.label}</span>}
      {collapsed && (
        <span className="pointer-events-none absolute left-full z-30 ml-3 hidden whitespace-nowrap rounded-md border border-border bg-panel px-2 py-1.5 text-xs text-foreground shadow-panel group-hover:block">
          {item.label}
        </span>
      )}
    </>
  );

  return (
    <button
      type="button"
      className={className}
      onClick={() => onNavigate(item.id)}
      aria-current={isActive ? "page" : undefined}
      title={collapsed ? item.label : undefined}
    >
      {content}
    </button>
  );
}

function Sidebar({ activePage, collapsed, onNavigate, onToggle, className = "" }) {
  return (
    <aside className={`flex h-full flex-col border-r border-border bg-sidebar ${className}`}>
      <div className={`flex h-[76px] items-center border-b border-border ${collapsed ? "justify-center px-3" : "justify-between px-5"}`}>
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary text-slate-950 shadow-sm">
            <BarChart3 size={19} aria-hidden="true" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="truncate text-base font-semibold tracking-wide text-foreground">FinAgent</p>
              <p className="truncate text-[11px] text-muted">Financial intelligence</p>
            </div>
          )}
        </div>
        {onToggle && (
          <button
            type="button"
            onClick={onToggle}
            className="hidden size-8 items-center justify-center rounded-md text-muted transition-colors hover:bg-panelRaised hover:text-foreground lg:inline-flex"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight size={17} /> : <ChevronLeft size={17} />}
          </button>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-5" aria-label="Main navigation">
        <p className={`mb-2 px-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500 ${collapsed ? "sr-only" : ""}`}>
          Workspace
        </p>
        <div className="space-y-1">
          {navigation.map((item) => (
            <NavButton key={item.id} item={item} isActive={activePage === item.id} collapsed={collapsed} onNavigate={onNavigate} />
          ))}
        </div>
        <p className={`mb-2 mt-7 px-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500 ${collapsed ? "sr-only" : ""}`}>
          System
        </p>
        <div className="space-y-1">
          {utilityNavigation.map((item) => (
            <NavButton key={item.id} item={item} isActive={activePage === item.id} collapsed={collapsed} onNavigate={onNavigate} />
          ))}
        </div>
      </nav>
    </aside>
  );
}

export function AppShell({ activePage, onNavigate, systemStatus = "checking", children }) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [theme, setTheme] = useState(getInitialTheme);
  const activeItem = [...navigation, ...utilityNavigation].find((item) => item.id === activePage);
  const pageTitle = activeItem?.title ?? "Overview";

  function handleNavigate(pageId) {
    onNavigate(pageId);
    setIsMobileOpen(false);
  }

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem(themeStorageKey, theme);
  }, [theme]);

  const isDarkTheme = theme === "dark";

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className={`fixed inset-y-0 left-0 z-30 hidden transition-[width] duration-200 lg:block ${isCollapsed ? "w-20" : "w-72"}`}>
        <Sidebar
          activePage={activePage}
          collapsed={isCollapsed}
          onNavigate={handleNavigate}
          onToggle={() => setIsCollapsed((value) => !value)}
        />
      </div>

      {isMobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/70"
            onClick={() => setIsMobileOpen(false)}
            aria-label="Close navigation menu"
          />
          <div className="relative h-full w-[min(19rem,86vw)] shadow-2xl">
            <Sidebar activePage={activePage} collapsed={false} onNavigate={handleNavigate} />
            <button
              type="button"
              className="absolute right-4 top-5 flex size-8 items-center justify-center rounded-md text-muted hover:bg-panelRaised hover:text-foreground"
              onClick={() => setIsMobileOpen(false)}
              aria-label="Close navigation menu"
            >
              <X size={18} />
            </button>
          </div>
        </div>
      )}

      <div className={`min-h-screen transition-[padding] duration-200 ${isCollapsed ? "lg:pl-20" : "lg:pl-72"}`}>
        <header className="sticky top-0 z-20 flex h-[76px] items-center justify-between border-b border-border bg-background/95 px-4 backdrop-blur sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              className="flex size-9 shrink-0 items-center justify-center rounded-md border border-border bg-panel text-muted transition-colors hover:bg-panelRaised hover:text-foreground lg:hidden"
              onClick={() => setIsMobileOpen(true)}
              aria-label="Open navigation menu"
            >
              <Menu size={19} />
            </button>
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">FinAgent workspace</p>
              <h1 className="truncate text-lg font-semibold text-foreground sm:text-xl">{pageTitle}</h1>
            </div>
          </div>
          <button
            type="button"
            className="flex size-9 items-center justify-center rounded-md border border-border bg-panel text-muted transition-colors hover:bg-panelRaised hover:text-foreground"
            onClick={() => setTheme((currentTheme) => currentTheme === "dark" ? "light" : "dark")}
            aria-label={`Switch to ${isDarkTheme ? "light" : "dark"} theme`}
            title={`Switch to ${isDarkTheme ? "light" : "dark"} theme`}
          >
            {isDarkTheme ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
          </button>
        </header>
        {systemStatus === "offline" && (
          <div className="border-b border-amber-200 bg-amber-50 px-4 py-2.5 sm:px-6 lg:px-8" role="status">
            <div className="mx-auto flex max-w-[1600px] items-center gap-2 text-sm text-amber-800">
              <AlertTriangle size={16} className="shrink-0" aria-hidden="true" />
              <span>Backend unavailable. Saved content may not refresh until the connection is restored.</span>
              <button
                type="button"
                className="ml-auto shrink-0 font-medium text-amber-800 underline underline-offset-4"
                onClick={() => handleNavigate("settings")}
              >
                System Status
              </button>
            </div>
          </div>
        )}
        <main className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
