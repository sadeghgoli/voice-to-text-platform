"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { formatDate } from "@/lib/format";
import { usePolling } from "@/lib/use-polling";

type LogItem = { event?: string; level?: string; timestamp?: string; error?: string };
type Audit = { id: string; action: string; actor_type: string; resource_type: string; ip: string | null; created_at: string };

export default function LogsPage() {
  const [tab, setTab] = useState<"ops" | "audit">("ops");
  const logs = usePolling<{ items: LogItem[] }>("/api/v1/admin/logs?limit=150", 8000);
  const audit = usePolling<{ items: Audit[] }>("/api/v1/admin/logs/audit", 8000);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">لاگ‌ها</h1>
        <p className="text-sm text-muted-foreground">رویدادهای عملیاتی و ممیزی مدیریت</p>
      </div>
      <div className="flex gap-2">
        <button className={`rounded-xl border px-3 py-1.5 text-sm ${tab === "ops" ? "bg-primary text-primary-foreground" : "bg-card"}`} onClick={() => setTab("ops")} type="button">عملیاتی</button>
        <button className={`rounded-xl border px-3 py-1.5 text-sm ${tab === "audit" ? "bg-primary text-primary-foreground" : "bg-card"}`} onClick={() => setTab("audit")} type="button">ممیزی</button>
      </div>
      {tab === "ops" ? (
        <div className="space-y-2">
          {(logs.data?.items || []).map((item, index) => (
            <Card key={`${item.timestamp}-${index}`}>
              <CardContent className="flex flex-wrap items-center justify-between gap-2 p-4 text-sm">
                <span className="font-medium">{item.event || "log"}</span>
                <span className="text-muted-foreground">{item.level} · {formatDate(item.timestamp)} {item.error ? `· ${item.error}` : ""}</span>
              </CardContent>
            </Card>
          ))}
          {!logs.data?.items?.length ? <p className="text-sm text-muted-foreground">{logs.error || "لاگی ثبت نشده است."}</p> : null}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border bg-card">
          <table className="w-full min-w-[680px] text-sm">
            <thead className="bg-muted/60 text-muted-foreground">
              <tr>
                {["زمان", "عمل", "فاعل", "منبع", "IP"].map((head) => <th key={head} className="px-3 py-3 text-right font-medium">{head}</th>)}
              </tr>
            </thead>
            <tbody>
              {(audit.data?.items || []).map((item) => (
                <tr key={item.id} className="border-t">
                  <td className="px-3 py-3">{formatDate(item.created_at)}</td>
                  <td className="px-3 py-3">{item.action}</td>
                  <td className="px-3 py-3">{item.actor_type}</td>
                  <td className="px-3 py-3">{item.resource_type}</td>
                  <td className="px-3 py-3">{item.ip || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
