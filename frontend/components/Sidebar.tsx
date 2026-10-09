"use client";

import type { DocInfo, SessionInfo, User } from "@/lib/api";
import HealthBadge from "./HealthBadge";
import { ChatIcon, FileIcon, LogoutIcon, PlusIcon, SettingsIcon, ShelfIcon, TrashIcon } from "./icons";

type Props = {
  user: User;
  docs: DocInfo[];
  /** Màn hình đang mở ở cột giữa */
  view: "shelf" | "chat" | "settings";
  activeDoc: DocInfo | null;
  sessions: SessionInfo[];
  activeSessionId: string | null;
  onOpenShelf: () => void;
  onOpenSettings: () => void;
  /** Tăng lên sau khi admin lưu cài đặt, để ô trạng thái tải lại chế độ mặc định */
  settingsVersion: number;
  onOpenDoc: (doc: DocInfo) => void;
  onNewChat: () => void;
  onOpenSession: (session: SessionInfo) => void;
  onDeleteSession: (session: SessionInfo) => void;
  onLogout: () => void;
  /** true khi panel nguồn đang mở: thu sidebar lại để chừa chỗ, chỉ hiện trên màn hình rất rộng */
  compact?: boolean;
};

const itemBase = "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm";
const itemIdle = "hover:bg-zinc-200/70 dark:hover:bg-zinc-800";
const itemActive = "bg-zinc-200/80 font-medium dark:bg-zinc-800";

export default function Sidebar(props: Props) {
  const { user, docs, view, activeDoc, sessions, activeSessionId, compact = false } = props;
  const initial = (user.full_name || user.username).trim().charAt(0).toUpperCase();

  return (
    <aside
      className={`hidden w-72 shrink-0 flex-col border-r border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900 ${
        compact ? "2xl:flex" : "md:flex"
      }`}
    >
      {/* ------------------------------------------------ Logo */}
      <button onClick={props.onOpenShelf} className="flex items-center gap-2.5 px-4 pt-5 pb-4 text-left">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white">
          <ShelfIcon className="h-4 w-4" />
        </span>
        <span className="text-base font-semibold">DocShelf</span>
      </button>

      <div className="space-y-0.5 px-3">
        <button onClick={props.onOpenShelf} className={`${itemBase} ${view === "shelf" ? itemActive : itemIdle}`}>
          <ShelfIcon className="h-4 w-4" />
          Kệ tài liệu
          <span className="ml-auto text-xs text-zinc-500 tabular-nums">{docs.length}</span>
        </button>
        {user.role === "admin" && (
          <button
            onClick={props.onOpenSettings}
            className={`${itemBase} ${view === "settings" ? itemActive : itemIdle}`}
          >
            <SettingsIcon className="h-4 w-4" />
            Cài đặt
          </button>
        )}
      </div>

      {/* ------------------------------------------------ Danh sách tài liệu + lịch sử của tài liệu đang mở */}
      <nav className="mt-4 min-h-0 flex-1 overflow-y-auto px-3 pb-3">
        <div className="px-3 pb-1.5 text-xs font-medium tracking-wide text-zinc-500 uppercase">Tài liệu</div>
        {docs.length === 0 && <p className="px-3 text-sm text-zinc-500">Chưa có tài liệu.</p>}
        <ul className="space-y-0.5">
          {docs.map((d) => {
            const active = view === "chat" && activeDoc?.doc_id === d.doc_id;
            return (
              <li key={d.doc_id}>
                <button
                  onClick={() => props.onOpenDoc(d)}
                  title={d.title}
                  className={`${itemBase} ${active ? itemActive : itemIdle}`}
                >
                  <FileIcon className="h-4 w-4 shrink-0 text-red-500" />
                  <span className="truncate">{d.title}</span>
                </button>

                {active && (
                  <div className="mt-1 mb-2 ml-5 border-l border-zinc-200 pl-2 dark:border-zinc-700">
                    <button onClick={props.onNewChat} className={`${itemBase} py-1.5 ${activeSessionId ? itemIdle : itemActive}`}>
                      <PlusIcon className="h-3.5 w-3.5" />
                      Cuộc trò chuyện mới
                    </button>
                    {sessions.map((s) => (
                      <div key={s.session_id} className="group relative">
                        <button
                          onClick={() => props.onOpenSession(s)}
                          title={s.title}
                          className={`${itemBase} py-1.5 pr-8 ${s.session_id === activeSessionId ? itemActive : itemIdle}`}
                        >
                          <ChatIcon className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
                          <span className="truncate">{s.title}</span>
                        </button>
                        <button
                          onClick={() => props.onDeleteSession(s)}
                          aria-label="Xóa cuộc trò chuyện"
                          title="Xóa cuộc trò chuyện"
                          className="absolute top-1/2 right-1 hidden -translate-y-1/2 rounded p-1 text-zinc-400 group-hover:block hover:text-red-600"
                        >
                          <TrashIcon className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </nav>

      {/* ------------------------------------------------ Trạng thái + tài khoản */}
      <div className="space-y-3 border-t border-zinc-200 p-3 dark:border-zinc-800">
        <div className="px-1">
          <HealthBadge key={props.settingsVersion} />
        </div>
        <div className="flex items-center gap-2.5 rounded-lg px-1">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-zinc-200 text-sm font-semibold dark:bg-zinc-700">
            {initial}
          </span>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium">{user.full_name || user.username}</div>
            <div className="text-xs text-zinc-500">{user.role === "admin" ? "Quản trị viên" : "Người dùng"}</div>
          </div>
          <button
            onClick={props.onLogout}
            title="Đăng xuất"
            aria-label="Đăng xuất"
            className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-200 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
          >
            <LogoutIcon className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
