"use client";

import { useEffect, useState } from "react";
import {
  getAdminSettings,
  resetAdminSettings,
  saveAdminSettings,
  type AdminSettings,
  type Mode,
  type SettingValues,
} from "@/lib/api";

// Thời gian ước tính trên laptop GPU 6GB (qwen3.5:4b, reranker chạy CPU) — để admin dễ hình dung
const MODE_TIME: Record<Mode, string> = {
  fast: "thường 3–8 giây",
  balanced: "thường 5–15 giây · câu hỏi vị trí 1–3 giây",
  accurate: "thường 15–25 giây",
};

// Các tham số số, theo thứ tự hiển thị trong mục "Nâng cao"
const TUNING_KEYS = ["top_k_retrieve", "top_k_context", "min_rerank_score", "min_vector_score", "history_turns"] as const;

type Props = {
  /** Gọi sau khi lưu, để trang cha tải lại chế độ mặc định (ô chọn chế độ khi chat, trạng thái ở sidebar) */
  onSaved: () => void;
};

export default function SettingsPanel({ onSaved }: Props) {
  const [data, setData] = useState<AdminSettings | null>(null);
  const [form, setForm] = useState<SettingValues | null>(null); // bản đang sửa, chưa lưu
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    getAdminSettings()
      .then((d) => {
        setData(d);
        setForm(d.values);
      })
      .catch((e) => setMessage({ ok: false, text: e instanceof Error ? e.message : "Không tải được cài đặt" }));
  }, []);

  if (!data || !form) {
    return (
      <div className="flex flex-1 items-center justify-center">
        {message ? (
          <p className="text-sm text-red-600">{message.text}</p>
        ) : (
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-300 border-t-blue-600" />
        )}
      </div>
    );
  }

  const dirty = JSON.stringify(form) !== JSON.stringify(data.values);

  function set<K extends keyof SettingValues>(key: K, value: SettingValues[K]) {
    setForm((f) => (f ? { ...f, [key]: value } : f));
    setMessage(null);
  }

  async function run(action: () => Promise<AdminSettings>, okText: string) {
    setSaving(true);
    setMessage(null);
    try {
      const d = await action();
      setData(d);
      setForm(d.values);
      setMessage({ ok: true, text: okText });
      onSaved();
    } catch (e) {
      setMessage({ ok: false, text: e instanceof Error ? e.message : "Không lưu được" });
    } finally {
      setSaving(false);
    }
  }

  function save() {
    if (!form || !data) return;
    // Chỉ gửi những giá trị đã đổi
    const changes = Object.fromEntries(
      Object.entries(form).filter(([k, v]) => data.values[k as keyof SettingValues] !== v),
    ) as Partial<SettingValues>;
    run(() => saveAdminSettings(changes), "Đã lưu. Có hiệu lực từ câu hỏi tiếp theo.");
  }

  function reset() {
    if (!window.confirm("Khôi phục toàn bộ cài đặt về mặc định (theo file .env)?")) return;
    run(resetAdminSettings, "Đã khôi phục mặc định.");
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-10">
        <header className="mb-8">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Cài đặt</h1>
          <p className="mt-1 text-zinc-500">
            Cân bằng giữa tốc độ và độ chính xác của câu trả lời. Thay đổi có hiệu lực ngay, không cần khởi động lại.
          </p>
        </header>

        {/* ------------------------------------------------ Chế độ mặc định */}
        <section className="mb-8">
          <h2 className="mb-1 font-medium">{data.spec.default_mode.label}</h2>
          <p className="mb-3 text-sm text-zinc-500">{data.spec.default_mode.help}</p>
          <div className="grid gap-3 sm:grid-cols-3" role="radiogroup">
            {data.modes.map((m) => {
              const active = form.default_mode === m.id;
              return (
                <button
                  key={m.id}
                  role="radio"
                  aria-checked={active}
                  onClick={() => set("default_mode", m.id)}
                  className={`rounded-xl border p-4 text-left transition-colors ${
                    active
                      ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500 dark:bg-blue-950/30"
                      : "border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-900"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{m.label}</span>
                    <span
                      className={`h-4 w-4 rounded-full border-2 ${
                        active ? "border-blue-600 bg-blue-600 ring-2 ring-white ring-inset dark:ring-zinc-950" : "border-zinc-300"
                      }`}
                    />
                  </div>
                  <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{m.description}</p>
                  <p className="mt-2 text-xs text-zinc-500">{MODE_TIME[m.id]}</p>
                </button>
              );
            })}
          </div>
        </section>

        {/* ------------------------------------------------ Cho người dùng chọn */}
        <section className="mb-8 flex items-start justify-between gap-4 rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
          <div>
            <h2 className="font-medium">{data.spec.allow_user_mode.label}</h2>
            <p className="mt-1 text-sm text-zinc-500">{data.spec.allow_user_mode.help}</p>
          </div>
          <button
            role="switch"
            aria-checked={form.allow_user_mode}
            aria-label={data.spec.allow_user_mode.label}
            onClick={() => set("allow_user_mode", !form.allow_user_mode)}
            className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${
              form.allow_user_mode ? "bg-blue-600" : "bg-zinc-300 dark:bg-zinc-700"
            }`}
          >
            <span
              className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                form.allow_user_mode ? "translate-x-5" : ""
              }`}
            />
          </button>
        </section>

        {/* ------------------------------------------------ Nâng cao */}
        <details className="mb-8 rounded-xl border border-zinc-200 dark:border-zinc-800">
          <summary className="cursor-pointer px-4 py-3 font-medium">Nâng cao</summary>
          <div className="space-y-5 border-t border-zinc-200 px-4 py-4 dark:border-zinc-800">
            <p className="text-sm text-zinc-500">
              Chỉ chỉnh khi đã hiểu ý nghĩa. Sau khi đổi ngưỡng, nên chạy lại benchmark để kiểm tra độ chính xác.
            </p>
            {TUNING_KEYS.map((key) => {
              const spec = data.spec[key];
              const changed = form[key] !== data.defaults[key];
              return (
                <div key={key} className="grid gap-2 sm:grid-cols-[1fr_8rem] sm:items-start">
                  <label htmlFor={key}>
                    <span className="text-sm font-medium">{spec.label}</span>
                    <span className="mt-0.5 block text-xs text-zinc-500">
                      {spec.help} Mặc định: {String(data.defaults[key])}
                      {spec.min !== undefined && ` · từ ${spec.min} đến ${spec.max}`}.
                    </span>
                  </label>
                  <input
                    id={key}
                    type="number"
                    min={spec.min}
                    max={spec.max}
                    step={spec.step ?? 1}
                    value={form[key]}
                    onChange={(e) => set(key, Number(e.target.value))}
                    className={`w-full rounded-lg border bg-white px-3 py-1.5 text-sm tabular-nums outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:bg-zinc-950 ${
                      changed ? "border-amber-400" : "border-zinc-300 dark:border-zinc-700"
                    }`}
                  />
                </div>
              );
            })}
          </div>
        </details>

        {/* ------------------------------------------------ Lưu */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={save}
            disabled={!dirty || saving}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-40 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            {saving ? "Đang lưu..." : "Lưu thay đổi"}
          </button>
          {dirty && (
            <button
              onClick={() => setForm(data.values)}
              disabled={saving}
              className="rounded-lg px-3 py-2 text-sm text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
            >
              Hủy
            </button>
          )}
          <button
            onClick={reset}
            disabled={saving}
            className="ml-auto rounded-lg px-3 py-2 text-sm text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
          >
            Khôi phục mặc định
          </button>
        </div>
        {message && (
          <p role="status" className={`mt-3 text-sm ${message.ok ? "text-green-700 dark:text-green-400" : "text-red-600"}`}>
            {message.text}
          </p>
        )}
      </div>
    </div>
  );
}
