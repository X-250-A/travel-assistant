"use client";

import type { HTMLAttributes } from "react";

interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
    title?: string;
    fullHeight?: boolean;
    variant?: "default" | "glass" | "flat";
    padding?: "sm" | "md" | "lg" | "none";
}

const paddingClasses: Record<string, string> = {
    sm: "p-3",
    md: "p-4",
    lg: "p-6",
    none: "p-0",
};

const variantClasses: Record<string, string> = {
    default:
        "bg-ticket-face border border-char/30 shadow-[0_10px_24px_-18px_rgba(38,34,28,0.45)]",
    glass:
        "glass shadow-sm",
    flat:
        "bg-ink/[0.035] border border-char/20",
};

export default function Card({
    title,
    fullHeight = false,
    variant = "default",
    padding = "md",
    children,
    className = "",
    ...rest
}: CardProps) {
    return (
        <div
            className={`rounded-lg ${variantClasses[variant]} ${fullHeight ? "h-full" : ""} ${className}`}
            {...rest}
        >
            {title && (
                <div className={`border-b border-char/15 px-5 py-3.5 ${padding !== "sm" ? "px-5" : "px-3"}`}>
                    <h3 className="font-mono text-xs tracking-[0.18em] text-mist flex items-center gap-2">
                        {title}
                    </h3>
                </div>
            )}
            <div className={paddingClasses[padding]}>{children}</div>
        </div>
    );
}
