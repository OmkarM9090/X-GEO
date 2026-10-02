import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, LogIn } from "lucide-react";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { FloatingField } from "@/components/auth/FloatingField";
import { Button } from "@/components/ui/button";

const signInSchema = z.object({
  email: z.string().email("Enter a valid work email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

type SignInValues = z.infer<typeof signInSchema>;

export default function SignInPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignInValues>({
    resolver: zodResolver(signInSchema),
    defaultValues: { email: params.get("email") ?? "", password: "" },
  });

  const onSubmit = async () => {
    // Phase 1: mock authentication round-trip.
    await new Promise((resolve) => setTimeout(resolve, 1500));
    navigate("/dashboard");
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to your workspace to see this week's intervals."
      footer={
        <>
          New to X-GEO?{" "}
          <Link to="/signup" className="font-medium text-accent underline-offset-4 hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <FloatingField
          label="Work email"
          type="email"
          autoComplete="email"
          registration={register("email")}
          error={errors.email?.message}
        />
        <div>
          <FloatingField
            label="Password"
            type="password"
            autoComplete="current-password"
            registration={register("password")}
            error={errors.password?.message}
          />
          <div className="mt-2 text-right">
            <Link
              to="/forgot-password"
              className="text-xs text-muted-foreground transition-colors hover:text-accent"
            >
              Forgot password?
            </Link>
          </div>
        </div>

        <Button type="submit" variant="accent" className="w-full" size="lg" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Signing in…
            </>
          ) : (
            <>
              <LogIn className="size-4" />
              Sign in
            </>
          )}
        </Button>

        <p className="pt-1 text-center text-xs text-muted-foreground/80">
          Demo build — any valid-format credentials will do.
        </p>
      </form>
    </AuthLayout>
  );
}
