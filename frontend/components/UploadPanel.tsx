"use client";

import { useRef, useState } from "react";
import { MAX_UPLOAD_MB, uploadDocument, type DocInfo } from "@/lib/api";
import { UploadIcon } from "./icons";

/** Ô kéo-thả để thêm tài liệu lên kệ (chỉ hiện với admin, backend cũng chặn user thường). */
export default function UploadPanel({ onUploaded }: { onUploaded: (doc: DocInfo) => void }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Chọn file xong là upload luôn, giống cách đính kèm file trong ChatGPT/Claude
  async function handleFile(file: File | null | undefined) {
    if (!file || loading) return;
    setError(null);
    if (!file.name.toLowerCase().endsWith(".pdf")) return setError("Chỉ hỗ trợ file PDF.");
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return setError(`File vượt quá ${MAX_UPLOAD_MB}MB.`);

    setFileName(file.name);
    setLoading(true);
    try {
      onUploaded(await uploadDocument(file));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi không xác định");
    } finally {
      setLoading(false);
      if (inputRef.current) inputRef.current.value = ""; // cho phép chọn lại cùng file
    }
  }

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault(); // bắt buộc, nếu không trình duyệt sẽ mở file thay vì thả vào đây
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFile(e.dataTransfer.files?.[0]);
        }}
        className={`cursor-pointer rounded-2xl border-2 border-dashed px-6 py-8 text-center transition-colors ${
          dragging
            ? "border-blue-500 bg-blue-50 dark:bg-blue-950/40"
            : "border-zinc-300 hover:border-zinc-400 hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-900"
        } ${loading ? "pointer-events-none opacity-70" : ""}`}
      >
        {loading ? (
          <div className="flex flex-col items-center gap-3">
            <div className="h-7 w-7 animate-spin rounded-full border-2 border-zinc-300 border-t-blue-600" />
            <div className="font-medium">Đang xử lý {fileName}...</div>
            <div className="text-sm text-zinc-500">Đang đọc, cắt đoạn và tạo vector. Có thể mất 1–2 phút.</div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <div className="rounded-full bg-zinc-100 p-2.5 dark:bg-zinc-800">
              <UploadIcon className="h-5 w-5" />
            </div>
            <div className="font-medium">Thêm tài liệu lên kệ</div>
            <div className="text-sm text-zinc-500">
              Kéo thả file PDF vào đây, hoặc bấm để chọn · tối đa {MAX_UPLOAD_MB}MB · PDF có chữ (không phải bản scan)
            </div>
          </div>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  );
}
