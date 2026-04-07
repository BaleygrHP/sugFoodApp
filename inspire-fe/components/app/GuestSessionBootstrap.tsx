"use client";

import { useEffect } from "react";

import { ensureGuestSession } from "@/lib/api";

export default function GuestSessionBootstrap() {
  useEffect(() => {
    ensureGuestSession().catch((error) => {
      console.error("Failed to bootstrap guest session", error);
    });
  }, []);

  return null;
}
