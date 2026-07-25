import {useState} from "react";
import type {KeyboardEvent} from "react";

interface Props {
    onSend: (text: string) => void;
    disabled: boolean;
}


// 输入框
export default function ChatInput(
    {onSend, disabled}: Props,
) {
    /* 状态管理 */
    const [text, setText] = useState("");

    /*负责触发发送事件*/
    const handleSend = () => {
        if (!text.trim() || disabled) return;
        onSend(text);
        setText("");
    };

    /**/
    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter" && !e.nativeEvent.isComposing) {
            e.preventDefault()
            handleSend();
        }
    };

    return (
        <div className="flex gap-2">
            <input
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={disabled}
                placeholder="输入消息..."
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm
                           placeholder-gray-400 focus:border-blue-500 focus:outline-none
                           disabled:bg-gray-100"
            />
            <button
                onClick={handleSend}
                disabled={disabled || !text.trim()}
                className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white
                           hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                           transition-colors"
            >
                发送
            </button>
        </div>);


}
