import { useSplitText } from "@/hooks/useSplitText";
import { useReveal } from "@/hooks/useScrollTrigger";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { FAQ_ITEMS } from "@/data/faq";

export function FAQ() {
  const headlineRef = useSplitText<HTMLHeadingElement>({ kind: "lines" });
  const listRef = useReveal<HTMLDivElement>({ stagger: 0.05, y: 16 });

  return (
    <section id="faq" className="py-24 md:py-32">
      <div className="mx-auto grid w-full max-w-7xl gap-12 px-4 sm:px-6 lg:grid-cols-[1fr_1.6fr] lg:gap-20 lg:px-8">
        <div>
          <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-accent">
            FAQ
          </p>
          <h2 ref={headlineRef} className="mt-4 font-heading text-h1 text-foreground">
            Precision questions, straight answers.
          </h2>
          <p className="mt-5 text-body text-muted-foreground">
            The math behind the product, the data policy behind the crawler. Something else?{" "}
            <a href="mailto:hello@xgeo.dev" className="text-accent underline-offset-4 hover:underline">
              hello@xgeo.dev
            </a>
          </p>
        </div>

        <div ref={listRef}>
          <Accordion type="single" collapsible defaultValue="item-0">
            {FAQ_ITEMS.map((item, i) => (
              <AccordionItem key={item.question} value={`item-${i}`} data-reveal>
                <AccordionTrigger>{item.question}</AccordionTrigger>
                <AccordionContent>{item.answer}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </section>
  );
}
