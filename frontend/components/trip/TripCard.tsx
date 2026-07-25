"use client";

import { useState } from "react";
import type { Trip } from "@/types";
import { deleteTrip } from "@/lib/api";
import Card from "@/components/ui/Card";
import Link from "next/link";

interface Props {
    trip: Trip;
    onDeleted?: () => void;  // 删除后通知父组件刷新列表
}

/** 行程摘要卡片，用于列表展示 */
export default function TripCard({ trip, onDeleted }: Props) {
    const { id, title, plan_data, status, created_at } = trip;
    const isConfirmed = status === "confirmed";
    const [deleting, setDeleting] = useState(false);

    const handleDelete = async (e: React.MouseEvent) => {
        e.preventDefault();      // 阻止 Link 跳转
        e.stopPropagation();     // 防止事件冒泡

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
        <div className="relative group">
            {/* 删除按钮：鼠标悬停卡片时显示 */}
            <button
                onClick={handleDelete}
                disabled={deleting}
                className="absolute top-2 right-2 z-10 p-1 rounded-md text-gray-400
                           hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100
                           transition-all disabled:opacity-50"
                title="删除行程"
            >
                {deleting ? "⏳" : "✕"}
            </button>

            <Link href={`/trips/${id}`}>
                <Card className="cursor-pointer hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between gap-3">
                        {/* 左侧：标题 + 目的地 + 日期 */}
                        <div className="min-w-0 flex-1">
                            <h3 className="text-base font-semibold text-gray-800 truncate pr-6">
                                {title}
                            </h3>
                            {plan_data?.destination && (
                                <p className="text-sm text-gray-500 mt-1">
                                    📍 {plan_data.destination}
                                    {plan_data.duration
                                        ? ` · ${plan_data.duration} 天`
                                        : ""}
                                </p>
                            )}
                            <p className="text-xs text-gray-400 mt-1.5">
                                {new Date(created_at).toLocaleDateString("zh-CN")}
                            </p>
                        </div>

                        {/* 右侧：状态标签 */}
                        <span
                            className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                                isConfirmed
                                    ? "bg-green-100 text-green-700"
                                    : "bg-yellow-100 text-yellow-700"
                            }`}
                        >
                            {isConfirmed ? "已确认" : "草稿"}
                        </span>
                    </div>
                </Card>
            </Link>
        </div>
    );
}
