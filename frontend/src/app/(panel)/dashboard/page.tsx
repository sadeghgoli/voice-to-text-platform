"use client";

import { useState } from "react";
import { BarBlock, ClientBars, LineBlock } from "@/components/charts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber, formatSeconds } from "@/lib/format";
import { usePolling } from "@/lib/use-polling";

type Summary = {
  total_jobs: number;
  queued_jobs: number;
  processing_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  total_audio_seconds: number;
  queue_length: number | null;
  avg_processing_ms: number | null;
  jobs_per_hour: number;
  gpu?: { name?: string; utilization_percent?: number; vram_used_mb?: number; vram_total_mb?: number; temperature_c?: number } | null;
  cpu?: { percent?: number } | null;
  memory?: { percent?: number; used_mb?: number; total_mb?: number } | null;
};

type Series = {
  jobs_over_time: { t: string; count: number; audio_seconds: number }[];
  processing_time: { t: string; avg_ms: number }[];
  api_usage: { client: string; requests: number }[];
  gpu_utilization: { t: string; gpu: number | null }[];
};

export default function DashboardPage() {
  const [range, setRange] = useState("7d");
  const summary = usePolling<Summary>("/api/v1/admin/dashboard", 8000);
  const series = usePolling<Series>(`/api/v1/admin/dashboard/series?range=${range}`, 15000);
  const data = summary.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">داشبورد</h1>
        <p className="text-sm text-muted-foreground">وضعیت صف، پردازش و سخت‌افزار سرویس مرکزی</p>
      </div>
      {summary.error ? <p className="text-sm text-destructive">{summary.error}</p> : null}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat title="کل درخواست‌ها" value={formatNumber(data?.total_jobs)} />
        <Stat title="در صف" value={formatNumber(data?.queued_jobs)} />
        <Stat title="در حال پردازش" value={formatNumber(data?.processing_jobs)} />
        <Stat title="تمام‌شده" value={formatNumber(data?.completed_jobs)} />
        <Stat title="ناموفق" value={formatNumber(data?.failed_jobs)} />
        <Stat title="مدت صوت" value={formatSeconds(data?.total_audio_seconds)} />
        <Stat title="طول صف" value={formatNumber(data?.queue_length)} />
        <Stat title="درخواست در ساعت" value={formatNumber(data?.jobs_per_hour)} />
        <Stat title="میانگین پردازش" value={data?.avg_processing_ms == null ? "—" : `${formatNumber(Math.round(data.avg_processing_ms / 1000))} ثانیه`} />
        <Stat title="CPU" value={data?.cpu?.percent == null ? "—" : `${formatNumber(Math.round(data.cpu.percent))}٪`} />
        <Stat title="RAM" value={data?.memory?.percent == null ? "—" : `${formatNumber(Math.round(data.memory.percent))}٪`} />
        <Stat
          title="GPU"
          value={
            data?.gpu?.utilization_percent == null
              ? data?.gpu?.name || "نامشخص"
              : `${data.gpu.name || "GPU"} · ${formatNumber(data.gpu.utilization_percent)}٪`
          }
        />
      </section>
      <div className="flex gap-2">
        {["24h", "7d", "30d"].map((item) => (
          <button
            key={item}
            className={`rounded-xl border px-3 py-1.5 text-sm ${range === item ? "bg-primary text-primary-foreground" : "bg-card"}`}
            onClick={() => setRange(item)}
            type="button"
          >
            {item === "24h" ? "۲۴ ساعت" : item === "7d" ? "۷ روز" : "۳۰ روز"}
          </button>
        ))}
      </div>
      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>درخواست‌ها در زمان</CardTitle></CardHeader>
          <CardContent><BarBlock data={series.data?.jobs_over_time || []} dataKey="count" /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>مدت صوت</CardTitle></CardHeader>
          <CardContent><BarBlock data={series.data?.jobs_over_time || []} dataKey="audio_seconds" color="hsl(173 58% 39%)" /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>زمان پردازش</CardTitle></CardHeader>
          <CardContent><LineBlock data={series.data?.processing_time || []} dataKey="avg_ms" /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>مصرف API</CardTitle></CardHeader>
          <CardContent><ClientBars data={series.data?.api_usage || []} /></CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>بهره‌وری GPU</CardTitle></CardHeader>
          <CardContent><LineBlock data={series.data?.gpu_utilization || []} dataKey="gpu" /></CardContent>
        </Card>
      </section>
    </div>
  );
}

function Stat({ title, value }: { title: string; value: string }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent><p className="text-2xl font-bold">{value}</p></CardContent>
    </Card>
  );
}
