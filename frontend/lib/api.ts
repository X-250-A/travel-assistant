import type {
    User,
    Trip,
    Message,
    TokenResponse,
    TripListResponse,
    TripUpdateRequest,
    SSEHandlers,
} from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── 底层请求 ──────────────────────────────────────────────────────────

async function request<T>(
    method: string,
    path: string,
    body?: unknown,
): Promise<T> {
    const token = localStorage.getItem("token");
    const res = await fetch(`${BASE_URL}${path}`, {
        method,
        headers: {
            "Content-Type": "application/json",
            Authorization: token ? `Bearer ${token}` : "",
        },
        body: body ? JSON.stringify(body) : undefined,
    });

    if (res.status === 401) {
        localStorage.removeItem("token");
        window.location.href = "/login";
        throw new Error("登录已过期，请重新登录");
    }

    if (!res.ok) {
        const text = await res.text();
        let message: string;
        try {
            const json = JSON.parse(text);
            message = json.detail ?? text;
        } catch {
            message = text || res.statusText;
        }
        throw new Error(message);
    }

    return await res.json() as Promise<T>;
}

// ── 认证 ──────────────────────────────────────────────────────────────

export async function register(
    username: string,
    password: string,
): Promise<User> {
    return request<User>("POST", "/api/auth/register", { username, password });
}

export async function login(
    username: string,
    password: string,
): Promise<TokenResponse> {
    return request<TokenResponse>("POST", "/api/auth/login", { username, password });
}

export async function getMe(): Promise<User> {
    return request<User>("GET", "/api/auth/me");
}

export function logOut(): Promise<void> {
    return request("POST", "/api/auth/logout");
}

// ── 行程 ──────────────────────────────────────────────────────────────

export async function getTrip(tripId: number): Promise<Trip> {
    return request<Trip>("GET", `/api/trips/${tripId}`);
}

export async function listTrip(
    page?: number,
    pageSize?: number,
): Promise<TripListResponse> {
    const params = new URLSearchParams({
        page: String(page ?? 1),
        page_size: String(pageSize ?? 100),
    });
    return request<TripListResponse>("GET", `/api/trips?${params.toString()}`);
}

export async function deleteTrip(tripId: number): Promise<void> {
    await request<unknown>("DELETE", `/api/trips/${tripId}`);
}

export async function updateTrip(
    tripId: number,
    body: TripUpdateRequest,
): Promise<Trip> {
    return request<Trip>("PATCH", `/api/trips/${tripId}`, body);
}

export async function getMessages(tripId: number): Promise<Message[]> {
    return request<Message[]>("GET", `/api/trips/${tripId}/messages`);
}

// ── 聊天 (SSE 流式) ───────────────────────────────────────────────────

export async function sendMessage(
    message: string,
    tripId: number | null | undefined,
    handlers: SSEHandlers,
): Promise<void> {
    const { onToken, onDone, onError, onThinking } = handlers;

    const token = localStorage.getItem("token");
    const res = await fetch(`${BASE_URL}/api/chat`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify({ message, trip_id: tripId ?? null }),
    });

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
            if (!part.startsWith("data: ")) continue;
            const data = JSON.parse(part.slice(6));
            switch (data.type) {
                case "thinking":
                    onThinking?.(data.content);
                    break;
                case "token":
                    onToken?.(data.content);
                    break;
                case "done":
                    onDone?.(data.trip_id);
                    break;
                case "error":
                    onError?.(data.detail);
                    break;
            }
        }
    }
}
