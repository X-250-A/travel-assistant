import type { ButtonHTMLAttributes } from "react";

// ── 类型 ──────────────────────────────────────────────────────────────

/** 按钮组件的 props */
interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className"> {
    /**
     * 按钮视觉风格
     * @default "primary"
     */
    variant?: "primary" | "secondary" | "danger";
    /**
     * 按钮尺寸，控制内边距和字号
     * @default "md"
     */
    size?: "sm" | "md" | "lg";
    /**
     * 是否处于加载中状态，为 true 时按钮禁用并显示"加载中..."
     * @default false
     */
    loading?: boolean;
}

// ── 样式映射表 ────────────────────────────────────────────────────────

/**
 * variant → Tailwind 颜色类名
 * primary:   蓝底白字，悬停加深
 * secondary: 白底蓝字蓝边框，悬停浅蓝背景
 * danger:    红底白字，悬停加深（用于删除等危险操作）
 */
const variantClasses: Record<string, string> = {
    primary:
        "bg-blue-600 text-white hover:bg-blue-700 focus-visible:ring-blue-500",
    secondary:
        "bg-white text-blue-600 border border-blue-600 hover:bg-blue-50 focus-visible:ring-blue-500",
    danger:
        "bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500",
};

/**
 * size → Tailwind 尺寸类名
 * sm: 紧凑型，适合表格行、卡片内部等空间有限场景
 * md: 默认尺寸，适合表单和大多数场景
 * lg: 大号，适合登录/注册页的主操作按钮
 */
const sizeClasses: Record<string, string> = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-5 py-2.5 text-base",
    lg: "px-8 py-3 text-lg",
};

// ── 组件 ──────────────────────────────────────────────────────────────

/**
 * 通用按钮组件
 *
 * 支持三种视觉风格（primary / secondary / danger）、三种尺寸（sm / md / lg），
 * 以及 loading 状态。所有原生 button 属性（onClick、type、disabled 等）均可透传。
 *
 * 使用示例：
 * ```tsx
 * <Button variant="danger" size="sm" onClick={handleDelete}>删除</Button>
 * <Button loading>提交中...</Button>
 * ```
 */
export default function Button({
    variant = "primary",
    size = "md",
    loading = false,
    children,
    disabled,
    ...rest // 剩余的原生属性（onClick、type 等）全部透传给 <button>
}: ButtonProps) {
    // 加载中时强制禁用按钮，防止重复点击
    const isDisabled = disabled || loading;

    return (
        <button
            disabled={isDisabled}
            className={`inline-flex items-center justify-center rounded-md font-medium
            transition-colors focus-visible:outline-none focus-visible:ring-2
            focus-visible:ring-offset-2
            ${isDisabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"}
            ${variantClasses[variant]}
            ${sizeClasses[size]}`}
            {...rest} // 展开 onClick、type 等，必须放在 className 之后以允许覆盖
        >
            {/* loading 时只显示文字，正常状态渲染 children */}
            {loading ? "加载中..." : children}
        </button>
    );
}
