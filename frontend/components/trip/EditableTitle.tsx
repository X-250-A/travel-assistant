"use client";

import { useState } from "react";
import type { Trip } from "@/types";
import { updateTrip } from "@/lib/api";

interface Props {
    trip: Trip;
    onSaved: (trip: Trip) => void;
}

export default function EditableTitle({ trip, onSaved }: Props) {
    const [editing, setEditing] = useState(false);
    const [value, setValue] = useState(trip.title);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");

    const startEdit = () => {
        setValue(trip.title);
        setError("");
        setEditing(true);
    };

    const cancel = () => {
        setEditing(false);
        setValue(trip.title);
        setError("");
    };

    const save = async () => {
        const title = value.trim();
        if (!title) {
            setError("标题不能为空");
            return;
        }
        if (title === trip.title) {
            setEditing(false);
            return;
        }

        setSaving(true);
        try {
            const updated = await updateTrip(trip.id, { title });
            onSaved(updated);
            setEditing(false);
        } catch (err) {
            setError(err instanceof Error ? err.message : "保存失败");
        } finally {
            setSaving(false);
        }
    };

    if (editing) {
        return (
            <div className="flex items-center gap-2 flex-1 min-w-0">
                <input
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === "Enter") save();
                        if (e.key === "Escape") cancel();
                    }}
                    autoFocus
                    maxLength={200}
                    className="w-full text-xl font-serif font-bold text-ink bg-ticket-face border border-gate rounded-md px-3 py-1.5
                               focus:outline-none focus-visible:ring-2 focus-visible:ring-gate/40"
                />
                <button
                    onClick={save}
                    disabled={saving}
                    className="shrink-0 px-3 py-1.5 text-sm rounded-md bg-gate text-[#FFFDF7] hover:bg-gate-dark transition-colors disabled:opacity-50
                               focus-visible:outline focus-visible:outline-2 focus-visible:outline-gate focus-visible:outline-offset-2"
                >
                    {saving ? "保存中..." : "保存"}
                </button>
                <button
                    onClick={cancel}
                    disabled={saving}
                    className="shrink-0 px-3 py-1.5 text-sm rounded-md text-mist border border-char/30 hover:text-ink hover:border-char/50 transition-colors disabled:opacity-50
                               focus-visible:outline focus-visible:outline-2 focus-visible:outline-gate focus-visible:outline-offset-2"
                >
                    取消
                </button>
                {error && (
                    <span className="basis-full flex items-center gap-1.5 font-mono text-[10px] tracking-[0.15em] text-stamp-red">
                        <span className="border border-stamp-red/50 rounded px-1">ERR</span>
                        <span className="font-sans tracking-normal">{error}</span>
                    </span>
                )}
            </div>
        );
    }

    return (
        <div className="flex items-center gap-2 group flex-1 min-w-0">
            <h2 className="text-xl font-serif font-bold text-ink truncate group-hover:underline decoration-gate/60 decoration-dashed underline-offset-4">
                {trip.title}
            </h2>
            <button
                onClick={startEdit}
                className="shrink-0 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity p-1 text-mist hover:text-gate hover:bg-gate/10 rounded
                           focus-visible:opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-gate"
                title="编辑标题"
            >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                    />
                </svg>
            </button>
        </div>
    );
}
