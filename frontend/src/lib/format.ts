export function formatNumber(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("fa-IR").format(value);
}

export function formatSeconds(seconds: number | null | undefined) {
  if (seconds == null) return "—";
  const total = Math.round(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const remain = total % 60;
  if (hours > 0) return `${formatNumber(hours)} ساعت و ${formatNumber(minutes)} دقیقه`;
  if (minutes > 0) return `${formatNumber(minutes)} دقیقه و ${formatNumber(remain)} ثانیه`;
  return `${formatNumber(remain)} ثانیه`;
}

export function formatDate(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("fa-IR");
}

export const STATUS_LABELS: Record<string, string> = {
  queued: "در صف",
  processing: "در حال پردازش",
  completed: "تمام‌شده",
  failed: "ناموفق",
  cancelled: "لغوشده",
  active: "فعال",
  disabled: "غیرفعال",
  revoked: "لغوشده",
  inactive: "غیرفعال",
};
