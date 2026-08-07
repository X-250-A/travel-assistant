"use client";

import {useChat} from "@/hooks/useChat";
import MessageBubble from "@/components/chat/MessageBubble";
import StreamingText from "@/components/chat/StreamingText";
import ChatInput from "@/components/chat/ChatInput";
import {useEffect, useRef} from "react";

interface Props {
    tripId: number | null;
    onTripCreated?: (tripId: number) => void;
}

export default function ChatContainer({tripId, onTripCreated}: Props) {
    const {messages, thinking, streaming, sending, sendMessage, loadMessages, reset} = useChat();
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (tripId) {
            loadMessages(tripId);
        } else {
            reset();
        }
    }, [tripId, loadMessages, reset]);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({behavior: "smooth"});
    }, [messages, streaming]);

    const handleSend = async (text: string) => {
        const returnedId = await sendMessage(text, tripId);
        if (!tripId && returnedId && onTripCreated) {
            onTripCreated(returnedId);
        }
    };

    return (
        <div className="flex flex-col h-full max-w-4xl mx-auto w-full">
            {/* 消息列表 */}
            <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
                {messages.length === 0 && !streaming && !thinking && (
                    <EmptyState/>
                )}

                {messages.map((msg, i) => (
                    <div
                        key={msg.id}
                        className="animate-fade-in-up"
                        style={{animationDelay: `${Math.min(i * 50, 300)}ms`}}
                    >
                        <MessageBubble message={msg}/>
                    </div>
                ))}

                {streaming && (
                    <div className="flex justify-start">
                        <div
                            className="max-w-[80%] rounded-2xl rounded-tl-md px-5 py-3.5 bg-white border border-orange-100 shadow-sm shadow-orange-50">
                            <StreamingText text={streaming}/>
                        </div>
                    </div>
                )}
                
                {thinking && (
                    <div className="flex justify-start">
                        <div
                            className="max-w-[80%] rounded-2xl rounded-tl-md px-5 py-3.5 bg-amber-50 border border-amber-100">
                            <div className="text-xs text-amber-500 font-medium mb-1">🤔 Agent 正在思考</div>
                            <p className="text-sm text-stone-500 leading-relaxed">{thinking}</p>
                        </div>
                    </div>
                )}

                <div ref={bottomRef}/>
            </div>

            {/* 输入框 */}
            <div className="border-t border-stone-100 bg-white/80 backdrop-blur-md px-4 py-3">
                <ChatInput onSend={handleSend} disabled={sending}/>
            </div>
        </div>
    );
}

function EmptyState() {
    return (
        <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="text-6xl mb-6 opacity-80">🌍</div>
            <h2 className="text-xl font-semibold text-stone-700 mb-2">开始规划你的旅行</h2>
            <p className="text-sm text-stone-400 max-w-sm leading-relaxed">
                告诉我你想去哪座城市、玩几天、预算是多少，
                <br/>
                AI 会为你量身定制行程方案。
            </p>
            <div className="flex flex-wrap gap-2 mt-6 justify-center">
                {["北京三日游", "上海周末逛逛", "成都美食之旅", "云南七天深度"].map((hint) => (
                    <span key={hint} className="text-xs text-stone-400 bg-stone-100 rounded-full px-3 py-1.5">
                        {hint}
                    </span>
                ))}
            </div>
        </div>
    );
}
