import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { ScrollTrigger } from "@/lib/gsap-config";
import { useLenis, scrollToTarget } from "@/hooks/useLenis";
import { Navbar } from "@/components/marketing/Navbar";
import { Hero } from "@/components/marketing/Hero";
import { LogoCloud } from "@/components/marketing/LogoCloud";
import { ProblemStatement } from "@/components/marketing/ProblemStatement";
import { StochasticDemo } from "@/components/marketing/StochasticDemo";
import { FeatureBento } from "@/components/marketing/FeatureBento";
import { DashboardScrub } from "@/components/marketing/DashboardScrub";
import { HowItWorks } from "@/components/marketing/HowItWorks";
import { ComparisonTable } from "@/components/marketing/ComparisonTable";
import { PricingTiers } from "@/components/marketing/PricingTiers";
import { Testimonials } from "@/components/marketing/Testimonials";
import { FAQ } from "@/components/marketing/FAQ";
import { FinalCTA } from "@/components/marketing/FinalCTA";
import { Footer } from "@/components/marketing/Footer";

export default function LandingPage() {
  const location = useLocation();
  const lenis = useLenis();

  useEffect(() => {
    if (!location.hash) return;
    const timer = window.setTimeout(() => {
      scrollToTarget(lenis, location.hash);
      ScrollTrigger.refresh();
    }, 120);
    return () => window.clearTimeout(timer);
  }, [location.hash, lenis]);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main>
        <Hero />
        <LogoCloud />
        <ProblemStatement />
        <StochasticDemo />
        <FeatureBento />
        <DashboardScrub />
        <HowItWorks />
        <ComparisonTable />
        <PricingTiers />
        <Testimonials />
        <FAQ />
        <FinalCTA />
      </main>
      <Footer />
    </div>
  );
}
