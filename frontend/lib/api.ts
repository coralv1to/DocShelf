export type DocInfo = {
  doc_id: string;
  title: string;
  filename?: string;
  num_chunks: number;
  num_pages: number;
  uploaded_by?: string | null;
  created_at?: string | null;
};

export type User = {
  id: number;
  username: string;
  full_name: string;
  role: "admin" | "user";
};

/** Một cuộc trò chuyện (phiên chat) của người dùng về một tài liệu */
export type SessionInfo = {
  session_id: string;
  doc_id: string;
  title: string;
  updated_at: string | null;
};

/** Tin nhắn đã lưu trong DB (xem GET /api/sessions/{id}/messages) */
export type StoredMessage = {
  role: "user" | "assistant";
  content: string;
  result?: ChatResult;
};

export type Citation = {
  quote: string;
  chunk_id: string;
  page: number; // trang chứa câu trích (đã được backend xác định chính xác)
  page_start: number;
  page_end: number;
  section: string;
  rects: number[][]; // vùng cần tô: [x0, y0, x1, y1], tọa độ tương đối 0..1 của trang
};

export type RetrievedChunk = {
  chunk_id?: string;
  page_start: number;
  page_end: number;
  header: string;
  score: number;
};

export type ChatResult = {
  answer: string;
  found: boolean;
  citations: Citation[];
  debug: {
    search_query: string;
    route?: "retrieval" | "overview" | "location" | "figure" | "chitchat";
    refusal_kind?: "not_in_doc" | "unsure" | "unverified" | "figure" | "chitchat";
    intent?: string; // loại câu nhắn khi không phải câu hỏi: abuse, greeting, thanks...
    mode?: Mode | "legacy"; // chế độ đã dùng để trả lời
    steps?: Record<string, string>; // bước nào đã chạy / bỏ qua và vì sao
    figure?: string; // hình/bảng câu hỏi nhắc tới, ví dụ "Hình 2.5"
    dropped_quotes?: string[]; // câu trích chép lệch đã bị bỏ (câu trả lời vẫn giữ)
    timings_ms?: Record<string, number>;
    best_score: number;
    gate: number;
    rejected_reason: string | null;
    raw_quotes?: string[]; // câu trích gốc của model (để chẩn đoán khi kiểm chứng thất bại)
    retrieved: RetrievedChunk[];
  };
};

/** Kết quả /api/chat: câu trả lời + cuộc trò chuyện chứa nó (tạo mới nếu là câu đầu tiên) */
export type ChatResponse = ChatResult & { session: SessionInfo };

export type HealthInfo = {
  status: string;
  chat_model: string;
  embed_model: string;
  default_mode: Mode;
};

/** Chế độ trả lời (xem backend/app/options.py) */
export type Mode = "fast" | "balanced" | "accurate";

export type ModeInfo = { id: Mode; label: string; description: string };

/** Mọi người dùng đều đọc được: chế độ mặc định + có được tự chọn chế độ không */
export type PublicSettings = {
  default_mode: Mode;
  allow_user_mode: boolean;
  modes: ModeInfo[];
};

export type SettingValues = {
  default_mode: Mode;
  allow_user_mode: boolean;
  top_k_retrieve: number;
  top_k_context: number;
  min_vector_score: number;
  min_rerank_score: number;
  history_turns: number;
};

export type SettingSpec = {
  type: "mode" | "bool" | "int" | "float";
  label: string;
  help: string;
  min?: number;
  max?: number;
  step?: number;
};

/** Trang Cài đặt của admin */
export type AdminSettings = {
  values: SettingValues;
  defaults: SettingValues;
  spec: Record<keyof SettingValues, SettingSpec>;
  modes: ModeInfo[];
};

/** Giới hạn phải khớp với MAX_UPLOAD_MB trong backend/app/main.py */
export const MAX_UPLOAD_MB = 20;

/** Lỗi có kèm mã HTTP, để nơi gọi phân biệt 401 (chưa đăng nhập), 403 (không có quyền)... */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (res.status === 401 && typeof window !== "undefined" && window.location.pathname !== "/login") {
    // Hết phiên đăng nhập (hoặc chưa đăng nhập): quay về trang đăng nhập.
    // Cố ý tải lại cả trang (không dùng router) để xóa sạch dữ liệu của phiên cũ trong bộ nhớ.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/login";
  }
  if (!res.ok) {
    let message = `Lỗi ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") {
        // Lỗi do code mình chủ động raise HTTPException(...)
        message = data.detail;
      } else if (Array.isArray(data?.detail)) {
        // Lỗi 422 do Pydantic kiểm tra dữ liệu: detail là một mảng
        message = data.detail.map((d: { msg?: string }) => d.msg).join("; ");
      }
    } catch {
      // Response không phải JSON: thường là backend chưa chạy,
      // Next.js không chuyển tiếp được nên trả về trang lỗi 500.
      if (res.status >= 500) message = "Không kết nối được backend. Kiểm tra uvicorn đã chạy ở cổng 8000 chưa.";
    }
    throw new ApiError(message, res.status);
  }
  return res.json() as Promise<T>;
}

export async function uploadDocument(file: File): Promise<DocInfo> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/documents", { method: "POST", body: form });
  return handle<DocInfo>(res);
}

// ---------------------------------------------------------------- đăng nhập
// Token nằm trong cookie httpOnly do backend đặt: trình duyệt tự gửi kèm mọi request,
// code JavaScript không cần (và không thể) đọc nó.

export async function login(username: string, password: string): Promise<User> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  return (await handle<{ user: User }>(res)).user;
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST" });
}

export async function getMe(): Promise<User> {
  return handle<User>(await fetch("/api/auth/me", { cache: "no-store" }));
}

// ---------------------------------------------------------------- kệ tài liệu
export async function listDocuments(): Promise<DocInfo[]> {
  return handle<DocInfo[]>(await fetch("/api/documents", { cache: "no-store" }));
}

export async function deleteDocument(docId: string): Promise<void> {
  await handle(await fetch(`/api/documents/${docId}`, { method: "DELETE" }));
}

// ---------------------------------------------------------------- trò chuyện
/** sessionId = null: bắt đầu cuộc trò chuyện mới, backend tạo và trả về trong `session` */
export async function askQuestion(
  docId: string,
  sessionId: string | null,
  question: string,
  mode?: Mode | null, // null/undefined = chế độ mặc định do admin đặt
): Promise<ChatResponse> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ doc_id: docId, session_id: sessionId, question, mode: mode ?? null }),
  });
  return handle<ChatResponse>(res);
}

// ---------------------------------------------------------------- cài đặt
export async function getPublicSettings(): Promise<PublicSettings> {
  return handle<PublicSettings>(await fetch("/api/settings", { cache: "no-store" }));
}

export async function getAdminSettings(): Promise<AdminSettings> {
  return handle<AdminSettings>(await fetch("/api/admin/settings", { cache: "no-store" }));
}

export async function saveAdminSettings(changes: Partial<SettingValues>): Promise<AdminSettings> {
  const res = await fetch("/api/admin/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  });
  return handle<AdminSettings>(res);
}

export async function resetAdminSettings(): Promise<AdminSettings> {
  return handle<AdminSettings>(await fetch("/api/admin/settings/reset", { method: "POST" }));
}

export async function listSessions(docId: string): Promise<SessionInfo[]> {
  return handle<SessionInfo[]>(await fetch(`/api/sessions?doc_id=${docId}`, { cache: "no-store" }));
}

export async function getSessionMessages(sessionId: string): Promise<StoredMessage[]> {
  const data = await handle<{ messages: StoredMessage[] }>(
    await fetch(`/api/sessions/${sessionId}/messages`, { cache: "no-store" }),
  );
  return data.messages;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await handle(await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" }));
}

export async function getHealth(): Promise<HealthInfo> {
  const res = await fetch("/api/health", { cache: "no-store" });
  return handle<HealthInfo>(res);
}

export function pageImageUrl(docId: string, page: number): string {
  return `/api/documents/${docId}/pages/${page}/image`;
}

