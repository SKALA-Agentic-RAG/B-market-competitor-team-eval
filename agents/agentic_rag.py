"""
Agentic RAG 공통 유틸리티

작동 방식:
  retrieve only

  - grade_documents : 임시 비활성화
  - rewrite_query   : 임시 비활성화
  - agentic_retrieve: 쿼리별 1회 Chroma 유사도 검색만 수행
"""

import os
from typing import List, Optional, Tuple

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

DEFAULT_CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
DEFAULT_HF_EMBEDDING_MODEL = os.getenv("HF_EMBEDDING_MODEL", "BAAI/bge-m3")

# 임베딩 모델을 모듈 레벨에서 한 번만 로드
_EMBEDDING_MODEL: Optional[HuggingFaceEmbeddings] = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        _EMBEDDING_MODEL = HuggingFaceEmbeddings(
            model_name=DEFAULT_HF_EMBEDDING_MODEL,
            encode_kwargs={"normalize_embeddings": True},
        )
    return _EMBEDDING_MODEL

def build_collection_name(base: str, domain: str) -> str:
    """`base_domain` 형식 컬렉션명을 중복 없이 생성합니다."""
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


# ────────────────────────────────────────────
# 저수준 Chroma 검색
# ────────────────────────────────────────────

def _retrieve_from_chroma(
    query: str,
    collection_name: str,
    k: int,
    persist_directory: str = DEFAULT_CHROMA_PERSIST_DIR,
) -> Tuple[List[str], Optional[str]]:
    """Chroma 벡터DB에서 문서를 검색합니다."""
    try:
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=_get_embeddings(),
            persist_directory=persist_directory,
        )
        docs = vectorstore.similarity_search(query, k=k)
        return [doc.page_content for doc in docs], None
    except Exception as e:
        error_msg = (
            f"Chroma 검색 실패 | collection={collection_name} | query={query} | error={e}"
        )
        print(error_msg)
        return [], error_msg


def grade_documents(docs: List[str], query: str, llm: ChatOpenAI) -> List[str]:
    """
    임시 비활성화된 관련성 평가 훅입니다.

    Args:
        docs  : 검색된 문서 목록
        query : 평가 기준이 되는 쿼리
        llm   : ChatOpenAI 인스턴스 (미사용)

    Returns:
        원본 문서 목록
    """
    return docs


def rewrite_query(query: str, llm: ChatOpenAI) -> str:
    """
    임시 비활성화된 쿼리 재작성 훅입니다.

    Args:
        query : 원본 쿼리
        llm   : ChatOpenAI 인스턴스 (미사용)

    Returns:
        원본 쿼리 문자열
    """
    return query


# ────────────────────────────────────────────
# Agentic RAG 검색 루프 (agentic_retrieve)
# ────────────────────────────────────────────

def agentic_retrieve(
    queries: List[str],
    collection_name: str,
    k: int,
    llm: ChatOpenAI,
    max_rewrites: int = 0,
    persist_directory: str = DEFAULT_CHROMA_PERSIST_DIR,
) -> Tuple[List[str], List[str]]:
    """
    RAG 검색 루프.

    각 쿼리에 대해 Chroma에서 문서를 검색하고 바로 반환합니다.
    현재는 검색 → 평가 → 재작성 루프를 비활성화하고,
    grading/rewrite 없이 유사도 검색 결과를 직접 사용합니다.

    Args:
        queries          : 검색 쿼리 목록
        collection_name  : Chroma 컬렉션 이름
        k                : 쿼리당 검색 문서 수
        llm              : ChatOpenAI 인스턴스 (미사용, 호환성 유지)
        max_rewrites     : 미사용 (호환성 유지)
        persist_directory: Chroma 저장 경로

    Returns:
        (docs, rag_errors)
    """
    all_docs: List[str] = []
    all_errors: List[str] = []

    for query in queries:
        docs, error = _retrieve_from_chroma(query, collection_name, k, persist_directory)
        if error:
            all_errors.append(error)
        else:
            all_docs.extend(docs)

    return all_docs, all_errors
