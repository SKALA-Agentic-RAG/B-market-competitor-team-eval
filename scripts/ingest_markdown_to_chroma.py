from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Iterable, List

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

def build_collection_name(base: str, domain: str) -> str:
    normalized_base = (base or "").strip()
    normalized_domain = (domain or "").strip()
    if not normalized_base:
        return normalized_domain
    if not normalized_domain:
        return normalized_base
    if normalized_domain == normalized_base:
        return normalized_base
    if normalized_domain.startswith(f"{normalized_base}_"):
        return normalized_domain
    return f"{normalized_base}_{normalized_domain}"


def _chunk_markdown(md_path: Path, chunk_size: int, chunk_overlap: int) -> List[Document]:
    text = md_path.read_text(encoding="utf-8")
    base = Document(
        page_content=text,
        metadata={"source_path": str(md_path), "title": md_path.stem},
    )
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    return splitter.split_documents([base])


def _stable_ids(path: Path, docs: Iterable[Document]) -> List[str]:
    ids: List[str] = []
    for i, d in enumerate(docs):
        key = f"{path.resolve()}::{i}::{d.page_content[:120]}"
        ids.append(hashlib.sha1(key.encode("utf-8")).hexdigest())
    return ids


def ingest_markdown_file(
    md_path: Path,
    collection_name: str,
    persist_directory: Path,
    embedding_model: str,
    chunk_size: int,
    chunk_overlap: int,
) -> int:
    docs = _chunk_markdown(md_path, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if not docs:
        return 0

    embeddings = HuggingFaceEmbeddings(
        model_name=embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(persist_directory),
    )

    ids = _stable_ids(md_path, docs)
    # 중복 적재 방지를 위해 먼저 기존 id를 확인한다.
    existing = set(vectorstore.get(ids=ids, include=[]).get("ids", []))

    new_docs: List[Document] = []
    new_ids: List[str] = []
    for doc, cid in zip(docs, ids):
        if cid in existing:
            continue
        new_docs.append(doc)
        new_ids.append(cid)

    if new_docs:
        vectorstore.add_documents(new_docs, ids=new_ids)
    return len(new_docs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Embed markdown files into Chroma collections")
    parser.add_argument("--domain", default="robotics", help="Target domain suffix for collection naming")
    parser.add_argument("--persist-dir", default="./chroma_db", help="Chroma persist directory")
    parser.add_argument("--embedding-model", default="BAAI/bge-m3", help="HF embedding model name")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--chunk-overlap", type=int, default=150)
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete target collections before ingesting",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    persist_dir = (project_root / args.persist_dir).resolve()
    persist_dir.mkdir(parents=True, exist_ok=True)

    targets = [
        (
            project_root / "document_1_fixed_sources.md",
            build_collection_name("investment_reports", args.domain),
        ),
        (
            project_root / "tech_analysis_knowledge_base_with_sources.md",
            build_collection_name("robotics", args.domain),
        ),
    ]

    embeddings = HuggingFaceEmbeddings(
        model_name=args.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    client_probe = Chroma(
        collection_name="probe",
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )
    client = client_probe._client

    if args.clear:
        for _, collection in targets:
            try:
                client.delete_collection(collection)
                print(f"[clear] deleted collection={collection}")
            except Exception:
                pass

    total_added = 0
    for md_path, collection in targets:
        if not md_path.exists():
            print(f"[skip] missing file: {md_path}")
            continue
        added = ingest_markdown_file(
            md_path=md_path,
            collection_name=collection,
            persist_directory=persist_dir,
            embedding_model=args.embedding_model,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        total_added += added

        probe = Chroma(
            collection_name=collection,
            embedding_function=embeddings,
            persist_directory=str(persist_dir),
        )
        count = probe._collection.count()
        sample = probe._collection.peek(limit=1)
        sample_doc = ""
        if sample.get("documents"):
            sample_doc = str(sample["documents"][0])[:140]
        print(f"[ok] collection={collection} added_now={added} total_count={count}")
        print(f"     sample={sample_doc}")

    print(f"[done] persist_dir={persist_dir} total_added={total_added}")


if __name__ == "__main__":
    main()
