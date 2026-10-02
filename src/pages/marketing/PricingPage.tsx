import { Navbar } from "@/components/marketing/Navbar";
import { PricingTiers } from "@/components/marketing/PricingTiers";
import { FAQ } from "@/components/marketing/FAQ";
import { CTA } from "@/components/marketing/CTA";
import { Footer } from "@/components/marketing/Footer";

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-16">
        <PricingTiers />
        <FAQ />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}
