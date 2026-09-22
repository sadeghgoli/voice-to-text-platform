"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { Input } from "@/components/ui/input";
import { formatDate, formatSeconds } from "@/lib/format";
import { usePolling } from "@/lib/use-polling";

type JobRow = {
  id: string;
  filename: string;
  client_name: string | null;
  language: string | null;
  detected_language: string | null;
  model: string;
  priority: number;
  status: string;
  duration: number | null;
  processing_time: number | null;
  created_at: string;
};

export default function JobsPage() {
  const [status, setStatus] = useState("");
  const [model, setModel] = useState("");
  const [language, setLanguage] = useState("");
  const [q, setQ] = useState("");
  const query = useMemo(() => {
    const params = new URLSearchParams({ page_size: "50" });
    if (status) params.set("status", status);
    if (model) params.set("model", model);
    if (language) params.set("language", language);
    if (q) params.set("q", q);
    return `/api/v1/admin/jobs?${params.toString()}`;
  }, [status, model, language, q]);
  const { data, error } = usePolling<{ items: JobRow[] }>(query, 5000);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">درخواست‌ها</h1>
        <p className="text-sm text-muted-foreground">جستجو و فیلتر صف پردازش</p>
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <Input placeholder="جستجوی نام فایل یا شناسه" value={q} onChange={(event) => setQ(event.target.value)} />
        <select className="h-10 rounded-xl border bg-card px-3 text-sm" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">همه وضعیت‌ها</option>
          <option value="queued">در صف</option>
          <option value="processing">در حال پردازش</option>
          <option value="completed">تمام‌شده</option>
          <option value="failed">ناموفق</option>
          <option value="cancelled">لغوشده</option>
        </select>
        <Input placeholder="مدل" value={model} onChange={(event) => setModel(event.target.value)} />
        <Input placeholder="زبان، مثلاً fa" value={language} onChange={(event) => setLanguage(event.target.value)} />
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <div className="overflow-x-auto rounded-2xl border bg-card">
        <table className="w-full min-w-[900px] text-sm">
          <thead className="bg-muted/60 text-muted-foreground">
            <tr>
              {["شناسه", "فایل", "کلاینت", "زبان", "مدل", "اولویت", "وضعیت", "مدت", "زمان پردازش", "ایجاد"].map((head) => (
                <th key={head} className="px-3 py-3 text-right font-medium">{head}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(data?.items || []).map((job) => (
              <tr key={job.id} className="border-t">
                <td className="px-3 py-3"><Link className="text-primary" href={`/jobs/${job.id}`}>{job.id.slice(0, 8)}</Link></td>
                <td className="px-3 py-3">{job.filename}</td>
                <td className="px-3 py-3">{job.client_name || "—"}</td>
                <td className="px-3 py-3">{job.detected_language || job.language || "خودکار"}</td>
                <td className="px-3 py-3">{job.model}</td>
                <td className="px-3 py-3">{job.priority}</td>
                <td className="px-3 py-3"><StatusBadge status={job.status} /></td>
                <td className="px-3 py-3">{formatSeconds(job.duration)}</td>
                <td className="px-3 py-3">{job.processing_time == null ? "—" : formatSeconds(job.processing_time)}</td>
                <td className="px-3 py-3">{formatDate(job.created_at)}</td>
              </tr>
            ))}
            {!data?.items?.length ? (
              <tr><td className="px-3 py-8 text-center text-muted-foreground" colSpan={10}>درخواستی پیدا نشد.</td></tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
