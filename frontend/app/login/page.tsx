"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ShelfIcon } from "@/components/icons";
import { getMe, login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Đã đăng nhập rồi (cookie còn hạn) thì vào thẳng kệ tài liệu
  useEffect(() => {
    getMe()
      .then(() => router.replace("/"))
      .catch(() => {}); // 401 = chưa đăng nhập, ở lại trang này
  }, [router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    setError(null);
    setLoading(true);
    try {
      await login(username.trim(), password);
      // Tải lại toàn trang để bắt đầu sạch (không giữ trạng thái của tài khoản trước, nếu có)
      window.location.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lỗi không xác định");
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-dvh items-center justify-center bg-zinc-50 px-4 dark:bg-zinc-950">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-sm">
            <ShelfIcon className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">DocShelf</h1>
          <p className="mt-1 text-sm text-zinc-500">Kệ tài liệu hỏi đáp bằng AI, có trích dẫn nguồn</p>
        </div>

        <form
          onSubmit={submit}
          className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
        >
          <div>
            <label htmlFor="username" className="mb-1.5 block text-sm font-medium">
              Tên đăng nhập
            </label>
            <input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              autoFocus
              required
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-950"
            />
          </div>
          <div>
            <label htmlFor="password" className="mb-1.5 block text-sm font-medium">
              Mật khẩu
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-950"
            />
          </div>

          {error && (
            <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !username.trim() || !password}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-zinc-900 py-2.5 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-40 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            {loading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white dark:border-zinc-400 dark:border-t-zinc-900" />}
            {loading ? "Đang đăng nhập..." : "Đăng nhập"}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-zinc-500">
          Chưa có tài khoản? Liên hệ quản trị viên để được cấp.
        </p>
      </div>
    </main>
  );
}
