"use client";

import { useState } from "react";
import { BarBlock } from "@/components/charts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber, formatSeconds } from "@/lib/format";
import { usePolling } from "@/lib/use-polling";

type Report = {
  totals: { requests: number; successful: number; failed: number; audio_minutes: number; avg_processing_ms: number | null };
  clients: { client: string; requests: number; successful: number; failed: number; audio_minutes: number; avg_processing_ms: number | null }[];
  series: { t: string; requests: number; audio_seconds: number }[];
};

export default function UsagePage() {
  const [range, setRange] = useState("week");
  const { data, error } = usePolling<Report>(`/api/v1/admin/usage?range=${range}`, 15000);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">مصرف</h1>
          <p className="text-sm text-muted-foreground">درخواست، دقیقه صوت و نتیجه به تفکیک کلاینت</p>
        </div>
        <div className="flex gap-2">
          {[
            ["day", "روز"],
            ["week", "هفته"],
            ["month", "ماه"],
          ].map(([value, label]) => (
            <button key={value} className={`rounded-xl border px-3 py-1.5 text-sm ${range === value ? "bg-primary text-primary-foreground" : "bg-card"}`} onClick={() => setRange(value)} type="button">
              {label}
            </button>
          ))}
        </div>
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Metric title="درخواست‌ها" value={formatNumber(data?.totals.requests)} />
        <Metric title="دقیقه صوت" value={formatNumber(data?.totals.audio_minutes)} />
        <Metric title="موفق" value={formatNumber(data?.totals.successful)} />
        <Metric title="ناموفق" value={formatNumber(data?.totals.failed)} />
        <Metric title="میانگین پردازش" value={data?.totals.avg_processing_ms == null ? "—" : formatSeconds((data.totals.avg_processing_ms || 0) / 1000)} />
      </section>
      <Card>
        <CardHeader><CardTitle>روند درخواست‌ها</CardTitle></CardHeader>
        <CardContent><BarBlock data={data?.series || []} dataKey="requests" /></CardContent>
      </Card>
      <div className="overflow-x-auto rounded-2xl border bg-card">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="bg-muted/60 text-muted-foreground">
            <tr>
              {["کلاینت", "درخواست", "موفق", "ناموفق", "دقیقه صوت", "میانگین پردازش"].map((head) => (
                <th key={head} className="px-3 py-3 text-right font-medium">{head}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(data?.clients || []).map((client) => (
              <tr key={client.client} className="border-t">
                <td className="px-3 py-3">{client.client}</td>
                <td className="px-3 py-3">{formatNumber(client.requests)}</td>
                <td className="px-3 py-3">{formatNumber(client.successful)}</td>
                <td className="px-3 py-3">{formatNumber(client.failed)}</td>
                <td className="px-3 py-3">{formatNumber(client.audio_minutes)}</td>
                <td className="px-3 py-3">{client.avg_processing_ms == null ? "—" : formatSeconds(client.avg_processing_ms / 1000)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Metric({ title, value }: { title: string; value: string }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent><p className="text-2xl font-bold">{value}</p></CardContent>
    </Card>
  );
}
