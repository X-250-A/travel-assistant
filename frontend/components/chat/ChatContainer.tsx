import { useChat } from "@/hooks/useChat";
import MessageBubble from "@/components/chat/MessageBubble";
import StreamingText from "@/components/chat/StreamingText";
import ChatInput from "@/components/chat/ChatInput";
import { useEffect, useRef } from "react";

interface Props {
    tripId: number | null;
    /** 新行程创建后通知父组件（回到首页聊新行程时用到） */
    onTripCreated?: (tripId: number) => void;
}

// 聊天主容器（消息列表 + 流式文本 + 输入框）
export default function ChatContainer({ tripId, onTripCreated }: Props) {
    const { messages, streaming, sending, sendMessage, loadMessages, reset } = useChat();
    const bottomRef = useRef<HTMLDivElement>(null);

    // 有 tripId 时加载历史消息，没有时重置为新对话
    useEffect(() => {
        if (tripId) {
            loadMessages(tripId);
        } else {
            reset();
        }
    }, [tripId, loadMessages, reset]);

    // 新消息或流式内容到达时自动滚到底部
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, streaming]);

    const handleSend = async (text: string) => {
        const returnedId = await sendMessage(text, tripId);
        // 如果之前没有 tripId（新行程），且后端返回了 ID，通知父组件
        if (!tripId && returnedId && onTripCreated) {
            onTripCreated(returnedId);
        }
    };

    return (
        <div className="flex flex-col h-full">
            {/* 消息列表区域：可滚动 */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
                {messages.map((msg) => (
                    <MessageBubble key={msg.id} message={msg} />
                ))}

                {/* AI 正在输出的流式文本 */}
                {streaming && (
                    <div className="flex justify-start">
                        <div className="max-w-[80%] rounded-lg px-4 py-2 text-sm bg-gray-100 text-gray-800">
                            <StreamingText text={streaming} />
                        </div>
                    </div>
                )}

                {/* 滚动锚点 */}
                <div ref={bottomRef} />
            </div>

            {/* 底部输入框 */}
            <div className="border-t border-gray-200 px-4 py-3">
                <ChatInput
                    onSend={handleSend}
                    disabled={sending}
                />
            </div>
        </div>
    );
}
