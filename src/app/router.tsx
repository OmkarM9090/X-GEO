import { useEffect } from "react";
import { createBrowserRouter, Navigate, Outlet, useLocation } from "react-router-dom";
import { ScrollTrigger } from "@/lib/gsap";
import { useLenis } from "@/hooks/useLenis";
import { NoiseOverlay } from "@/components/shared/NoiseOverlay";
import { DashboardLayout } from "@/components/dashboard/DashboardLayout";

import LandingPage from "@/pages/marketing/LandingPage";
import PricingPage from "@/pages/marketing/PricingPage";
import FeaturesPage from "@/pages/marketing/FeaturesPage";
import DocsPage from "@/pages/marketing/DocsPage";
import SignInPage from "@/pages/auth/SignInPage";
import SignUpPage from "@/pages/auth/SignUpPage";
import ForgotPasswordPage from "@/pages/auth/ForgotPasswordPage";
import OverviewPage from "@/pages/dashboard/OverviewPage";
import ProjectsPage from "@/pages/dashboard/ProjectsPage";
import AuditDetailPage from "@/pages/dashboard/AuditDetailPage";
import OptimizationsPage from "@/pages/dashboard/OptimizationsPage";
import ReportsPage from "@/pages/dashboard/ReportsPage";
import SettingsPage from "@/pages/dashboard/SettingsPage";

/** Shell: scroll restoration, ScrollTrigger refresh, grain overlay, route fade. */
function RootLayout() {
  const location = useLocation();
  const lenis = useLenis();

  useEffect(() => {
    if (location.hash) return; // hash deep-links handle their own scrolling
    if (lenis) {
      lenis.scrollTo(0, { immediate: true });
    } else {
      window.scrollTo(0, 0);
    }
    const frame = requestAnimationFrame(() => ScrollTrigger.refresh());
    return () => cancelAnimationFrame(frame);
  }, [location.pathname, location.hash, lenis]);

  return (
    <>
      <NoiseOverlay />
      <div key={location.pathname} className="animate-fade-page">
        <Outlet />
      </div>
    </>
  );
}

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      { path: "/", element: <LandingPage /> },
      { path: "/features", element: <FeaturesPage /> },
      { path: "/pricing", element: <PricingPage /> },
      { path: "/docs", element: <DocsPage /> },
      { path: "/signin", element: <SignInPage /> },
      { path: "/signup", element: <SignUpPage /> },
      { path: "/forgot-password", element: <ForgotPasswordPage /> },
      {
        path: "/dashboard",
        element: <DashboardLayout />,
        children: [
          { index: true, element: <OverviewPage /> },
          { path: "projects", element: <ProjectsPage /> },
          { path: "audits", element: <AuditDetailPage /> },
          { path: "optimizations", element: <OptimizationsPage /> },
          { path: "reports", element: <ReportsPage /> },
          { path: "settings", element: <SettingsPage /> },
        ],
      },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
