/* Trang đăng nhập. Backend đặt cookie httpOnly khi đăng nhập đúng -> vào trang chính. */

const form = $("login-form");
const userInput = $("username");
const passInput = $("password");
const button = $("login-btn");
const errorBox = $("login-error");
let busy = false;

fillIcons();

// Đã đăng nhập rồi (cookie còn hạn) thì vào thẳng kệ tài liệu
fetch("/api/auth/me", { cache: "no-store" }).then((r) => {
  if (r.ok) location.replace("/");
});

function updateButton() {
  button.disabled = busy || !userInput.value.trim() || !passInput.value;
}
userInput.addEventListener("input", updateButton);
passInput.addEventListener("input", updateButton);

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (busy) return;
  busy = true;
  errorBox.hidden = true;
  setChildren(button, el("span", { class: "spinner sm" }), "Đang đăng nhập...");
  updateButton();
  try {
    await api.login(userInput.value.trim(), passInput.value);
    // Tải lại toàn trang để bắt đầu sạch (không giữ trạng thái của tài khoản trước)
    location.replace("/");
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.hidden = false;
    busy = false;
    button.textContent = "Đăng nhập";
    updateButton();
  }
});
