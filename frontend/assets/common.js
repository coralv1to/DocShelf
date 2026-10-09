/* =====================================================================
   Dùng chung cho index.html và login.html: icon, hàm tạo phần tử, gọi API.
   FastAPI phục vụ giao diện CÙNG địa chỉ với API -> gọi thẳng "/api/...",
   cookie đăng nhập được trình duyệt tự gửi kèm, không cần CORS.
   ===================================================================== */

// ---------------------------------------------------------------- Icon SVG (viết tay, nét 2px, theo màu chữ)
const ICONS = {
  plus: '<path d="M12 5v14M5 12h14"/>',
  arrowUp: '<path d="M12 19V5M5 12l7-7 7 7"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6.3 6.3l2.5 2.5M15.2 15.2l2.5 2.5M6.3 17.7l2.5-2.5M15.2 8.8l2.5-2.5"/>',
  chevronLeft: '<path d="m15 18-6-6 6-6"/>',
  chevronRight: '<path d="m9 18 6-6-6-6"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  shelf: '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/><path d="M8 7h8M8 11h6"/>',
  settings: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
  chat: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  trash: '<path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6M10 11v6M14 11v6"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
};

function iconSvg(name) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]}</svg>`;
}

/** Điền icon vào mọi phần tử có data-icon="tên" trong HTML tĩnh */
function fillIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach((n) => (n.innerHTML = iconSvg(n.dataset.icon)));
}

const $ = (id) => document.getElementById(id);

/**
 * Tạo phần tử DOM gọn: el("div", { class: "x", text: "nội dung" }, con1, con2)
 * - `text` gán textContent: nội dung lấy từ tài liệu / người dùng KHÔNG BAO GIỜ bị hiểu là HTML
 *   (chống chèn mã độc). Không có tùy chọn gán innerHTML tùy ý.
 * - `icon` chỉ nhận tên icon cố định ở ICONS.
 * - Con là null/undefined/false thì bỏ qua -> viết điều kiện gọn: cond && el(...)
 *   Lưu ý: điều kiện phải là true/false, đừng viết `list.length && el(...)` (số 0 sẽ bị in ra).
 */
function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k === "icon") node.innerHTML = iconSvg(v);
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) if (c !== null && c !== undefined && c !== false) node.append(c);
  return node;
}

/** Thay toàn bộ con của một phần tử, bỏ qua null/false (replaceChildren gốc sẽ in chữ "null") */
function setChildren(node, ...children) {
  node.replaceChildren(...children.flat().filter((c) => c !== null && c !== undefined && c !== false));
}

const MODE_LABEL = { fast: "Nhanh", balanced: "Cân bằng", accurate: "Kỹ" };

// ---------------------------------------------------------------- Gọi API
class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function handle(res) {
  // Hết phiên đăng nhập / chưa đăng nhập: về trang đăng nhập.
  // Tải lại cả trang để xóa sạch dữ liệu của phiên cũ trong bộ nhớ.
  if (res.status === 401 && !location.pathname.endsWith("/login.html")) {
    location.href = "/login.html";
  }
  if (res.ok) return res.json();
  let message = `Lỗi ${res.status}`;
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") message = data.detail;                              // lỗi do code chủ động raise
    else if (Array.isArray(data?.detail)) message = data.detail.map((d) => d.msg).join("; ");  // lỗi 422 của Pydantic
  } catch {
    if (res.status >= 500) message = "Lỗi máy chủ. Xem cửa sổ uvicorn để biết chi tiết.";
  }
  throw new ApiError(message, res.status);
}

const get = (url) => fetch(url, { cache: "no-store" }).then(handle);
const send = (method, url, body) =>
  fetch(url, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then(handle);

const api = {
  // đăng nhập: token nằm trong cookie httpOnly do backend đặt, JavaScript không đọc được
  login: (username, password) => send("POST", "/api/auth/login", { username, password }).then((r) => r.user),
  logout: () => fetch("/api/auth/logout", { method: "POST" }),
  me: () => get("/api/auth/me"),

  health: () => get("/api/health"),
  publicSettings: () => get("/api/settings"),
  adminSettings: () => get("/api/admin/settings"),
  saveAdminSettings: (changes) => send("PUT", "/api/admin/settings", changes),
  resetAdminSettings: () => send("POST", "/api/admin/settings/reset"),

  listDocuments: () => get("/api/documents"),
  deleteDocument: (docId) => send("DELETE", `/api/documents/${docId}`),
  uploadDocument(file) {
    const form = new FormData();
    form.append("file", file); // không tự đặt Content-Type: trình duyệt tự thêm "boundary"
    return fetch("/api/documents", { method: "POST", body: form }).then(handle);
  },

  listSessions: (docId) => get(`/api/sessions?doc_id=${docId}`),
  sessionMessages: (sessionId) => get(`/api/sessions/${sessionId}/messages`).then((r) => r.messages),
  deleteSession: (sessionId) => send("DELETE", `/api/sessions/${sessionId}`),
  /** sessionId = null: bắt đầu cuộc trò chuyện mới, backend tạo và trả về trong `session` */
  ask: (docId, sessionId, question, mode) =>
    send("POST", "/api/chat", { doc_id: docId, session_id: sessionId, question, mode: mode ?? null }),

  pageImageUrl: (docId, page) => `/api/documents/${docId}/pages/${page}/image`,
};
