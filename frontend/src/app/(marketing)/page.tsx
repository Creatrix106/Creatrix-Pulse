import { FeaturesSection } from "@/features/marketing/components/features-section";
import { FinalCta } from "@/features/marketing/components/final-cta";
import { HeroSection } from "@/features/marketing/components/hero-section";
import { HowItWorksSection } from "@/features/marketing/components/how-it-works-section";
import { ShowcaseSection } from "@/features/marketing/components/showcase-section";
import { ValueSection } from "@/features/marketing/components/value-section";

export default function LandingPage() {
  return (
    <>
      <HeroSection />
      <ValueSection />
      <FeaturesSection />
      <HowItWorksSection />
      <ShowcaseSection />
      <FinalCta />
    </>
  );
}
