"use client";

interface StatusStampProps {
    confirmed: boolean;
    /** 章的直径（px） */
    size?: number;
}

/** 车票状态章：已检票 = 邮戳红斜章；待检票 = 检票橙虚线章 */
export default function StatusStamp({ confirmed, size = 72 }: StatusStampProps) {
    if (confirmed) {
        return (
            <div className="shrink-0 select-none" style={{ transform: "rotate(-12deg)", opacity: 0.9 }}>
                <div style={{ border: "2px solid var(--color-stamp-red)", borderRadius: 9999, padding: 3 }}>
                    <div
                        className="flex flex-col items-center justify-center"
                        style={{ border: "1px solid var(--color-stamp-red)", borderRadius: 9999, width: size, height: size }}
                    >
                        <span
                            className="font-serif"
                            style={{ fontWeight: 900, fontSize: size * 0.21, lineHeight: 1, color: "var(--color-stamp-red)" }}
                        >
                            已检票
                        </span>
                        <span
                            className="font-mono"
                            style={{ fontSize: size * 0.1, letterSpacing: "0.1em", color: "var(--color-stamp-red)", marginTop: 3 }}
                        >
                            CHECKED
                        </span>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="shrink-0 select-none" style={{ transform: "rotate(8deg)", opacity: 0.85 }}>
            <div
                className="flex flex-col items-center justify-center"
                style={{ border: "1.5px dashed var(--color-gate)", borderRadius: 9999, width: size, height: size }}
            >
                <span
                    className="font-serif"
                    style={{ fontWeight: 900, fontSize: size * 0.19, lineHeight: 1, color: "var(--color-gate)" }}
                >
                    待检票
                </span>
                <span
                    className="font-mono"
                    style={{ fontSize: size * 0.09, letterSpacing: "0.1em", color: "var(--color-gate)", marginTop: 3 }}
                >
                    PENDING
                </span>
            </div>
        </div>
    );
}
