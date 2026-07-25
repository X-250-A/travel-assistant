"use client";

import { Suspense, useEffect } from "react";
import { useRouter } from "next/navigation";
import Card from "@/components/ui/Card";
import AuthForm from "@/components/auth/AuthForm";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

// 登录页
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

    // 登录成功后自动跳转首页
    useEffect(() => {
        if (user) {
            router.push("/");
        }
    }, [user, router]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="w-full max-w-sm">
                <h1 className="text-center text-3xl font-bold text-gray-800 mb-8">
                    旅游助手
                </h1>

                <Card title="登录">
                    <AuthForm mode="login" />
                </Card>

                <p className="text-center text-sm text-gray-500 mt-4">
                    没有账号？{" "}
                    <Link href="/register" className="text-blue-600 hover:underline">
                        去注册
                    </Link>
                </p>
            </div>
        </div>
    );
}
