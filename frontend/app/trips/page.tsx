"use client";

import { useEffect, useState } from "react";
import { listTrip } from "@/lib/api";
import TripCard from "@/components/trip/TripCard";
import Loading from "@/components/ui/Loading";
import Button from "@/components/ui/Button";
import { useRouter } from "next/navigation";
import type { Trip } from "@/types";

/** 行程列表页 */
export default function TripsPage() {
    const router = useRouter();
    const [trips, setTrips] = useState<Trip[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        listTrip()
            .then((res) => setTrips(res.trips))
            .catch((err) => setError(err instanceof Error ? err.message : "加载失败"))
            .finally(() => setLoading(false));
    }, []);

    /* 加载中 */
    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loading size="lg" />
            </div>
        );
    }

    /* 加载出错 */
    if (error) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center gap-4">
                <p className="text-red-500">{error}</p>
                <Button variant="secondary" onClick={() => window.location.reload()}>
                    重试
                </Button>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-2xl mx-auto px-4 py-8">
                {/* 顶部标题栏 */}
                <div className="flex items-center justify-between mb-6">
                    <h1 className="text-2xl font-bold text-gray-800">我的行程</h1>
                    <Button
                        variant="primary"
                        size="sm"
                        onClick={() => router.push("/")}
                    >
                        返回首页
                    </Button>
                </div>

                {/* 空状态 */}
                {trips.length === 0 ? (
                    <div className="text-center py-20">
                        <p className="text-gray-400 text-lg mb-2">还没有行程</p>
                        <p className="text-gray-300 text-sm">
                            回到首页，告诉 AI 你想去哪里
                        </p>
                    </div>
                ) : (
                    /* 行程列表 */
                    <div className="space-y-3">
                        {trips.map((trip) => (
                            <TripCard
                                key={trip.id}
                                trip={trip}
                                onDeleted={() =>
                                    setTrips((prev) => prev.filter((t) => t.id !== trip.id))
                                }
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
