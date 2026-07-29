"use client";

interface Props {
    text: string;
}

export default function StreamingText({ text }: Props) {
    return (
        <span className="text-sm text-stone-700 leading-relaxed whitespace-pre-wrap break-words">
            <span className="message-content">{text}</span>
            <span className="inline-block w-0.5 h-4 bg-orange-400 ml-0.5 align-text-bottom animate-pulse rounded-full" />
        </span>
    );
}
