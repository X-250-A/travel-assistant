"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import Button from "@/components/ui/Button";

interface Props {
    mode: "login" | "register";
}

export default function AuthForm({ mode }: Props) {
    const { login, register, loading } = useAuth();

    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");

    return (
        <form
            onSubmit={async (e) => {
                e.preventDefault();
                setError("");

                try {
                    if (mode === "login") {
                        await login(username, password);
                    } else {
                        await register(username, password);
                    }
                } catch (err) {
                    setError(err instanceof Error ? err.message : "操作失败");
                }
            }}
            className="space-y-4"
        >
            {error && (
                <div className="rounded-xl bg-red-50 border border-red-100 p-3.5 text-sm text-red-600 flex items-start gap-2.5">
                    <span className="shrink-0 mt-0.5">⚠️</span>
                    <span>{error}</span>
                </div>
            )}

            <div>
                <label className="block text-xs font-medium text-stone-500 mb-1.5">
                    用户名
                </label>
                <input
                    placeholder="请输入用户名"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    disabled={loading}
                    className="w-full rounded-xl border border-stone-200 bg-stone-50 px-4 py-2.5 text-sm
                               placeholder:text-stone-300 focus:border-orange-300 focus:bg-white focus:outline-none
                               focus:ring-2 focus:ring-orange-100 transition-all duration-200"
                />
            </div>

            <div>
                <label className="block text-xs font-medium text-stone-500 mb-1.5">
                    密码
                </label>
                <input
                    type="password"
                    placeholder="请输入密码"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={loading}
                    className="w-full rounded-xl border border-stone-200 bg-stone-50 px-4 py-2.5 text-sm
                               placeholder:text-stone-300 focus:border-orange-300 focus:bg-white focus:outline-none
                               focus:ring-2 focus:ring-orange-100 transition-all duration-200"
                />
            </div>

            <Button type="submit" loading={loading} size="lg" className="w-full">
                {mode === "login" ? "登录" : "创建账号"}
            </Button>
        </form>
    );
}
