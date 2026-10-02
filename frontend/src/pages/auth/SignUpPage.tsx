import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Sparkles } from "lucide-react";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { FloatingField } from "@/components/auth/FloatingField";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const signUpSchema = z
  .object({
    name: z.string().min(2, "Tell us your name"),
    email: z.string().email("Enter a valid work email"),
    company: z.string().optional(),
    password: z
      .string()
      .min(8, "At least 8 characters")
      .regex(/\d/, "Include at least one number"),
    confirm: z.string(),
    terms: z.boolean().refine((v) => v, "Please accept the terms to continue"),
  })
  .refine((values) => values.password === values.confirm, {
    message: "Passwords don't match",
    path: ["confirm"],
  });

type SignUpValues = z.infer<typeof signUpSchema>;

export default function SignUpPage() {
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignUpValues>({
    resolver: zodResolver(signUpSchema),
    defaultValues: { name: "", email: "", company: "", password: "", confirm: "", terms: false },
  });

  const onSubmit = async () => {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    navigate("/dashboard");
  };

  return (
    <AuthLayout
      title="Create your workspace"
      subtitle="Ten free Monte Carlo audits. First interval in under an hour."
      footer={
        <>
          Already measuring?{" "}
          <Link to="/signin" className="font-medium text-accent underline-offset-4 hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <FloatingField
          label="Full name"
          autoComplete="name"
          registration={register("name")}
          error={errors.name?.message}
        />
        <FloatingField
          label="Work email"
          type="email"
          autoComplete="email"
          registration={register("email")}
          error={errors.email?.message}
        />
        <FloatingField
          label="Company (optional)"
          autoComplete="organization"
          registration={register("company")}
          error={errors.company?.message}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <FloatingField
            label="Password"
            type="password"
            autoComplete="new-password"
            registration={register("password")}
            error={errors.password?.message}
          />
          <FloatingField
            label="Confirm"
            type="password"
            autoComplete="new-password"
            registration={register("confirm")}
            error={errors.confirm?.message}
          />
        </div>

        <div>
          <label className="flex cursor-pointer items-start gap-2.5 text-xs text-muted-foreground">
            <input
              type="checkbox"
              {...register("terms")}
              className={cn(
                "mt-0.5 size-4 shrink-0 cursor-pointer rounded border-border bg-background",
                "accent-[hsl(var(--accent))]",
              )}
            />
            <span>
              I agree to the{" "}
              <Link to="/docs#terms" className="text-accent underline-offset-4 hover:underline">
                Terms of Service
              </Link>{" "}
              and{" "}
              <Link to="/docs#privacy" className="text-accent underline-offset-4 hover:underline">
                Privacy Policy
              </Link>
              .
            </span>
          </label>
          {errors.terms?.message && (
            <p role="alert" className="mt-1.5 text-xs text-danger">
              {errors.terms.message}
            </p>
          )}
        </div>

        <Button type="submit" variant="accent" className="w-full" size="lg" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Creating workspace…
            </>
          ) : (
            <>
              <Sparkles className="size-4" />
              Start Free Audit
            </>
          )}
        </Button>
      </form>
    </AuthLayout>
  );
}
