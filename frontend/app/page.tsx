"use client";

import { Suspense, useState, useCallback } from "react";
import { useAuth } from "@/hooks/useAuth";
import Loading from "@/components/ui/Loading";
import Button from "@/components/ui/Button";
import ChatContainer from "@/components/chat/ChatContainer";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

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
                <Loading size="lg" text="正在加载..." />
            </div>
        );
    }

    if (!user) {
        return <LandingPage />;
    }

    return (
        <div className="min-h-screen flex flex-col">
            {/* 导航栏 */}
            <header className="glass-strong sticky top-0 z-50 border-b border-white/50">
                <div className="max-w-5xl mx-auto flex items-center justify-between px-6 py-3">
                    <Link href="/" className="flex items-center gap-2 shrink-0">
                        <span className="text-2xl">✈️</span>
                        <span className="text-lg font-bold gradient-text">旅游助手</span>
                    </Link>

                    <div className="flex items-center gap-2 flex-wrap justify-end">
                        <Link
                            href="/?tripId=0"
                            onClick={(e) => {
                                e.preventDefault();
                                setCurrentTripId(null);
                                window.history.replaceState(null, "", "/");
                            }}
                            className="text-sm text-stone-500 hover:text-orange-600 transition-colors px-2 py-1"
                        >
                            ＋ 新建行程
                        </Link>
                        {currentTripId && (
                            <Link
                                href={`/trips/${currentTripId}`}
                                className="text-sm text-stone-500 hover:text-orange-600 transition-colors px-2 py-1"
                            >
                                当前行程
                            </Link>
                        )}
                        <Link
                            href="/trips"
                            className="text-sm text-stone-500 hover:text-orange-600 transition-colors px-2 py-1"
                        >
                            行程列表
                        </Link>
                        <span className="text-sm text-stone-400 pl-2 border-l border-stone-200">
                            {user.username}
                        </span>
                        <Button variant="ghost" size="sm" onClick={logout}>
                            退出
                        </Button>
                    </div>
                </div>
            </header>

            <main className="flex-1 overflow-hidden flex flex-col">
                <ChatContainer tripId={currentTripId} onTripCreated={handleTripCreated} />
            </main>
        </div>
    );
}

/** 未登录时展示的 Landing 页 */
function LandingPage() {
    return (
        <div className="min-h-screen flex flex-col">
            {/* 顶部导航 */}
            <header className="glass-strong sticky top-0 z-50 border-b border-white/50">
                <div className="max-w-6xl mx-auto flex items-center justify-between px-6 py-4">
                    <div className="flex items-center gap-2.5">
                        <span className="text-2xl">✈️</span>
                        <span className="text-lg font-bold gradient-text">旅游助手</span>
                    </div>
                    <div className="flex items-center gap-3">
                        <Link href="/login">
                            <Button variant="ghost" size="sm">登录</Button>
                        </Link>
                        <Link href="/register">
                            <Button variant="primary" size="sm">免费注册</Button>
                        </Link>
                    </div>
                </div>
            </header>

            {/* Hero 区域 */}
            <main className="flex-1 flex items-center justify-center px-6">
                <div className="max-w-3xl w-full text-center">
                    {/* 浮动装饰图标 */}
                    <div className="relative mb-8">
                        <div className="animate-scale-in inline-flex items-center justify-center w-24 h-24 rounded-3xl bg-gradient-to-br from-orange-400 to-rose-500 shadow-2xl shadow-orange-300/50 mb-4">
                            <span className="text-5xl">🗺️</span>
                        </div>
                    </div>

                    <h1 className="text-5xl sm:text-6xl font-extrabold text-stone-800 tracking-tight mb-4 animate-fade-in-up">
                        AI 规划你的
                        <br />
                        <span className="gradient-text">完美旅行</span>
                    </h1>

                    <p className="text-lg text-stone-500 mb-10 max-w-lg mx-auto leading-relaxed animate-fade-in-up" style={{ animationDelay: "0.1s" }}>
                        告诉我想去哪里、玩几天、预算多少，
                        <br className="hidden sm:block" />
                        剩下的交给 AI — 景点、美食、交通，一步到位。
                    </p>

                    <div className="flex gap-4 justify-center animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
                        <Link href="/register">
                            <Button variant="primary" size="lg">
                                ✨ 开始规划
                            </Button>
                        </Link>
                        <Link href="/login">
                            <Button variant="secondary" size="lg">
                                已有账号
                            </Button>
                        </Link>
                    </div>

                    {/* 特色功能卡片 */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-16 animate-fade-in-up" style={{ animationDelay: "0.3s" }}>
                        <FeatureCard
                            emoji="🤖"
                            title="AI 智能规划"
                            desc="多轮对话理解偏好，自动生成每日行程"
                        />
                        <FeatureCard
                            emoji="🍜"
                            title="美食推荐"
                            desc="地道餐厅 + 安全选择，每餐都有推荐"
                        />
                        <FeatureCard
                            emoji="📋"
                            title="一键调整"
                            desc="想去的不想去随时增减，AI 替你更新"
                        />
                    </div>
                </div>
            </main>

            {/* 底部 */}
            <footer className="py-6 text-center text-sm text-stone-400">
                Made with ❤️ by AI Travel Planner
            </footer>
        </div>
    );
}

function FeatureCard({ emoji, title, desc }: { emoji: string; title: string; desc: string }) {
    return (
        <div className="glass rounded-2xl p-5 text-center hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300">
            <div className="text-3xl mb-2">{emoji}</div>
            <h3 className="text-sm font-semibold text-stone-700 mb-1">{title}</h3>
            <p className="text-xs text-stone-400 leading-relaxed">{desc}</p>
        </div>
    );
}

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
