"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";

const fields: { key: string; label: string; type?: string }[] = [
  { key: "default_model", label: "مدل پیش‌فرض" },
  { key: "default_language", label: "زبان پیش‌فرض" },
  { key: "max_upload_mb", label: "سقف آپلود (مگابایت)", type: "number" },
  { key: "max_audio_duration_seconds", label: "سقف مدت صوت (ثانیه)", type: "number" },
  { key: "max_concurrent_jobs", label: "کار همزمان", type: "number" },
  { key: "default_priority", label: "اولویت پیش‌فرض", type: "number" },
  { key: "retention_days", label: "نگهداری نتیجه (روز)", type: "number" },
  { key: "audio_retention_hours", label: "حذف فایل صوتی بعد از (ساعت)", type: "number" },
  { key: "storage_path", label: "مسیر ذخیره‌سازی" },
  { key: "temp_path", label: "مسیر موقت" },
  { key: "gpu_device", label: "دستگاه GPU" },
  { key: "webhook_timeout_seconds", label: "مهلت وبهوک (ثانیه)", type: "number" },
  { key: "rate_limit_per_minute", label: "محدودیت درخواست در دقیقه", type: "number" },
  { key: "beam_size", label: "beam size", type: "number" },
  { key: "temperature", label: "temperature", type: "number" },
  { key: "max_retries", label: "تلاش مجدد خودکار", type: "number" },
  { key: "persian_initial_prompt", label: "پرامپت اولیه فارسی" },
];

export default function SettingsPage() {
  const [values, setValues] = useState<Record<string, string>>({});
  const [vad, setVad] = useState(true);
  const [words, setWords] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    api<{ items: Record<string, unknown> }>("/api/v1/admin/settings")
      .then((result) => {
        const next: Record<string, string> = {};
        for (const field of fields) next[field.key] = String(result.items[field.key] ?? "");
        setValues(next);
        setVad(Boolean(result.items.vad_filter));
        setWords(Boolean(result.items.word_timestamps));
      })
      .catch((err: Error) => setMessage(err.message));
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    const body: Record<string, unknown> = { vad_filter: vad, word_timestamps: words };
    for (const field of fields) {
      const raw = values[field.key] ?? "";
      body[field.key] = field.type === "number" ? Number(raw) : raw;
    }
    try {
      await api("/api/v1/admin/settings", { method: "PUT", body: JSON.stringify(body) });
      setMessage("تنظیمات ذخیره شد. تغییر دستگاه GPU بعد از ری‌استارت Worker اعمال می‌شود.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "ذخیره ناموفق بود");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">تنظیمات</h1>
        <p className="text-sm text-muted-foreground">مقادیر پیش‌فرض پردازش، نگهداری فایل و محدودیت‌ها</p>
      </div>
      <Card>
        <CardHeader><CardTitle>پیکربندی سرویس</CardTitle></CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-2" onSubmit={save}>
            {fields.map((field) => (
              <label key={field.key} className="space-y-2 text-sm">
                <span>{field.label}</span>
                <Input
                  type={field.type || "text"}
                  step={field.key === "temperature" ? "0.1" : undefined}
                  value={values[field.key] || ""}
                  onChange={(event) => setValues((current) => ({ ...current, [field.key]: event.target.value }))}
                />
              </label>
            ))}
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={vad} onChange={(event) => setVad(event.target.checked)} /> فیلتر VAD</label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={words} onChange={(event) => setWords(event.target.checked)} /> زمان‌بندی واژه‌ها</label>
            <div className="md:col-span-2">
              <Button type="submit">ذخیره</Button>
              {message ? <p className="mt-3 text-sm">{message}</p> : null}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
