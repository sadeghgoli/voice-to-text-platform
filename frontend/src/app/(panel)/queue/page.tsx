"use client";

import { useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { STATUS_LABELS, formatNumber, formatSeconds } from "@/lib/format";
import { usePolling } from "@/lib/use-polling";

type QueueInfo = {
  paused: boolean | null;
  queue_length: number | null;
  worker_online: boolean;
  counts: Record<string, number>;
  avg_waiting_ms: number | null;
  avg_processing_ms: number | null;
};

export default function QueuePage() {
  const { data, error, reload } = usePolling<QueueInfo>("/api/v1/admin/queue", 5000);
  const [actionError, setActionError] = useState("");

  async function setPaused(paused: boolean) {
    setActionError("");
    try {
      await api(paused ? "/api/v1/admin/queue/pause" : "/api/v1/admin/queue/resume", { method: "POST" });
      await reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "تغییر وضعیت صف ناموفق بود");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">صف پردازش</h1>
          <p className="text-sm text-muted-foreground">Worker {data?.worker_online ? "آنلاین است" : "آفلاین است"}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setPaused(true)}>توقف صف</Button>
          <Button onClick={() => setPaused(false)}>ادامه صف</Button>
        </div>
      </div>
      {error || actionError ? <p className="text-sm text-destructive">{error || actionError}</p> : null}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <Info title="طول صف" value={formatNumber(data?.queue_length)} />
        <Info title="وضعیت صف" value={data?.paused ? "متوقف" : "فعال"} />
        <Info title="میانگین انتظار" value={data?.avg_waiting_ms == null ? "—" : formatSeconds(data.avg_waiting_ms / 1000)} />
        <Info title="میانگین پردازش" value={data?.avg_processing_ms == null ? "—" : formatSeconds(data.avg_processing_ms / 1000)} />
        {Object.entries(data?.counts || {}).map(([status, count]) => (
          <Card key={status}>
            <CardHeader className="items-center"><CardTitle>{STATUS_LABELS[status] || status}</CardTitle><StatusBadge status={status} /></CardHeader>
            <CardContent><p className="text-2xl font-bold">{formatNumber(count)}</p></CardContent>
          </Card>
        ))}
      </section>
    </div>
  );
}

function Info({ title, value }: { title: string; value: string }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent><p className="text-2xl font-bold">{value}</p></CardContent>
    </Card>
  );
}
