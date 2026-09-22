"use client";

import { LineBlock } from "@/components/charts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber } from "@/lib/format";
import { usePolling } from "@/lib/use-polling";

type SystemInfo = {
  health: { status: string; gpu: string; queue: string; database: string; worker?: string };
  stats: {
    gpu?: {
      name?: string;
      utilization_percent?: number;
      vram_used_mb?: number;
      vram_total_mb?: number;
      temperature_c?: number;
      power_w?: number;
    };
    cpu?: { percent?: number };
    memory?: { percent?: number; used_mb?: number; total_mb?: number };
  } | null;
  history: { t: string; gpu: number | null; cpu?: number; ram?: number }[];
};

export default function SystemPage() {
  const { data, error } = usePolling<SystemInfo>("/api/v1/admin/system", 5000);
  const gpu = data?.stats?.gpu;
  const vram = gpu?.vram_used_mb != null && gpu.vram_total_mb ? `${(gpu.vram_used_mb / 1024).toFixed(1)} / ${(gpu.vram_total_mb / 1024).toFixed(1)} GB` : "—";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">سیستم</h1>
        <p className="text-sm text-muted-foreground">سلامت سرویس و وضعیت کارت گرافیک</p>
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Card className="overflow-hidden">
        <CardContent className="grid gap-6 p-6 md:grid-cols-[1.2fr_1fr]">
          <div>
            <p className="text-sm text-muted-foreground">پردازنده گرافیکی</p>
            <h2 className="mt-1 text-3xl font-bold">{gpu?.name || "در انتظار Worker"}</h2>
            <p className="mt-4 text-lg">GPU: {gpu?.utilization_percent == null ? "—" : `${formatNumber(gpu.utilization_percent)}٪`}</p>
            <p>VRAM: {vram}</p>
            <p>دما: {gpu?.temperature_c == null ? "—" : `${formatNumber(gpu.temperature_c)}°C`}</p>
            <p>توان: {gpu?.power_w == null ? "—" : `${gpu.power_w} W`}</p>
          </div>
          <div className="grid gap-3 text-sm">
            <Health label="کل سیستم" value={data?.health.status} />
            <Health label="GPU" value={data?.health.gpu} />
            <Health label="صف" value={data?.health.queue} />
            <Health label="پایگاه داده" value={data?.health.database} />
            <Health label="CPU" value={data?.stats?.cpu?.percent == null ? "—" : `${formatNumber(Math.round(data.stats.cpu.percent))}٪`} />
            <Health label="RAM" value={data?.stats?.memory?.percent == null ? "—" : `${formatNumber(Math.round(data.stats.memory.percent))}٪`} />
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>نمودار بهره‌وری</CardTitle></CardHeader>
        <CardContent><LineBlock data={data?.history || []} dataKey="gpu" /></CardContent>
      </Card>
    </div>
  );
}

function Health({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex items-center justify-between rounded-xl border px-3 py-2">
      <span>{label}</span>
      <span className="font-medium">{value || "—"}</span>
    </div>
  );
}
