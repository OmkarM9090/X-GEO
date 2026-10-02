import { forwardRef, useId, type InputHTMLAttributes } from "react";
import type { UseFormRegisterReturn } from "react-hook-form";
import { cn } from "@/lib/utils";

interface FloatingFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "placeholder"> {
  label: string;
  registration: UseFormRegisterReturn;
  error?: string;
}

/**
 * Input with a floating label: label sits inside until focus or value,
 * then docks above with an accent tint. Errors render with role="alert".
 */
export const FloatingField = forwardRef<HTMLInputElement, FloatingFieldProps>(
  ({ label, registration, error, type = "text", className, ...rest }, _ref) => {
    const id = useId();
    return (
      <div>
        <div className="relative">
          <input
            {...registration}
            {...rest}
            id={id}
            type={type}
            placeholder=" "
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? `${id}-error` : undefined}
            className={cn(
              "peer h-[54px] w-full rounded-lg border border-border bg-background/60 px-3.5 pb-1.5 pt-[22px] text-body text-foreground",
              "transition-all duration-200 placeholder:text-transparent",
              "hover:border-muted-foreground/30 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/25",
              "aria-[invalid=true]:border-danger aria-[invalid=true]:ring-2 aria-[invalid=true]:ring-danger/20",
              className,
            )}
          />
            <label
              htmlFor={id}
              className={cn(
                "pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-sm text-muted-foreground transition-all duration-200",
                "peer-focus:top-[13px] peer-focus:text-[11px] peer-focus:text-accent",
                "peer-[:not(:placeholder-shown)]:top-[13px] peer-[:not(:placeholder-shown)]:text-[11px]",
              )}
            >
              {label}
            </label>
        </div>
        {error && (
          <p id={`${id}-error`} role="alert" className="mt-1.5 text-xs text-danger">
            {error}
          </p>
        )}
      </div>
    );
  },
);
FloatingField.displayName = "FloatingField";
