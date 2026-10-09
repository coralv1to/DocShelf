from app import pdf_parser, chunker, config

lines = pdf_parser.parse_pdf("sample.pdf")
print("Số dòng:", len(lines))

chunks = chunker.chunk_document(lines, "sample", config.CHUNK_WORDS, config.CHUNK_OVERLAP_WORDS)
print("Số đoạn:", len(chunks))
for c in chunks[:5]:
    print("=" * 60)
    print(f"{c.id} | trang {c.page_start}-{c.page_end} | {c.header}")
    print(c.text[:300])