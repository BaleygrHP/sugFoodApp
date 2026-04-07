import { createHmac, timingSafeEqual } from "crypto";
import { cookies } from "next/headers";

import { appConfig } from "@/lib/server/config";
import { AppError } from "@/lib/server/errors";
import { query } from "@/lib/db";
import { safeDate } from "@/lib/server/utils";
import type { SessionUser, UserRole } from "@/lib/server/types";

type SessionPayload = {
  userId: string;
  role: UserRole;
  exp: number;
};

function encode(payload: SessionPayload) {
  const raw = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const signature = createHmac("sha256", appConfig.sessionSecret).update(raw).digest("base64url");
  return `${raw}.${signature}`;
}

function decode(token: string): SessionPayload | null {
  const [raw, signature] = token.split(".");
  if (!raw || !signature) {
    return null;
  }

  const expected = createHmac("sha256", appConfig.sessionSecret).update(raw).digest("base64url");
  const signatureBuffer = Buffer.from(signature);
  const expectedBuffer = Buffer.from(expected);

  if (signatureBuffer.length !== expectedBuffer.length || !timingSafeEqual(signatureBuffer, expectedBuffer)) {
    return null;
  }

  try {
    const payload = JSON.parse(Buffer.from(raw, "base64url").toString("utf8")) as SessionPayload;
    if (payload.exp <= Date.now()) {
      return null;
    }
    return payload;
  } catch {
    return null;
  }
}

export async function setSessionCookie(user: SessionUser) {
  const cookieStore = await cookies();
  const token = encode({
    userId: user.id,
    role: user.role,
    exp: Date.now() + 1000 * 60 * 60 * 24 * 30,
  });

  cookieStore.set(appConfig.sessionCookieName, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
}

export async function clearSessionCookie() {
  const cookieStore = await cookies();
  cookieStore.delete(appConfig.sessionCookieName);
}

export async function getSessionUser(): Promise<SessionUser | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(appConfig.sessionCookieName)?.value;
  if (!token) {
    return null;
  }

  const payload = decode(token);
  if (!payload) {
    return null;
  }

  const result = await query<{
    id: string;
    role: UserRole;
    account_status: string;
    display_name: string;
    email: string | null;
  }>(
    `
      SELECT id, role, account_status, display_name, email
      FROM users
      WHERE id = $1
    `,
    [payload.userId],
  );

  if (result.rows.length === 0) {
    return null;
  }

  const row = result.rows[0];
  return {
    id: row.id,
    role: row.role,
    accountStatus: row.account_status,
    displayName: row.display_name,
    email: row.email,
  };
}

export async function requireSessionUser() {
  const user = await getSessionUser();
  if (!user) {
    throw new AppError("Authentication required", 401, "unauthorized");
  }
  return user;
}

export async function requireRole(roles: UserRole[]) {
  const user = await requireSessionUser();
  if (!roles.includes(user.role)) {
    throw new AppError("Forbidden", 403, "forbidden");
  }
  return user;
}

export function buildGuestSessionResponse(user: SessionUser) {
  return {
    user,
    session: {
      expiresAt: safeDate(Date.now() + 1000 * 60 * 60 * 24 * 30),
    },
  };
}
