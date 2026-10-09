"""Kiểm tra nhanh locate.py: tìm câu trích trên trang và xuất ảnh có tô màu để xem bằng mắt.

Cách chạy (trong backend/, đã activate .venv):
    python -m tools.check_locate sample.pdf 3 "Hàm sigmoid g, còn được biết đến như là hàm logistic"
"""
import sys

import pymupdf

from app import locate

pdf_path, page_no, quote = sys.argv[1], int(sys.argv[2]), sys.argv[3]

result = locate.locate_quote(pdf_path, quote, page_no, page_no)
print("Kết quả:", result)

if result:
    with pymupdf.open(pdf_path) as doc:
        page = doc[result["page"] - 1]
        w, h = page.rect.width, page.rect.height
        for x0, y0, x1, y1 in result["rects"]:
            page.draw_rect(
                pymupdf.Rect(x0 * w, y0 * h, x1 * w, y1 * h),
                color=None, fill=(1, 0.85, 0), fill_opacity=0.4,
            )
        page.get_pixmap(dpi=110).save("locate_test.png")
    print("Đã lưu locate_test.png — mở ra xem vùng tô vàng có đúng câu trích không.")
