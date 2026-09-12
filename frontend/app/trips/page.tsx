"use client";

import { useEffect, useState } from "react";
import { listTrip } from "@/lib/api";
import TripCard from "@/components/trip/TripCard";
import TicketNav from "@/components/ui/TicketNav";
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
                <Loading size="lg" text="正在取票..." />
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center gap-3 px-4 text-center">
                <p className="font-mono text-[11px] tracking-[0.25em] text-stamp-red">ERROR · 取票失败</p>
                <p className="text-sm text-mist">{error}</p>
                <Button variant="secondary" size="sm" onClick={() => window.location.reload()}>
                    重试
                </Button>
            </div>
        );
    }

    return (
        <div className="min-h-screen">
            <TicketNav
                links={[{ label: "车票夹", href: "/trips", active: true }]}
                actions={
                    <Button variant="primary" size="sm" onClick={() => router.push("/")}>
                        ＋ 新行程
                    </Button>
                }
            />

            <div className="max-w-2xl mx-auto px-4 py-8">
                {/* 票夹页头 */}
                <div className="flex items-end justify-between mb-7">
                    <div>
                        <p className="font-mono text-[11px] tracking-[0.35em] text-gate">MY TICKETS · 车票夹</p>
                        <h1 className="mt-2 font-serif text-3xl font-black text-ink">我的车票</h1>
                    </div>
                    <p className="font-mono text-[11px] tracking-[0.1em] text-mist pb-1.5">
                        共 {trips.length} 张
                    </p>
                </div>

                {trips.length === 0 ? (
                    /* 空票夹 */
                    <div className="border-[1.5px] border-dashed border-char/35 rounded-lg bg-ticket-face/60 px-6 py-14 flex flex-col items-center text-center">
                        <div className="relative w-44 h-20 mb-6">
                            <div className="absolute inset-0 -rotate-[4deg] rounded-md border-[1.5px] border-dashed border-mist/60 bg-paper" />
                            <div className="absolute inset-0 rotate-[3deg] rounded-md border-[1.5px] border-dashed border-mist/80 bg-ticket-face flex items-center justify-center">
                                <span className="font-mono text-[9px] tracking-[0.3em] text-mist">NO TICKET</span>
                            </div>
                        </div>
                        <p className="font-serif text-lg font-bold text-ink">票夹还是空的</p>
                        <p className="mt-1.5 text-sm text-mist">
                            回到首页，告诉 AI 你想去哪里，第一张票马上开
                        </p>
                        <Button variant="primary" size="sm" className="mt-6" onClick={() => router.push("/")}>
                            去开第一张票
                        </Button>
                    </div>
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
