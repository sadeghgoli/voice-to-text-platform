"use client";

import { FormEvent, useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { formatDate, formatSeconds } from "@/lib/format";
import { usePolling } from "@/lib/use-polling";

type Client = {
  id: string;
  name: string;
  description: string;
  owner_name: string;
  status: string;
  api_keys: number;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  audio_seconds: number;
  last_request: string | null;
};

export default function ClientsPage() {
  const { data, error, reload } = usePolling<{ items: Client[] }>("/api/v1/admin/clients", 10000);
  const [name, setName] = useState("");
  const [owner, setOwner] = useState("");
  const [description, setDescription] = useState("");
  const [message, setMessage] = useState("");

  async function create(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    try {
      await api("/api/v1/admin/clients", {
        method: "POST",
        body: JSON.stringify({ name, owner_name: owner, description, status: "active" }),
      });
      setName("");
      setOwner("");
      setDescription("");
      await reload();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "ثبت کلاینت ناموفق بود");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">کلاینت‌های API</h1>
        <p className="text-sm text-muted-foreground">هر پروژه یک کلاینت و کلید مخصوص خودش را دارد.</p>
      </div>
      <Card>
        <CardHeader><CardTitle>کلاینت جدید</CardTitle></CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-4" onSubmit={create}>
            <Input placeholder="نام پروژه" value={name} onChange={(event) => setName(event.target.value)} required />
            <Input placeholder="مالک" value={owner} onChange={(event) => setOwner(event.target.value)} />
            <Input placeholder="توضیح" value={description} onChange={(event) => setDescription(event.target.value)} />
            <Button type="submit">ثبت</Button>
          </form>
          {message ? <p className="mt-3 text-sm text-destructive">{message}</p> : null}
        </CardContent>
      </Card>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        {(data?.items || []).map((client) => (
          <Card key={client.id}>
            <CardHeader>
              <div>
                <h2 className="font-bold">{client.name}</h2>
                <p className="text-sm text-muted-foreground">{client.owner_name || "بدون مالک"} · {client.description}</p>
              </div>
              <StatusBadge status={client.status} />
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-3 text-sm">
              <p>کلیدها: {client.api_keys}</p>
              <p>درخواست‌ها: {client.total_requests}</p>
              <p>موفق: {client.successful_requests}</p>
              <p>ناموفق: {client.failed_requests}</p>
              <p>صوت: {formatSeconds(client.audio_seconds)}</p>
              <p>آخرین درخواست: {formatDate(client.last_request)}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
