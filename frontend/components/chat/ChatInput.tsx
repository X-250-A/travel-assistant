"use client";

import { useState } from "react";
import type { KeyboardEvent } from "react";

interface Props {
    onSend: (text: string) => void;
    disabled: boolean;
}

export default function ChatInput({ onSend, disabled }: Props) {
    const [text, setText] = useState("");

    const handleSend = () => {
        if (!text.trim() || disabled) return;
        onSend(text);
        setText("");
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter" && !e.nativeEvent.isComposing) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex gap-2.5 items-center">
            <div className="flex-1 relative">
                <input
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={disabled}
                    placeholder="说说你的旅行需求..."
                    className="w-full rounded-2xl border border-stone-200 bg-stone-50 px-5 py-3 text-sm
                               placeholder:text-stone-400 focus:border-orange-300 focus:bg-white focus:outline-none
                               focus:ring-2 focus:ring-orange-100 transition-all duration-200
                               disabled:opacity-50"
                />
            </div>
            <button
                onClick={handleSend}
                disabled={disabled || !text.trim()}
                className="shrink-0 w-11 h-11 rounded-2xl bg-gradient-to-br from-orange-500 to-rose-500
                           text-white flex items-center justify-center shadow-lg shadow-orange-200
                           hover:shadow-orange-300 hover:scale-105 active:scale-95
                           disabled:opacity-40 disabled:shadow-none disabled:hover:scale-100
                           transition-all duration-200"
            >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
            </button>
        </div>
    );
}
