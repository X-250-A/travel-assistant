"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getTrip, deleteTrip, updateTrip } from "@/lib/api";
import TripDetail from "@/components/trip/TripDetail";
import Loading from "@/components/ui/Loading";
import Button from "@/components/ui/Button";
import Link from "next/link";
import type { Trip } from "@/types";

export default function TripDetailPage() {
    const params = useParams();
    const router = useRouter();
    const tripId = Number(params.id);
    const invalidId = Number.isNaN(tripId);

    const [trip, setTrip] = useState<Trip | null>(null);
    const [loading, setLoading] = useState(!invalidId);
    const [error, setError] = useState(invalidId ? "无效的行程 ID" : "");
    const [deleting, setDeleting] = useState(false);
    const [confirming, setConfirming] = useState(false);

    useEffect(() => {
        if (invalidId) return;
        getTrip(tripId)
            .then(setTrip)
            .catch((err) =>
                setError(err instanceof Error ? err.message : "加载失败")
            )
            .finally(() => setLoading(false));
    }, [tripId, invalidId]);

    const handleDelete = async () => {
        if (!trip) return;
        if (!window.confirm(`确定删除行程「${trip.title}」吗？`)) return;

        setDeleting(true);
        try {
            await deleteTrip(trip.id);
            router.push("/trips");
        } catch (err) {
            alert(err instanceof Error ? err.message : "删除失败");
        } finally {
            setDeleting(false);
        }
    };

    const handleConfirm = async () => {
        if (!trip || trip.status === "confirmed") return;
        setConfirming(true);
        try {
            const updated = await updateTrip(trip.id, { status: "confirmed" });
            setTrip(updated);
        } catch (err) {
            alert(err instanceof Error ? err.message : "确认失败");
        } finally {
            setConfirming(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loading size="lg" text="加载行程详情..." />
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center gap-4">
                <div className="text-5xl mb-2">😕</div>
                <p className="text-red-500 text-sm">{error}</p>
                <Button variant="secondary" size="sm" onClick={() => router.back()}>
                    ← 返回
                </Button>
            </div>
        );
    }

    if (!trip) return null;

    return (
        <div className="min-h-screen">
            {/* 顶栏 */}
            <header className="glass-strong sticky top-0 z-50 border-b border-white/50">
                <div className="max-w-2xl mx-auto flex items-center justify-between px-4 py-3">
                    <div className="flex items-center gap-2">
                        <Link href="/trips" className="text-sm text-stone-400 hover:text-orange-500 transition-colors flex items-center gap-1">
                            <span>←</span> 行程列表
                        </Link>
                    </div>
                    <Link href="/" className="flex items-center gap-2">
                        <span className="text-xl">✈️</span>
                        <span className="text-lg font-bold gradient-text">旅游助手</span>
                    </Link>
                </div>
            </header>

            <div className="max-w-2xl mx-auto px-4 py-8">
                {/* 操作栏 */}
                <div className="mb-6 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Link href={`/?tripId=${tripId}`}>
                            <Button variant="accent" size="sm">
                                💬 继续对话
                            </Button>
                        </Link>
                        {trip.status === "draft" && (
                            <Button
                                variant="primary"
                                size="sm"
                                loading={confirming}
                                onClick={handleConfirm}
                            >
                                ✅ 确认行程
                            </Button>
                        )}
                    </div>
                    <Button
                        variant="danger"
                        size="sm"
                        loading={deleting}
                        onClick={handleDelete}
                    >
                        删除
                    </Button>
                </div>

                <TripDetail trip={trip} />
            </div>
        </div>
    );
}
