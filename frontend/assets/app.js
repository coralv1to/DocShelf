/* =====================================================================
   DocShelf — trang chính (JavaScript thuần, không build).
   Cần common.js nạp trước (icon, el(), api).

   Đọc theo thứ tự:
     1. Trạng thái            5. Chat (tin nhắn, chế độ trả lời, lịch sử)
     2. Điều hướng            6. Trang Cài đặt (admin)
     3. Sidebar + thanh trên  7. Panel nguồn (ảnh trang PDF có tô vàng)
     4. Kệ tài liệu + upload  8. Khởi động
   ===================================================================== */

// Dung lượng upload tối đa: lấy từ backend (/api/settings, MAX_UPLOAD_MB trong .env); 100 nếu chưa tải xong
const maxUploadMb = () => state.settings?.max_upload_mb ?? 100;

const SUGGESTIONS = [
  "Tài liệu này nói về chủ đề gì?",
  "Tài liệu gồm những phần chính nào?",
  "Tóm tắt nội dung chính của tài liệu",
];

// Loại từ chối (backend trả về debug.refusal_kind) -> nhãn dễ hiểu
const REFUSAL_LABEL = {
  not_in_doc: "Không có trong tài liệu",
  unsure: "Chưa trả lời được",
  unverified: "Chưa kiểm chứng được",
  figure: "Nằm trong hình",
};

// Thời gian ước tính trên laptop GPU 6GB (qwen3.5:4b, reranker chạy CPU) — để admin dễ hình dung
const MODE_TIME = {
  fast: "thường 3–8 giây",
  balanced: "thường 5–15 giây · câu hỏi vị trí 1–3 giây",
  accurate: "thường 15–25 giây",
};

// Các tham số số trong mục "Nâng cao" của trang Cài đặt, theo thứ tự hiển thị
const TUNING_KEYS = ["top_k_retrieve", "top_k_context", "hard_rerank_score", "min_rerank_score", "hard_vector_score", "min_vector_score", "history_turns"];

const MODE_STORAGE_KEY = "docshelf.mode";

// ---------------------------------------------------------------- 1. TRẠNG THÁI
const state = {
  user: null,          // { id, username, full_name, role }
  docs: [],            // kệ tài liệu
  docsLoading: true,
  view: "shelf",       // "shelf" | "chat" | "settings"
  doc: null,           // tài liệu đang mở
  sessions: [],        // lịch sử trò chuyện của tài liệu đang mở
  sessionId: null,     // cuộc trò chuyện đang mở (null = cuộc mới, backend tạo ở câu hỏi đầu)
  settings: null,      // { default_mode, allow_user_mode, modes }
  citation: null,      // trích dẫn đang mở trong panel nguồn
  chat: null,          // cuộc trò chuyện đang hiển thị (xem createChat)
};

const isAdmin = () => state.user?.role === "admin";

// ---------------------------------------------------------------- 2. ĐIỀU HƯỚNG
function openShelf() {
  state.view = "shelf";
  state.doc = null;
  closeSource();
  renderMain();
}

function openSettings() {
  state.view = "settings";
  closeSource();
  renderMain();
}

function openDoc(doc) {
  state.view = "chat";
  state.doc = doc;
  state.sessions = [];
  startChat(null);
  api.listSessions(doc.doc_id)
    .then((list) => {
      if (state.doc?.doc_id !== doc.doc_id) return; // đã chuyển sang tài liệu khác
      state.sessions = list;
      renderSidebar();
    })
    .catch(() => {});
}

/** Mở một cuộc trò chuyện (null = cuộc mới). Mỗi cuộc là một khung chat mới, không lẫn trạng thái. */
function startChat(sessionId) {
  state.sessionId = sessionId;
  closeSource(); // trích dẫn cũ không thuộc cuộc trò chuyện mới
  state.chat?.destroy(); // câu trả lời của khung cũ về muộn sẽ không chèn nhầm vào khung mới
  state.chat = createChat(state.doc, sessionId);
  renderMain();
}

function renderMain() {
  const view = $("view");
  if (state.view === "settings") setChildren(view, buildSettings());
  else if (state.view === "chat") setChildren(view, state.chat.node);
  else setChildren(view, buildShelf());
  renderSidebar();
  renderTopbar();
  if (state.view === "chat") state.chat.focus();
}

// ---------------------------------------------------------------- 3. SIDEBAR + THANH TRÊN
function navItem({ icon, label, active, onclick, title, extra, iconClass }) {
  return el("button", { class: `nav-item${active ? " active" : ""}`, onclick, title },
    el("span", { class: `icon ${iconClass || ""}`, icon }),
    el("span", { class: "ellipsis", text: label }),
    extra);
}

function renderSidebar() {
  const { user, docs, view, doc, sessions, sessionId } = state;
  const initial = (user.full_name || user.username).trim().charAt(0).toUpperCase();

  const docItems = docs.map((d) => {
    const active = view === "chat" && doc?.doc_id === d.doc_id;
    return el("li", {},
      navItem({ icon: "file", iconClass: "doc-icon", label: d.title, title: d.title, active, onclick: () => openDoc(d) }),
      active && el("div", { class: "sessions" },
        navItem({ icon: "plus", label: "Cuộc trò chuyện mới", active: !sessionId, onclick: () => startChat(null) }),
        sessions.map((s) => el("div", { class: "session-row" },
          navItem({ icon: "chat", iconClass: "chat-icon", label: s.title, title: s.title,
            active: s.session_id === sessionId, onclick: () => startChat(s.session_id) }),
          el("button", { class: "session-del", title: "Xóa cuộc trò chuyện", "aria-label": "Xóa cuộc trò chuyện",
            icon: "trash", onclick: () => removeSession(s) })))));
  });

  setChildren($("sidebar"),
    el("button", { class: "brand", onclick: openShelf },
      el("span", { class: "brand-logo" }, el("span", { class: "icon", icon: "shelf" })), "DocShelf"),
    el("div", { class: "nav" },
      navItem({ icon: "shelf", label: "Kệ tài liệu", active: view === "shelf", onclick: openShelf,
        extra: el("span", { class: "count", text: String(docs.length) }) }),
      isAdmin() && navItem({ icon: "settings", label: "Cài đặt", active: view === "settings", onclick: openSettings })),
    el("nav", { class: "doc-nav" },
      el("div", { class: "label-caps", text: "Tài liệu" }),
      docs.length === 0 && el("p", { class: "muted", text: "Chưa có tài liệu." }),
      el("ul", { class: "doc-list" }, docItems)),
    el("div", { class: "sidebar-footer" },
      healthBox,
      el("div", { class: "user-card" },
        el("span", { class: "avatar-initial", text: initial }),
        el("div", { class: "who" },
          el("div", { class: "small medium ellipsis", text: user.full_name || user.username }),
          el("div", { class: "xs muted", text: isAdmin() ? "Quản trị viên" : "Người dùng" })),
        el("button", { class: "icon-btn", title: "Đăng xuất", "aria-label": "Đăng xuất", icon: "logout", onclick: signOut }))),
  );
}

function renderTopbar() {
  const { view, doc } = state;
  $("top-title").textContent = view === "settings" ? "Cài đặt" : view === "chat" ? doc.title : "DocShelf";
  $("top-settings").hidden = !isAdmin() || view === "settings";
  $("top-new-chat").hidden = view !== "chat";
}

/** Ô trạng thái backend ở chân sidebar (giữ một phần tử, chỉ nạp lại khi cần) */
const healthBox = el("div", { class: "health" });
async function loadHealth() {
  setChildren(healthBox, el("div", { class: "health-row" }, el("span", { class: "dot pulse" }), "Đang kiểm tra backend..."));
  try {
    const h = await api.health();
    setChildren(healthBox,
      el("div", { class: "health-row" }, el("span", { class: "dot ok" }), el("span", { class: "health-model ellipsis", text: h.chat_model })),
      el("div", { class: "health-indent ellipsis", text: h.embed_model }),
      el("div", { class: "health-indent", text: `Chế độ mặc định: ${MODE_LABEL[h.default_mode] || h.default_mode}` }));
  } catch (e) {
    setChildren(healthBox, el("div", { class: "health-row health-err" }, el("span", { class: "dot err" }), e.message));
  }
}

async function signOut() {
  await api.logout();
  // Tải lại toàn bộ trang: xóa sạch dữ liệu của người dùng trước trong bộ nhớ
  location.replace("/login.html");
}

async function removeSession(s) {
  if (!confirm(`Xóa cuộc trò chuyện “${s.title}”?`)) return;
  try {
    await api.deleteSession(s.session_id);
    state.sessions = state.sessions.filter((x) => x.session_id !== s.session_id);
    if (s.session_id === state.sessionId) startChat(null);
    else renderSidebar();
  } catch (e) {
    alert(e.message);
  }
}

// ---------------------------------------------------------------- 4. KỆ TÀI LIỆU + UPLOAD
function formatDate(iso) {
  return iso ? new Date(iso).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" }) : "";
}

const upload = { busy: false, name: null, error: null, dragging: false };

function buildShelf() {
  const { docs, docsLoading } = state;
  let body;
  if (docsLoading) {
    body = el("div", { class: "shelf-grid" }, [0, 1, 2].map(() => el("div", { class: "skeleton" })));
  } else if (docs.length === 0) {
    body = el("div", { class: "empty-shelf" },
      el("span", { class: "icon i32", icon: "shelf" }),
      el("p", { class: "medium", text: "Kệ còn trống" }),
      el("p", { class: "small muted", text: isAdmin()
        ? "Thêm file PDF đầu tiên ở ô phía trên."
        : "Chưa có tài liệu nào. Liên hệ quản trị viên để thêm tài liệu." }));
  } else {
    body = el("div", {},
      el("div", { class: "label-caps", style: "margin-bottom:12px", text: `${docs.length} tài liệu` }),
      el("div", { class: "shelf-grid" }, docs.map(docTile)));
  }
  return el("div", { class: "page-scroll" },
    el("div", { class: "page" },
      el("header", { class: "page-head" },
        el("h1", { text: "Kệ tài liệu" }),
        el("p", { text: "Chọn một tài liệu để hỏi đáp. Câu trả lời chỉ dựa trên nội dung tài liệu đó, kèm trích dẫn và vị trí trang." })),
      isAdmin() && buildDropzone(),
      isAdmin() && upload.error && el("p", { class: "error-text", text: upload.error }),
      body));
}

function docTile(d) {
  const meta = [d.uploaded_by && `Thêm bởi ${d.uploaded_by}`, formatDate(d.created_at)].filter(Boolean).join(" · ");
  return el("div", { class: "doc-tile" },
    el("button", { class: "doc-tile-open", onclick: () => openDoc(d) },
      el("div", { class: "doc-tile-head" },
        el("div", { class: "doc-tile-icon" }, el("span", { class: "icon", icon: "file" })),
        el("div", { style: "min-width:0;flex:1" },
          el("div", { class: "doc-tile-title clamp2", text: d.title, title: d.title }),
          el("div", { class: "xs muted", style: "margin-top:4px", text: `${d.num_pages} trang · ${d.num_chunks} đoạn` }))),
      meta && el("div", { class: "doc-tile-meta ellipsis", text: meta })),
    isAdmin() && el("button", { class: "doc-tile-del", title: "Xóa tài liệu", "aria-label": `Xóa ${d.title}`,
      icon: "trash", onclick: () => removeDoc(d) }));
}

/** Ô kéo-thả thêm tài liệu (chỉ admin; backend cũng chặn người dùng thường) */
function buildDropzone() {
  const zone = el("div", {
    class: `dropzone${upload.busy ? " busy" : ""}`, role: "button", tabindex: "0",
    onclick: () => $("file-input").click(),
    onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); $("file-input").click(); } },
    ondragover: (e) => { e.preventDefault(); zone.classList.add("dragging"); }, // preventDefault: không cho trình duyệt mở file
    ondragleave: () => zone.classList.remove("dragging"),
    ondrop: (e) => { e.preventDefault(); zone.classList.remove("dragging"); handleFile(e.dataTransfer.files[0]); },
  },
  upload.busy
    ? el("div", { class: "drop-content" },
        el("div", { class: "spinner" }),
        el("div", { class: "medium", text: `Đang xử lý ${upload.name}...` }),
        el("div", { class: "small muted", text: "Đang đọc, cắt đoạn và tạo vector. Có thể mất 1–2 phút." }))
    : el("div", { class: "drop-content" },
        el("div", { class: "drop-icon" }, el("span", { class: "icon", icon: "upload" })),
        el("div", { class: "medium", text: "Thêm tài liệu lên kệ" }),
        el("div", { class: "small muted",
          text: `Kéo thả file PDF vào đây, hoặc bấm để chọn · tối đa ${maxUploadMb()}MB · PDF có chữ (không phải bản scan)` })));
  return zone;
}

async function handleFile(file) {
  if (!file || upload.busy) return;
  upload.error = null;
  // Thuộc tính accept chỉ là gợi ý cho hộp thoại chọn file -> phải kiểm tra lại bằng code
  if (!file.name.toLowerCase().endsWith(".pdf")) upload.error = "Chỉ hỗ trợ file PDF.";
  else if (file.size > maxUploadMb() * 1024 * 1024) upload.error = `File vượt quá ${maxUploadMb()}MB.`;
  if (upload.error) return state.view === "shelf" && renderMain();

  upload.busy = true;
  upload.name = file.name;
  if (state.view === "shelf") renderMain();
  try {
    const doc = await api.uploadDocument(file);
    state.docs = [doc, ...state.docs];
    upload.busy = false;
    openDoc(doc);
  } catch (e) {
    upload.error = e.message;
  } finally {
    upload.busy = false;
    $("file-input").value = ""; // cho phép chọn lại cùng một file
    if (state.view === "shelf") renderMain();
  }
}

async function removeDoc(d) {
  if (!confirm(`Xóa “${d.title}” khỏi kệ?\nMọi cuộc trò chuyện về tài liệu này cũng bị xóa.`)) return;
  try {
    await api.deleteDocument(d.doc_id);
    state.docs = state.docs.filter((x) => x.doc_id !== d.doc_id);
    if (state.doc?.doc_id === d.doc_id) openShelf();
    else renderMain();
  } catch (e) {
    alert(e.message);
  }
}

// ---------------------------------------------------------------- 5. CHAT
function readSavedMode() {
  try {
    const v = localStorage.getItem(MODE_STORAGE_KEY);
    return ["fast", "balanced", "accurate"].includes(v) ? v : null;
  } catch {
    return null; // trình duyệt chặn lưu trữ (chế độ riêng tư...)
  }
}

function saveMode(mode) {
  try {
    if (mode) localStorage.setItem(MODE_STORAGE_KEY, mode);
    else localStorage.removeItem(MODE_STORAGE_KEY);
  } catch { /* không lưu được thì thôi, chỉ là tiện ích */ }
}

/**
 * Tạo một khung chat cho một cuộc trò chuyện. Mọi biến nằm trong closure này,
 * mở cuộc khác là tạo khung mới -> không lẫn tin nhắn / trạng thái giữa các cuộc.
 */
function createChat(doc, initialSessionId) {
  let sessionId = initialSessionId; // null cho tới khi backend tạo ở câu hỏi đầu
  let loading = false;
  let historyLoading = initialSessionId !== null;
  let chosenMode = readSavedMode(); // null = theo mặc định của admin
  let alive = true;                 // false khi người dùng đã chuyển sang cuộc khác

  const list = el("div", { class: "messages-inner" });
  const empty = el("div", { class: "empty-state" },
    el("h2", { text: "Bạn muốn hỏi gì về tài liệu này?" }),
    el("p", { class: "muted ellipsis", text: doc.title, title: doc.title }),
    el("div", { class: "suggestions" }, SUGGESTIONS.map((s) => el("button", { class: "chip", text: s, onclick: () => sendQuestion(s) }))));
  const scroller = el("div", { class: "messages" }, empty, list);

  const input = el("textarea", { rows: "1", maxlength: "2000", placeholder: "Hỏi về nội dung tài liệu..." });
  const sendBtn = el("button", { type: "submit", class: "send-btn", "aria-label": "Gửi", icon: "arrowUp", disabled: true });
  const modeBox = el("div", { class: "mode-switch", role: "radiogroup", "aria-label": "Chế độ trả lời" });
  const form = el("form", { class: "composer", onsubmit: (e) => { e.preventDefault(); sendQuestion(); } }, input, sendBtn);
  const node = el("div", { class: "chat-view" }, scroller,
    el("div", { class: "composer-wrap" }, form,
      el("div", { class: "composer-foot" }, modeBox,
        el("span", { text: "Câu trả lời chỉ dựa trên tài liệu đã tải lên. Hãy đối chiếu với trích dẫn." }))));

  // Ô nhập tự giãn theo nội dung, tối đa 200px
  function autoGrow() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 200)}px`;
    sendBtn.disabled = loading || historyLoading || !input.value.trim();
  }
  input.addEventListener("input", autoGrow);
  input.addEventListener("keydown", (e) => {
    // Enter = gửi, Shift+Enter = xuống dòng.
    // isComposing: bộ gõ tiếng Việt (Unikey/IME) đang ghép dấu -> Enter dùng để chốt chữ, KHÔNG gửi.
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      sendQuestion();
    }
  });

  // --- Chế độ trả lời: chỉ hiện khi admin cho phép người dùng tự chọn
  function currentMode() {
    const s = state.settings;
    if (!s?.allow_user_mode) return null; // null = backend dùng chế độ mặc định
    return chosenMode || s.default_mode;
  }
  function renderModes() {
    const s = state.settings;
    const mode = currentMode();
    modeBox.hidden = !mode;
    if (!mode) return;
    setChildren(modeBox, s.modes.map((m) => el("button", {
      type: "button", role: "radio", "aria-checked": String(mode === m.id), title: m.description, text: m.label,
      onclick: () => {
        chosenMode = m.id === s.default_mode ? null : m.id; // chọn đúng mặc định = bỏ lựa chọn riêng
        saveMode(chosenMode);
        renderModes();
      },
    })));
  }
  renderModes();

  function scrollToBottom() {
    scroller.scrollTo({ top: scroller.scrollHeight, behavior: "smooth" });
  }
  function add(nodeToAdd) {
    empty.hidden = true;
    list.append(nodeToAdd);
    scrollToBottom();
  }

  async function sendQuestion(text) {
    const question = (text ?? input.value).trim();
    if (!question || loading || historyLoading) return;
    input.value = "";
    loading = true;
    autoGrow();
    add(userMessage(question)); // hiện câu hỏi ngay, không chờ backend
    const typing = typingIndicator();
    add(typing);
    try {
      const { session, ...result } = await api.ask(doc.doc_id, sessionId, question, currentMode());
      if (!alive) return;
      sessionId = session.session_id;
      typing.replaceWith(assistantMessage(result));
      onSessionUpdated(session);
    } catch (e) {
      if (!alive) return;
      typing.replaceWith(errorMessage(e.message));
    } finally {
      loading = false;
      if (alive) {
        autoGrow();
        scrollToBottom();
        input.focus();
      }
    }
  }

  // Mở lại cuộc trò chuyện cũ: nạp tin nhắn đã lưu trong database
  if (initialSessionId) {
    empty.hidden = true;
    const spinner = el("div", { class: "center-fill", style: "height:100%" }, el("div", { class: "spinner" }));
    scroller.prepend(spinner);
    api.sessionMessages(initialSessionId)
      .then((messages) => {
        if (!alive) return;
        for (const m of messages) {
          list.append(m.role === "user" ? userMessage(m.content) : m.result ? assistantMessage(m.result) : errorMessage(m.content));
        }
        if (!messages.length) empty.hidden = false;
        scroller.scrollTop = scroller.scrollHeight;
      })
      .catch((e) => alive && list.append(el("div", { class: "error-box", text: `⚠️ ${e.message}` })))
      .finally(() => {
        spinner.remove();
        historyLoading = false;
        if (alive) autoGrow();
      });
  }

  return {
    node,
    focus: () => input.focus(),
    refreshModes: renderModes,
    destroy: () => { alive = false; },
  };
}

/** Sau mỗi câu trả lời: cuộc trò chuyện được tạo/cập nhật -> đưa lên đầu danh sách lịch sử */
function onSessionUpdated(s) {
  state.sessionId = s.session_id;
  state.sessions = [s, ...state.sessions.filter((x) => x.session_id !== s.session_id)];
  renderSidebar();
}

function userMessage(text) {
  return el("div", { class: "msg-user" }, el("div", { class: "bubble", text }));
}

function botShell(...children) {
  return el("div", { class: "msg-bot" },
    el("div", { class: "avatar" }, el("span", { class: "icon", icon: "spark" })),
    el("div", { class: "msg-body" }, ...children));
}

function typingIndicator() {
  return botShell(el("div", { class: "typing" },
    el("span", { class: "b" }), el("span", { class: "b" }), el("span", { class: "b" }),
    el("span", { class: "muted", text: "Đang tìm trong tài liệu..." })));
}

function errorMessage(msg) {
  return botShell(el("div", { class: "error-box", text: `⚠️ ${msg}` }));
}

function copyButton(text) {
  const btn = el("button", { class: "icon-btn", title: "Sao chép", icon: "copy" });
  btn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(text);
      btn.innerHTML = iconSvg("check");
      setTimeout(() => (btn.innerHTML = iconSvg("copy")), 1500);
    } catch { /* clipboard chỉ chạy ở localhost/https */ }
  });
  return btn;
}

/** Dòng "Chi tiết" thu gọn: chế độ, điểm, ngưỡng, luồng xử lý, lý do từ chối, tổng thời gian */
function debugInfo(d) {
  const parts = ["Chi tiết"];
  if (d.mode && d.mode !== "legacy") parts.push(MODE_LABEL[d.mode] || d.mode);
  parts.push(`điểm ${d.best_score} / ngưỡng ${d.gate}`);
  if (d.route === "overview") parts.push("trả lời từ dàn ý");
  if (d.route === "location") parts.push("tra vị trí");
  if (d.route === "figure") parts.push(`tra ${d.figure || "hình"}`);
  if (d.rejected_reason) parts.push(d.rejected_reason);
  if (d.timings_ms) parts.push(`${(Object.values(d.timings_ms).reduce((a, b) => a + b, 0) / 1000).toFixed(1)}s`);
  return el("details", { class: "debug" },
    el("summary", { text: parts.join(" · ") }),
    el("pre", { text: JSON.stringify(d, null, 2) }));
}

/** Các thẻ nguồn: bấm vào mở panel trang PDF */
function sourcesBlock(citations) {
  return el("div", { class: "sources" },
    el("div", { class: "label-caps", text: "Nguồn" }),
    el("div", { class: "sources-grid" }, citations.map((c, j) => {
      const card = el("button", { type: "button", class: "source-card", title: "Xem trong tài liệu gốc", onclick: () => openSource(c) },
        el("div", { class: "source-card-head" },
          el("span", { class: "source-num", text: String(j + 1) }),
          el("span", { class: "ellipsis" },
            el("span", { class: "medium", text: `Trang ${c.page}` }),
            c.section && el("span", { class: "muted", text: ` · ${c.section.split(" > ").pop()}` }))),
        el("p", { class: "source-card-quote clamp2", text: `“${c.quote}”` }));
      card._citation = c; // gắn object trích dẫn vào nút để biết nút nào đang mở
      return card;
    })));
}

function assistantMessage(result) {
  const d = result.debug || {};
  const chitchat = d.route === "chitchat"; // chào hỏi/cảm ơn/chửi...: hiện như tin nhắn thường
  const refused = !result.found && !chitchat;
  const dropped = d.dropped_quotes?.length || 0;
  const example = result.example || d.example; // ví dụ do trợ lý tự nghĩ (không có trong sách)
  return botShell(
    refused && el("span", { class: "badge", text: REFUSAL_LABEL[d.refusal_kind] || "Không có trong tài liệu" }),
    el("div", { class: "answer", text: result.answer }),
    Boolean(example) && el("div", { class: "example" },
      el("div", { class: "example-label", text: "Ví dụ minh họa · do trợ lý tự đưa ra, không có trong sách" }),
      el("div", { class: "answer", text: example })),
    result.found && d.confidence === "medium" && result.citations?.length > 0 &&
      el("p", { class: "note", text: "Đoạn tìm được chỉ khớp một phần với câu hỏi — nên mở nguồn bên dưới để đối chiếu." }),
    dropped > 0 && el("p", { class: "note", text: `Đã bỏ ${dropped} trích dẫn không khớp nguyên văn với tài liệu.` }),
    result.citations?.length > 0 && sourcesBlock(result.citations),
    el("div", { class: "actions" }, copyButton(result.answer), !chitchat && debugInfo(d)));
}

// ---------------------------------------------------------------- 6. TRANG CÀI ĐẶT (admin)
function buildSettings() {
  const root = el("div", { class: "page-scroll" }, el("div", { class: "center-fill", style: "height:100%" }, el("div", { class: "spinner" })));
  let data = null;   // { values, defaults, spec, modes } từ backend
  let form = null;   // bản đang sửa, chưa lưu
  let saving = false;
  let message = null; // { ok, text }

  const dirty = () => JSON.stringify(form) !== JSON.stringify(data.values);

  function set(key, value) {
    form = { ...form, [key]: value };
    message = null;
    render();
  }

  async function run(action, okText) {
    saving = true;
    message = null;
    render();
    try {
      data = await action();
      form = { ...data.values };
      message = { ok: true, text: okText };
      afterSettingsSaved();
    } catch (e) {
      message = { ok: false, text: e.message };
    } finally {
      saving = false;
      render();
    }
  }

  function save() {
    // Chỉ gửi những giá trị đã đổi
    const changes = Object.fromEntries(Object.entries(form).filter(([k, v]) => data.values[k] !== v));
    run(() => api.saveAdminSettings(changes), "Đã lưu. Có hiệu lực từ câu hỏi tiếp theo.");
  }

  function reset() {
    if (!confirm("Khôi phục toàn bộ cài đặt về mặc định (theo file .env)?")) return;
    run(api.resetAdminSettings, "Đã khôi phục mặc định.");
  }

  function render() {
    // Giữ trạng thái mở/đóng của mục "Nâng cao" khi vẽ lại
    const advOpen = root.querySelector("details.advanced")?.open ?? false;
    const spec = data.spec;
    const modeCards = data.modes.map((m) => el("button", {
      class: "mode-card", role: "radio", "aria-checked": String(form.default_mode === m.id), onclick: () => set("default_mode", m.id),
    },
      el("div", { class: "mode-card-head" }, el("span", { text: m.label }), el("span", { class: "radio-dot" })),
      el("p", { text: m.description }),
      el("p", { class: "xs", text: MODE_TIME[m.id] || "" })));

    const tuning = TUNING_KEYS.map((key) => {
      const s = spec[key];
      const input = el("input", {
        id: key, type: "number", class: `field${form[key] !== data.defaults[key] ? " changed" : ""}`,
        min: s.min, max: s.max, step: s.step ?? 1, value: String(form[key]),
      });
      input.addEventListener("change", () => set(key, Number(input.value)));
      return el("div", { class: "tune-row" },
        el("label", { for: key },
          el("span", { class: "small medium", text: s.label }),
          el("span", { class: "xs muted", style: "display:block;margin-top:2px",
            text: `${s.help} Mặc định: ${data.defaults[key]}${s.min !== undefined ? ` · từ ${s.min} đến ${s.max}` : ""}.` })),
        input);
    });

    const isDirty = dirty();
    setChildren(root, el("div", { class: "page narrow" },
      el("header", { class: "page-head" },
        el("h1", { text: "Cài đặt" }),
        el("p", { text: "Cân bằng giữa tốc độ và độ chính xác của câu trả lời. Thay đổi có hiệu lực ngay, không cần khởi động lại." })),

      el("section", { class: "settings-section" },
        el("h2", { text: spec.default_mode.label }),
        el("p", { class: "small muted", text: spec.default_mode.help }),
        el("div", { class: "mode-cards", role: "radiogroup" }, modeCards)),

      el("section", { class: "settings-section toggle-row" },
        el("div", {}, el("h2", { text: spec.allow_user_mode.label }), el("p", { class: "small muted", text: spec.allow_user_mode.help })),
        el("button", { class: "switch", role: "switch", "aria-checked": String(form.allow_user_mode),
          "aria-label": spec.allow_user_mode.label, onclick: () => set("allow_user_mode", !form.allow_user_mode) })),

      el("details", { class: "advanced", open: advOpen },
        el("summary", { text: "Nâng cao" }),
        el("div", { class: "advanced-body" },
          el("p", { class: "small muted", text: "Chỉ chỉnh khi đã hiểu ý nghĩa. Sau khi đổi ngưỡng, nên chạy lại benchmark để kiểm tra độ chính xác." }),
          tuning)),

      el("div", { class: "save-row" },
        el("button", { class: "btn-primary", disabled: !isDirty || saving, onclick: save, text: saving ? "Đang lưu..." : "Lưu thay đổi" }),
        isDirty && el("button", { class: "btn-ghost", disabled: saving, text: "Hủy", onclick: () => { form = { ...data.values }; render(); } }),
        el("button", { class: "btn-ghost push-right", disabled: saving, text: "Khôi phục mặc định", onclick: reset })),
      message && el("p", { class: `save-msg ${message.ok ? "ok-text" : "error-text"}`, role: "status", text: message.text })));
  }

  api.adminSettings()
    .then((d) => {
      data = d;
      form = { ...d.values };
      render();
    })
    .catch((e) => setChildren(root, el("div", { class: "center-fill", style: "height:100%" }, el("p", { class: "error-text", text: e.message }))));

  return root;
}

/** Admin vừa lưu cài đặt: tải lại chế độ mặc định (ô chọn chế độ khi chat + trạng thái ở sidebar) */
function afterSettingsSaved() {
  loadHealth();
  api.publicSettings().then((s) => {
    state.settings = s;
    state.chat?.refreshModes();
  }).catch(() => {});
}

// ---------------------------------------------------------------- 7. PANEL NGUỒN
const panel = { page: 1 };

function openSource(citation) {
  state.citation = citation;
  panel.page = citation.page;
  $("source").hidden = false;
  $("app").classList.add("panel-open");
  $("source-doc").textContent = state.doc.title;
  const section = citation.section.split(" > ").slice(1).join(" › ") || state.doc.title;
  $("source-section").textContent = section;
  $("source-section").title = section;
  $("source-quote").textContent = `“${citation.quote}”`;
  markActiveCards();
  showPage();
}

function closeSource() {
  state.citation = null;
  $("source").hidden = true;
  $("app").classList.remove("panel-open");
  markActiveCards();
}

/** Thẻ nguồn đang mở có nền vàng (so sánh đúng object, không so nội dung) */
function markActiveCards() {
  document.querySelectorAll(".source-card").forEach((b) => b.classList.toggle("active", b._citation === state.citation));
}

function goPage(page) {
  if (!state.citation || page < 1 || page > state.doc.num_pages || page === panel.page) return;
  panel.page = page;
  showPage();
}

/** Hiện trang panel.page; ô tô vàng chỉ vẽ khi đang ở đúng trang của trích dẫn */
function showPage() {
  const c = state.citation;
  const page = panel.page;
  const onCitationPage = page === c.page;

  $("source-page").textContent = `${page} / ${state.doc.num_pages}`;
  $("source-prev").disabled = page <= 1;
  $("source-next").disabled = page >= state.doc.num_pages;
  $("source-back").hidden = onCitationPage;
  $("source-back").textContent = `Quay lại trang ${c.page}`;
  setChildren($("page-marks"));
  $("page-error").hidden = true;
  $("page-nomark").hidden = true;
  $("page-frame").hidden = false;
  $("page-frame").classList.add("loading");
  $("page-loading").hidden = false;

  const img = $("page-img");
  img.alt = `Trang ${page}`;
  img.onload = () => {
    if (panel.page !== page || state.citation !== c) return; // ảnh cũ tải xong muộn -> bỏ qua
    $("page-loading").hidden = true;
    $("page-frame").classList.remove("loading");
    if (onCitationPage) drawMarks(c);
  };
  img.onerror = () => {
    if (panel.page !== page || state.citation !== c) return;
    $("page-frame").hidden = true;
    $("page-error").hidden = false;
  };
  const url = api.pageImageUrl(state.doc.doc_id, page);
  // Cùng ảnh đã tải sẵn (mở lại trích dẫn ở trang đang hiện): trình duyệt không bắn onload lần nữa
  if (img.getAttribute("src") === url && img.complete && img.naturalWidth) img.onload();
  else img.src = url;
}

/** rects là tọa độ tương đối 0..1 của trang -> đặt bằng %, ảnh co giãn thì ô tô màu co giãn theo */
function drawMarks(c) {
  if (!c.rects?.length) {
    $("page-nomark").hidden = false;
    return;
  }
  const marks = c.rects.map(([x0, y0, x1, y1]) => el("div", {
    class: "mark",
    style: `left:${x0 * 100}%;top:${y0 * 100}%;width:${(x1 - x0) * 100}%;height:${(y1 - y0) * 100}%`,
  }));
  setChildren($("page-marks"), marks);
  marks[0].scrollIntoView({ behavior: "smooth", block: "center" }); // tự cuộn tới vùng tô
}

// ---------------------------------------------------------------- 8. KHỞI ĐỘNG
function initStatic() {
  fillIcons();
  $("top-shelf").addEventListener("click", openShelf);
  $("top-settings").addEventListener("click", openSettings);
  $("top-new-chat").addEventListener("click", () => startChat(null));
  $("file-input").addEventListener("change", (e) => handleFile(e.target.files[0]));
  $("source-close").addEventListener("click", closeSource);
  $("source-prev").addEventListener("click", () => goPage(panel.page - 1));
  $("source-next").addEventListener("click", () => goPage(panel.page + 1));
  $("source-back").addEventListener("click", () => goPage(state.citation.page));
  // Phím tắt panel nguồn: Esc đóng, ← → chuyển trang (trừ khi đang gõ chữ)
  document.addEventListener("keydown", (e) => {
    if (!state.citation) return;
    const typing = ["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName);
    if (e.key === "Escape") closeSource();
    else if (!typing && e.key === "ArrowLeft") goPage(panel.page - 1);
    else if (!typing && e.key === "ArrowRight") goPage(panel.page + 1);
  });
}

async function boot() {
  initStatic();
  try {
    state.user = await api.me(); // chưa đăng nhập -> common.js tự chuyển sang /login.html
  } catch {
    return;
  }
  $("boot").hidden = true;
  $("app").hidden = false;
  renderMain();
  loadHealth();
  api.publicSettings().then((s) => {
    state.settings = s;
    state.chat?.refreshModes();
  }).catch(() => {});
  try {
    state.docs = await api.listDocuments();
  } catch (e) {
    upload.error = e.message;
  } finally {
    state.docsLoading = false;
    if (state.view === "shelf") renderMain();
    else renderSidebar();
  }
}

boot();
