"use client";

interface BarcodeProps {
    className?: string;
    color?: string;
}

const WIDTHS = [2, 1, 3, 1, 2, 1, 1, 3, 2, 1, 3, 1, 2, 2, 1, 3, 1, 1];

/** 票面装饰条码 */
export default function Barcode({ className = "", color = "rgba(38, 34, 28, 0.7)" }: BarcodeProps) {
    return (
        <span
            className={`inline-flex items-stretch ${className}`}
            aria-hidden="true"
            style={{ gap: 1.5 }}
        >
            {WIDTHS.map((w, i) => (
                <span
                    key={i}
                    className="inline-block h-full"
                    style={{ width: w, backgroundColor: color }}
                />
            ))}
        </span>
    );
}
