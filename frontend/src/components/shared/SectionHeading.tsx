import type { ReactNode } from "react";
import { SplitTextReveal, type SplitTextAnimation, type SplitTextType } from "@/components/animations/SplitTextReveal";
import { cn } from "@/lib/utils";

interface SectionHeadingProps {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  id?: string;
  as?: "h1" | "h2" | "h3";
  align?: "left" | "center";
  size?: "display" | "h1" | "h2";
  reveal?: boolean;
  animation?: SplitTextAnimation;
  split?: SplitTextType;
  className?: string;
  titleClassName?: string;
  descriptionClassName?: string;
}

/** Shared marketing section heading hierarchy. */
export function SectionHeading({
  eyebrow,
  title,
  description,
  id,
  as = "h2",
  align = "center",
  size = "display",
  reveal = true,
  animation = "rise",
  split = "lines",
  className,
  titleClassName,
  descriptionClassName,
}: SectionHeadingProps) {
  const alignClass = align === "center" ? "mx-auto text-center" : "text-left";
  const titleStyles = cn(
    "font-heading text-foreground",
    size === "display" && "text-display",
    size === "h1" && "text-h1",
    size === "h2" && "text-h2",
    titleClassName,
  );

  return (
    <div className={cn("max-w-3xl", alignClass, className)}>
      {eyebrow && (
        <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-accent">
          {eyebrow}
        </p>
      )}
      {reveal ? (
        <SplitTextReveal
          as={as}
          id={id}
          type={split}
          animation={animation}
          trigger="scroll"
          threshold={0.18}
          className={cn("mt-4", titleStyles)}
        >
          {title}
        </SplitTextReveal>
      ) : (
        <HeadingTag as={as} id={id} className={cn("mt-4", titleStyles)}>{title}</HeadingTag>
      )}
      {description && (
        <p className={cn("mt-5 text-body-lg text-muted-foreground", descriptionClassName)}>
          {description}
        </p>
      )}
    </div>
  );
}

function HeadingTag({ as, children, id, className }: { as: "h1" | "h2" | "h3"; children: ReactNode; id?: string; className?: string }) {
  if (as === "h1") return <h1 id={id} className={className}>{children}</h1>;
  if (as === "h3") return <h3 id={id} className={className}>{children}</h3>;
  return <h2 id={id} className={className}>{children}</h2>;
}
