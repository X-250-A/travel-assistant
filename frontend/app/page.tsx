"use client";

import { Suspense, useState, useCallback } from "react";
import { useAuth } from "@/hooks/useAuth";
import Loading from "@/components/ui/Loading";
import Button from "@/components/ui/Button";
import ChatContainer from "@/components/chat/ChatContainer";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

/** 页面主体（在 Suspense 内，所以可以用 useSearchParams） */
function HomeContent() {
    const { user, loading, logout } = useAuth();
    const searchParams = useSearchParams();

    const initialTripId = (() => {
        const raw = searchParams.get("tripId");
        if (!raw) return null;
        const n = Number(raw);
        return Number.isNaN(n) ? null : n;
    })();

    const [currentTripId, setCurrentTripId] = useState<number | null>(initialTripId);

    const handleTripCreated = useCallback((tripId: number) => {
        setCurrentTripId(tripId);
        window.history.replaceState(null, "", `/?tripId=${tripId}`);
    }, []);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loading size="lg" />
            </div>
        );
    }

    if (!user) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center max-w-md px-6">
                    <h1 className="text-4xl font-bold text-gray-800 mb-4">
                        🗺️ 旅游助手
                    </h1>
                    <p className="text-gray-500 mb-8 text-lg">
                        面向国内游的 AI 行程规划助手。
                        <br />
                        告诉我想去哪里、玩几天，剩下的交给我。
                    </p>
                    <div className="flex gap-4 justify-center">
                        <Link href="/login">
                            <Button variant="primary" size="lg">登录</Button>
                        </Link>
                        <Link href="/register">
                            <Button variant="secondary" size="lg">注册</Button>
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex flex-col">
            <header className="flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-white">
                <h1 className="text-lg font-semibold text-gray-800">
                    🗺️ 旅游助手
                </h1>
                <div className="flex items-center gap-3">
                    <Link
                        href="/?tripId=0"
                        onClick={(e) => {
                            e.preventDefault();
                            setCurrentTripId(null);
                            window.history.replaceState(null, "", "/");
                        }}
                        className="text-sm text-blue-500 hover:text-blue-700 transition-colors cursor-pointer"
                    >
                        ＋ 新建行程
                    </Link>
                    {currentTripId && (
                        <Link
                            href={`/trips/${currentTripId}`}
                            className="text-sm text-blue-500 hover:text-blue-700 transition-colors"
                        >
                            当前行程详情
                        </Link>
                    )}
                    <Link
                        href="/trips"
                        className="text-sm text-gray-500 hover:text-blue-600 transition-colors"
                    >
                        行程列表
                    </Link>
                    <span className="text-sm text-gray-500">{user.username}</span>
                    <Button variant="secondary" size="sm" onClick={logout}>
                        退出
                    </Button>
                </div>
            </header>

            <main className="flex-1 overflow-hidden">
                <ChatContainer tripId={currentTripId} onTripCreated={handleTripCreated} />
            </main>
        </div>
    );
}

// 首页入口：Suspense 包裹是 Next.js 15 useSearchParams 的硬性要求
export default function HomePage() {
    return (
        <Suspense
            fallback={
                <div className="min-h-screen flex items-center justify-center">
                    <Loading size="lg" />
                </div>
            }
        >
            <HomeContent />
        </Suspense>
    );
}
