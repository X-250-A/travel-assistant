"use client";

import Link from "next/link";
import type { ReactNode } from "react";

/**
 * TicketNav — 车票主题共用导航栏
 * 票券头部语汇：PASSAGE 字标 + 撕票线底边（虚线 + 两端打孔）+ 站牌式 mono 导航
 * links: { label, href, active?, onClick? } ；actions 放按钮/用户区
 */
interface NavLink {
    label: string;
    href: string;
    active?: boolean;
    onClick?: (e: React.MouseEvent) => void;
}

interface Props {
    links: NavLink[];
    actions?: ReactNode;
}

export default function TicketNav({ links, actions }: Props) {
    return (
        <header className="ticket-nav sticky top-0 z-50">
            <div className="max-w-5xl mx-auto flex items-center justify-between px-6 h-14">
                <Link href="/" className="flex items-baseline gap-2 shrink-0 group">
                    <span className="font-mono text-[10px] tracking-[0.3em] text-gate group-hover:text-stamp-red transition-colors">
                        PASSAGE
                    </span>
                    <span className="font-serif text-lg font-bold text-ink">旅游助手</span>
                </Link>

                <div className="flex items-center gap-5 min-w-0">
                    {/* 站牌式导航：mono 大写 + 到达箭头，当前站在检票橙下方划线 */}
                    <nav className="hidden sm:flex items-center gap-5" aria-label="主导航">
                        {links.map((l) =>
                            l.onClick ? (
                                <button
                                    key={l.label}
                                    onClick={l.onClick}
                                    className={`ticket-nav-link ${l.active ? "is-active" : ""}`}
                                >
                                    {l.label}
                                </button>
                            ) : (
                                <Link
                                    key={l.label}
                                    href={l.href}
                                    className={`ticket-nav-link ${l.active ? "is-active" : ""}`}
                                >
                                    {l.label}
                                </Link>
                            )
                        )}
                    </nav>

                    {/* 移动端折叠为紧凑链接 */}
                    <nav className="flex sm:hidden items-center gap-1" aria-label="主导航">
                        {links.map((l) =>
                            l.onClick ? (
                                <button
                                    key={l.label}
                                    onClick={l.onClick}
                                    className="font-mono text-[10px] text-mist hover:text-gate px-1.5 py-1"
                                >
                                    {l.label}
                                </button>
                            ) : (
                                <Link
                                    key={l.label}
                                    href={l.href}
                                    className="font-mono text-[10px] text-mist hover:text-gate px-1.5 py-1"
                                >
                                    {l.label}
                                </Link>
                            )
                        )}
                    </nav>

                    {/* PAX 票面字段 + 操作区 */}
                    <div className="flex items-center gap-3 pl-4 border-l border-dashed border-char/25">
                        {actions}
                    </div>
                </div>
            </div>

            {/* 撕票线底边：虚线 + 两端打孔半圆 */}
            <div className="ticket-nav-perf" aria-hidden="true" />
        </header>
    );
}
