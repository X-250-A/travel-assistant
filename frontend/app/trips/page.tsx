"use client";

import { useEffect, useState } from "react";
import { listTrip } from "@/lib/api";
import TripCard from "@/components/trip/TripCard";
import Card from "@/components/ui/Card";
import Loading from "@/components/ui/Loading";
import Button from "@/components/ui/Button";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { Trip } from "@/types";

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

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loading size="lg" text="加载行程中..." />
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center gap-4">
                <p className="text-red-500 text-sm">{error}</p>
                <Button variant="secondary" onClick={() => window.location.reload()}>
                    重试
                </Button>
            </div>
        );
    }

    return (
        <div className="min-h-screen">
            {/* 顶栏 */}
            <header className="glass-strong sticky top-0 z-50 border-b border-white/50">
                <div className="max-w-2xl mx-auto flex items-center justify-between px-4 py-3">
                    <Link href="/" className="flex items-center gap-2">
                        <span className="text-xl">✈️</span>
                        <span className="text-lg font-bold gradient-text">旅游助手</span>
                    </Link>
                    <Button variant="primary" size="sm" onClick={() => router.push("/")}>
                        ＋ 新行程
                    </Button>
                </div>
            </header>

            <div className="max-w-2xl mx-auto px-4 py-8">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-stone-800">我的行程</h1>
                        <p className="text-sm text-stone-400 mt-1">共 {trips.length} 个行程</p>
                    </div>
                </div>

                {trips.length === 0 ? (
                    <Card variant="glass">
                        <div className="flex flex-col items-center py-16 text-center">
                            <div className="text-6xl mb-4">🗺️</div>
                            <p className="text-stone-500 font-medium mb-1">还没有行程</p>
                            <p className="text-sm text-stone-400 mb-6">
                                回到首页，告诉 AI 你想去哪里
                            </p>
                            <Button variant="primary" size="sm" onClick={() => router.push("/")}>
                                开始规划
                            </Button>
                        </div>
                    </Card>
                ) : (
                    <div className="space-y-3">
                        {trips.map((trip, i) => (
                            <div
                                key={trip.id}
                                className="animate-fade-in-up"
                                style={{ animationDelay: `${i * 50}ms` }}
                            >
                                <TripCard
                                    trip={trip}
                                    onDeleted={() =>
                                        setTrips((prev) => prev.filter((t) => t.id !== trip.id))
                                    }
                                />
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
