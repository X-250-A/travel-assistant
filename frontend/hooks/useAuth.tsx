"use client";
// 认证 hook：登录/注册/登出/获取当前用户

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { getMe, login as apiLogin, register as apiRegister } from "@/lib/api";
import type { User } from "@/types";

interface AuthContextValue {
    user: User | null;
    loading: boolean;
    login: (username: string, password: string) => Promise<void>;
    register: (username: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Provider：包裹整个 app，让所有组件共享同一个 user 状态 */
export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem("token");
        if (!token) {
            setLoading(false);
            return;
        }
        getMe()
            .then(setUser)
            .finally(() => setLoading(false));
    }, []);

    const login = useCallback(async (username: string, password: string) => {
        const res = await apiLogin(username, password);
        localStorage.setItem("token", res.access_token);
        const userData = await getMe();
        setUser(userData);
    }, []);

    const register = useCallback(async (username: string, password: string) => {
        await apiRegister(username, password);
        const res = await apiLogin(username, password);
        localStorage.setItem("token", res.access_token);
        const userData = await getMe();
        setUser(userData);
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem("token");
        setUser(null);
    }, []);

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

/** 在任意组件中获取认证状态 */
export function useAuth(): AuthContextValue {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
    return ctx;
}
