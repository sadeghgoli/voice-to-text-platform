"use client";

import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await api<{ access_token: string }>("/api/v1/admin/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem("stt_token", result.access_token);
      window.location.href = "/dashboard";
    } catch (err) {
      setError(err instanceof Error ? err.message : "ورود ناموفق بود");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[radial-gradient(circle_at_top,_hsl(226_72%_48%/0.16),_transparent_45%)] p-4">
      <Card className="w-full max-w-md">
        <CardContent className="space-y-6 p-8">
          <div>
            <p className="text-sm text-muted-foreground">سرویس مرکزی گفتار به نوشتار</p>
            <h1 className="mt-1 text-2xl font-bold">ورود به پنل مدیریت</h1>
          </div>
          <form className="space-y-4" onSubmit={onSubmit}>
            <label className="block space-y-2 text-sm">
              <span>ایمیل</span>
              <Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </label>
            <label className="block space-y-2 text-sm">
              <span>رمز عبور</span>
              <Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} />
            </label>
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            <Button className="w-full" disabled={loading} type="submit">
              {loading ? "در حال ورود..." : "ورود"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
