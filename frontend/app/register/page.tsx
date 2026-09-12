"use client";

import { Suspense, useEffect } from "react";
import { useRouter } from "next/navigation";
import AuthForm from "@/components/auth/AuthForm";
import Barcode from "@/components/ui/Barcode";
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
        <div className="min-h-screen flex flex-col items-center justify-center px-4 py-10">
            <Link
                href="/"
                className="font-mono text-xs tracking-[0.2em] text-mist hover:text-gate transition-colors mb-10"
            >
                ← 返回首页
            </Link>

            <div className="w-full max-w-sm animate-scale-in">
                {/* 签发窗口眉标 */}
                <div className="text-center mb-7">
                    <p className="font-mono text-[11px] tracking-[0.35em] text-gate">GATE A1 · ISSUE</p>
                    <h1 className="mt-3 font-serif text-3xl font-black text-ink">新旅客登记</h1>
                    <p className="mt-2 text-sm text-mist">写下名字和密码，第一张车票马上打印</p>
                </div>

                {/* 待签发车票 */}
                <div className="relative bg-ticket-face border border-char rounded-lg shadow-[0_24px_44px_-26px_rgba(38,34,28,0.55)]">
                    <div className="px-5 pt-5 pb-4">
                        <div className="flex items-center justify-between font-mono text-[10px] tracking-[0.18em]">
                            <span className="text-ink">TRAVEL PASS — SIGN UP</span>
                            <span className="text-mist">NO. 2610</span>
                        </div>
                        <div className="mt-4">
                            <AuthForm mode="register" />
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
                    已有账号？{" "}
                    <Link href="/login" className="text-gate hover:text-gate-dark font-medium transition-colors">
                        去登录 →
                    </Link>
                </p>
            </div>
        </div>
    );
}
