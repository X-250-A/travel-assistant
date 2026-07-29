"use client";

interface LoadingProps {
    size?: "sm" | "md" | "lg";
    text?: string;
}

const spinnerSize: Record<string, string> = {
    sm: "w-5 h-5",
    md: "w-10 h-10",
    lg: "w-16 h-16",
};

const textSize: Record<string, string> = {
    sm: "text-xs",
    md: "text-sm",
    lg: "text-base",
};

export default function Loading({ size = "md", text = "加载中..." }: LoadingProps) {
    return (
        <div className="flex flex-col items-center justify-center gap-3 py-8">
            <div className={`relative ${spinnerSize[size]}`}>
                <div
                    className={`absolute inset-0 rounded-full border-4 border-orange-100`}
                />
                <div
                    className={`absolute inset-0 rounded-full border-4 border-transparent border-t-orange-500 animate-spin`}
                />
            </div>
            <p className={`text-stone-400 font-medium ${textSize[size]}`}>{text}</p>
        </div>
    );
}
