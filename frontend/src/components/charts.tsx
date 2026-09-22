"use client";

import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function tick(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("fa-IR", { month: "short", day: "numeric", hour: "2-digit" });
}

export function BarBlock({ data, dataKey, color = "hsl(226 72% 48%)" }: { data: object[]; dataKey: string; color?: string }) {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="t" tickFormatter={tick} tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip labelFormatter={(label) => tick(String(label))} />
          <Bar dataKey={dataKey} fill={color} radius={6} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LineBlock({ data, dataKey }: { data: object[]; dataKey: string }) {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="t" tickFormatter={tick} tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip labelFormatter={(label) => tick(String(label))} />
          <Area dataKey={dataKey} stroke="hsl(226 72% 48%)" fill="hsl(226 72% 48% / 0.2)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ClientBars({ data }: { data: { client: string; requests: number }[] }) {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="client" width={110} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="requests" fill="hsl(173 58% 39%)" radius={6} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
