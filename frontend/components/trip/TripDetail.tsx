"use client";

import { useState } from "react";
import type { Trip, DayPlan } from "@/types";
import Card from "@/components/ui/Card";
import StatusStamp from "@/components/ui/Stamp";
import EditableTitle from "./EditableTitle";

interface Props {
    trip: Trip;
    onTitleChange?: (trip: Trip) => void;
}

function formatDate(iso: string): string {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function TripDetail({ trip, onTitleChange }: Props) {
    const { title, plan_data, status, created_at } = trip;
    const isConfirmed = status === "confirmed";

    if (!plan_data) {
        return (
            <Card>
                <div className="flex flex-col items-center py-12 text-center">
                    <p className="font-mono text-[11px] tracking-[0.3em] text-mist">NO PRINT</p>
                    <p className="mt-3 font-medium text-ink">票面尚未打印</p>
                    <p className="mt-1 text-xs text-mist">返回对话继续完善行程</p>
                </div>
            </Card>
        );
    }

    return (
        <div className="space-y-5">
            {/* 票面：行程概览 */}
            <Card variant="default">
                {/* 票头：起讫 */}
                <div className="flex items-center justify-between gap-2 font-mono text-[10px] tracking-[0.18em]">
                    <span className="text-ink">TRAVEL PASS — NO.{String(trip.id).padStart(4, "0")}</span>
                    <span className="shrink-0 text-mist">ISSUED {formatDate(created_at)}</span>
                </div>

                <div className="mt-3 flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                        {onTitleChange ? (
                            <EditableTitle trip={trip} onSaved={onTitleChange} />
                        ) : (
                            <h2 className="font-serif text-2xl font-black text-ink">{title}</h2>
                        )}
                        <p className="mt-1.5 font-mono text-[11px] tracking-[0.12em] text-mist truncate">
                            PASSAGE → {plan_data.destination}
                        </p>
                    </div>
                    <StatusStamp confirmed={isConfirmed} size={76} />
                </div>

                {/* 撕票线 */}
                <div className="relative -mx-4 my-4">
                    <div className="border-t-[1.5px] border-dashed border-char/35" />
                    <span aria-hidden="true" className="absolute -left-[9px] -top-[9px] w-[18px] h-[18px] rounded-full bg-paper" />
                    <span aria-hidden="true" className="absolute -right-[9px] -top-[9px] w-[18px] h-[18px] rounded-full bg-paper" />
                </div>

                {/* 票面字段 */}
                <div className="flex flex-wrap gap-x-7 gap-y-3">
                    <TicketField label="DESTINATION 目的地" value={plan_data.destination} />
                    <TicketField label="DAYS 天数" value={`${plan_data.duration} 天`} />
                    {plan_data.budget > 0 && (
                        <TicketField label="BUDGET 预算" value={`¥${plan_data.budget.toLocaleString()}`} />
                    )}
                </div>

                {/* 风格标签：检票员批注 */}
                {plan_data.style.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-1.5">
                        {plan_data.style.map((s) => (
                            <span
                                key={s}
                                className="font-mono text-[10px] tracking-[0.08em] text-stamp-red border border-dashed border-stamp-red/50 rounded px-2 py-0.5"
                            >
                                ※ {s}
                            </span>
                        ))}
                    </div>
                )}

                <p className="mt-4 text-sm leading-relaxed text-char/85">{plan_data.overview}</p>

                <p className="mt-3 font-mono text-[10px] tracking-[0.12em] text-mist">
                    CREATED {formatDate(created_at)}
                </p>
            </Card>

            {/* 逐日行程：站台编号 */}
            <div className="space-y-3">
                {plan_data.days.map((day, idx) => (
                    <DaySection key={day.day} day={day} index={idx} />
                ))}
            </div>

            {/* 出行贴士 */}
            {plan_data.overall_tips && (
                <Card title="NOTES · 出行贴士" variant="flat">
                    <p className="text-sm text-char/85 whitespace-pre-wrap leading-relaxed">
                        {plan_data.overall_tips}
                    </p>
                </Card>
            )}
        </div>
    );
}

function TicketField({ label, value }: { label: string; value: string }) {
    return (
        <div className="min-w-0">
            <div className="font-mono text-[9px] tracking-[0.16em] text-mist">{label}</div>
            <div className="mt-1 font-mono text-[13px] text-ink truncate">{value}</div>
        </div>
    );
}

function DaySection({ day, index }: { day: DayPlan; index: number }) {
    const [open, setOpen] = useState(true);

    return (
        <div className="animate-fade-in-up" style={{ animationDelay: `${index * 70}ms` }}>
            <Card variant="default" padding="none" className="overflow-hidden">
                <button
                    onClick={() => setOpen((v) => !v)}
                    className="w-full flex items-center justify-between gap-3 px-4 py-3.5 text-left cursor-pointer
                               hover:bg-ink/[0.03] transition-colors
                               focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-gate"
                >
                    <div className="flex items-baseline gap-3 min-w-0">
                        <span className="shrink-0 font-mono text-[13px] font-bold tracking-[0.14em] text-gate">
                            DAY {String(day.day).padStart(2, "0")}
                            {day.date ? ` · ${day.date}` : ""}
                        </span>
                        {day.theme && (
                            <span className="font-serif text-[15px] font-bold text-ink truncate">
                                {day.theme}
                            </span>
                        )}
                    </div>
                    <svg
                        className={`w-4 h-4 shrink-0 text-mist transition-transform duration-200 ${open ? "rotate-180" : ""}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                    >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                </button>

                {open && (
                    <div className="px-4 pb-4 pt-4 space-y-4 border-t-[1.5px] border-dashed border-char/30">
                        {/* 景点 */}
                        {day.attractions.length > 0 && (
                            <div>
                                <h4 className="font-mono text-[10px] tracking-[0.25em] text-mist mb-2.5">
                                    STOPS · 景点
                                </h4>
                                <div className="space-y-2">
                                    {day.attractions.map((attr, i) => (
                                        <div
                                            key={i}
                                            className="flex items-start gap-3 rounded-md border border-char/20 bg-ink/[0.025] p-3 hover:border-gate/50 transition-colors"
                                        >
                                            {/* 站序 */}
                                            <span className="shrink-0 w-6 h-6 rounded-[4px] border border-char/40 flex items-center justify-center font-mono text-[11px] text-ink">
                                                {String(i + 1).padStart(2, "0")}
                                            </span>
                                            <div className="min-w-0 flex-1">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="text-sm font-semibold text-ink">
                                                        {attr.name}
                                                    </span>
                                                    {attr.type && (
                                                        <span className="font-mono text-[9px] tracking-[0.12em] text-mist border border-char/25 rounded px-1.5 py-px">
                                                            {attr.type}
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 font-mono text-[10.5px] text-char/60">
                                                    {attr.duration_minutes > 0 && (
                                                        <span>{attr.duration_minutes} MIN</span>
                                                    )}
                                                    {attr.cost_yuan > 0 && (
                                                        <span>¥{attr.cost_yuan}</span>
                                                    )}
                                                    {attr.transport_from_previous && attr.transport_from_previous !== "None" && (
                                                        <span>{attr.transport_from_previous}</span>
                                                    )}
                                                </div>
                                                {attr.tips && (
                                                    <p className="mt-1 text-xs text-mist italic">
                                                        ※ {attr.tips}
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* 餐饮 */}
                        {day.meals.length > 0 && (
                            <div>
                                <h4 className="font-mono text-[10px] tracking-[0.25em] text-mist mb-2.5">
                                    MEALS · 餐饮
                                </h4>
                                <div className="space-y-2">
                                    {day.meals.map((meal, i) => (
                                        <div
                                            key={i}
                                            className="flex items-start gap-2.5 text-sm rounded-md border border-char/20 bg-ink/[0.025] p-2.5"
                                        >
                                            <span className="shrink-0 mt-px font-mono text-[10px] tracking-[0.1em] text-ink border border-char/35 rounded px-1.5 py-0.5">
                                                {MEAL_LABELS[meal.meal_type] ?? meal.meal_type}
                                            </span>
                                            <div className="min-w-0">
                                                <span className="text-char">{meal.suggestion}</span>
                                                {meal.location_near && (
                                                    <span className="ml-1.5 text-[0.7rem] text-mist">
                                                        靠近{meal.location_near}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </Card>
        </div>
    );
}

const MEAL_LABELS: Record<string, string> = {
    breakfast: "早餐",
    lunch: "午餐",
    dinner: "晚餐",
    snack: "小吃",
};
