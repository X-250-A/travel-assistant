"use client";

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { getMe, login as apiLogin, register as apiRegister, logOut as apiLogOut } from "@/lib/api";
import type { User } from "@/types";

interface AuthContextValue {
    user: User | null;
    loading: boolean;
    login: (username: string, password: string) => Promise<void>;
    register: (username: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function hasToken(): boolean {
    if (typeof window === "undefined") return false;
    return !!localStorage.getItem("token");
}

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!hasToken()) {
            setLoading(false);
            return;
        }
        getMe()
            .then(setUser)
            .catch(() => localStorage.removeItem("token"))
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

    const logout = useCallback(async () => {
        try {
            await apiLogOut();
        }
        finally{
            localStorage.removeItem("token");
            setUser(null);
        }

    }, []);

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth(): AuthContextValue {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
    return ctx;
}
