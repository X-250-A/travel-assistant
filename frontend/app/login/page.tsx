"use client";

import { Suspense, useEffect } from "react";
import { useRouter } from "next/navigation";
import Card from "@/components/ui/Card";
import AuthForm from "@/components/auth/AuthForm";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
    return (
        <Suspense fallback={null}>
            <LoginContent />
        </Suspense>
    );
}

function LoginContent() {
    const router = useRouter();
    const { user } = useAuth();

    useEffect(() => {
        if (user) {
            router.push("/");
        }
    }, [user, router]);

    return (
        <div className="min-h-screen flex flex-col items-center justify-center px-4">
            {/* 回首页链接 */}
            <Link
                href="/"
                className="flex items-center gap-1.5 text-sm text-stone-400 hover:text-orange-500 transition-colors mb-8"
            >
                <span>←</span>
                <span>返回首页</span>
            </Link>

            <div className="w-full max-w-sm animate-scale-in">
                {/* Logo */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-400 to-rose-500 shadow-xl shadow-orange-200 mb-4">
                        <span className="text-3xl">🗺️</span>
                    </div>
                    <h1 className="text-2xl font-bold text-stone-800">欢迎回来</h1>
                    <p className="text-sm text-stone-400 mt-1">登录你的旅游助手账号</p>
                </div>

                <Card variant="glass">
                    <AuthForm mode="login" />
                </Card>

                <p className="text-center text-sm text-stone-400 mt-6">
                    还没有账号？{" "}
                    <Link href="/register" className="text-orange-500 hover:text-orange-600 font-medium transition-colors">
                        去注册 →
                    </Link>
                </p>
            </div>
        </div>
    );
}
