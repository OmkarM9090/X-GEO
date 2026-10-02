import { Outlet, useLocation } from "react-router-dom";
import { useUIStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { TopBar } from "@/components/dashboard/TopBar";

/** Dashboard shell: fixed sidebar (240→64px) + 56px topbar + routed content. */
export function DashboardLayout() {
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div
        className={cn(
          "flex min-h-screen flex-col transition-[margin] duration-300 ease-out-expo",
          collapsed ? "lg:ml-16" : "lg:ml-60",
        )}
      >
        <TopBar />
        <main className="flex-1">
          <div
            key={location.pathname}
            className="mx-auto w-full max-w-7xl animate-page-enter p-4 sm:p-6 lg:p-8"
          >
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
