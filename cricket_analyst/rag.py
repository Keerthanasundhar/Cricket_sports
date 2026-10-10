"""RAG over rules documents (ICC playing conditions, IPL rules, fantasy scoring, match reports).
  python -m cricket_analyst.rag --ingest      # (re)index knowledge_base/*.md|*.txt
"""
import argparse
import re

from .config import CHROMA_DIR, KB_DIR


def _collection():
    import chromadb
    return chromadb.PersistentClient(path=str(CHROMA_DIR)).get_or_create_collection("cricket_rules")


def _chunks(text, max_chars=1200):
    for section in re.split(r"\n(?=## )", text):
        title = (re.match(r"#+ (.*)", section) or [None, ""])[1]
        buf = ""
        for para in section.split("\n\n"):
            if len(buf) + len(para) > max_chars and buf:
                yield title, buf.strip(); buf = ""
            buf += para + "\n\n"
        if buf.strip():
            yield title, buf.strip()


def ingest():
    col, docs, ids, metas = _collection(), [], [], []
    for f in sorted([*KB_DIR.glob("*.md"), *KB_DIR.glob("*.txt")]):
        for i, (title, chunk) in enumerate(_chunks(f.read_text(encoding="utf-8"))):
            docs.append(chunk); ids.append(f"{f.stem}-{i}")
            metas.append({"source": f.name, "section": title})
    if docs:
        col.upsert(documents=docs, ids=ids, metadatas=metas)
    return len(docs)


def retrieve(query, k=4):
    col = _collection()
    if col.count() == 0:
        ingest()
    r = col.query(query_texts=[query], n_results=k)
    return [{"id": i, "text": d, "source": m["source"], "section": m["section"], "distance": dist}
            for i, d, m, dist in zip(r["ids"][0], r["documents"][0], r["metadatas"][0], r["distances"][0])]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--ingest", action="store_true")
    if ap.parse_args().ingest:
        print("Indexed chunks:", ingest())
