"""
스타트업 탐색 에이전트 (Startup Exploration Agent)
- Chroma 벡터DB에서 로보틱스 투자 리포트(CB Insights, KOTRA 등) 검색
- 후보 스타트업 리스트 추출 (LLM 구조화 출력)
- 각 후보의 기본 정보(창업연도, 투자 현황, 제품군) 수집
- GlobalEvaluationState.pending_startups / startup_info_map 업데이트
"""

import os
from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from agents.agentic_rag import agentic_retrieve, build_collection_name


# ────────────────────────────────────────────
# State (탐색 에이전트 전용 — AgentInputState 미상속: startup_name이 없는 단계)
# ────────────────────────────────────────────

class ExplorationState(TypedDict):
    target_domain: str
    top_k_candidates: int           # 최종 선정할 후보 수
    max_documents: int              # RAG 검색 문서 수
    retrieved_docs: List[str]       # Chroma에서 가져온 원문
    rag_errors: List[str]           # RAG 검색 실패 내역
    evidence_available: bool        # 실제 근거 문서 확보 여부
    raw_candidates: List[Dict[str, Any]]    # 1차 LLM 추출 결과
    startup_candidates: List[Dict[str, Any]]  # 최종 후보 (기본 정보 포함)
    messages: Annotated[list, add_messages]


# ────────────────────────────────────────────
# Pydantic 출력 스키마
# ────────────────────────────────────────────

class StartupCandidate(BaseModel):
    """개별 스타트업 후보"""
    name: str = Field(..., description="스타트업 공식 명칭")
    founded_year: Optional[int] = Field(None, description="창업 연도")
    headquarters: Optional[str] = Field(None, description="본사 소재지 (국가/도시)")
    funding_stage: Optional[str] = Field(None, description="투자 단계 (Seed/Series A/B/C/IPO 등)")
    funding_amount: Optional[str] = Field(None, description="총 투자 유치 금액 (단위 포함, 예: $120M)")
    product_categories: List[str] = Field(default_factory=list, description="주요 제품군 (예: 협동로봇, 자율주행, 드론)")
    key_technology: Optional[str] = Field(None, description="핵심 기술 키워드")
    description: str = Field(..., description="스타트업 한 줄 소개")
    source: str = Field(..., description="정보 출처 (예: CB Insights 2024, KOTRA 로보틱스 리포트)")


class StartupCandidateList(BaseModel):
    """후보 스타트업 목록"""
    candidates: List[StartupCandidate] = Field(..., description="추출된 후보 스타트업 목록")
    selection_rationale: str = Field(..., description="후보 선정 기준 및 근거")


class RankedCandidateList(BaseModel):
    """우선순위 정렬된 최종 후보 목록"""
    ranked_names: List[str] = Field(..., description="투자 매력도 순으로 정렬된 스타트업 이름 목록")
    ranking_rationale: str = Field(..., description="순위 산정 근거")


# ────────────────────────────────────────────
# LLM 초기화
# ────────────────────────────────────────────

llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
    temperature=0,
    api_key=os.environ.get("OPENAI_API_KEY"),
)

llm_extract = llm.with_structured_output(
    StartupCandidateList, method="function_calling"
)
llm_rank = llm.with_structured_output(
    RankedCandidateList, method="function_calling"
)


# ────────────────────────────────────────────
# 노드 함수
# ────────────────────────────────────────────

def retrieve_reports_node(state: ExplorationState) -> Dict[str, Any]:
    """Chroma에서 투자 리포트 문서를 검색합니다."""
    domain = state["target_domain"]
    k = state.get("max_documents", 10)

    queries = [
        f"{domain} AMR 창고 물류 자동화 스타트업 투자 유치 유니콘 RaaS 차별화",
        f"{domain} 휴머노이드 AI 피킹 로봇 물류 최우수 경쟁 우위 해자",
        f"{domain} 경쟁 구도 포지셔닝 기술 독창성 Series 투자 매력 최고",
    ]

    docs, rag_errors = agentic_retrieve(
        queries=queries,
        collection_name=build_collection_name("investment_reports", domain),
        k=k,
        llm=llm,
    )

    evidence_available = bool(docs)
    status_message = (
        f"투자 리포트 {len(docs)}건 검색 완료 (관련성 평가 통과)"
        if evidence_available
        else "투자 리포트 검색 실패 또는 관련 문서 없음"
    )

    return {
        "retrieved_docs": docs,
        "rag_errors": rag_errors,
        "evidence_available": evidence_available,
        "messages": [{"role": "system", "content": status_message}],
    }


def extract_candidates_node(state: ExplorationState) -> Dict[str, Any]:
    """검색된 리포트에서 후보 스타트업을 추출합니다."""
    domain = state["target_domain"]
    docs = state.get("retrieved_docs", [])
    top_k = state.get("top_k_candidates", 5)

    if not docs:
        return {
            "raw_candidates": [],
            "messages": [{"role": "assistant", "content": "근거 문서가 없어 후보 스타트업 추출을 중단했습니다."}],
        }

    docs_text = "\n\n".join(docs[:15])  # 상위 15건

    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 로보틱스 스타트업 투자 리서치 전문가입니다.
목표는 제공된 투자 리포트에서 최종적으로 단 하나의 최고 투자 대상을 선정하기 위한 후보를 추출하는 것입니다.

추출 기준 (엄격하게 적용):
1. {domain} 도메인에 해당하는 스타트업
2. 기술적 독창성과 경쟁 우위가 뚜렷한 기업
3. 실질적인 투자 유치 이력이 있는 기업 (Seed 이상)
4. 창업 연도, 투자 단계, 제품군 정보가 확인 가능한 기업

최대 {top_k}개 이상의 후보를 추출하세요 (이후 최고 투자 대상 1개 선정 단계에서 추린다)."""),
        ("human", """도메인: {domain}

투자 리포트:
{docs}

위 리포트에서 {domain} 분야에서 가장 투자 가치가 높을 것으로 보이는 스타트업 후보를 추출하세요."""),
    ])

    result: StartupCandidateList = (prompt | llm_extract).invoke({
        "domain": domain,
        "top_k": top_k,
        "docs": docs_text,
    })

    raw_candidates = [c.model_dump() for c in result.candidates]

    return {
        "raw_candidates": raw_candidates,
        "messages": [{"role": "assistant", "content": f"후보 {len(raw_candidates)}개 추출 완료: {[c['name'] for c in raw_candidates]}"}],
    }


def rank_and_select_node(state: ExplorationState) -> Dict[str, Any]:
    """추출된 후보를 투자 매력도 순으로 정렬하고 top_k를 선정합니다."""
    domain = state["target_domain"]
    raw_candidates = state.get("raw_candidates", [])
    top_k = state.get("top_k_candidates", 5)

    if not raw_candidates:
        return {
            "startup_candidates": [],
            "messages": [{"role": "assistant", "content": "후보 스타트업 없음 — 검색 결과 부족"}],
        }

    candidates_text = "\n".join([
        f"- {c['name']}: {c.get('description', '')} | "
        f"창업 {c.get('founded_year', '미확인')} | "
        f"{c.get('funding_stage', '미확인')} | "
        f"제품군: {', '.join(c.get('product_categories', []))}"
        for c in raw_candidates
    ])

    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 로보틱스 스타트업 투자 분석가입니다.
목표는 후보 중에서 최종적으로 단 하나의 최고 투자 대상을 찾는 것입니다.
아래 후보 목록을 투자 매력도 기준으로 엄격하게 순위를 매기고 상위 {top_k}개를 선정하세요.

순위 기준 (중요도 순):
1. 기술 독창성 및 경쟁사 대비 명확한 차별화
2. 시장 규모 및 성장 가능성
3. 투자 유치 모멘텀 (단계, 금액, 투자자 tier)
4. 팀/창업자 도메인 전문성"""),
        ("human", """도메인: {domain}
선정 수: {top_k}개

후보 목록:
{candidates}

투자 매력도 순위를 매겨 상위 {top_k}개를 선정하세요. 1위 후보는 최종 최고 투자 대상 선정에서 가장 우선 검토됩니다."""),
    ])

    result: RankedCandidateList = (prompt | llm_rank).invoke({
        "domain": domain,
        "top_k": top_k,
        "candidates": candidates_text,
    })

    # 순위 기준으로 raw_candidates 재정렬 + top_k 슬라이싱
    name_to_candidate = {c["name"]: c for c in raw_candidates}
    selected = [
        name_to_candidate[name]
        for name in result.ranked_names[:top_k]
        if name in name_to_candidate
    ]

    # 순위에 없는 이름은 원본에서 순서대로 채움 (LLM이 이름을 살짝 바꾸는 경우 대비)
    if len(selected) < top_k:
        existing_names = {c["name"] for c in selected}
        for c in raw_candidates:
            if c["name"] not in existing_names and len(selected) < top_k:
                selected.append(c)

    return {
        "startup_candidates": selected,
        "messages": [{"role": "assistant", "content": f"최종 선정 {len(selected)}개: {[c['name'] for c in selected]}"}],
    }


# ────────────────────────────────────────────
# 그래프 구성
# ────────────────────────────────────────────

def build_exploration_graph() -> StateGraph:
    graph = StateGraph(ExplorationState)

    graph.add_node("retrieve_reports", retrieve_reports_node)
    graph.add_node("extract_candidates", extract_candidates_node)
    graph.add_node("rank_and_select", rank_and_select_node)

    graph.add_edge(START, "retrieve_reports")
    graph.add_edge("retrieve_reports", "extract_candidates")
    graph.add_edge("extract_candidates", "rank_and_select")
    graph.add_edge("rank_and_select", END)

    return graph.compile()


exploration_graph = build_exploration_graph()


# ────────────────────────────────────────────
# 실행 헬퍼
# ────────────────────────────────────────────

def run_startup_exploration(
    target_domain: str = "robotics",
    top_k_candidates: int = 5,
    max_documents: int = 10,
) -> Dict[str, Any]:
    """
    스타트업 탐색 에이전트를 실행합니다.

    Returns:
        {
            "pending_startups": List[str],              # 후보 스타트업 이름 목록
            "startup_info_map": Dict[str, Dict],        # GlobalEvaluationState.startup_info_map에 할당
        }
    """
    initial_state: ExplorationState = {
        "target_domain": target_domain,
        "top_k_candidates": top_k_candidates,
        "max_documents": max_documents,
        "retrieved_docs": [],
        "rag_errors": [],
        "evidence_available": False,
        "raw_candidates": [],
        "startup_candidates": [],
        "messages": [],
    }

    final_state = exploration_graph.invoke(initial_state)
    candidates = final_state["startup_candidates"]

    return {
        "pending_startups": [c["name"] for c in candidates],
        "startup_info_map": {c["name"]: c for c in candidates},
    }


# ────────────────────────────────────────────
# 실행 예시
# ────────────────────────────────────────────

if __name__ == "__main__":
    result = run_startup_exploration(
        target_domain="robotics",
        top_k_candidates=5,
        max_documents=10,
    )

    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
