"use client";

import { useState } from "react";
import type { Trip } from "@/types";
import { deleteTrip } from "@/lib/api";
import StatusStamp from "@/components/ui/Stamp";
import Barcode from "@/components/ui/Barcode";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import Link from "next/link";

interface Props {
    trip: Trip;
    onDeleted?: () => void;
}

const STUB_WIDTH = 84;

function formatDate(iso: string): string {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** 由行程号派生一个稳定的座位号（07A 风格） */
function seatOf(id: number): string {
    return `${String((id % 60) + 1).padStart(2, "0")}${"ACDF"[id % 4]}`;
}

export default function TripCard({ trip, onDeleted }: Props) {
    const { id, title, plan_data, status, created_at } = trip;
    const isConfirmed = status === "confirmed";
    const [deleting, setDeleting] = useState(false);
    const [confirmOpen, setConfirmOpen] = useState(false);
    const [toast, setToast] = useState("");

    // 点作废 → 弹主题化确认框；确认后真正删除
    const handleDelete = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setConfirmOpen(true);
    };

    const handleConfirmDelete = async () => {
        setConfirmOpen(false);
        setDeleting(true);
        try {
            await deleteTrip(id);
            onDeleted?.();
        } catch (err) {
            setConfirmOpen(false);
            setToast(err instanceof Error ? err.message : "删除失败");
        } finally {
            setDeleting(false);
        }
    };

    const station = plan_data?.destination || title;
    const rideDate = formatDate(created_at);
    const seat = seatOf(id);

    return (
        <>
            <Link href={`/trips/${id}`} className="block group">
                {/* 一张车票：左主票面 + 右撕票副联 */}
                <div className="relative flex bg-ticket-face border border-char rounded-lg shadow-[0_14px_28px_-22px_rgba(38,34,28,0.5)] cursor-pointer transition-all duration-200 group-hover:-translate-y-0.5 group-hover:shadow-[0_18px_34px_-20px_rgba(38,34,28,0.55)]">
                {/* 主票面 */}
                <div className="relative flex-1 min-w-0 px-4 py-3.5">
                    <div className="pr-14 font-mono text-[9px] tracking-[0.18em] text-mist">
                        TRIP NO. {String(id).padStart(4, "0")} · {rideDate} 乘车
                    </div>

                    <h3 className="mt-1.5 pr-14 font-serif text-xl font-black text-ink truncate">
                        {station}
                    </h3>

                    {station !== title && (
                        <p className="mt-0.5 pr-14 text-xs text-char/70 truncate">{title}</p>
                    )}

                    <div className="mt-2.5 flex items-end justify-between gap-3">
                        <div className="flex gap-6">
                            {plan_data?.duration ? (
                                <div>
                                    <div className="font-mono text-[9px] tracking-[0.14em] text-mist">DAYS 天数</div>
                                    <div className="mt-0.5 font-mono text-xs text-ink">{plan_data.duration} 天</div>
                                </div>
                            ) : null}
                            {plan_data?.budget ? (
                                <div>
                                    <div className="font-mono text-[9px] tracking-[0.14em] text-mist">BUDGET 预算</div>
                                    <div className="mt-0.5 font-mono text-xs text-ink">¥{plan_data.budget.toLocaleString()}</div>
                                </div>
                            ) : null}
                        </div>

                        {plan_data?.style && plan_data.style.length > 0 && (
                            <div className="hidden sm:flex flex-wrap gap-1 justify-end max-w-[45%]">
                                {plan_data.style.slice(0, 2).map((s) => (
                                    <span
                                        key={s}
                                        className="font-mono text-[9px] text-mist border border-dashed border-char/30 rounded px-1.5 py-0.5 whitespace-nowrap"
                                    >
                                        {s}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* 状态章 */}
                    <div className="absolute right-3 top-3">
                        <StatusStamp confirmed={isConfirmed} size={52} />
                    </div>
                </div>

                {/* 副联（撕票线右侧） */}
                <div
                    className="flex flex-col items-center justify-between shrink-0 py-3"
                    style={{ width: STUB_WIDTH, borderLeft: "1.5px dashed rgba(38, 34, 28, 0.4)" }}
                >
                    <span className="font-mono text-[9px] tracking-[0.18em] text-mist">GATE B12</span>
                    <span className="font-mono text-lg font-bold text-ink">{seat}</span>
                    <Barcode className="h-3.5" color="rgba(38, 34, 28, 0.55)" />
                </div>

                {/* 打孔缺口（骑在撕线与票缘交点） */}
                <span
                    aria-hidden="true"
                    className="absolute w-[18px] h-[18px] rounded-full bg-paper"
                    style={{ left: `calc(100% - ${STUB_WIDTH + 9}px)`, top: -9 }}
                />
                <span
                    aria-hidden="true"
                    className="absolute w-[18px] h-[18px] rounded-full bg-paper"
                    style={{ left: `calc(100% - ${STUB_WIDTH + 9}px)`, bottom: -9 }}
                />

                {/* 删除（作废）按钮 */}
                <button
                    type="button"
                    onClick={handleDelete}
                    disabled={deleting}
                    className="absolute top-1.5 right-1.5 z-10 p-1.5 rounded-full bg-ticket-face/95 border border-char/25 text-char/60
                               hover:text-stamp-red hover:border-stamp-red/60
                               opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 max-sm:opacity-100
                               focus-visible:opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-gate
                               transition-all duration-200"
                    title="删除行程"
                >
                    {deleting ? (
                        <svg className="animate-spin w-3.5 h-3.5" viewBox="0 0 24 24" fill="none">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                    ) : (
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    )}
                </button>
            </div>
            </Link>

            {/* 主题化删除确认弹窗（替代 window.confirm） */}
            <ConfirmDialog
                open={confirmOpen}
                title="VOID · 作废确认"
                message={`确定将车票「${station}」作废吗？此操作无法撤销。`}
                confirmLabel="作废"
                cancelLabel="保留"
                danger
                onConfirm={handleConfirmDelete}
                onCancel={() => setConfirmOpen(false)}
            />

            {/* 删除失败内嵌提示（替代 alert） */}
            {toast && (
                <div className="mt-2 flex items-center gap-2 rounded-md border border-stamp-red/40 bg-stamp-red/5 px-3 py-2">
                    <span className="font-mono text-[10px] tracking-[0.2em] text-stamp-red shrink-0">ERR</span>
                    <span className="text-xs text-ink/80">{toast}</span>
                    <button
                        type="button"
                        onClick={() => setToast("")}
                        className="ml-auto font-mono text-[10px] text-mist hover:text-ink"
                    >
                        ×
                    </button>
                </div>
            )}
        </>
    );
}
