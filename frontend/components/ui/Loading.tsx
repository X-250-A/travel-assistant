// ── 类型 ──────────────────────────────────────────────────────────────

/** Loading 组件的 props */
interface LoadingProps {
    /**
     * 尺寸
     * - sm: 适合内嵌在按钮或小卡片中
     * - md: 默认，适合区块占位
     * - lg: 整页 loading 或大卡片
     * @default "md"
     */
    size?: "sm" | "md" | "lg";
}

// ── 样式映射表 ────────────────────────────────────────────────────────

/**
 * size 到旋钮圆圈 Tailwind 类名的映射
 * w/h 控制宽高，border 控制边框厚度
 */
const spinnerSize: Record<string, string> = {
    sm: "w-5 h-5 border-2",
    md: "w-8 h-8 border-4",
    lg: "w-12 h-12 border-4",
};

/** size 到底部文字 Tailwind 类名的映射 */
const textSize: Record<string, string> = {
    sm: "text-xs",
    md: "text-sm",
    lg: "text-base",
};

// ── 组件 ──────────────────────────────────────────────────────────────

/**
 * 通用加载动画组件
 *
 * 显示一个旋转的圆环 + 说明文字，用于数据加载、异步操作等待等场景。
 *
 * 原理：用 Tailwind 的 border 画一个空心圆环，顶部边框着色、其他三边浅色，
 * 配合 animate-spin（CSS 旋转动画）产生"转动"的视觉效果。
 */
export default function Loading({ size = "md" }: LoadingProps) {
    return (
        // 纵向排列：圆环在上，文字在下，居中对齐
        <div className="flex flex-col items-center justify-center gap-2">
            {/*
              旋钮圆环：
              - animate-spin       → CSS 旋转动画，无限循环
              - rounded-full       → 变成圆形
              - border-blue-200    → 圆环底色（浅灰蓝）
              - border-t-blue-600  → 只有顶部边框是深蓝，旋转时像指针在转
            */}
            <div
                className={`animate-spin rounded-full border-blue-200 border-t-blue-600 ${spinnerSize[size]}`}
            />
            {/* 加载中提示文字 */}
            <p className={`text-gray-500 ${textSize[size]}`}>加载中...</p>
        </div>
    );
}
