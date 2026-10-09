"""Kiểm thử tải: nhiều người hỏi cùng lúc qua API tích hợp /api/v1/chat.

Mỗi "người dùng ảo" gửi 1 câu hỏi thật (gọi LLM thật), đo thời gian tới khi nhận câu trả lời.
Tăng dần số người cùng lúc để thấy hệ thống chịu được tới đâu.

Cách chạy (trong backend/, đã activate .venv; cần 1 API key và 1 doc_id của key đó):
    python -m tools.load_test --url http://127.0.0.1:8000 --key dsk_xxx --doc <doc_id> --levels 1 2 4 8

Đọc kết quả:
    p95  : 95% câu hỏi xong trong khoảng thời gian này (quan trọng hơn trung bình)
    lỗi  : số request thất bại (timeout, 5xx...)
    câu/phút : thông lượng thực tế ở mức tải đó
"""
import argparse
import asyncio
import statistics
import time

import httpx

QUESTIONS = [
    "Tài liệu này nói về chủ đề gì?",
    "Hàm sigmoid còn được gọi là gì?",
    "Mục đích của kiểm định chéo là gì?",
    "Tài liệu gồm những phần chính nào?",
]


async def one_user(client: httpx.AsyncClient, url: str, key: str, doc: str, i: int) -> tuple[float, str | None]:
    t = time.perf_counter()
    try:
        r = await client.post(
            f"{url}/api/v1/chat",
            headers={"X-API-Key": key},
            json={"doc_id": doc, "question": QUESTIONS[i % len(QUESTIONS)], "user_ref": f"loadtest-{i}"},
        )
        err = None if r.status_code == 200 else f"HTTP {r.status_code}"
    except httpx.HTTPError as e:
        err = type(e).__name__
    return time.perf_counter() - t, err


async def run_level(url: str, key: str, doc: str, users: int, timeout: float) -> None:
    async with httpx.AsyncClient(timeout=timeout) as client:
        t = time.perf_counter()
        results = await asyncio.gather(*(one_user(client, url, key, doc, i) for i in range(users)))
        wall = time.perf_counter() - t
    times = sorted(d for d, e in results if e is None)
    errors = [e for _, e in results if e is not None]
    if times:
        p95 = times[min(len(times) - 1, int(round(0.95 * len(times))) - 1)]
        print(
            f"{users:>4} người | TB {statistics.mean(times):6.1f}s | p95 {p95:6.1f}s | "
            f"chậm nhất {times[-1]:6.1f}s | lỗi {len(errors):>3} | {60 * len(times) / wall:5.1f} câu/phút"
        )
    else:
        print(f"{users:>4} người | tất cả lỗi: {sorted(set(errors))}")
    if errors:
        print(f"       loại lỗi: {sorted(set(errors))}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--key", required=True, help="API key (python -m app.cli create-api-key loadtest)")
    ap.add_argument("--doc", required=True, help="doc_id thuộc API key đó")
    ap.add_argument("--levels", type=int, nargs="+", default=[1, 2, 4, 8])
    ap.add_argument("--timeout", type=float, default=300)
    args = ap.parse_args()
    print(f"Kiểm thử {args.url}, tài liệu {args.doc}")
    for n in args.levels:
        asyncio.run(run_level(args.url.rstrip("/"), args.key, args.doc, n, args.timeout))


if __name__ == "__main__":
    main()
