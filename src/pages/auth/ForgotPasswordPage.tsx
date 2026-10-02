import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, Loader2, Mail } from "lucide-react";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { FloatingField } from "@/components/auth/FloatingField";
import { Button } from "@/components/ui/button";

const forgotSchema = z.object({
  email: z.string().email("Enter the email you signed up with"),
});

type ForgotValues = z.infer<typeof forgotSchema>;

export default function ForgotPasswordPage() {
  const [sentTo, setSentTo] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotValues>({ resolver: zodResolver(forgotSchema), defaultValues: { email: "" } });

  const onSubmit = async (values: ForgotValues) => {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setSentTo(values.email);
  };

  return (
    <AuthLayout
      title={sentTo ? "Check your inbox" : "Reset your password"}
      subtitle={
        sentTo
          ? `If an account exists for ${sentTo}, a reset link is on its way.`
          : "Enter your work email and we'll send a reset link."
      }
      footer={
        <>
          Remembered it?{" "}
          <Link to="/signin" className="font-medium text-accent underline-offset-4 hover:underline">
            Back to sign in
          </Link>
        </>
      }
    >
      {sentTo ? (
        <div className="flex flex-col items-center gap-5 text-center">
          <span className="grid size-14 place-items-center rounded-full border border-success/30 bg-success/10">
            <CheckCircle2 className="size-6 text-success" />
          </span>
          <p className="text-sm text-muted-foreground">
            The link expires in 30 minutes. No email? Check spam, or{" "}
            <button
              type="button"
              onClick={() => setSentTo(null)}
              className="text-accent underline-offset-4 hover:underline"
            >
              try another address
            </button>
            .
          </p>
          <Button variant="outline" asChild className="w-full" size="lg">
            <Link to="/signin">Back to sign in</Link>
          </Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <FloatingField
            label="Work email"
            type="email"
            autoComplete="email"
            registration={register("email")}
            error={errors.email?.message}
          />
          <Button type="submit" variant="accent" className="w-full" size="lg" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Sending link…
              </>
            ) : (
              <>
                <Mail className="size-4" />
                Send reset link
              </>
            )}
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}
