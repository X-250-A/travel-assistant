"use client";

import { Suspense, useEffect } from "react";
import { useRouter } from "next/navigation";
import Card from "@/components/ui/Card";
import AuthForm from "@/components/auth/AuthForm";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

// 注册页
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

    // 注册成功后自动跳转首页
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

                <Card title="注册">
                    <AuthForm mode="register" />
                </Card>

                <p className="text-center text-sm text-gray-500 mt-4">
                    已有账号？{" "}
                    <Link href="/login" className="text-blue-600 hover:underline">
                        去登录
                    </Link>
                </p>
            </div>
        </div>
    );
}
