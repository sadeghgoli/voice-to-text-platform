export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/backend";

export function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("stt_token");
}

export class ApiError extends Error {}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers, cache: "no-store" });
  if (response.status === 401 && !path.includes("/auth/login")) {
    localStorage.removeItem("stt_token");
    window.location.href = "/login";
    throw new ApiError("نشست منقضی شده است");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data?.error?.message || "خطا در ارتباط با سرور");
  }
  return data as T;
}

export async function downloadResult(id: string, format: string) {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}/api/v1/admin/jobs/${id}/result?format=${format}`, { headers });
  if (!response.ok) throw new ApiError("دانلود نتیجه ممکن نشد");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${id}.${format}`;
  link.click();
  URL.revokeObjectURL(url);
}
