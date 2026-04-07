import { randomUUID } from "crypto";

export function normalizeText(value: string | null | undefined): string {
  return (value || "")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}

export function splitPreferenceText(value: string | null | undefined): string[] {
  return (value || "")
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function numberOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function jsonParse<T>(value: unknown, fallback: T): T {
  if (value === null || value === undefined) {
    return fallback;
  }

  if (typeof value === "object") {
    return value as T;
  }

  if (typeof value !== "string") {
    return fallback;
  }

  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

export function clamp(value: number, min = 0, max = 1) {
  return Math.min(max, Math.max(min, value));
}

export function safeDate(date: Date | string | number | null | undefined): string {
  if (!date) {
    return new Date().toISOString();
  }

  return new Date(date).toISOString();
}

export function buildInviteToken() {
  return randomUUID().replace(/-/g, "");
}

export function buildDisplayName(prefix: string, id: string) {
  return `${prefix}-${id.slice(0, 8)}`;
}
