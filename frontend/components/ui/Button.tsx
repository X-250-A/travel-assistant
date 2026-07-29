"use client";

import type { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "secondary" | "danger" | "ghost" | "accent";
    size?: "sm" | "md" | "lg";
    loading?: boolean;
}

const variantClasses: Record<string, string> = {
    primary:
        "bg-gradient-to-r from-orange-500 to-rose-500 text-white shadow-lg shadow-orange-200 hover:shadow-orange-300 hover:from-orange-600 hover:to-rose-600 active:scale-[0.97]",
    secondary:
        "bg-white text-stone-700 border border-stone-200 hover:border-orange-300 hover:text-orange-600 hover:bg-orange-50 shadow-sm",
    danger:
        "bg-gradient-to-r from-red-500 to-red-600 text-white shadow-lg shadow-red-200 hover:shadow-red-300 hover:from-red-600 hover:to-red-700 active:scale-[0.97]",
    ghost:
        "text-stone-500 hover:text-orange-600 hover:bg-orange-50",
    accent:
        "bg-gradient-to-r from-sky-500 to-cyan-500 text-white shadow-lg shadow-sky-200 hover:shadow-sky-300 hover:from-sky-600 hover:to-cyan-600 active:scale-[0.97]",
};

const sizeClasses: Record<string, string> = {
    sm: "px-3.5 py-1.5 text-sm rounded-lg",
    md: "px-5 py-2.5 text-sm font-medium rounded-xl",
    lg: "px-8 py-3.5 text-base font-semibold rounded-xl",
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
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400 focus-visible:ring-offset-2
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
