"use client";

import { Suspense, useEffect } from "react";
import { useRouter } from "next/navigation";
import AuthForm from "@/components/auth/AuthForm";
import Barcode from "@/components/ui/Barcode";
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
        <div className="min-h-screen flex flex-col items-center justify-center px-4 py-10">
            <Link
                href="/"
                className="font-mono text-xs tracking-[0.2em] text-mist hover:text-gate transition-colors mb-10"
            >
                ← 返回首页
            </Link>

            <div className="w-full max-w-sm animate-scale-in">
                {/* 检票口眉标 */}
                <div className="text-center mb-7">
                    <p className="font-mono text-[11px] tracking-[0.35em] text-gate">GATE A1 · CHECK-IN</p>
                    <h1 className="mt-3 font-serif text-3xl font-black text-ink">欢迎回站</h1>
                    <p className="mt-2 text-sm text-mist">出示你的账号车票，检票进站</p>
                </div>

                {/* 待检车票 */}
                <div className="relative bg-ticket-face border border-char rounded-lg shadow-[0_24px_44px_-26px_rgba(38,34,28,0.55)]">
                    <div className="px-5 pt-5 pb-4">
                        <div className="flex items-center justify-between font-mono text-[10px] tracking-[0.18em]">
                            <span className="text-ink">TRAVEL PASS — LOGIN</span>
                            <span className="text-mist">NO. 2609</span>
                        </div>
                        <div className="mt-4">
                            <AuthForm mode="login" />
                        </div>
                    </div>

                    {/* 撕票线与打孔 */}
                    <div className="relative">
                        <div className="border-t-[1.5px] border-dashed border-char/40" />
                        <span aria-hidden="true" className="absolute -left-[9px] -top-[9px] w-[18px] h-[18px] rounded-full bg-paper" />
                        <span aria-hidden="true" className="absolute -right-[9px] -top-[9px] w-[18px] h-[18px] rounded-full bg-paper" />
                    </div>

                    {/* 票根 */}
                    <div className="flex items-center justify-between px-5 py-3 bg-ink/[0.04]">
                        <span className="font-mono text-[9px] tracking-[0.22em] text-char/50">STUB · 存根联</span>
                        <Barcode className="h-3" color="rgba(38, 34, 28, 0.5)" />
                    </div>
                </div>

                <p className="text-center text-sm text-mist mt-6">
                    还没有账号？{" "}
                    <Link href="/register" className="text-gate hover:text-gate-dark font-medium transition-colors">
                        去注册 →
                    </Link>
                </p>
            </div>
        </div>
    );
}
