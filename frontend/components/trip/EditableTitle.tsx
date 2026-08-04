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

    const startEdit = () => {
        setValue(trip.title);
        setEditing(true);
    };

    const cancel = () => {
        setEditing(false);
        setValue(trip.title);
    };

    const save = async () => {
        const title = value.trim();
        if (!title) {
            alert("标题不能为空");
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
            alert(err instanceof Error ? err.message : "保存失败");
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
                    className="w-full text-xl font-bold text-stone-800 bg-white border border-orange-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-orange-300"
                />
                <button
                    onClick={save}
                    disabled={saving}
                    className="shrink-0 px-3 py-1.5 text-sm rounded-lg bg-gradient-to-r from-orange-500 to-rose-500 text-white hover:from-orange-600 hover:to-rose-600 transition-colors disabled:opacity-50"
                >
                    {saving ? "保存中..." : "保存"}
                </button>
                <button
                    onClick={cancel}
                    disabled={saving}
                    className="shrink-0 px-3 py-1.5 text-sm rounded-lg text-stone-500 border border-stone-200 hover:border-stone-300 hover:text-stone-700 transition-colors disabled:opacity-50"
                >
                    取消
                </button>
            </div>
        );
    }

    return (
        <div className="flex items-center gap-2 group flex-1 min-w-0">
            <h2 className="text-xl font-bold text-stone-800 truncate">{trip.title}</h2>
            <button
                onClick={startEdit}
                className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity p-1 text-stone-400 hover:text-orange-600 hover:bg-orange-50 rounded"
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
