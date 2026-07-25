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
                <p className="rounded-md bg-red-50 p-3 text-sm text-red-600">
                    {error}
                </p>
            )}

            <input
                placeholder="用户名"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={loading}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm
                           focus:border-blue-500 focus:outline-none"
            />

            <input
                type="password"
                placeholder="密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm
                           focus:border-blue-500 focus:outline-none"
            />

            <Button type="submit" loading={loading} size="lg">
                {mode === "login" ? "登录" : "注册"}
            </Button>
        </form>
    );
}
