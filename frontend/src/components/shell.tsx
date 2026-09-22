"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Activity,
  AudioLines,
  Gauge,
  KeyRound,
  LayoutDashboard,
  ListTree,
  LogOut,
  Menu,
  Moon,
  ScrollText,
  Settings,
  Sun,
  Users,
  X,
} from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const links = [
  { href: "/dashboard", label: "داشبورد", icon: LayoutDashboard },
  { href: "/jobs", label: "درخواست‌ها", icon: AudioLines },
  { href: "/queue", label: "صف", icon: ListTree },
  { href: "/clients", label: "کلاینت‌ها", icon: Users },
  { href: "/keys", label: "کلیدهای API", icon: KeyRound },
  { href: "/models", label: "مدل‌ها", icon: Gauge },
  { href: "/usage", label: "مصرف", icon: Activity },
  { href: "/system", label: "سیستم", icon: Gauge },
  { href: "/logs", label: "لاگ‌ها", icon: ScrollText },
  { href: "/settings", label: "تنظیمات", icon: Settings },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [open, setOpen] = useState(false);
  const { theme, setTheme } = useTheme();

  useEffect(() => {
    if (!localStorage.getItem("stt_token")) {
      window.location.href = "/login";
      return;
    }
    setReady(true);
  }, []);

  if (!ready) {
    return <div className="grid min-h-screen place-items-center text-muted-foreground">در حال بارگذاری پنل...</div>;
  }

  return (
    <div className="min-h-screen md:grid md:grid-cols-[16rem_1fr]">
      <aside className={cn("border-l bg-card md:sticky md:top-0 md:h-screen", open ? "block" : "hidden md:block")}>
        <div className="flex items-center justify-between px-5 py-5">
          <div>
            <p className="text-xs text-muted-foreground">سرویس مرکزی</p>
            <p className="text-lg font-bold">تبدیل صوت به متن</p>
          </div>
          <button className="md:hidden" onClick={() => setOpen(false)} type="button" aria-label="بستن منو">
            <X className="h-5 w-5" />
          </button>
        </div>
        <nav className="space-y-1 px-3">
          {links.map((link) => {
            const active = link.href === "/dashboard" ? pathname === link.href : pathname.startsWith(link.href);
            const Icon = link.icon;
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm",
                  active ? "bg-primary text-primary-foreground" : "hover:bg-muted",
                )}
              >
                <Icon className="h-4 w-4" />
                {link.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b bg-background/90 px-4 py-3 backdrop-blur md:px-8">
          <Button variant="outline" size="icon" className="md:hidden" onClick={() => setOpen(true)} aria-label="منو">
            <Menu className="h-4 w-4" />
          </Button>
          <div className="mr-auto flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="تغییر پوسته">
              <Sun className="h-4 w-4 dark:hidden" />
              <Moon className="hidden h-4 w-4 dark:block" />
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                localStorage.removeItem("stt_token");
                window.location.href = "/login";
              }}
            >
              <LogOut className="h-4 w-4" />
              خروج
            </Button>
          </div>
        </header>
        <main className="mx-auto max-w-7xl space-y-6 p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
}
