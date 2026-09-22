"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, downloadResult } from "@/lib/api";
import { formatDate, formatSeconds } from "@/lib/format";
import { usePolling } from "@/lib/use-polling";

type JobDetail = {
  id: string;
  filename: string;
  client_name: string | null;
  api_key_name: string | null;
  api_key_prefix: string | null;
  model: string;
  language: string | null;
  detected_language: string | null;
  duration: number | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  processing_time: number | null;
  queue_time: number | null;
  status: string;
  progress: number;
  text: string | null;
  error_message: string | null;
  priority: number;
  segments: { start: number; end: number; text: string }[];
};

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const { data, error, reload } = usePolling<JobDetail>(`/api/v1/admin/jobs/${params.id}`, 4000);
  const [message, setMessage] = useState("");

  async function act(path: string) {
    setMessage("");
    try {
      await api(path, { method: "POST" });
      await reload();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "عملیات ناموفق بود");
    }
  }

  async function copyText() {
    if (!data?.text) return;
    await navigator.clipboard.writeText(data.text);
    setMessage("متن کپی شد.");
  }

  if (!data) return <p className="text-muted-foreground">{error || "در حال دریافت جزئیات..."}</p>;

  const fields = [
    ["شناسه", data.id],
    ["فایل", data.filename],
    ["کلاینت", data.client_name || "—"],
    ["کلید", data.api_key_prefix || data.api_key_name || "—"],
    ["مدل", data.model],
    ["زبان", data.detected_language || data.language || "خودکار"],
    ["اولویت", String(data.priority)],
    ["مدت", formatSeconds(data.duration)],
    ["ایجاد", formatDate(data.created_at)],
    ["شروع", formatDate(data.started_at)],
    ["پایان", formatDate(data.completed_at)],
    ["زمان صف", data.queue_time == null ? "—" : formatSeconds(data.queue_time)],
    ["زمان پردازش", data.processing_time == null ? "—" : formatSeconds(data.processing_time)],
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">جزئیات درخواست</h1>
          <p className="text-sm text-muted-foreground">پیشرفت {data.progress}٪</p>
        </div>
        <StatusBadge status={data.status} />
      </div>
      {message ? <p className="text-sm">{message}</p> : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Card>
        <CardContent className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-3">
          {fields.map(([label, value]) => (
            <div key={label}>
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="mt-1 break-all text-sm font-medium">{value}</p>
            </div>
          ))}
        </CardContent>
      </Card>
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={copyText} disabled={!data.text}>کپی متن</Button>
        {["txt", "json", "srt", "vtt"].map((format) => (
          <Button key={format} variant="outline" disabled={data.status !== "completed"} onClick={() => downloadResult(data.id, format)}>
            دانلود {format.toUpperCase()}
          </Button>
        ))}
        <Button variant="destructive" onClick={() => act(`/api/v1/admin/jobs/${data.id}/cancel`)}>لغو</Button>
        <Button onClick={() => act(`/api/v1/admin/jobs/${data.id}/retry`)}>تلاش مجدد</Button>
      </div>
      <Card>
        <CardHeader><CardTitle>متن تبدیل‌شده</CardTitle></CardHeader>
        <CardContent>
          {data.error_message ? <p className="mb-3 text-sm text-destructive">{data.error_message}</p> : null}
          <p className="whitespace-pre-wrap leading-8">{data.text || "هنوز متنی ثبت نشده است."}</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>قطعه‌ها</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {data.segments.map((segment, index) => (
            <div key={`${segment.start}-${index}`} className="rounded-xl border p-3">
              <p className="text-xs text-muted-foreground">{formatSeconds(segment.start)} تا {formatSeconds(segment.end)}</p>
              <p className="mt-1">{segment.text}</p>
            </div>
          ))}
          {!data.segments.length ? <p className="text-sm text-muted-foreground">قطعه‌ای ثبت نشده است.</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
