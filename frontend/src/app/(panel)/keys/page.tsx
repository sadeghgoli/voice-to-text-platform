"use client";

import { FormEvent, useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { formatSeconds } from "@/lib/format";
import { usePolling } from "@/lib/use-polling";

type Client = { id: string; name: string };
type ApiKey = {
  id: string;
  client_name: string | null;
  name: string;
  description: string;
  prefix: string;
  status: string;
  requests: number;
  audio_seconds: number;
  rate_limit_per_minute: number;
};

export default function KeysPage() {
  const keys = usePolling<{ items: ApiKey[] }>("/api/v1/admin/keys", 10000);
  const clients = usePolling<{ items: Client[] }>("/api/v1/admin/clients", 20000);
  const [clientId, setClientId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [secret, setSecret] = useState("");
  const [error, setError] = useState("");

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const created = await api<{ api_key: string }>("/api/v1/admin/keys", {
        method: "POST",
        body: JSON.stringify({ client_id: clientId, name, description }),
      });
      setSecret(created.api_key);
      setName("");
      setDescription("");
      await keys.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "ساخت کلید ناموفق بود");
    }
  }

  async function act(id: string, action: string) {
    setError("");
    try {
      const result = await api<{ api_key?: string }>(`/api/v1/admin/keys/${id}/${action}`, { method: "POST" });
      if (result.api_key) setSecret(result.api_key);
      await keys.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "عملیات ناموفق بود");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">کلیدهای API</h1>
        <p className="text-sm text-muted-foreground">کلید فقط یک‌بار نمایش داده می‌شود و بعد از آن فقط هش آن نگهداری می‌شود.</p>
      </div>
      <Card>
        <CardHeader><CardTitle>ساخت کلید</CardTitle></CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-4" onSubmit={create}>
            <select className="h-10 rounded-xl border bg-card px-3 text-sm" value={clientId} onChange={(event) => setClientId(event.target.value)} required>
              <option value="">انتخاب کلاینت</option>
              {(clients.data?.items || []).map((client) => (
                <option key={client.id} value={client.id}>{client.name}</option>
              ))}
            </select>
            <Input placeholder="نام کلید" value={name} onChange={(event) => setName(event.target.value)} required />
            <Input placeholder="توضیح" value={description} onChange={(event) => setDescription(event.target.value)} />
            <Button type="submit">ایجاد</Button>
          </form>
        </CardContent>
      </Card>
      {secret ? (
        <Card>
          <CardContent className="space-y-3 p-5">
            <p className="text-sm">این کلید را همین حالا کپی کنید. دوباره نمایش داده نمی‌شود.</p>
            <code className="block break-all rounded-xl bg-muted p-3 text-sm">{secret}</code>
            <Button variant="outline" onClick={() => navigator.clipboard.writeText(secret)}>کپی کلید</Button>
          </CardContent>
        </Card>
      ) : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <div className="space-y-3">
        {(keys.data?.items || []).map((key) => (
          <Card key={key.id}>
            <CardHeader>
              <div>
                <h2 className="font-bold">{key.name}</h2>
                <p className="text-sm text-muted-foreground">{key.client_name} · {key.prefix}</p>
              </div>
              <StatusBadge status={key.status} />
            </CardHeader>
            <CardContent className="flex flex-wrap items-center justify-between gap-3 text-sm">
              <p>درخواست‌ها: {key.requests} · صوت: {formatSeconds(key.audio_seconds)} · سقف دقیقه: {key.rate_limit_per_minute}</p>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => act(key.id, "disable")}>غیرفعال</Button>
                <Button size="sm" variant="outline" onClick={() => act(key.id, "enable")}>فعال</Button>
                <Button size="sm" variant="destructive" onClick={() => act(key.id, "revoke")}>لغو</Button>
                <Button size="sm" onClick={() => act(key.id, "regenerate")}>بازتولید</Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
