"use client";

import { useState } from "react";
import type { Trip } from "@/types";
import { deleteTrip } from "@/lib/api";
import Card from "@/components/ui/Card";
import Link from "next/link";

interface Props {
    trip: Trip;
    onDeleted?: () => void;
}

export default function TripCard({ trip, onDeleted }: Props) {
    const { id, title, plan_data, status, created_at } = trip;
    const isConfirmed = status === "confirmed";
    const [deleting, setDeleting] = useState(false);

    const handleDelete = async (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();

        if (!window.confirm(`确定删除行程「${title}」吗？`)) return;

        setDeleting(true);
        try {
            await deleteTrip(id);
            onDeleted?.();
        } catch (err) {
            alert(err instanceof Error ? err.message : "删除失败");
        } finally {
            setDeleting(false);
        }
    };

    return (
        <Link href={`/trips/${id}`} className="block group">
            <Card className="cursor-pointer !p-0 overflow-hidden hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300">
                {/* 顶部渐变条 */}
                <div
                    className={`h-1.5 w-full ${
                        isConfirmed
                            ? "bg-gradient-to-r from-emerald-400 to-teal-500"
                            : "bg-gradient-to-r from-amber-400 to-orange-500"
                    }`}
                />

                <div className="p-4">
                    <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 mb-1">
                                <h3 className="text-base font-semibold text-stone-800 truncate">
                                    {title}
                                </h3>
                            </div>

                            {plan_data?.destination && (
                                <p className="text-sm text-stone-500 mb-0.5">
                                    📍 {plan_data.destination}
                                    {plan_data.duration ? ` · ${plan_data.duration} 天` : ""}
                                    {plan_data.budget > 0 ? ` · ¥${plan_data.budget.toLocaleString()}` : ""}
                                </p>
                            )}

                            <p className="text-xs text-stone-400 mt-1.5">
                                {new Date(created_at).toLocaleDateString("zh-CN", {
                                    year: "numeric",
                                    month: "long",
                                    day: "numeric",
                                })}
                            </p>
                        </div>

                        <div className="flex flex-col items-end gap-2 shrink-0">
                            <span
                                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                                    isConfirmed
                                        ? "bg-emerald-50 text-emerald-600 border border-emerald-200"
                                        : "bg-amber-50 text-amber-600 border border-amber-200"
                                }`}
                            >
                                {isConfirmed ? "已确认" : "草稿"}
                            </span>

                            {plan_data?.style && plan_data.style.length > 0 && (
                                <div className="flex flex-wrap gap-1 justify-end">
                                    {plan_data.style.slice(0, 3).map((s) => (
                                        <span
                                            key={s}
                                            className="text-[0.65rem] text-stone-400 bg-stone-100 rounded-full px-2 py-0.5"
                                        >
                                            {s}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* 删除按钮 */}
                    <button
                        onClick={handleDelete}
                        disabled={deleting}
                        className="absolute top-3 right-3 z-[5] p-1.5 rounded-lg text-stone-400
                                   hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100
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
            </Card>
        </Link>
    );
}
