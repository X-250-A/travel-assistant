"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getTrip, deleteTrip, updateTrip } from "@/lib/api";
import TripDetail from "@/components/trip/TripDetail";
import Loading from "@/components/ui/Loading";
import TicketNav from "@/components/ui/TicketNav";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
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
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [actionError, setActionError] = useState("");

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
        setDeleteOpen(false);

        setDeleting(true);
        try {
            await deleteTrip(trip.id);
            router.push("/trips");
        } catch (err) {
            setError(err instanceof Error ? err.message : "删除失败");
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
            setActionError("");
        } catch (err) {
            setActionError(err instanceof Error ? err.message : "确认失败");
        } finally {
            setConfirming(false);
        }
    };

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
                <p className="font-mono text-[11px] tracking-[0.25em] text-stamp-red">ERROR · 车票读取失败</p>
                <p className="text-sm text-mist">{error}</p>
                <Button variant="secondary" size="sm" onClick={() => router.back()}>
                    ← 返回
                </Button>
            </div>
        );
    }

    if (!trip) return null;

    return (
        <div className="min-h-screen">
            <TicketNav
                links={[{ label: "车票夹", href: "/trips" }]}
                actions={
                    <span className="font-mono text-[9px] tracking-[0.2em] text-mist">
                        TICKET N°{trip.id.toString().padStart(4, "0")}
                    </span>
                }
            />

            <div className="max-w-2xl mx-auto px-4 py-8">
                {/* 操作栏 */}
                <div className="mb-6 flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2">
                        <Link href={`/?tripId=${tripId}`}>
                            <Button variant="accent" size="sm">
                                继续对话
                            </Button>
                        </Link>
                        {trip.status === "draft" && (
                            <Button
                                variant="primary"
                                size="sm"
                                loading={confirming}
                                onClick={handleConfirm}
                            >
                                检票确认
                            </Button>
                        )}
                    </div>
                    <Button
                        variant="danger"
                        size="sm"
                        loading={deleting}
                        onClick={() => setDeleteOpen(true)}
                    >
                        删除
                    </Button>
                </div>

                {/* 操作失败提示条 */}
                {actionError && (
                    <div className="mb-4 flex items-center gap-2 rounded-md border border-stamp-red/40 bg-stamp-red/5 px-3 py-2">
                        <span className="font-mono text-[10px] tracking-[0.2em] text-stamp-red shrink-0">ERR</span>
                        <span className="text-xs text-ink/80">{actionError}</span>
                        <button
                            type="button"
                            onClick={() => setActionError("")}
                            className="ml-auto font-mono text-[10px] text-mist hover:text-ink"
                        >
                            ×
                        </button>
                    </div>
                )}

                <TripDetail trip={trip} onTitleChange={setTrip} />
            </div>

            {/* 主题化删除确认弹窗 */}
            <ConfirmDialog
                open={deleteOpen}
                title="VOID · 作废确认"
                message={`确定将车票「${trip.title}」作废吗？此操作无法撤销。`}
                confirmLabel="作废"
                cancelLabel="保留"
                danger
                onConfirm={handleDelete}
                onCancel={() => setDeleteOpen(false)}
            />
        </div>
    );
}
