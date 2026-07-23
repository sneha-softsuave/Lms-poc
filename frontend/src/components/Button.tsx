import { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "default" | "primary" | "success" | "danger" | "ghost" | "gold";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "sm" | "md";
  /** Shows an inline spinner, swaps the label for `loadingText` and blocks further clicks. */
  loading?: boolean;
  /** Label shown while `loading`. Falls back to the normal children. */
  loadingText?: ReactNode;
  block?: boolean;
  icon?: ReactNode;
}

/**
 * The single button primitive for the app. Everything that can take more than a
 * blink (generate, publish, enrol, submit, ask) goes through this so the busy
 * state looks and behaves identically everywhere.
 */
export function Button({
  variant = "default",
  size = "md",
  loading = false,
  loadingText,
  block = false,
  icon,
  className = "",
  children,
  disabled,
  ...rest
}: ButtonProps) {
  const cls = [
    "btn",
    variant !== "default" && `btn-${variant}`,
    size === "sm" && "btn-sm",
    block && "btn-block",
    loading && "btn-loading",
    className,
  ].filter(Boolean).join(" ");

  return (
    <button className={cls} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {loading ? (
        <>
          <span className="btn-spinner" aria-hidden="true" />
          <span>{loadingText ?? children}</span>
        </>
      ) : (
        <>
          {icon && <span className="btn-icon">{icon}</span>}
          {children}
        </>
      )}
    </button>
  );
}
