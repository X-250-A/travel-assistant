"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getTrip, deleteTrip, updateTrip } from "@/lib/api";
import TripDetail from "@/components/trip/TripDetail";
import Loading from "@/components/ui/Loading";
import Button from "@/components/ui/Button";
import type { Trip } from "@/types";

/** 单个行程详情页 */
export default function TripDetailPage() {
    const params = useParams();
    const router = useRouter();
    const tripId = Number(params.id);

    const [trip, setTrip] = useState<Trip | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [deleting, setDeleting] = useState(false);
    const [confirming, setConfirming] = useState(false);

    useEffect(() => {
        if (Number.isNaN(tripId)) {
            setError("无效的行程 ID");
            setLoading(false);
            return;
        }
        getTrip(tripId)
            .then(setTrip)
            .catch((err) =>
                setError(err instanceof Error ? err.message : "加载失败")
            )
            .finally(() => setLoading(false));
    }, [tripId]);

    const handleDelete = async () => {
        if (!trip) return;
        if (!window.confirm(`确定删除行程「${trip.title}」吗？`)) return;

        setDeleting(true);
        try {
            await deleteTrip(trip.id);
            router.push("/trips"); // 删完回到列表
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
                <Loading size="lg" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center gap-4">
                <p className="text-red-500">{error}</p>
                <Button variant="secondary" onClick={() => router.back()}>
                    返回
                </Button>
            </div>
        );
    }

    if (!trip) return null;

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-2xl mx-auto px-4 py-8">
                {/* 顶部导航 */}
                <div className="mb-6 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Button variant="secondary" size="sm" onClick={() => router.back()}>
                            ← 返回
                        </Button>
                        <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => router.push("/trips")}
                        >
                            行程列表
                        </Button>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="primary"
                            size="sm"
                            onClick={() => router.push(`/?tripId=${tripId}`)}
                        >
                            💬 继续对话
                        </Button>
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
                        <Button
                            variant="danger"
                            size="sm"
                            loading={deleting}
                            onClick={handleDelete}
                        >
                            删除
                        </Button>
                    </div>
                </div>

                <TripDetail trip={trip} />
            </div>
        </div>
    );
}
