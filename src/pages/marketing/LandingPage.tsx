import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { ScrollTrigger } from "@/lib/gsap";
import { useLenis, scrollToTarget } from "@/hooks/useLenis";
import { Navbar } from "@/components/marketing/Navbar";
import { Hero } from "@/components/marketing/Hero";
import { LogoCloud } from "@/components/marketing/LogoCloud";
import { StochasticDemo } from "@/components/marketing/StochasticDemo";
import { FeatureBento } from "@/components/marketing/FeatureBento";
import { HowItWorks } from "@/components/marketing/HowItWorks";
import { PricingTiers } from "@/components/marketing/PricingTiers";
import { Testimonials } from "@/components/marketing/Testimonials";
import { FAQ } from "@/components/marketing/FAQ";
import { CTA } from "@/components/marketing/CTA";
import { Footer } from "@/components/marketing/Footer";

export default function LandingPage() {
  const location = useLocation();
  const lenis = useLenis();

  // Deep links like /#how-it-works → smooth scroll once settled.
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
        <StochasticDemo />
        <FeatureBento />
        <HowItWorks />
        <PricingTiers />
        <Testimonials />
        <FAQ />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}
