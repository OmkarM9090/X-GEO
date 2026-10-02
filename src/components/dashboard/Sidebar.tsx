import { Link, NavLink, useLocation } from "react-router-dom";
import {
  ChevronsLeft, ChevronsRight, FileText, Folder, LayoutDashboard, ScanSearch, Settings, Zap,
} from "lucide-react";
import { useUIStore } from "@/lib/store";
import { DASHBOARD_METRICS } from "@/lib/mock-data";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/shared/Logo";
import { Button } from "@/components/ui/button";

const NAV_ITEMS = [
  { label: "Overview", to: "/dashboard", Icon: LayoutDashboard, end: true },
  { label: "Projects", to: "/dashboard/projects", Icon: Folder, end: false },
  { label: "Audits", to: "/dashboard/audits", Icon: ScanSearch, end: false, badge: "12" },
  { label: "Optimizations", to: "/dashboard/optimizations", Icon: Zap, end: false, badge: "3" },
  { label: "Reports", to: "/dashboard/reports", Icon: FileText, end: false },
];

function UsageMeter({ collapsed }: { collapsed: boolean }) {
  const { monthlyRuns } = DASHBOARD_METRICS;
  const pct = Math.min(1, monthlyRuns.value / monthlyRuns.limit);
  if (collapsed) return null;
  return (
    <div className="mx-3 mb-3 rounded-xl border border-border bg-background/50 p-4">
      <div className="flex items-baseline justify-between">
        <p className="text-xs font-medium text-foreground">Monthly runs</p>
        <p className="font-mono text-[11px] text-muted-foreground">
          {monthlyRuns.value.toLocaleString()}/{monthlyRuns.limit.toLocaleString()}
        </p>
      </div>
      <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-accent transition-all duration-700" style={{ width: `${pct * 100}%` }} />
      </div>
      <Button variant="outline" size="sm" className="mt-3 w-full" asChild>
        <Link to="/pricing">Upgrade</Link>
      </Button>
    </div>
  );
}

/** Shared nav — rendered in the desktop aside and the mobile sheet. */
export function SidebarContent({ collapsed = false, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
  const location = useLocation();
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);

  return (
    <div className="flex h-full flex-col">
      <div className={cn("flex h-14 items-center border-b border-border/60", collapsed ? "justify-center px-0" : "justify-between px-4")}>
        {collapsed ? (
          <Link to="/" aria-label="X-GEO — home" className="grid size-8 place-items-center rounded-lg bg-accent/15 font-heading text-sm font-bold text-accent">
            X
          </Link>
        ) : (
          <Logo to="/dashboard" />
        )}
      </div>

      <nav aria-label="Dashboard" className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {NAV_ITEMS.map(({ label, to, Icon, end, badge }) => {
          const active = end ? location.pathname === to : location.pathname.startsWith(to);
          return (
            <NavLink
              key={label}
              to={to}
              end={end}
              onClick={onNavigate}
              aria-label={collapsed ? label : undefined}
              className={cn(
                "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all duration-200",
                collapsed && "justify-center px-0",
                active
                  ? "bg-accent/10 font-medium text-accent"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
              )}
            >
              <span
                className={cn(
                  "absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-accent transition-all duration-300",
                  active ? "opacity-100" : "opacity-0",
                  collapsed && "hidden",
                )}
              />
              <Icon className="size-[18px] shrink-0" strokeWidth={active ? 2 : 1.75} />
              {!collapsed && <span className="flex-1 truncate">{label}</span>}
              {!collapsed && badge && (
                <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
                  {badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      <UsageMeter collapsed={collapsed} />

      <div className="border-t border-border/60 px-3 py-3">
        <NavLink
          to="/dashboard/settings"
          onClick={onNavigate}
          aria-label={collapsed ? "Settings" : undefined}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all duration-200",
              collapsed && "justify-center px-0",
              isActive
                ? "bg-accent/10 font-medium text-accent"
                : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
            )
          }
        >
          <Settings className="size-[18px] shrink-0" strokeWidth={1.75} />
          {!collapsed && <span>Settings</span>}
        </NavLink>
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={cn(
            "mt-1 hidden w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground lg:flex",
            collapsed ? "justify-center px-0" : "",
          )}
        >
          {collapsed ? <ChevronsRight className="size-[18px]" /> : <ChevronsLeft className="size-[18px]" />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </div>
  );
}

/** Desktop aside — 240px, collapsible to 64px. */
export function Sidebar() {
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-30 hidden border-r border-border/60 bg-card/60 backdrop-blur transition-[width] duration-300 ease-out-expo lg:block",
        collapsed ? "w-16" : "w-60",
      )}
    >
      <SidebarContent collapsed={collapsed} />
    </aside>
  );
}
