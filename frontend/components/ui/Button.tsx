"use client";

import type { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "secondary" | "danger" | "ghost" | "accent";
    size?: "sm" | "md" | "lg";
    loading?: boolean;
}

const variantClasses: Record<string, string> = {
    primary:
        "bg-gate text-[#FFFDF7] shadow-[0_10px_22px_-12px_rgba(229,106,31,0.7)] hover:bg-gate-dark active:scale-[0.97]",
    secondary:
        "bg-ticket-face text-ink border border-char/35 shadow-sm hover:border-gate hover:text-gate",
    danger:
        "bg-stamp-red text-[#FFFDF7] shadow-[0_10px_22px_-12px_rgba(200,68,42,0.6)] hover:bg-[#B03A22] active:scale-[0.97]",
    ghost:
        "text-mist hover:text-ink hover:bg-ink/[0.06]",
    accent:
        "bg-ink text-ticket-face shadow-[0_10px_22px_-14px_rgba(22,50,79,0.8)] hover:bg-[#0F2438] active:scale-[0.97]",
};

const sizeClasses: Record<string, string> = {
    sm: "px-3.5 py-1.5 text-sm rounded-md",
    md: "px-5 py-2.5 text-sm font-medium rounded-lg",
    lg: "px-8 py-3.5 text-base font-semibold rounded-lg",
};

export default function Button({
    variant = "primary",
    size = "md",
    loading = false,
    children,
    disabled,
    className = "",
    ...rest
}: ButtonProps) {
    const isDisabled = disabled || loading;

    return (
        <button
            disabled={isDisabled}
            className={`inline-flex items-center justify-center gap-2 transition-all duration-200
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gate focus-visible:ring-offset-2 focus-visible:ring-offset-paper
            ${isDisabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"}
            ${variantClasses[variant]}
            ${sizeClasses[size]}
            ${className}`}
            {...rest}
        >
            {loading && (
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
            )}
            {children}
        </button>
    );
}
