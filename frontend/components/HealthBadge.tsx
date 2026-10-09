"use client";

import { useEffect, useState } from "react";
import { getHealth, type HealthInfo } from "@/lib/api";

export default function HealthBadge() {
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e) => setError(e instanceof Error ? e.message : "Lỗi không xác định"));
  }, []);

  if (error) {
    return (
      <div className="flex items-start gap-2 text-xs text-red-600 dark:text-red-400">
        <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-red-500" />
        <span>{error}</span>
      </div>
    );
  }
  if (!health) {
    return (
      <div className="flex items-center gap-2 text-xs text-zinc-500">
        <span className="h-2 w-2 animate-pulse rounded-full bg-zinc-400" />
        Đang kiểm tra backend...
      </div>
    );
  }

  const modeLabel = { fast: "Nhanh", balanced: "Cân bằng", accurate: "Kỹ" }[health.default_mode] ?? health.default_mode;

  return (
    <div className="space-y-1 text-xs text-zinc-500">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-green-500" />
        <span className="truncate font-medium text-zinc-700 dark:text-zinc-300">{health.chat_model}</span>
      </div>
      <div className="truncate pl-4">{health.embed_model}</div>
      <div className="pl-4">Chế độ mặc định: {modeLabel}</div>
    </div>
  );
}
