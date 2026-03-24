"""
Agentic RAG 공통 유틸리티

작동 방식:
  retrieve → grade_documents → rewrite → retrieve (loop)

  - grade_documents : 문서 관련성 평가 (yes/no)
  - rewrite_query   : 관련 문서 부족 시 쿼리 재작성
  - agentic_retrieve: 검색 → 평가 → 재작성 루프 (에이전트별 retrieve 노드에서 호출)
"""

import os
from typing import List, Optional, Tuple

from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

DEFAULT_CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
DEFAULT_HF_EMBEDDING_MODEL = os.getenv("HF_EMBEDDING_MODEL", "BAAI/bge-m3")

# ────────────────────────────────────────────
# Pydantic 스키마
# ────────────────────────────────────────────

class GradeDocuments(BaseModel):
    """검색된 문서의 관련성을 평가하는 이진 점수"""
    binary_score: str = Field(
        description="문서가 질문과 관련이 있으면 'yes', 없으면 'no'"
    )


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
            embedding_function=HuggingFaceEmbeddings(model_name=DEFAULT_HF_EMBEDDING_MODEL),
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


# ────────────────────────────────────────────
# 관련성 평가 (grade_documents)
# ────────────────────────────────────────────

_GRADE_PROMPT = PromptTemplate(
    template="""당신은 검색된 문서의 관련성을 평가하는 전문가입니다.

검색된 문서:
{context}

사용자 질문/검색 쿼리:
{question}

문서가 질문과 키워드 또는 의미적으로 관련이 있으면 'yes', 없으면 'no'를 반환하세요.""",
    input_variables=["context", "question"],
)


def grade_documents(docs: List[str], query: str, llm: ChatOpenAI) -> List[str]:
    """
    검색된 문서 중 쿼리와 관련 있는 것만 필터링합니다.

    Args:
        docs  : 검색된 문서 목록
        query : 평가 기준이 되는 쿼리
        llm   : ChatOpenAI 인스턴스

    Returns:
        관련 있는 문서 목록
    """
    llm_grader = llm.with_structured_output(GradeDocuments)
    chain = _GRADE_PROMPT | llm_grader

    relevant = []
    for doc in docs:
        result: GradeDocuments = chain.invoke({"question": query, "context": doc})
        if result.binary_score == "yes":
            relevant.append(doc)

    return relevant


# ────────────────────────────────────────────
# 쿼리 재작성 (rewrite_query)
# ────────────────────────────────────────────

_REWRITE_PROMPT = PromptTemplate(
    template="""당신은 검색 쿼리 최적화 전문가입니다.

아래 쿼리로 검색했지만 관련 문서를 찾지 못했습니다.
쿼리의 의미와 의도를 보존하면서 더 좋은 검색 결과를 얻을 수 있도록 쿼리를 개선하세요.

원본 쿼리:
{query}

개선된 검색 쿼리 (한 문장으로):""",
    input_variables=["query"],
)


def rewrite_query(query: str, llm: ChatOpenAI) -> str:
    """
    관련 문서가 없을 때 검색 쿼리를 재작성합니다.

    Args:
        query : 원본 쿼리
        llm   : ChatOpenAI 인스턴스

    Returns:
        개선된 쿼리 문자열
    """
    chain = _REWRITE_PROMPT | llm
    result = chain.invoke({"query": query})
    rewritten = result.content.strip()
    print(f"==== [QUERY REWRITE] ====\n  원본: {query}\n  개선: {rewritten}")
    return rewritten


# ────────────────────────────────────────────
# Agentic RAG 검색 루프 (agentic_retrieve)
# ────────────────────────────────────────────

def agentic_retrieve(
    queries: List[str],
    collection_name: str,
    k: int,
    llm: ChatOpenAI,
    max_rewrites: int = 2,
    persist_directory: str = DEFAULT_CHROMA_PERSIST_DIR,
) -> Tuple[List[str], List[str]]:
    """
    Agentic RAG 패턴 검색 루프.

    각 쿼리에 대해:
      1. Chroma에서 문서 검색
      2. grade_documents로 관련성 평가
      3. 관련 문서 부족 시 rewrite_query 후 재검색 (최대 max_rewrites회)

    Args:
        queries          : 검색 쿼리 목록
        collection_name  : Chroma 컬렉션 이름
        k                : 쿼리당 검색 문서 수
        llm              : ChatOpenAI 인스턴스 (grading/rewriting 공유)
        max_rewrites     : 쿼리 재작성 최대 횟수 (기본 2)
        persist_directory: Chroma 저장 경로

    Returns:
        (relevant_docs, rag_errors)
          - relevant_docs : 관련성 평가를 통과한 문서 목록
          - rag_errors    : 검색 실패 또는 관련 문서 미발견 오류 목록
    """
    all_relevant: List[str] = []
    all_errors: List[str] = []

    for original_query in queries:
        current_query = original_query
        found = False

        for attempt in range(max_rewrites + 1):
            docs, error = _retrieve_from_chroma(
                current_query, collection_name, k, persist_directory
            )

            if error:
                all_errors.append(error)
                break  # Chroma 자체 오류 → 이 쿼리는 포기

            if not docs:
                # 검색 결과 없음 → 재작성 시도
                if attempt < max_rewrites:
                    current_query = rewrite_query(current_query, llm)
                    continue
                else:
                    all_errors.append(
                        f"관련 문서 없음: '{original_query}' (재작성 {max_rewrites}회 시도)"
                    )
                    break

            relevant = grade_documents(docs, current_query, llm)
            print(
                f"==== [GRADE] '{current_query[:40]}...' → "
                f"{len(relevant)}/{len(docs)} 관련 문서 ====",
                flush=True,
            )

            if relevant:
                all_relevant.extend(relevant)
                found = True
                break

            # 관련 문서 없음 → 쿼리 재작성
            if attempt < max_rewrites:
                current_query = rewrite_query(current_query, llm)
            else:
                all_errors.append(
                    f"관련 문서 미발견: '{original_query}' (재작성 {max_rewrites}회 후에도 관련 없음)"
                )

    return all_relevant, all_errors
