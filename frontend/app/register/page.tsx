"use client";

import { Suspense, useEffect } from "react";
import { useRouter } from "next/navigation";
import Card from "@/components/ui/Card";
import AuthForm from "@/components/auth/AuthForm";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

export default function RegisterPage() {
    return (
        <Suspense fallback={null}>
            <RegisterContent />
        </Suspense>
    );
}

function RegisterContent() {
    const router = useRouter();
    const { user } = useAuth();

    useEffect(() => {
        if (user) {
            router.push("/");
        }
    }, [user, router]);

    return (
        <div className="min-h-screen flex flex-col items-center justify-center px-4">
            <Link
                href="/"
                className="flex items-center gap-1.5 text-sm text-stone-400 hover:text-orange-500 transition-colors mb-8"
            >
                <span>←</span>
                <span>返回首页</span>
            </Link>

            <div className="w-full max-w-sm animate-scale-in">
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-400 to-rose-500 shadow-xl shadow-orange-200 mb-4">
                        <span className="text-3xl">✈️</span>
                    </div>
                    <h1 className="text-2xl font-bold text-stone-800">创建账号</h1>
                    <p className="text-sm text-stone-400 mt-1">开始你的 AI 旅行规划之旅</p>
                </div>

                <Card variant="glass">
                    <AuthForm mode="register" />
                </Card>

                <p className="text-center text-sm text-stone-400 mt-6">
                    已有账号？{" "}
                    <Link href="/login" className="text-orange-500 hover:text-orange-600 font-medium transition-colors">
                        去登录 →
                    </Link>
                </p>
            </div>
        </div>
    );
}
