"use client";

import { useEffect, useRef, useState } from "react";
import { pageImageUrl, type Citation, type DocInfo } from "@/lib/api";
import { ChevronLeftIcon, ChevronRightIcon, XIcon } from "./icons";

type Props = {
  doc: DocInfo;
  citation: Citation;
  onClose: () => void;
};

// Lưu ý: component cha đặt `key` theo trích dẫn, nên mỗi lần bấm trích dẫn khác
// component được tạo mới hoàn toàn và `page` bắt đầu lại từ trang của trích dẫn đó.
export default function SourcePanel({ doc, citation, onClose }: Props) {
  const [page, setPage] = useState(citation.page);
  const [loadedPage, setLoadedPage] = useState<number | null>(null);
  const [failedPage, setFailedPage] = useState<number | null>(null);
  const firstMarkRef = useRef<HTMLDivElement>(null);

  // Trạng thái suy ra từ "trang nào đã tải xong / bị lỗi" -> không cần effect để reset
  const status = failedPage === page ? "error" : loadedPage === page ? "ready" : "loading";

  const onCitationPage = page === citation.page;
  const showMarks = onCitationPage && citation.rects.length > 0;

  // Ảnh tải xong -> cuộn tới vùng được tô
  useEffect(() => {
    if (status === "ready" && showMarks) {
      firstMarkRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [status, showMarks]);

  // Phím tắt: Esc đóng panel, ← → chuyển trang
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const typing = e.target instanceof HTMLElement && ["INPUT", "TEXTAREA"].includes(e.target.tagName);
      if (e.key === "Escape") onClose();
      else if (!typing && e.key === "ArrowLeft") setPage((p) => Math.max(1, p - 1));
      else if (!typing && e.key === "ArrowRight") setPage((p) => Math.min(doc.num_pages, p + 1));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey); // dọn dẹp khi panel đóng
  }, [onClose, doc.num_pages]);

  const canPrev = page > 1;
  const canNext = page < doc.num_pages;
  const section = citation.section.split(" > ").slice(1).join(" › ") || doc.title;

  return (
    <aside className="flex h-full flex-col border-l border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900">
      {/* ------------------------------------------------ Thanh tiêu đề */}
      <header className="flex items-center gap-1 border-b border-zinc-200 bg-white px-3 py-2.5 dark:border-zinc-800 dark:bg-zinc-950">
        <div className="min-w-0 flex-1 px-1">
          <p className="truncate text-sm font-medium" title={doc.title}>
            {doc.title}
          </p>
          <p className="truncate text-xs text-zinc-500" title={section}>
            {section}
          </p>
        </div>
        <button
          onClick={() => setPage((p) => p - 1)}
          disabled={!canPrev}
          aria-label="Trang trước"
          className="rounded-md p-1.5 hover:bg-zinc-100 disabled:opacity-30 disabled:hover:bg-transparent dark:hover:bg-zinc-800"
        >
          <ChevronLeftIcon className="h-4 w-4" />
        </button>
        <span className="min-w-[4.5rem] text-center text-xs text-zinc-500 tabular-nums">
          {page} / {doc.num_pages}
        </span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={!canNext}
          aria-label="Trang sau"
          className="rounded-md p-1.5 hover:bg-zinc-100 disabled:opacity-30 disabled:hover:bg-transparent dark:hover:bg-zinc-800"
        >
          <ChevronRightIcon className="h-4 w-4" />
        </button>
        <button
          onClick={onClose}
          aria-label="Đóng"
          className="ml-1 rounded-md p-1.5 hover:bg-zinc-100 dark:hover:bg-zinc-800"
        >
          <XIcon className="h-4 w-4" />
        </button>
      </header>

      {/* ------------------------------------------------ Câu trích đang xem */}
      <div className="border-b border-zinc-200 bg-white px-4 py-3 text-sm dark:border-zinc-800 dark:bg-zinc-950">
        <p className="line-clamp-3 border-l-2 border-yellow-400 pl-3 text-zinc-700 italic dark:text-zinc-300">
          “{citation.quote}”
        </p>
        {!onCitationPage && (
          <button
            onClick={() => setPage(citation.page)}
            className="mt-2 text-xs font-medium text-blue-600 hover:underline dark:text-blue-400"
          >
            Quay lại trang {citation.page}
          </button>
        )}
      </div>

      {/* ------------------------------------------------ Ảnh trang + lớp tô màu */}
      <div className="flex-1 overflow-y-auto p-4">
        {status === "error" ? (
          <p className="text-sm text-red-600">
            Không tải được trang. Nếu tài liệu được upload trước khi có tính năng này, hãy upload lại.
          </p>
        ) : (
          <div
            className={`relative mx-auto w-full max-w-3xl bg-white shadow-sm ring-1 ring-zinc-200 dark:ring-zinc-700 ${
              status === "loading" ? "min-h-64" : ""
            }`}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              key={page}
              src={pageImageUrl(doc.doc_id, page)}
              alt={`Trang ${page}`}
              className="block w-full"
              onLoad={() => setLoadedPage(page)}
              onError={() => setFailedPage(page)}
            />
            {status === "ready" &&
              showMarks &&
              citation.rects.map(([x0, y0, x1, y1], i) => (
                <div
                  key={i}
                  ref={i === 0 ? firstMarkRef : undefined}
                  className="pointer-events-none absolute rounded-sm bg-yellow-300/40 ring-1 ring-yellow-500/60"
                  style={{
                    left: `${x0 * 100}%`,
                    top: `${y0 * 100}%`,
                    width: `${(x1 - x0) * 100}%`,
                    height: `${(y1 - y0) * 100}%`,
                  }}
                />
              ))}
            {status === "loading" && (
              <div className="absolute inset-0 flex items-center justify-center bg-white dark:bg-zinc-900">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-300 border-t-blue-600" />
              </div>
            )}
          </div>
        )}

        {onCitationPage && citation.rects.length === 0 && status === "ready" && (
          <p className="mt-3 text-xs text-zinc-500">
            Không xác định được vị trí chính xác của câu trích trên trang này.
          </p>
        )}
      </div>
    </aside>
  );
}
