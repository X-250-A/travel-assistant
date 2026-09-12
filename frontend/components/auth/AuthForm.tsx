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
                <div className="rounded-md border border-stamp-red/60 bg-stamp-red/[0.06] p-3 text-sm text-stamp-red flex items-start gap-2.5">
                    <span className="shrink-0 font-mono text-[10px] tracking-[0.25em] mt-1">ERR</span>
                    <span>{error}</span>
                </div>
            )}

            <div>
                <label className="block font-mono text-[10px] tracking-[0.18em] text-mist mb-1.5">
                    用户名 · USERNAME
                </label>
                <input
                    placeholder="请输入用户名"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    disabled={loading}
                    className="w-full rounded-md border border-char/30 bg-ink/[0.03] px-4 py-2.5 text-sm text-ink
                               placeholder:text-mist/70 focus:border-gate focus:outline-none focus-visible:ring-2 focus-visible:ring-gate/30
                               transition-all duration-200 disabled:opacity-60"
                />
            </div>

            <div>
                <label className="block font-mono text-[10px] tracking-[0.18em] text-mist mb-1.5">
                    密码 · PASSWORD
                </label>
                <input
                    type="password"
                    placeholder="请输入密码"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={loading}
                    className="w-full rounded-md border border-char/30 bg-ink/[0.03] px-4 py-2.5 text-sm text-ink
                               placeholder:text-mist/70 focus:border-gate focus:outline-none focus-visible:ring-2 focus-visible:ring-gate/30
                               transition-all duration-200 disabled:opacity-60"
                />
            </div>

            <Button type="submit" loading={loading} size="lg" className="w-full">
                {mode === "login" ? "检票进站" : "签发车票"}
            </Button>
        </form>
    );
}
