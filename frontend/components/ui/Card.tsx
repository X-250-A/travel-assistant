import type {HTMLAttributes} from "react";

// ── 类型 ──────────────────────────────────────────────────────────────

/** Card 组件的 props */
interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
    /**
     * 卡片顶部的标题文字（可选）
     * 通常在 children 之前显示
     */
    title?: string;
    /**
     * 是否撑满父容器高度
     * @default false
     */
    fullHeight?: boolean;
}

// ── 组件 ──────────────────────────────────────────────────────────────

/**
 * 通用卡片容器组件
 *
 * 用于包裹任意内容（表单、行程列表、消息气泡等），提供统一的白色背景、
 * 圆角边框和阴影样式。通过 title prop 可在顶部显示卡片标题。
 *
 * 所有原生 div 属性（onClick、ref、style 等）均可透传。
 *
 * 使用示例：
 * ```tsx
 * <Card title="行程概览">
 *   <TripDetail trip={trip} />
 * </Card>
 *
 * <Card onClick={handleClick} className="cursor-pointer">
 *   点击整张卡片
 * </Card>
 * ```
 */
export default function Card({
                                 title,
                                 fullHeight = false,
                                 children,
                                 className = "",
                                 ...rest // 剩余的原生 div 属性全部透传
                             }: CardProps) {
    return (
        <div
            className={`bg-white rounded-lg border border-gray-200 shadow-sm ${fullHeight ? "h-full" : ""} ${className}`}
            {...rest}
        >
            {/* 有 title 时才渲染标题栏 */}
            {title && (
                <div className="border-b border-gray-200 px-5 py-3">
                    <h3 className="text-base font-semibold text-gray-800">
                        {title}
                    </h3>
                </div>
            )}
            {/* 卡片内容区域（title 存在时自动加顶部内边距） */}
            <div className={`px-5 py-4 ${title ? "" : ""}`}>{children}</div>
        </div>
    );
}
