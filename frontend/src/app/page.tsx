"use client";

import { useEffect } from "react";

export default function HomePage() {
  useEffect(() => {
    window.location.replace(localStorage.getItem("stt_token") ? "/dashboard" : "/login");
  }, []);
  return <main className="grid min-h-screen place-items-center text-muted-foreground">در حال انتقال...</main>;
}
