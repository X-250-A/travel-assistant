"use client";

import { useState } from "react";
import type { Trip, DayPlan } from "@/types";
import Card from "@/components/ui/Card";

interface Props {
    trip: Trip;
}

/** 行程详情：按天展示景点、餐饮、交通 */
export default function TripDetail({ trip }: Props) {
    const { title, plan_data, status, created_at } = trip;

    if (!plan_data) {
        return (
            <Card>
                <p className="text-gray-400 text-center py-8">
                    AI 尚未生成行程内容
                </p>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            {/* 行程概览 */}
            <Card>
                <div className="space-y-2">
                    <h2 className="text-xl font-bold text-gray-800">{title}</h2>

                    <div className="flex flex-wrap gap-2 text-sm text-gray-600">
                        <span>📍 {plan_data.destination}</span>
                        <span>·</span>
                        <span>🗓️ {plan_data.duration} 天</span>
                        {plan_data.budget > 0 && (
                            <>
                                <span>·</span>
                                <span>💰 ¥{plan_data.budget.toLocaleString()}</span>
                            </>
                        )}
                    </div>

                    {plan_data.style.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2">
                            {plan_data.style.map((s) => (
                                <span
                                    key={s}
                                    className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs text-blue-600"
                                >
                                    {s}
                                </span>
                            ))}
                        </div>
                    )}

                    <p className="text-sm text-gray-600 mt-3 leading-relaxed">
                        {plan_data.overview}
                    </p>

                    <p className="text-xs text-gray-400 mt-2">
                        {isConfirmed(status)}
                        创建于 {new Date(created_at).toLocaleDateString("zh-CN")}
                    </p>
                </div>
            </Card>

            {/* 每日行程 — 可折叠 */}
            {plan_data.days.map((day) => (
                <DaySection key={day.day} day={day} />
            ))}

            {/* 总体贴士 */}
            {plan_data.overall_tips && (
                <Card title="💡 出行贴士">
                    <p className="text-sm text-gray-600 whitespace-pre-wrap leading-relaxed">
                        {plan_data.overall_tips}
                    </p>
                </Card>
            )}
        </div>
    );
}

/** 单日行程的可折叠区块 */
function DaySection({ day }: { day: DayPlan }) {
    const [open, setOpen] = useState(true);

    return (
        <Card>
            {/* 标题栏：点击折叠/展开 */}
            <button
                onClick={() => setOpen((v) => !v)}
                className="w-full flex items-center justify-between cursor-pointer"
            >
                <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-gray-700">
                        第 {day.day} 天
                    </span>
                    {day.theme && (
                        <span className="text-sm text-gray-500">— {day.theme}</span>
                    )}
                    {day.date && (
                        <span className="text-xs text-gray-400">{day.date}</span>
                    )}
                </div>
                <span className="text-gray-400 text-sm transition-transform duration-200">
                    {open ? "收起 ▲" : "展开 ▼"}
                </span>
            </button>

            {open && (
                <div className="mt-4 space-y-4">
                    {/* 景点列表 */}
                    {day.attractions.length > 0 && (
                        <div>
                            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                                🏛️ 景点
                            </h4>
                            <div className="space-y-3">
                                {day.attractions.map((attr, i) => (
                                    <div
                                        key={i}
                                        className="border-l-2 border-blue-200 pl-3"
                                    >
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-medium text-gray-800">
                                                {attr.name}
                                            </span>
                                            {attr.type && (
                                                <span className="text-xs text-gray-400 bg-gray-100 rounded px-1.5 py-0.5">
                                                    {attr.type}
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex gap-3 mt-1 text-xs text-gray-500">
                                            {attr.duration_minutes > 0 && (
                                                <span>
                                                    ⏱ {attr.duration_minutes} 分钟
                                                </span>
                                            )}
                                            {attr.cost_yuan > 0 && (
                                                <span>🎫 ¥{attr.cost_yuan}</span>
                                            )}
                                            {attr.transport_from_previous && (
                                                <span>🚶 {attr.transport_from_previous}</span>
                                            )}
                                        </div>
                                        {attr.tips && (
                                            <p className="text-xs text-gray-400 mt-1">
                                                {attr.tips}
                                            </p>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 餐饮推荐 */}
                    {day.meals.length > 0 && (
                        <div>
                            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                                🍽️ 餐饮
                            </h4>
                            <div className="space-y-2">
                                {day.meals.map((meal, i) => (
                                    <div key={i} className="text-sm">
                                        <span className="text-gray-500">
                                            {labelOf(meal.meal_type)}：
                                        </span>
                                        <span className="text-gray-700">
                                            {meal.suggestion}
                                        </span>
                                        {meal.location_near && (
                                            <span className="text-xs text-gray-400 ml-1">
                                                （{meal.location_near}附近）
                                            </span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </Card>
    );
}

/* 辅助函数 */

function isConfirmed(status: string) {
    return status === "confirmed" ? "✅ 已确认 ·" : "📝 草稿 ·";
}

const MEAL_LABELS: Record<string, string> = {
    breakfast: "早餐",
    lunch: "午餐",
    dinner: "晚餐",
    snack: "小吃",
};

function labelOf(mealType: string): string {
    return MEAL_LABELS[mealType] ?? mealType;
}
