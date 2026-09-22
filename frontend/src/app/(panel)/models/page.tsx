"use client";

import { useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { usePolling } from "@/lib/use-polling";

type Model = {
  id: string;
  name: string;
  display_name: string;
  language: string;
  size: string;
  vram_mb: number;
  status: string;
  default: boolean;
  engine: string;
};

export default function ModelsPage() {
  const { data, error, reload } = usePolling<{ items: Model[] }>("/api/v1/admin/models", 15000);
  const [actionError, setActionError] = useState("");

  async function makeDefault(id: string) {
    setActionError("");
    try {
      await api(`/api/v1/admin/models/${id}/default`, { method: "POST" });
      await reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "تغییر مدل پیش‌فرض ناموفق بود");
    }
  }

  async function toggle(model: Model) {
    setActionError("");
    try {
      await api(`/api/v1/admin/models/${model.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: model.status !== "active" }),
      });
      await reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "تغییر وضعیت مدل ناموفق بود");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">مدل‌ها</h1>
        <p className="text-sm text-muted-foreground">مدل پیش‌فرض یک‌بار در Worker بارگذاری می‌شود و برای هر درخواست دوباره لود نمی‌شود.</p>
      </div>
      {error || actionError ? <p className="text-sm text-destructive">{error || actionError}</p> : null}
      <div className="grid gap-4 md:grid-cols-2">
        {(data?.items || []).map((model) => (
          <Card key={model.id}>
            <CardHeader>
              <div>
                <h2 className="font-bold">{model.display_name}</h2>
                <p className="text-sm text-muted-foreground">{model.engine} · {model.name}</p>
              </div>
              <StatusBadge status={model.default ? "active" : model.status} />
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <p>زبان: {model.language}</p>
              <p>حجم: {model.size}</p>
              <p>حافظه GPU: {formatNumber(model.vram_mb)} مگابایت</p>
              <p>{model.default ? "مدل پیش‌فرض" : "قابل انتخاب"}</p>
              <div className="flex gap-2">
                <Button size="sm" disabled={model.default} onClick={() => makeDefault(model.id)}>پیش‌فرض</Button>
                <Button size="sm" variant="outline" onClick={() => toggle(model)}>{model.status === "active" ? "غیرفعال‌سازی" : "فعال‌سازی"}</Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
