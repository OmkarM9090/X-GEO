import { useEffect } from "react";
import { createBrowserRouter, Navigate, useLocation, useOutlet } from "react-router-dom";
import { ScrollTrigger } from "@/lib/gsap-config";
import { useLenis } from "@/hooks/useLenis";
import { NoiseOverlay } from "@/components/shared/NoiseOverlay";
import { CustomCursor } from "@/components/shared/CustomCursor";
import { ScrollProgress } from "@/components/shared/ScrollProgress";
import { PageTransition } from "@/components/shared/PageTransition";
import { DashboardLayout } from "@/pages/dashboard/layouts/DashboardLayout";

import LandingPage from "@/pages/marketing/LandingPage";
import PricingPage from "@/pages/marketing/PricingPage";
import FeaturesPage from "@/pages/marketing/FeaturesPage";
import DocsPage from "@/pages/marketing/DocsPage";
import ChangelogPage from "@/pages/marketing/ChangelogPage";
import SignInPage from "@/pages/auth/SignInPage";
import SignUpPage from "@/pages/auth/SignUpPage";
import ForgotPasswordPage from "@/pages/auth/ForgotPasswordPage";
import OverviewPage from "@/pages/dashboard/OverviewPage";
import ProjectsPage from "@/pages/dashboard/ProjectsPage";
import AuditDetailPage from "@/pages/dashboard/AuditDetailPage";
import OptimizationsPage from "@/pages/dashboard/OptimizationsPage";
import ReportsPage from "@/pages/dashboard/ReportsPage";
import SettingsPage from "@/pages/dashboard/SettingsPage";

function RootLayout() {
  const location = useLocation();
  const lenis = useLenis();
  const outlet = useOutlet();

  useEffect(() => {
    if (location.hash) return;
    if (lenis) {
      lenis.scrollTo(0, { immediate: true });
    } else {
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    }

    const frame = requestAnimationFrame(() => ScrollTrigger.refresh());
    return () => cancelAnimationFrame(frame);
  }, [location.pathname, location.hash, lenis]);

  return (
    <>
      <ScrollProgress />
      <NoiseOverlay />
      <CustomCursor />
      <PageTransition routeKey={`${location.pathname}${location.search}`}>{outlet}</PageTransition>
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
      { path: "/changelog", element: <ChangelogPage /> },
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
