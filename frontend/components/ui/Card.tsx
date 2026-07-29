"use client";

import type { HTMLAttributes } from "react";

interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
    title?: string;
    fullHeight?: boolean;
    variant?: "default" | "glass" | "flat";
    padding?: "sm" | "md" | "lg";
}

const paddingClasses: Record<string, string> = {
    sm: "p-3",
    md: "p-4",
    lg: "p-6",
};

const variantClasses: Record<string, string> = {
    default:
        "bg-white border border-stone-200/80 shadow-sm hover:shadow-md transition-shadow duration-300",
    glass:
        "glass shadow-sm hover:shadow-md transition-shadow duration-300",
    flat:
        "bg-stone-50/80 border border-stone-200/50",
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
            className={`rounded-2xl ${variantClasses[variant]} ${fullHeight ? "h-full" : ""} ${className}`}
            {...rest}
        >
            {title && (
                <div className={`border-b border-stone-100 px-5 py-3.5 ${padding !== "sm" ? "px-5" : "px-3"}`}>
                    <h3 className="text-sm font-semibold text-stone-700 flex items-center gap-2">
                        {title}
                    </h3>
                </div>
            )}
            <div className={paddingClasses[padding]}>{children}</div>
        </div>
    );
}
