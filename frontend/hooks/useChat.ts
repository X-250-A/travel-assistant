import { sendMessage as apiSendMessage, getMessages } from "@/lib/api";
import { Message } from "@/types";
import { useState, useRef, useCallback } from "react";


// 聊天核心 hook：发消息、接收 SSE 流、消息列表状态
export function useChat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [streaming, setStreaming] = useState("");
    const [sending, setSending] = useState(false);
    /** 当前已加载的 tripId，避免同一行程重复加载 */
    const loadedTripIdRef = useRef<number | null>(null);
    /** streaming 内容的同步副本，避免在 setStreaming updater 里嵌套 setMessages */
    const streamingBufRef = useRef("");

    /** 加载历史消息 */
    const loadMessages = useCallback(async (tripId: number) => {
        if (loadedTripIdRef.current === tripId) return;
        loadedTripIdRef.current = tripId;
        try {
            const history = await getMessages(tripId);
            setMessages(history);
        } catch {
            // 加载失败不阻断聊天，静默处理
        }
    }, []);

    /** 切回新行程时重置状态 */
    const reset = useCallback(() => {
        setMessages([]);
        setStreaming("");
        setSending(false);
        loadedTripIdRef.current = null;
        streamingBufRef.current = "";
    }, []);

    const sendMessage = async (text: string, tripId: number | null): Promise<number | null> => {
        if (!text.trim() || sending) {
            return null;
        }

        const userMsg: Message = {role: "user", content: text, trip_id : tripId ?? 0, created_at : new Date().toISOString(), id : Date.now()};
        setMessages(prev => [...prev, userMsg]);
        setSending(true);

        // 用 Promise 包装 SSE，以便 await 拿到 done 事件中的 trip_id
        const finalTripId = await new Promise<number | null>((resolve) => {
            apiSendMessage(
                text, tripId, {
                    onToken: (chunk) => {
                        streamingBufRef.current += chunk;
                        setStreaming(streamingBufRef.current);
                    },
                    onDone: (newTripId) => {
                        const finalText = streamingBufRef.current;
                        streamingBufRef.current = "";
                        setStreaming("");

                        if (finalText.trim()) {
                            const aiMsg: Message = {
                                id: Date.now(),
                                trip_id: newTripId ?? tripId ?? 0,
                                role: "assistant",
                                content: finalText,
                                created_at: new Date().toISOString(),
                            };
                            setMessages(prevMsgs => [...prevMsgs, aiMsg]);
                        }
                        setSending(false);
                        resolve(newTripId ?? null);
                    },
                    onError: (err) => {
                        setStreaming("");
                        setSending(false);

                        const errMsg : Message = {
                            id : Date.now(),
                            trip_id : tripId ?? 0,
                            role : "assistant",
                            content : `${err}`,
                            created_at : new Date().toISOString()
                        };
                        setMessages(prevMsgs => [...prevMsgs, errMsg])
                        resolve(null);
                    },
                }
            )
        });

        return finalTripId;
    }


    return { messages, streaming, sending, sendMessage, loadMessages, reset };
}
