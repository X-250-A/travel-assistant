"use client";

import { Suspense, useState, useCallback } from "react";
import { useAuth } from "@/hooks/useAuth";
import Loading from "@/components/ui/Loading";
import Button from "@/components/ui/Button";
import ChatContainer from "@/components/chat/ChatContainer";
import TicketNav from "@/components/ui/TicketNav";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

function HomeContent() {
    const { user, loading, logout } = useAuth();
    const searchParams = useSearchParams();

    const initialTripId = (() => {
        const raw = searchParams.get("tripId");
        if (!raw) return null;
        const n = Number(raw);
        return Number.isNaN(n) ? null : n;
    })();

    const [currentTripId, setCurrentTripId] = useState<number | null>(initialTripId);

    const handleTripCreated = useCallback((tripId: number) => {
        setCurrentTripId(tripId);
        window.history.replaceState(null, "", `/?tripId=${tripId}`);
    }, []);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loading size="lg" text="正在加载..." />
            </div>
        );
    }

    if (!user) {
        return <LandingPage />;
    }

    return (
        <div className="min-h-screen flex flex-col">
            <TicketNav
                links={[
                    {
                        label: "新建行程",
                        href: "/?tripId=0",
                        onClick: (e) => {
                            e.preventDefault();
                            setCurrentTripId(null);
                            window.history.replaceState(null, "", "/");
                        },
                    },
                    ...(currentTripId
                        ? [
                              {
                                  label: "当前行程",
                                  href: `/trips/${currentTripId}`,
                              },
                          ]
                        : []),
                    { label: "车票夹", href: "/trips", active: false },
                ]}
                actions={
                    <>
                        <span className="font-mono text-xs text-ink/80 flex items-center gap-1.5">
                            <span className="text-[9px] tracking-[0.15em] text-mist">PAX</span>
                            {user.username}
                        </span>
                        <Button variant="ghost" size="sm" onClick={logout}>
                            退出
                        </Button>
                    </>
                }
            />

            <main className="flex-1 overflow-hidden flex flex-col">
                <ChatContainer tripId={currentTripId} onTripCreated={handleTripCreated} />
            </main>
        </div>
    );
}

/* ── 车票主题设计令牌（全部由 5 个基础色派生）────────────────────── */
const INK = "#16324F"; // 墨蓝：标题、主文字
const ORANGE = "#E56A1F"; // 检票橙：CTA、强调
const MIST = "#7A9AA8"; // 烟青：次要文字、辅助线
const CHAR = "#26221C"; // 炭墨：票面细节、阴影
const PAPER = "#F7F3EA"; // 车票米：页面底色
const TICKET_FACE = "#FFFDF7"; // 票面米白
const STAMP_RED = "#C8442A"; // 邮戳红（检票橙偏红）

const serifFont = { fontFamily: "'Noto Serif SC','Source Han Serif SC',serif" };
const monoFont = { fontFamily: "ui-monospace,'JetBrains Mono',monospace" };

const BARCODE_WIDTHS = [2, 1, 3, 1, 2, 1, 1, 3, 2, 1, 3, 1, 2, 2, 1, 3, 1, 1];

/** 未登录时展示的 Landing 页：一张“行程票” */
function LandingPage() {
    return (
        <div className="min-h-screen flex flex-col" style={{ backgroundColor: PAPER }}>
            {/* 唯一一组进场动画：左列 fade-up 依次 80ms，车票 rotate-in 一次 */}
            <style>{`
                @keyframes lpFadeUp {
                    from { opacity: 0; transform: translateY(18px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                @keyframes lpRotateIn {
                    from { opacity: 0; transform: rotate(3deg) translateY(24px); }
                    to { opacity: 1; transform: rotate(-2deg) translateY(0); }
                }
                .lp-fade-up { opacity: 0; animation: lpFadeUp 0.55s cubic-bezier(0.22, 0.61, 0.36, 1) forwards; }
                .lp-ticket-tilt { transform: rotate(-2deg); }
                .lp-ticket-in { opacity: 0; animation: lpRotateIn 0.7s cubic-bezier(0.22, 0.61, 0.36, 1) 0.15s forwards; }
                @media (prefers-reduced-motion: reduce) {
                    .lp-fade-up, .lp-ticket-in { animation: none; opacity: 1; }
                }
            `}</style>

            {/* 顶部导航 */}
            <header
                className="sticky top-0 z-50 border-b"
                style={{ backgroundColor: "rgba(247, 243, 234, 0.92)", borderColor: "rgba(38, 34, 28, 0.12)" }}
            >
                <div className="max-w-6xl mx-auto flex items-center justify-between px-6 py-4">
                    <div className="flex items-center gap-2.5">
                        <span className="text-2xl">✈️</span>
                        <span className="text-lg font-bold" style={{ color: INK }}>旅游助手</span>
                    </div>
                    <div className="flex items-center gap-3">
                        <Link href="/login">
                            <Button variant="ghost" size="sm">登录</Button>
                        </Link>
                        <Link href="/register">
                            <Button variant="primary" size="sm">免费注册</Button>
                        </Link>
                    </div>
                </div>
            </header>

            <main className="flex-1 w-full">
                <div className="max-w-6xl mx-auto px-6 pt-14 pb-16 lg:pt-20">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-14 lg:gap-10 items-center">
                        {/* 左列：文案与 CTA */}
                        <div className="lg:col-span-7">
                            <p className="lp-fade-up text-xs uppercase tracking-[0.3em]" style={{ ...monoFont, color: ORANGE }}>
                                PASSAGE / 安先生的车票系统
                            </p>
                            <h1
                                className="lp-fade-up mt-5 text-5xl sm:text-6xl leading-[1.14]"
                                style={{ ...serifFont, fontWeight: 900, color: INK, animationDelay: "80ms" }}
                            >
                                把下一次出发
                                <br />
                                印成一张
                                <span style={{ boxShadow: "inset 0 -0.28em 0 rgba(229, 106, 31, 0.28)" }}>车票</span>
                            </h1>
                            <p
                                className="lp-fade-up mt-6 max-w-xl text-base sm:text-lg leading-relaxed"
                                style={{ color: MIST, animationDelay: "160ms" }}
                            >
                                想去哪儿、玩几天、预算多少，从一句对话开始。
                                景点、吃饭、坐车，逐天排进你的行程；想改，随时开口。
                            </p>
                            <div className="lp-fade-up mt-9 flex flex-wrap items-center gap-4" style={{ animationDelay: "240ms" }}>
                                <Link
                                    href="/register"
                                    className="inline-flex items-center justify-center rounded-lg px-8 py-3.5 text-base font-semibold text-white transition-transform focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 active:scale-[0.98]"
                                    style={{ backgroundColor: ORANGE, boxShadow: "0 12px 26px -14px rgba(229, 106, 31, 0.7)", outlineColor: ORANGE }}
                                >
                                    检票出发
                                </Link>
                                <Link
                                    href="/login"
                                    className="inline-flex items-center justify-center rounded-lg border px-8 py-3.5 text-base font-semibold transition-colors hover:bg-[rgba(22,50,79,0.06)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
                                    style={{ color: INK, borderColor: INK, outlineColor: INK }}
                                >
                                    登录
                                </Link>
                            </div>
                            <p
                                className="lp-fade-up mt-4 text-[11px] tracking-[0.12em]"
                                style={{ ...monoFont, color: MIST, animationDelay: "320ms" }}
                            >
                                检票出发 = 免费注册 — 行程只保存在你自己的账号里
                            </p>
                        </div>

                        {/* 右列：签名车票 */}
                        <div className="lg:col-span-5 flex justify-center lg:justify-end">
                            <div className="lp-ticket-in lp-ticket-tilt relative pb-5 lg:mt-4">
                                <TicketCard />
                            </div>
                        </div>
                    </div>

                    {/* 票根特色卡 */}
                    <div className="mt-20 grid grid-cols-1 gap-4 sm:grid-cols-3">
                        <FeatureStub
                            index="A"
                            code="ASK"
                            title="一句一句，聊出行程"
                            desc="说出想去的地方、天数和预算，行程在对话里逐天成形。"
                            delay="320ms"
                        />
                        <FeatureStub
                            index="B"
                            code="BITE"
                            title="饭点有人指路"
                            desc="按你所在的城市推荐地道馆子和稳妥选择，不用站在街头翻点评。"
                            delay="400ms"
                        />
                        <FeatureStub
                            index="C"
                            code="CHANGE"
                            title="不合适就当场改"
                            desc="多留一天、删掉一个点，开口即改，新安排马上可见。"
                            delay="480ms"
                        />
                    </div>
                </div>
            </main>

            {/* 底部 */}
            <footer className="py-6 text-center text-[11px] tracking-[0.15em]" style={{ ...monoFont, color: MIST }}>
                PASSAGE · 安先生的旅游助手 — 下一次出发，随时打印
            </footer>
        </div>
    );
}

/** 签名元素：撕线车票 */
function TicketCard() {
    return (
        <div className="relative">
            {/* 第二张票根：在主票下方错位露出一角 */}
            <div
                className="absolute flex items-center justify-between rounded-md border px-4"
                style={{
                    left: 26,
                    bottom: -12,
                    width: "58%",
                    height: 32,
                    transform: "rotate(1.8deg)",
                    backgroundColor: TICKET_FACE,
                    borderColor: "rgba(38, 34, 28, 0.4)",
                    zIndex: 0,
                }}
            >
                <span style={{ ...monoFont, fontSize: 9, letterSpacing: "0.25em", color: "rgba(38, 34, 28, 0.45)" }}>
                    STUB — 存根联
                </span>
                <span style={{ ...monoFont, fontSize: 9, color: "rgba(38, 34, 28, 0.45)" }}>07A</span>
            </div>

            {/* 主票 */}
            <div
                className="relative flex"
                style={{
                    width: 440,
                    maxWidth: "100%",
                    backgroundColor: TICKET_FACE,
                    border: `1px solid ${CHAR}`,
                    borderRadius: 8,
                    boxShadow: "0 26px 48px -22px rgba(38, 34, 28, 0.45)",
                    zIndex: 1,
                }}
            >
                {/* 左：票面主区 */}
                <div className="relative flex-1 px-6 py-5" style={{ minWidth: 0 }}>
                    <div className="flex items-center justify-between gap-3">
                        <span style={{ ...monoFont, fontSize: 10, letterSpacing: "0.18em", color: INK }}>
                            TRAVEL PASS — NO. 2609
                        </span>
                        <span style={{ ...monoFont, fontSize: 10, letterSpacing: "0.08em", color: MIST }}>NYN → HRB</span>
                    </div>

                    <div className="mt-4 flex items-baseline gap-2.5">
                        <span
                            style={{ ...serifFont, fontWeight: 900, fontSize: "clamp(24px, 7.5vw, 34px)", color: INK, lineHeight: 1.2 }}
                        >
                            南宁
                        </span>
                        <span style={{ ...monoFont, fontSize: 18, color: ORANGE }}>→</span>
                        <span
                            style={{ ...serifFont, fontWeight: 900, fontSize: "clamp(24px, 7.5vw, 34px)", color: INK, lineHeight: 1.2 }}
                        >
                            哈尔滨
                        </span>
                    </div>

                    <div className="mt-2.5" style={{ ...monoFont, fontSize: 11, letterSpacing: "0.08em", color: MIST }}>
                        2026-10-01 08:26 开
                    </div>

                    <div className="mt-5 flex gap-7">
                        <TicketField label="车次 TRAIN" value="D 2609" />
                        <TicketField label="检票口 GATE" value="B 12" />
                        <TicketField label="座位 SEAT" value="靠窗 07A" />
                    </div>

                    {/* 已检票邮戳 */}
                    <div className="absolute" style={{ right: 12, top: 22, transform: "rotate(-14deg)", opacity: 0.88 }}>
                        <div style={{ border: `2px solid ${STAMP_RED}`, borderRadius: 9999, padding: 3 }}>
                            <div
                                className="flex flex-col items-center justify-center"
                                style={{ border: `1px solid ${STAMP_RED}`, borderRadius: 9999, width: 76, height: 76 }}
                            >
                                <span style={{ ...serifFont, fontWeight: 900, fontSize: 15, lineHeight: 1, color: STAMP_RED }}>
                                    已检票
                                </span>
                                <span style={{ ...monoFont, fontSize: 8, letterSpacing: "0.14em", color: STAMP_RED, marginTop: 4 }}>
                                    2026.10.01
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* 撕线与打孔缺口 */}
                <div
                    className="absolute"
                    style={{ left: "70%", top: 6, bottom: 6, borderLeft: "1.5px dashed rgba(38, 34, 28, 0.4)" }}
                />
                <div
                    className="absolute rounded-full"
                    style={{ left: "calc(70% - 8px)", top: -8, width: 16, height: 16, backgroundColor: PAPER }}
                />
                <div
                    className="absolute rounded-full"
                    style={{ left: "calc(70% - 8px)", bottom: -8, width: 16, height: 16, backgroundColor: PAPER }}
                />

                {/* 右：副联 */}
                <div className="flex flex-col items-center justify-between py-4" style={{ width: "30%" }}>
                    <span style={{ ...monoFont, fontSize: 9, letterSpacing: "0.2em", color: MIST }}>GATE B12</span>
                    <span style={{ ...monoFont, fontSize: 24, fontWeight: 700, color: INK }}>07A</span>
                    <span style={{ ...monoFont, fontSize: 9, color: MIST }}>靠窗 WINDOW</span>
                    <div className="flex items-end" style={{ gap: 2, height: 22 }}>
                        {BARCODE_WIDTHS.map((w, i) => (
                            <span key={i} className="inline-block" style={{ width: w, height: "100%", backgroundColor: CHAR }} />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

/** 票面上的小字段 */
function TicketField({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <div style={{ ...monoFont, fontSize: 9, letterSpacing: "0.14em", color: MIST }}>{label}</div>
            <div className="mt-1" style={{ ...monoFont, fontSize: 12, color: INK }}>{value}</div>
        </div>
    );
}

/** 票根风格特色卡 */
function FeatureStub({
    index,
    code,
    title,
    desc,
    delay,
}: {
    index: string;
    code: string;
    title: string;
    desc: string;
    delay: string;
}) {
    return (
        <div
            className="lp-fade-up flex overflow-hidden rounded-lg border"
            style={{
                backgroundColor: TICKET_FACE,
                borderColor: "rgba(38, 34, 28, 0.5)",
                boxShadow: "0 12px 26px -20px rgba(38, 34, 28, 0.5)",
                animationDelay: delay,
            }}
        >
            <div
                className="flex flex-col items-center justify-between py-4"
                style={{
                    width: 52,
                    borderRight: "1.5px dashed rgba(38, 34, 28, 0.35)",
                    backgroundColor: "rgba(122, 154, 168, 0.12)",
                }}
            >
                <span style={{ ...monoFont, fontSize: 20, fontWeight: 700, color: ORANGE, lineHeight: 1 }}>{index}</span>
                <span
                    className="uppercase"
                    style={{ ...monoFont, fontSize: 8, letterSpacing: "0.3em", color: MIST, writingMode: "vertical-rl", textOrientation: "upright" }}
                >
                    {code}
                </span>
            </div>
            <div className="flex-1 p-4">
                <h3 style={{ ...serifFont, fontWeight: 900, fontSize: 16, color: INK }}>{title}</h3>
                <p className="mt-2 text-xs leading-relaxed" style={{ color: MIST }}>{desc}</p>
            </div>
        </div>
    );
}

export default function HomePage() {
    return (
        <Suspense
            fallback={
                <div className="min-h-screen flex items-center justify-center">
                    <Loading size="lg" />
                </div>
            }
        >
            <HomeContent />
        </Suspense>
    );
}
