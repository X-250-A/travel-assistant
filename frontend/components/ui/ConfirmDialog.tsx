"use client";

import { useEffect, useRef } from "react";

/**
 * ConfirmDialog — 车票主题确认弹窗（替代 window.confirm）
 * 语汇：作废 = 邮戳红；confirm 文案由调用方传入
 */
interface Props {
    open: boolean;
    title?: string;
    message: string;
    confirmLabel?: string;
    cancelLabel?: string;
    danger?: boolean;
    onConfirm: () => void;
    onCancel: () => void;
}

export default function ConfirmDialog({
    open,
    title = "CONFIRM",
    message,
    confirmLabel = "确认",
    cancelLabel = "取消",
    danger = false,
    onConfirm,
    onCancel,
}: Props) {
    const confirmRef = useRef<HTMLButtonElement>(null);

    // 打开时聚焦确认钮 + Esc 取消；打开期间锁滚动
    useEffect(() => {
        if (!open) return;
        confirmRef.current?.focus();
        const onKey = (e: KeyboardEvent) => {
            if (e.key === "Escape") onCancel();
        };
        window.addEventListener("keydown", onKey);
        const prev = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        return () => {
            window.removeEventListener("keydown", onKey);
            document.body.style.overflow = prev;
        };
    }, [open, onCancel]);

    if (!open) return null;

    return (
        <div
            className="fixed inset-0 z-[100] flex items-center justify-center px-4"
            role="dialog"
            aria-modal="true"
            aria-label={message}
        >
            {/* 遮罩：车票米加深 */}
            <div
                className="absolute inset-0 bg-char/40 backdrop-blur-[2px]"
                onClick={onCancel}
                aria-hidden="true"
            />

            {/* 票面卡片 */}
            <div className="relative w-full max-w-sm bg-ticket-face rounded-lg shadow-xl border border-char/15 overflow-hidden">
                {/* 眉标条 */}
                <div className="px-5 pt-4 pb-3 border-b border-dashed border-char/20 flex items-center justify-between">
                    <span
                        className={`font-mono text-[10px] tracking-[0.25em] ${
                            danger ? "text-stamp-red" : "text-gate"
                        }`}
                    >
                        {title}
                    </span>
                    <span className="font-mono text-[9px] tracking-[0.15em] text-mist">
                        PASSAGE
                    </span>
                </div>

                <div className="px-5 py-5">
                    <p className="font-serif text-base text-ink leading-relaxed">{message}</p>
                </div>

                {/* 撕线 */}
                <div className="ticket-nav-perf" aria-hidden="true" />

                <div className="px-5 py-4 flex justify-end gap-2.5">
                    <button
                        onClick={onCancel}
                        className="px-4 py-2 rounded-md font-mono text-xs tracking-[0.1em] text-mist hover:text-ink border border-char/20 hover:border-char/40 transition-colors"
                    >
                        {cancelLabel}
                    </button>
                    <button
                        ref={confirmRef}
                        onClick={onConfirm}
                        className={`px-4 py-2 rounded-md font-mono text-xs tracking-[0.1em] text-paper transition-colors ${
                            danger
                                ? "bg-stamp-red hover:bg-[#a93a24]"
                                : "bg-gate hover:bg-gate-dark"
                        }`}
                    >
                        {confirmLabel}
                    </button>
                </div>
            </div>
        </div>
    );
}
