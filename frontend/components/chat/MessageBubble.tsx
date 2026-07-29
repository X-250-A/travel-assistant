"use client";

import type { Message } from "@/types";

interface Props {
    message: Message;
}

export default function MessageBubble({ message }: Props) {
    const isUser = message.role === "user";

    return (
        <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
            {/* 头像 */}
            {!isUser && (
                <div className="shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-orange-400 to-rose-400 flex items-center justify-center mr-2.5 shadow-sm">
                    <span className="text-white text-xs">🤖</span>
                </div>
            )}

            <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    isUser
                        ? "bg-gradient-to-br from-orange-500 to-rose-500 text-white rounded-br-md shadow-md shadow-orange-200"
                        : "bg-white border border-stone-100 rounded-bl-md shadow-sm text-stone-700"
                }`}
            >
                <div className="message-content whitespace-pre-wrap break-words">
                    {message.content}
                </div>
                <div className={`text-[0.65rem] mt-1.5 ${isUser ? "text-orange-100" : "text-stone-400"}`}>
                    {formatTime(message.created_at)}
                </div>
            </div>

            {isUser && (
                <div className="shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center ml-2.5 shadow-sm">
                    <span className="text-white text-xs">👤</span>
                </div>
            )}
        </div>
    );
}

function formatTime(iso: string): string {
    try {
        const d = new Date(iso);
        return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
    } catch {
        return "";
    }
}
