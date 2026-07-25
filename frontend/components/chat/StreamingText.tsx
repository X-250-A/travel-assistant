interface Props {
    text: string;
}

// SSE 流式文本逐字渲染组件
export default function StreamingText({ text }: Props) {
    return (
        <span>
            {text}
            {text && (
                <span className="animate-pulse inline-block w-0.5 h-5 bg-blue-600 ml-0.5 align-bottom" />
            )}
        </span>
    );
}