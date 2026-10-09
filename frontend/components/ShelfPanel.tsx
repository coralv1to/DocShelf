"use client";

import type { DocInfo, User } from "@/lib/api";
import { FileIcon, ShelfIcon, TrashIcon } from "./icons";
import UploadPanel from "./UploadPanel";

type Props = {
  user: User;
  docs: DocInfo[];
  loading: boolean;
  onOpen: (doc: DocInfo) => void;
  onUploaded: (doc: DocInfo) => void;
  onDelete: (doc: DocInfo) => void;
};

function formatDate(iso?: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

/** Màn hình chính khi chưa chọn tài liệu: toàn bộ kệ dạng lưới thẻ. */
export default function ShelfPanel({ user, docs, loading, onOpen, onUploaded, onDelete }: Props) {
  const isAdmin = user.role === "admin";

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10">
        <header className="mb-6">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Kệ tài liệu</h1>
          <p className="mt-1 text-zinc-500">
            Chọn một tài liệu để hỏi đáp. Câu trả lời chỉ dựa trên nội dung tài liệu đó, kèm trích dẫn và vị trí trang.
          </p>
        </header>

        {isAdmin && (
          <div className="mb-8">
            <UploadPanel onUploaded={onUploaded} />
          </div>
        )}

        {loading ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-28 animate-pulse rounded-xl bg-zinc-100 dark:bg-zinc-900" />
            ))}
          </div>
        ) : docs.length === 0 ? (
          <div className="flex flex-col items-center rounded-2xl border border-zinc-200 px-6 py-14 text-center dark:border-zinc-800">
            <ShelfIcon className="mb-3 h-8 w-8 text-zinc-400" />
            <p className="font-medium">Kệ còn trống</p>
            <p className="mt-1 text-sm text-zinc-500">
              {isAdmin ? "Thêm file PDF đầu tiên ở ô phía trên." : "Chưa có tài liệu nào. Liên hệ quản trị viên để thêm tài liệu."}
            </p>
          </div>
        ) : (
          <>
            <div className="mb-3 text-xs font-medium tracking-wide text-zinc-500 uppercase">{docs.length} tài liệu</div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {docs.map((d) => (
                <div
                  key={d.doc_id}
                  className="group relative rounded-xl border border-zinc-200 bg-white transition-colors hover:border-zinc-300 hover:bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950 dark:hover:border-zinc-700 dark:hover:bg-zinc-900"
                >
                  <button onClick={() => onOpen(d)} className="block w-full p-4 text-left">
                    <div className="flex items-start gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-red-50 text-red-600 dark:bg-red-950/40 dark:text-red-400">
                        <FileIcon className="h-4 w-4" />
                      </div>
                      <div className="min-w-0 flex-1 pr-6">
                        <div className="line-clamp-2 font-medium leading-snug" title={d.title}>
                          {d.title}
                        </div>
                        <div className="mt-1 text-xs text-zinc-500">
                          {d.num_pages} trang · {d.num_chunks} đoạn
                        </div>
                      </div>
                    </div>
                    {(d.uploaded_by || d.created_at) && (
                      <div className="mt-3 truncate text-xs text-zinc-400">
                        {d.uploaded_by && <>Thêm bởi {d.uploaded_by}</>}
                        {d.uploaded_by && d.created_at && " · "}
                        {formatDate(d.created_at)}
                      </div>
                    )}
                  </button>
                  {isAdmin && (
                    <button
                      onClick={() => onDelete(d)}
                      title="Xóa tài liệu"
                      aria-label={`Xóa ${d.title}`}
                      className="absolute top-3 right-3 rounded-md p-1.5 text-zinc-400 hover:bg-red-50 sm:opacity-0 sm:group-hover:opacity-100 hover:text-red-600 focus:opacity-100 dark:hover:bg-red-950/40"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
