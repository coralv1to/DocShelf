"use client";

import { useEffect, useState } from "react";
import ChatPanel from "@/components/ChatPanel";
import { PlusIcon, SettingsIcon, ShelfIcon } from "@/components/icons";
import SettingsPanel from "@/components/SettingsPanel";
import ShelfPanel from "@/components/ShelfPanel";
import Sidebar from "@/components/Sidebar";
import SourcePanel from "@/components/SourcePanel";
import {
  deleteDocument,
  deleteSession,
  getMe,
  getPublicSettings,
  listDocuments,
  listSessions,
  logout,
  type Citation,
  type DocInfo,
  type PublicSettings,
  type SessionInfo,
  type User,
} from "@/lib/api";

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [docs, setDocs] = useState<DocInfo[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);

  const [doc, setDoc] = useState<DocInfo | null>(null);          // tài liệu đang mở (null = xem kệ)
  const [sessions, setSessions] = useState<SessionInfo[]>([]);   // lịch sử trò chuyện của tài liệu đang mở
  const [sessionId, setSessionId] = useState<string | null>(null); // cuộc trò chuyện đang mở (null = mới)
  const [chatKey, setChatKey] = useState(0);                     // tăng lên để tạo ChatPanel mới
  const [citation, setCitation] = useState<Citation | null>(null); // trích dẫn đang xem trong panel
  const [settingsOpen, setSettingsOpen] = useState(false);       // admin đang mở trang Cài đặt
  const [settings, setSettings] = useState<PublicSettings | null>(null); // chế độ trả lời mặc định...
  const [settingsVersion, setSettingsVersion] = useState(0);     // tăng sau mỗi lần admin lưu cài đặt

  // Lần đầu vào trang: biết mình là ai + tải kệ tài liệu. Chưa đăng nhập -> api.ts tự chuyển sang /login.
  useEffect(() => {
    getMe()
      .then((me) => {
        setUser(me);
        getPublicSettings()
          .then(setSettings)
          .catch(() => {});
        return listDocuments().then(setDocs);
      })
      .catch(() => {})
      .finally(() => setDocsLoading(false));
  }, []);

  function startChat(nextSessionId: string | null) {
    setSessionId(nextSessionId);
    setChatKey((k) => k + 1);
    setCitation(null); // trích dẫn cũ không thuộc cuộc trò chuyện mới
  }

  function openDoc(d: DocInfo) {
    setSettingsOpen(false);
    setDoc(d);
    setSessions([]);
    startChat(null);
    listSessions(d.doc_id)
      .then(setSessions)
      .catch(() => {});
  }

  function openShelf() {
    setSettingsOpen(false);
    setDoc(null);
    setCitation(null);
  }

  function openSettings() {
    setSettingsOpen(true);
    setCitation(null);
  }

  // Admin vừa lưu cài đặt: tải lại chế độ mặc định cho ô chọn chế độ khi chat + trạng thái ở sidebar
  function onSettingsSaved() {
    setSettingsVersion((v) => v + 1);
    getPublicSettings()
      .then(setSettings)
      .catch(() => {});
  }

  // Sau mỗi câu trả lời: cuộc trò chuyện được tạo/cập nhật -> đưa lên đầu danh sách lịch sử
  function onSessionUpdated(s: SessionInfo) {
    setSessionId(s.session_id); // không đổi chatKey: giữ nguyên ChatPanel đang hiển thị
    setSessions((prev) => [s, ...prev.filter((x) => x.session_id !== s.session_id)]);
  }

  async function removeSession(s: SessionInfo) {
    if (!window.confirm(`Xóa cuộc trò chuyện “${s.title}”?`)) return;
    try {
      await deleteSession(s.session_id);
      setSessions((prev) => prev.filter((x) => x.session_id !== s.session_id));
      if (s.session_id === sessionId) startChat(null);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "Không xóa được");
    }
  }

  function onUploaded(d: DocInfo) {
    setDocs((prev) => [d, ...prev]);
    openDoc(d);
  }

  async function removeDoc(d: DocInfo) {
    if (!window.confirm(`Xóa “${d.title}” khỏi kệ?\nMọi cuộc trò chuyện về tài liệu này cũng bị xóa.`)) return;
    try {
      await deleteDocument(d.doc_id);
      setDocs((prev) => prev.filter((x) => x.doc_id !== d.doc_id));
      if (doc?.doc_id === d.doc_id) openShelf();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "Không xóa được");
    }
  }

  async function signOut() {
    await logout();
    // Tải lại toàn bộ trang (không dùng router): Next.js giữ trạng thái trang khi chuyển route,
    // nếu không xóa sạch thì người đăng nhập sau sẽ thấy lịch sử của người trước trên giao diện.
    window.location.replace("/login");
  }

  // Đang kiểm tra đăng nhập
  if (!user) {
    return (
      <div className="flex h-dvh items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-300 border-t-blue-600" />
      </div>
    );
  }

  const view = settingsOpen ? "settings" : doc ? "chat" : "shelf";
  const panelOpen = view === "chat" && citation !== null;

  return (
    <div className="flex h-dvh overflow-hidden bg-white text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      <Sidebar
        user={user}
        docs={docs}
        view={view}
        activeDoc={doc}
        sessions={sessions}
        activeSessionId={sessionId}
        onOpenShelf={openShelf}
        onOpenSettings={openSettings}
        settingsVersion={settingsVersion}
        onOpenDoc={openDoc}
        onNewChat={() => startChat(null)}
        onOpenSession={(s) => startChat(s.session_id)}
        onDeleteSession={removeSession}
        onLogout={signOut}
        compact={panelOpen}
      />

      {/* Cột giữa. min-w-0 cho phép co lại, không đẩy panel ra ngoài màn hình */}
      <main className="flex min-w-0 flex-1 flex-col">
        {/* Thanh trên cùng: hiện khi sidebar bị ẩn (màn hình nhỏ, hoặc lúc panel nguồn đang mở) */}
        <header
          className={`flex items-center gap-2 border-b border-zinc-200 px-3 py-2.5 dark:border-zinc-800 ${
            panelOpen ? "2xl:hidden" : "md:hidden"
          }`}
        >
          <button
            onClick={openShelf}
            aria-label="Kệ tài liệu"
            title="Kệ tài liệu"
            className="rounded-lg p-1.5 hover:bg-zinc-100 dark:hover:bg-zinc-800"
          >
            <ShelfIcon className="h-5 w-5" />
          </button>
          <span className="min-w-0 flex-1 truncate font-semibold">
            {view === "settings" ? "Cài đặt" : doc ? doc.title : "DocShelf"}
          </span>
          {user.role === "admin" && view !== "settings" && (
            <button
              onClick={openSettings}
              aria-label="Cài đặt"
              title="Cài đặt"
              className="rounded-lg p-1.5 hover:bg-zinc-100 dark:hover:bg-zinc-800"
            >
              <SettingsIcon className="h-5 w-5" />
            </button>
          )}
          {view === "chat" && (
            <button
              onClick={() => startChat(null)}
              aria-label="Cuộc trò chuyện mới"
              title="Cuộc trò chuyện mới"
              className="rounded-lg p-1.5 hover:bg-zinc-100 dark:hover:bg-zinc-800"
            >
              <PlusIcon className="h-5 w-5" />
            </button>
          )}
        </header>

        {view === "settings" ? (
          <SettingsPanel onSaved={onSettingsSaved} />
        ) : doc ? (
          <ChatPanel
            key={chatKey}
            doc={doc}
            sessionId={sessionId}
            settings={settings}
            onSessionUpdated={onSessionUpdated}
            activeCitation={citation}
            onOpenCitation={setCitation}
          />
        ) : (
          <ShelfPanel
            user={user}
            docs={docs}
            loading={docsLoading}
            onOpen={openDoc}
            onUploaded={onUploaded}
            onDelete={removeDoc}
          />
        )}
      </main>

      {/* Cột phải: trang nguồn. Màn hình rộng: cột 45%; màn hình hẹp: phủ toàn màn hình */}
      {view === "chat" && doc && citation && (
        <div className="fixed inset-0 z-20 lg:static lg:z-auto lg:w-[45%] lg:shrink-0">
          <SourcePanel
            key={`${citation.chunk_id}-${citation.quote}`}
            doc={doc}
            citation={citation}
            onClose={() => setCitation(null)}
          />
        </div>
      )}
    </div>
  );
}
