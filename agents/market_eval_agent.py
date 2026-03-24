"""
시장성 평가 에이전트 (Market Evaluation Agent)
- Chroma RAG 기반 시장/수요 문서 검색
- TAM/SAM/SOM, CAGR, 고객 수요 검증 평가
- 수직 시장별 수요와 규제 환경 요약
"""

import os
from typing import Any, Dict, List
from dotenv import load_dotenv

load_dotenv()

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, field_validator

from agents.agentic_rag import agentic_retrieve, build_collection_name
from state import AgentInputState


class MarketEvalState(AgentInputState):
    max_pages_per_document: int
    retrieved_docs: List[str]
    rag_errors: List[str]
    evidence_available: bool
    market_analysis: Dict[str, Any]


class MarketScores(BaseModel):
    tam: float = Field(
        2.0,
        ge=1.0,
        le=5.0,
        description="목표 시장 규모(TAM) 점수 (1=<$100M / 3=$1B 수준 / 5=>$10B)",
    )
    cagr: float = Field(
        2.0,
        ge=1.0,
        le=5.0,
        description="시장 성장률(CAGR) 점수 (1=<5% / 3=10~20% / 5=>30%)",
    )
    demand_validation: float = Field(
        2.0,
        ge=1.0,
        le=5.0,
        description="고객 수요 검증 점수 (1=없음 / 3=파일럿 중 / 5=매출 발생)",
    )


class MarketEvidence(BaseModel):
    claim: str = Field(default="")
    source_title: str = Field(default="")
    url: str = Field(default="")


class MarketAnalysisPayload(BaseModel):
    scores: MarketScores = Field(default_factory=MarketScores)
    tam: str = Field(
        default="",
        description="TAM 추정치 또는 시장 규모 설명 문자열 (예: '$10B+', '약 1조원 규모')",
    )
    sam: str = Field(
        default="",
        description="SAM 추정치 또는 서비스 가능 시장 설명 문자열",
    )
    som: str = Field(
        default="",
        description="SOM 추정치 또는 초기 점유 가능 시장 설명 문자열",
    )
    cagr: str = Field(
        default="",
        description="시장 CAGR 또는 성장성 설명 문자열 (예: '연 18%', '10~20%')",
    )
    target_customers: List[str] = Field(default_factory=list, description="핵심 타깃 고객군")
    vertical_demand: List[str] = Field(
        default_factory=list,
        description="물류·제조·의료 등 수직 시장별 수요 및 도입 신호",
    )
    regulatory_environment: List[str] = Field(
        default_factory=list,
        description="시장 확장에 영향을 주는 규제·표준·인증 환경",
    )
    demand_signals: List[str] = Field(
        default_factory=list,
        description="파일럿, POC, 고객 계약, 매출 등 수요 검증 신호",
    )
    score_rationale: str = Field(default="", description="세부 점수 산정 근거 요약")
    summary: str = Field(default="", description="시장성 평가 요약 (3~5문장)")
    evidence: List[MarketEvidence] = Field(default_factory=list)

    @field_validator("tam", "sam", "som", "cagr", mode="before")
    @classmethod
    def _coerce_market_text_fields(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            return str(value)
        return value


def _unique_docs(*doc_groups: List[str]) -> List[str]:
    seen = set()
    unique_docs: List[str] = []
    for docs in doc_groups:
        for doc in docs:
            normalized = doc.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_docs.append(normalized)
    return unique_docs


def _normalize_market_analysis(
    startup_name: str,
    payload: Dict[str, Any],
    rag_errors: List[str],
    evidence_available: bool,
    source_documents: List[str],
) -> Dict[str, Any]:
    scores = payload.get("scores") or {}
    market_detail = {
        "tam": payload.get("tam", ""),
        "sam": payload.get("sam", ""),
        "som": payload.get("som", ""),
        "cagr": payload.get("cagr", ""),
        "target_customers": payload.get("target_customers", []),
        "vertical_demand": payload.get("vertical_demand", []),
        "regulatory_environment": payload.get("regulatory_environment", []),
        "demand_signals": payload.get("demand_signals", []),
    }

    return {
        "startup_name": startup_name,
        "assessment_status": "completed" if evidence_available else "insufficient_evidence",
        "evidence_available": evidence_available,
        "rag_errors": rag_errors,
        "scores": {
            "tam": float(scores.get("tam", 1.0)),
            "cagr": float(scores.get("cagr", 1.0)),
            "demand_validation": float(scores.get("demand_validation", 1.0)),
        },
        "market_detail": market_detail,
        "tam": market_detail["tam"],
        "sam": market_detail["sam"],
        "som": market_detail["som"],
        "cagr": market_detail["cagr"],
        "target_customers": market_detail["target_customers"],
        "vertical_demand": market_detail["vertical_demand"],
        "regulatory_environment": market_detail["regulatory_environment"],
        "demand_signals": market_detail["demand_signals"],
        "score_rationale": payload.get("score_rationale", ""),
        "summary": payload.get("summary") or f"{startup_name} 시장성 평가 요약",
        "evidence": payload.get("evidence", []),
        "source_documents": source_documents[:8],
    }


def build_insufficient_market_analysis(
    startup_name: str,
    rag_errors: List[str],
) -> Dict[str, Any]:
    return _normalize_market_analysis(
        startup_name=startup_name,
        payload={
            "scores": {"tam": 1.0, "cagr": 1.0, "demand_validation": 1.0},
            "score_rationale": "근거 문서 부족으로 시장성 점수를 산정하지 않았습니다.",
            "summary": (
                "RAG에서 유효한 시장 문서를 충분히 확보하지 못해 TAM, 성장률, "
                "고객 수요 검증을 보수적으로 정리했습니다."
            ),
            "regulatory_environment": ["시장 규제·인증 관련 근거 문서 추가 확보 필요"],
        },
        rag_errors=rag_errors,
        evidence_available=False,
        source_documents=[],
    )


llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
    temperature=0,
    api_key=os.environ.get("OPENAI_API_KEY"),
)

llm_market = llm.with_structured_output(
    MarketAnalysisPayload, method="function_calling"
)


def retrieve_market_docs_node(state: MarketEvalState) -> Dict[str, Any]:
    startup_name = state["startup_name"]
    domain = state.get("target_domain", "robotics")
    k = state.get("max_documents", 5)

    company_queries = [
        f"{startup_name} 고객사 파트너십 매출 계약 파일럿 수요 검증",
        f"{startup_name} 물류 창고 이커머스 제조 시장 도입 ROI",
        f"{startup_name} RaaS 유니콘 시리즈 투자 규모 성장 상용화",
    ]
    company_docs, company_errors = agentic_retrieve(
        queries=company_queries,
        collection_name=build_collection_name("robotics", domain),
        k=k,
        llm=llm,
    )

    report_queries = [
        f"{domain} AMR 물류 자동화 시장 TAM CAGR 성장률 규모",
        f"{domain} 창고 로봇 이커머스 물동량 수요 전망 시장 선도",
        f"{domain} 규제 인증 물류 로봇 도입 장벽 시장 전망 성장",
    ]
    report_docs, report_errors = agentic_retrieve(
        queries=report_queries,
        collection_name=build_collection_name("investment_reports", domain),
        k=k,
        llm=llm,
    )

    docs = _unique_docs(company_docs, report_docs)
    rag_errors = company_errors + report_errors
    evidence_available = bool(docs)

    status_message = (
        f"시장성 문서 {len(docs)}건 검색 완료 (관련성 평가 통과)"
        if evidence_available
        else "시장성 문서 검색 실패 또는 관련 문서 없음"
    )

    return {
        "retrieved_docs": docs,
        "rag_errors": rag_errors,
        "evidence_available": evidence_available,
        "messages": [{"role": "system", "content": status_message}],
    }


def analyze_market_node(state: MarketEvalState) -> Dict[str, Any]:
    startup_name = state["startup_name"]
    startup_info = state.get("startup_info", {})
    docs = state.get("retrieved_docs", [])
    rag_errors = state.get("rag_errors", [])

    if not docs:
        return {
            "market_analysis": build_insufficient_market_analysis(startup_name, rag_errors),
            "messages": [
                {
                    "role": "assistant",
                    "content": "근거 문서가 부족해 시장성 평가를 보수적으로 정리했습니다.",
                }
            ],
        }

    docs_text = "\n\n".join(docs[:12])
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """당신은 로보틱스/딥테크 스타트업 전문 투자 심사역입니다.
목표는 이 스타트업이 시장성 측면에서 최고 투자 대상인지 판단하는 것입니다.
제공된 문서만 근거로 시장성 평가를 수행하세요. 문서에 없는 수치나 고객 실적은 추측하지 마세요.

반드시 아래 항목을 포함하세요.
- TAM/SAM/SOM 추정 또는 추정 가능한 범위 설명
- 시장 성장률(CAGR)
- 물류·제조·의료 등 수직 시장별 수요
- 시장 진입에 영향을 주는 규제/인증 환경
- 파일럿, 계약, 매출 등 고객 수요 검증 신호

점수 기준:
- scores.tam: 1=<$100M / 3=$1B 수준 / 5=>$10B
- scores.cagr: 1=<5% / 3=10~20% / 5=>30%
- demand_validation: 1=없음 / 3=파일럿 중 / 5=매출 발생

이 기업이 가장 큰 시장 기회를 선점하고 있는지 중점적으로 평가하세요.
`scores.tam`, `scores.cagr`, `scores.demand_validation`만 1~5 숫자로 반환하세요.
루트의 `tam`, `sam`, `som`, `cagr` 필드는 숫자 점수가 아니라 설명 문자열이어야 합니다.
근거는 score_rationale에 간단히 정리하세요.""",
            ),
            (
                "human",
                """스타트업: {startup_name}
도메인: {domain}
스타트업 정보:
{startup_info}

관련 문서:
{docs}

위 정보를 바탕으로 시장성 평가를 수행하세요.""",
            ),
        ]
    )

    result: MarketAnalysisPayload = (prompt | llm_market).invoke(
        {
            "startup_name": startup_name,
            "domain": state.get("target_domain", "robotics"),
            "startup_info": str(startup_info),
            "docs": docs_text,
        }
    )

    market_analysis = _normalize_market_analysis(
        startup_name=startup_name,
        payload=result.model_dump(),
        rag_errors=rag_errors,
        evidence_available=True,
        source_documents=docs,
    )

    return {
        "market_analysis": market_analysis,
        "messages": [{"role": "assistant", "content": "시장성 평가 완료"}],
    }


def build_market_eval_graph() -> StateGraph:
    graph = StateGraph(MarketEvalState)

    graph.add_node("retrieve_market_docs", retrieve_market_docs_node)
    graph.add_node("analyze_market", analyze_market_node)

    graph.add_edge(START, "retrieve_market_docs")
    graph.add_edge("retrieve_market_docs", "analyze_market")
    graph.add_edge("analyze_market", END)

    return graph.compile()


market_eval_graph = build_market_eval_graph()


def run_market_assessment(
    startup_name: str,
    startup_info: Dict[str, Any],
    target_domain: str = "robotics",
    max_documents: int = 5,
    max_pages_per_document: int = 10,
) -> Dict[str, Any]:
    initial_state: MarketEvalState = {
        "startup_name": startup_name,
        "startup_info": startup_info,
        "target_domain": target_domain,
        "max_documents": max_documents,
        "max_pages_per_document": max_pages_per_document,
        "retrieved_docs": [],
        "rag_errors": [],
        "evidence_available": False,
        "market_analysis": {},
        "messages": [],
    }

    final_state = market_eval_graph.invoke(initial_state)
    return final_state["market_analysis"]


def run_market_eval(
    startup_name: str,
    startup_info: Dict[str, Any],
    target_domain: str = "robotics",
    max_documents: int = 5,
    max_pages_per_document: int = 10,
) -> Dict[str, Any]:
    return run_market_assessment(
        startup_name=startup_name,
        startup_info=startup_info,
        target_domain=target_domain,
        max_documents=max_documents,
        max_pages_per_document=max_pages_per_document,
    )
