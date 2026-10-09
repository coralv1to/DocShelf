"use client";

import { useEffect, useRef, useState } from "react";
import {
  askQuestion,
  getSessionMessages,
  type ChatResult,
  type Citation,
  type DocInfo,
  type Mode,
  type PublicSettings,
  type SessionInfo,
} from "@/lib/api";
import { ArrowUpIcon, CheckIcon, CopyIcon, SparkIcon } from "./icons";

type Message = {
  role: "user" | "assistant";
  content: string;
  result?: ChatResult;
  isError?: boolean;
};

const SUGGESTIONS = [
  "Tài liệu này nói về chủ đề gì?",
  "Tài liệu gồm những phần chính nào?",
  "Tóm tắt nội dung chính của tài liệu",
];

const MODE_LABEL: Record<string, string> = { fast: "Nhanh", balanced: "Cân bằng", accurate: "Kỹ" };

// Loại từ chối (backend trả về trong debug.refusal_kind) -> nhãn dễ hiểu
const REFUSAL_LABEL: Record<string, string> = {
  not_in_doc: "Không có trong tài liệu",
  unsure: "Chưa trả lời được",
  unverified: "Chưa kiểm chứng được",
  figure: "Nằm trong hình",
};

const MODE_STORAGE_KEY = "docshelf.mode";

/** Chế độ người dùng chọn lần trước (lưu trong trình duyệt). Có thể không đọc được: chế độ riêng tư... */
function readSavedMode(): Mode | null {
  try {
    const v = window.localStorage.getItem(MODE_STORAGE_KEY);
    return v === "fast" || v === "balanced" || v === "accurate" ? v : null;
  } catch {
    return null;
  }
}

function saveMode(mode: Mode | null) {
  try {
    if (mode) window.localStorage.setItem(MODE_STORAGE_KEY, mode);
    else window.localStorage.removeItem(MODE_STORAGE_KEY);
  } catch {
    // không lưu được thì thôi, chỉ là tiện ích
  }
}

type Props = {
  doc: DocInfo;
  /** Chế độ trả lời: mặc định + người dùng có được tự chọn không (null khi chưa tải xong) */
  settings: PublicSettings | null;
  /** null = cuộc trò chuyện mới (backend tạo khi gửi câu hỏi đầu tiên) */
  sessionId: string | null;
  /** Gọi sau mỗi câu trả lời, để trang cha cập nhật danh sách lịch sử ở sidebar */
  onSessionUpdated: (session: SessionInfo) => void;
  activeCitation: Citation | null;
  onOpenCitation: (citation: Citation) => void;
};

// Lưu ý: component cha đặt `key` khi đổi tài liệu / mở cuộc trò chuyện khác,
// nên mỗi cuộc trò chuyện là một ChatPanel mới, trạng thái không lẫn sang nhau.
export default function ChatPanel({ doc, settings, sessionId, onSessionUpdated, activeCitation, onOpenCitation }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(sessionId !== null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // Mã cuộc trò chuyện hiện tại: null cho tới khi backend tạo ở câu hỏi đầu tiên
  const sessionRef = useRef<string | null>(sessionId);
  // Chế độ người dùng tự chọn; null = theo mặc định của admin
  const [chosenMode, setChosenMode] = useState<Mode | null>(() => (typeof window === "undefined" ? null : readSavedMode()));
  const canChoose = settings?.allow_user_mode ?? false;
  const mode: Mode | null = canChoose ? (chosenMode ?? settings?.default_mode ?? null) : null;

  function chooseMode(m: Mode) {
    const next = m === settings?.default_mode ? null : m; // chọn đúng mặc định = bỏ lựa chọn riêng
    setChosenMode(next);
    saveMode(next);
  }

  // Mở lại cuộc trò chuyện cũ: nạp các tin nhắn đã lưu trong database
  useEffect(() => {
    const id = sessionRef.current;
    if (id === null) return;
    let cancelled = false; // tránh cập nhật state nếu người dùng đã chuyển sang cuộc khác
    getSessionMessages(id)
      .then((stored) => {
        if (!cancelled) setMessages(stored.map((m) => ({ role: m.role, content: m.content, result: m.result })));
      })
      .catch((e) => !cancelled && setHistoryError(e instanceof Error ? e.message : "Lỗi không xác định"))
      .finally(() => !cancelled && setHistoryLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  // Tự cuộn xuống tin mới nhất
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Ô nhập tự giãn chiều cao theo nội dung, tối đa 200px
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [input]);

  async function send(text?: string) {
    const question = (text ?? input).trim();
    if (!question || loading || historyLoading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);
    try {
      const { session, ...result } = await askQuestion(doc.doc_id, sessionRef.current, question, canChoose ? mode : null);
      sessionRef.current = session.session_id;
      setMessages((prev) => [...prev, { role: "assistant", content: result.answer, result }]);
      onSessionUpdated(session);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Lỗi không xác định";
      setMessages((prev) => [...prev, { role: "assistant", content: msg, isError: true }]);
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  }

  const empty = messages.length === 0 && !historyLoading && !historyError;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* ------------------------------------------------ Danh sách tin nhắn */}
      <div className="flex-1 overflow-y-auto">
        {empty ? (
          <div className="mx-auto flex h-full max-w-3xl flex-col items-center justify-center px-4 text-center">
            <h2 className="mb-2 text-2xl font-semibold tracking-tight">Bạn muốn hỏi gì về tài liệu này?</h2>
            <p className="mb-8 max-w-md truncate text-zinc-500" title={doc.title}>
              {doc.title}
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full border border-zinc-200 px-4 py-2 text-sm text-zinc-700 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : historyLoading ? (
          <div className="flex h-full items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-300 border-t-blue-600" />
          </div>
        ) : historyError ? (
          <div className="mx-auto max-w-3xl px-4 py-8 text-sm text-red-600">⚠️ {historyError}</div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-8 px-4 py-8">
            {messages.map((m, i) =>
              m.role === "user" ? (
                <UserMessage key={i} content={m.content} />
              ) : (
                <AssistantMessage key={i} message={m} activeCitation={activeCitation} onOpenCitation={onOpenCitation} />
              ),
            )}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* ------------------------------------------------ Ô nhập (composer) */}
      <div className="mx-auto w-full max-w-3xl px-4 pb-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
          className="flex items-end gap-2 rounded-3xl border border-zinc-200 bg-white p-2 pl-4 shadow-sm focus-within:border-zinc-400 dark:border-zinc-700 dark:bg-zinc-900 dark:focus-within:border-zinc-500"
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              // Enter = gửi, Shift+Enter = xuống dòng, bỏ qua khi bộ gõ tiếng Việt đang ghép dấu
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                send();
              }
            }}
            rows={1}
            maxLength={2000}
            placeholder="Hỏi về nội dung tài liệu..."
            className="max-h-[200px] flex-1 resize-none bg-transparent py-2 leading-6 outline-none placeholder:text-zinc-400"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            aria-label="Gửi"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-zinc-900 text-white disabled:opacity-25 dark:bg-white dark:text-zinc-900"
          >
            <ArrowUpIcon className="h-4 w-4" />
          </button>
        </form>
        <div className="mt-2 flex flex-wrap items-center justify-center gap-x-3 gap-y-1.5 text-xs text-zinc-500">
          {canChoose && settings && mode && (
            <div role="radiogroup" aria-label="Chế độ trả lời" className="flex rounded-full bg-zinc-100 p-0.5 dark:bg-zinc-800">
              {settings.modes.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  role="radio"
                  aria-checked={mode === m.id}
                  title={m.description}
                  onClick={() => chooseMode(m.id)}
                  className={`rounded-full px-2.5 py-0.5 transition-colors ${
                    mode === m.id
                      ? "bg-white font-medium text-zinc-900 shadow-sm dark:bg-zinc-950 dark:text-zinc-100"
                      : "hover:text-zinc-900 dark:hover:text-zinc-100"
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>
          )}
          <span>Câu trả lời chỉ dựa trên tài liệu đã tải lên. Hãy đối chiếu với trích dẫn.</span>
        </div>
      </div>
    </div>
  );
}

// ==================================================================== Các mảnh giao diện nhỏ

function UserMessage({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-3xl bg-zinc-100 px-5 py-2.5 whitespace-pre-wrap dark:bg-zinc-800">
        {content}
      </div>
    </div>
  );
}

function Avatar() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white">
      <SparkIcon className="h-4 w-4" />
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-4">
      <Avatar />
      <div className="flex items-center gap-1 pt-2">
        {[0, 150, 300].map((delay) => (
          <span
            key={delay}
            className="h-2 w-2 animate-bounce rounded-full bg-zinc-400"
            style={{ animationDelay: `${delay}ms` }}
          />
        ))}
        <span className="ml-2 text-sm text-zinc-500">Đang tìm trong tài liệu...</span>
      </div>
    </div>
  );
}

type AssistantProps = {
  message: Message;
  activeCitation: Citation | null;
  onOpenCitation: (citation: Citation) => void;
};

function AssistantMessage({ message: m, activeCitation, onOpenCitation }: AssistantProps) {
  // Câu chào/cảm ơn/chửi... (không phải câu hỏi): hiện như câu trả lời thường, không nhãn, không "Chi tiết"
  const chitchat = m.result?.debug.route === "chitchat";
  const refused = m.result && !m.result.found && !chitchat;

  return (
    <div className="flex gap-4">
      <Avatar />
      <div className="min-w-0 flex-1 pt-1">
        {m.isError ? (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
            ⚠️ {m.content}
          </div>
        ) : refused ? (
          <div>
            <span className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
              {REFUSAL_LABEL[m.result?.debug.refusal_kind ?? ""] ?? "Không có trong tài liệu"}
            </span>
            <div className="leading-7 whitespace-pre-wrap">{m.content}</div>
          </div>
        ) : (
          <div className="leading-7 whitespace-pre-wrap">{m.content}</div>
        )}

        {m.result?.debug.dropped_quotes && m.result.debug.dropped_quotes.length > 0 && (
          <p className="mt-2 text-xs text-zinc-500">
            Đã bỏ {m.result.debug.dropped_quotes.length} trích dẫn không khớp nguyên văn với tài liệu.
          </p>
        )}

        {m.result && m.result.citations.length > 0 && (
          <Sources citations={m.result.citations} active={activeCitation} onOpen={onOpenCitation} />
        )}

        {!m.isError && (
          <div className="mt-2 flex items-center gap-1 text-zinc-500">
            <CopyButton text={m.content} />
            {m.result && !chitchat && <DebugInfo result={m.result} />}
          </div>
        )}
      </div>
    </div>
  );
}

type SourcesProps = {
  citations: Citation[];
  active: Citation | null;
  onOpen: (citation: Citation) => void;
};

function Sources({ citations, active, onOpen }: SourcesProps) {
  return (
    <div className="mt-4">
      <div className="mb-2 text-xs font-medium tracking-wide text-zinc-500 uppercase">Nguồn</div>
      <div className="grid gap-2 sm:grid-cols-2">
        {citations.map((c, j) => {
          // So sánh tham chiếu: đúng object trích dẫn đang mở trong panel
          const isActive = active === c;
          return (
            <button
              key={j}
              type="button"
              onClick={() => onOpen(c)}
              title="Xem trong tài liệu gốc"
              className={`rounded-xl border px-3 py-2 text-left text-sm transition-colors ${
                isActive
                  ? "border-yellow-400 bg-yellow-50 dark:border-yellow-600 dark:bg-yellow-950/40"
                  : "border-zinc-200 bg-zinc-50 hover:border-zinc-300 hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:bg-zinc-800"
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                    isActive ? "bg-yellow-400 text-zinc-900" : "bg-zinc-200 dark:bg-zinc-700"
                  }`}
                >
                  {j + 1}
                </span>
                <span className="truncate">
                  <span className="font-medium">Trang {c.page}</span>
                  {c.section && <span className="text-zinc-500"> · {c.section.split(" > ").pop()}</span>}
                </span>
              </div>
              <p className="mt-1.5 line-clamp-2 text-xs text-zinc-600 italic dark:text-zinc-400">“{c.quote}”</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard chỉ chạy ở localhost/https; bỏ qua nếu không được phép
    }
  }

  return (
    <button
      onClick={copy}
      title="Sao chép"
      className="rounded-md p-1.5 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
    >
      {copied ? <CheckIcon className="h-4 w-4" /> : <CopyIcon className="h-4 w-4" />}
    </button>
  );
}

function DebugInfo({ result }: { result: ChatResult }) {
  const d = result.debug;
  // Tổng thời gian xử lý ở backend = cộng các bước trong timings_ms
  const totalMs = d.timings_ms ? Object.values(d.timings_ms).reduce((a, b) => a + b, 0) : null;
  return (
    <details className="text-xs">
      <summary className="cursor-pointer list-none rounded-md px-2 py-1.5 hover:bg-zinc-100 dark:hover:bg-zinc-800">
        Chi tiết
        {d.mode && d.mode !== "legacy" && ` · ${MODE_LABEL[d.mode] ?? d.mode}`} · điểm {d.best_score} / ngưỡng {d.gate}
        {d.route === "overview" && " · trả lời từ dàn ý"}
        {d.route === "location" && " · tra vị trí"}
        {d.route === "figure" && ` · tra ${d.figure ?? "hình"}`}
        {d.rejected_reason && ` · ${d.rejected_reason}`}
        {totalMs !== null && ` · ${(totalMs / 1000).toFixed(1)}s`}
      </summary>
      <pre className="mt-1 max-w-full overflow-x-auto rounded-lg bg-zinc-100 p-3 whitespace-pre-wrap dark:bg-zinc-900">
        {JSON.stringify(d, null, 2)}
      </pre>
    </details>
  );
}
