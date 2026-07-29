"use client";

import { useState } from "react";
import type { Trip, DayPlan } from "@/types";
import Card from "@/components/ui/Card";

interface Props {
    trip: Trip;
}

export default function TripDetail({ trip }: Props) {
    const { title, plan_data, status, created_at } = trip;
    const isConfirmed = status === "confirmed";

    if (!plan_data) {
        return (
            <Card>
                <div className="flex flex-col items-center py-12 text-center">
                    <div className="text-5xl mb-4">📝</div>
                    <p className="text-stone-400">AI 尚未生成行程内容</p>
                    <p className="text-xs text-stone-300 mt-1">返回对话继续完善行程</p>
                </div>
            </Card>
        );
    }

    return (
        <div className="space-y-5">
            {/* 行程概览卡片 */}
            <Card variant="glass">
                <div className="space-y-3">
                    <div className="flex items-start justify-between">
                        <h2 className="text-xl font-bold text-stone-800">{title}</h2>
                        <span
                            className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium ${
                                isConfirmed
                                    ? "bg-emerald-50 text-emerald-600 border border-emerald-200"
                                    : "bg-amber-50 text-amber-600 border border-amber-200"
                            }`}
                        >
                            {isConfirmed ? "✅ 已确认" : "📝 草稿"}
                        </span>
                    </div>

                    {/* 旅程指标 */}
                    <div className="flex flex-wrap gap-4 text-sm">
                        <Metric icon="📍" label="目的地" value={plan_data.destination} />
                        <Metric icon="🗓️" label="天数" value={`${plan_data.duration} 天`} />
                        {plan_data.budget > 0 && (
                            <Metric
                                icon="💰"
                                label="预算"
                                value={`¥${plan_data.budget.toLocaleString()}`}
                            />
                        )}
                    </div>

                    {/* 风格标签 */}
                    {plan_data.style.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                            {plan_data.style.map((s) => (
                                <span
                                    key={s}
                                    className="rounded-full bg-gradient-to-r from-orange-50 to-rose-50 px-3 py-1 text-xs text-orange-600 border border-orange-100"
                                >
                                    {s}
                                </span>
                            ))}
                        </div>
                    )}

                    <p className="text-sm text-stone-600 leading-relaxed pt-1">
                        {plan_data.overview}
                    </p>

                    <p className="text-xs text-stone-400">
                        创建于{" "}
                        {new Date(created_at).toLocaleDateString("zh-CN", {
                            year: "numeric",
                            month: "long",
                            day: "numeric",
                        })}
                    </p>
                </div>
            </Card>

            {/* 每日行程 — 时间线风格 */}
            <div className="relative pl-8">
                {/* 时间线竖线 */}
                <div className="absolute left-[15px] top-4 bottom-4 w-0.5 bg-gradient-to-b from-orange-300 via-rose-300 to-orange-100 rounded-full" />

                <div className="space-y-4">
                    {plan_data.days.map((day, idx) => (
                        <DayTimeline key={day.day} day={day} index={idx} />
                    ))}
                </div>
            </div>

            {/* 出行贴士 */}
            {plan_data.overall_tips && (
                <Card title="💡 出行贴士" variant="flat">
                    <p className="text-sm text-stone-600 whitespace-pre-wrap leading-relaxed">
                        {plan_data.overall_tips}
                    </p>
                </Card>
            )}
        </div>
    );
}

function Metric({ icon, label, value }: { icon: string; label: string; value: string }) {
    return (
        <div className="flex items-center gap-1.5 text-stone-500">
            <span>{icon}</span>
            <span className="text-stone-400">{label}:</span>
            <span className="font-medium text-stone-700">{value}</span>
        </div>
    );
}

function DayTimeline({ day, index }: { day: DayPlan; index: number }) {
    const [open, setOpen] = useState(true);

    return (
        <div className="animate-fade-in-up" style={{ animationDelay: `${index * 80}ms` }}>
            {/* 时间线圆点 */}
            <div className="absolute left-[11px] mt-5 w-[9px] h-[9px] rounded-full bg-gradient-to-br from-orange-400 to-rose-500 shadow-md shadow-orange-200 ring-2 ring-white z-10" />

            <Card variant="glass" className="!p-0 overflow-hidden">
                <button
                    onClick={() => setOpen((v) => !v)}
                    className="w-full flex items-center justify-between px-4 py-3.5 cursor-pointer hover:bg-white/50 transition-colors"
                >
                    <div className="flex items-center gap-3">
                        <span className="text-sm font-bold text-stone-700">
                            第 {day.day} 天
                        </span>
                        {day.theme && (
                            <span className="text-sm text-orange-600 font-medium">
                                {day.theme}
                            </span>
                        )}
                    </div>
                    <svg
                        className={`w-4 h-4 text-stone-400 transition-transform duration-300 ${open ? "rotate-180" : ""}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                    >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                </button>

                {open && (
                    <div className="px-4 pb-4 space-y-4 border-t border-stone-100 pt-4">
                        {/* 景点 */}
                        {day.attractions.length > 0 && (
                            <div>
                                <h4 className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                                    <span className="text-base">🏛️</span> 景点
                                </h4>
                                <div className="space-y-2.5">
                                    {day.attractions.map((attr, i) => (
                                        <div
                                            key={i}
                                            className="flex items-start gap-3 bg-stone-50/80 rounded-xl p-3 hover:bg-orange-50/50 transition-colors"
                                        >
                                            {/* 序号 */}
                                            <div className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-orange-400 to-rose-400 flex items-center justify-center text-xs text-white font-semibold shadow-sm">
                                                {i + 1}
                                            </div>
                                            <div className="min-w-0 flex-1">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="text-sm font-semibold text-stone-800">
                                                        {attr.name}
                                                    </span>
                                                    {attr.type && (
                                                        <span className="text-[0.6rem] text-stone-400 bg-stone-200/70 rounded-full px-2 py-0.5 uppercase tracking-wide">
                                                            {attr.type}
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="flex flex-wrap gap-2 mt-1.5">
                                                    {attr.duration_minutes > 0 && (
                                                        <span className="text-[0.7rem] text-stone-500 flex items-center gap-1">
                                                            <span className="inline-block w-1 h-1 rounded-full bg-orange-400" />
                                                            {attr.duration_minutes} 分钟
                                                        </span>
                                                    )}
                                                    {attr.cost_yuan > 0 && (
                                                        <span className="text-[0.7rem] text-stone-500 flex items-center gap-1">
                                                            <span className="inline-block w-1 h-1 rounded-full bg-emerald-400" />
                                                            ¥{attr.cost_yuan}
                                                        </span>
                                                    )}
                                                    {attr.transport_from_previous && attr.transport_from_previous !== "None" && (
                                                        <span className="text-[0.7rem] text-stone-400 flex items-center gap-1">
                                                            <span className="inline-block w-1 h-1 rounded-full bg-sky-400" />
                                                            {attr.transport_from_previous}
                                                        </span>
                                                    )}
                                                </div>
                                                {attr.tips && (
                                                    <p className="text-[0.7rem] text-stone-400 mt-1.5 italic">
                                                        💬 {attr.tips}
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
                                <h4 className="text-xs font-semibold text-stone-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                                    <span className="text-base">🍽️</span> 餐饮推荐
                                </h4>
                                <div className="space-y-2">
                                    {day.meals.map((meal, i) => (
                                        <div
                                            key={i}
                                            className="flex items-start gap-2.5 text-sm bg-stone-50/80 rounded-xl p-2.5"
                                        >
                                            <span className="shrink-0 text-xs font-medium text-orange-500 bg-orange-50 rounded-lg px-2 py-0.5">
                                                {MEAL_LABELS[meal.meal_type] ?? meal.meal_type}
                                            </span>
                                            <div className="min-w-0">
                                                <span className="text-stone-700">{meal.suggestion}</span>
                                                {meal.location_near && (
                                                    <span className="text-[0.65rem] text-stone-400 ml-1.5">
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
