"""
경쟁사 분석 에이전트 (Competitor Analysis Agent)
- Chroma RAG 기반 경쟁사/대체재 문서 검색
- 기술·팀·리스크 분석 결과를 참고해 경쟁 구도 평가
- 경쟁사 비교 결과를 competitor_analysis로 정리
"""

import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agents.agentic_rag import agentic_retrieve, build_collection_name
from state import AgentInputState


class CompetitorAnalysisState(AgentInputState):
    tech_analysis: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    team_assessment: Dict[str, Any]
    max_pages_per_document: int
    retrieved_docs: List[str]
    rag_errors: List[str]
    evidence_available: bool
    competitor_analysis: Dict[str, Any]


class StrictSchemaModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CompetitorScores(StrictSchemaModel):
    differentiation: float = Field(
        2.0, ge=1.0, le=5.0, description="경쟁사 대비 제품·기술·비즈니스 모델 차별화"
    )
    moat: float = Field(
        2.0, ge=1.0, le=5.0, description="진입장벽(특허·데이터·고객 lock-in 등)"
    )


class CompetitorProfile(StrictSchemaModel):
    name: str = Field(default="")
    segment: str = Field(default="")
    tech_spec: str = Field(default="")
    price_range: str = Field(default="비공개")
    customers: str = Field(default="")
    partnerships: str = Field(default="")
    region: str = Field(default="")
    differentiator: str = Field(default="")


class CompetitorEvidence(StrictSchemaModel):
    claim: str = Field(default="")
    source_title: str = Field(default="")
    url: str = Field(default="")


class ComparisonTable(StrictSchemaModel):
    columns: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)

    @field_validator("columns", mode="before")
    @classmethod
    def _coerce_columns(cls, value: Any) -> List[str]:
        if not value:
            return []
        return [str(item) for item in value]

    @field_validator("rows", mode="before")
    @classmethod
    def _coerce_rows(cls, value: Any) -> List[List[str]]:
        if not value:
            return []
        normalized_rows: List[List[str]] = []
        for row in value:
            if isinstance(row, list):
                normalized_rows.append([str(item) for item in row])
            else:
                normalized_rows.append([str(row)])
        return normalized_rows


class CompetitorAnalysisPayload(StrictSchemaModel):
    scores: CompetitorScores = Field(default_factory=CompetitorScores)
    target_segment: str = Field(default="")
    comparison_table: ComparisonTable = Field(default_factory=ComparisonTable)
    competitors: List[CompetitorProfile] = Field(default_factory=list)
    our_advantages: List[str] = Field(default_factory=list)
    our_disadvantages: List[str] = Field(default_factory=list)
    summary: str = Field(default="")
    evidence: List[CompetitorEvidence] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_flat_payload(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        normalized = dict(value)

        if "scores" not in normalized:
            scores: Dict[str, Any] = {}
            if "differentiation" in normalized:
                scores["differentiation"] = normalized.pop("differentiation")
            if "moat" in normalized:
                scores["moat"] = normalized.pop("moat")
            if scores:
                normalized["scores"] = scores

        if "comparison_table" not in normalized:
            columns = normalized.pop("columns", None)
            rows = normalized.pop("rows", None)
            if columns is not None or rows is not None:
                normalized["comparison_table"] = {
                    "columns": columns or [],
                    "rows": rows or [],
                }

        return normalized


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


def _normalize_competitor_analysis(
    startup_name: str,
    payload: Dict[str, Any],
    rag_errors: List[str],
    evidence_available: bool,
) -> Dict[str, Any]:
    scores = payload.get("scores") or {}
    comparison_table = payload.get("comparison_table") or {}

    return {
        "startup_name": startup_name,
        "assessment_status": "completed" if evidence_available else "insufficient_evidence",
        "evidence_available": evidence_available,
        "rag_errors": rag_errors,
        "scores": {
            "differentiation": float(scores.get("differentiation", 2.0)),
            "moat": float(scores.get("moat", 2.0)),
        },
        "target_segment": payload.get("target_segment", ""),
        "comparison_table": {
            "columns": comparison_table.get("columns", []),
            "rows": comparison_table.get("rows", []),
        },
        "competitors": payload.get("competitors", []),
        "our_advantages": payload.get("our_advantages", []),
        "our_disadvantages": payload.get("our_disadvantages", []),
        "summary": payload.get("summary") or f"{startup_name} 경쟁사 분석 요약",
        "evidence": payload.get("evidence", []),
    }


def build_insufficient_competitor_analysis(
    startup_name: str,
    rag_errors: List[str],
) -> Dict[str, Any]:
    return _normalize_competitor_analysis(
        startup_name=startup_name,
        payload={
            "summary": (
                "RAG에서 유효한 경쟁사 문서를 충분히 확보하지 못해 경쟁 구도를 보수적으로 "
                "정리했습니다."
            ),
            "our_disadvantages": [
                "경쟁 지형을 직접 비교할 근거 문서 부족",
                "가격·고객·포지셔닝 정보 추가 확보 필요",
            ],
        },
        rag_errors=rag_errors,
        evidence_available=False,
    )


llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
    temperature=0,
    api_key=os.environ.get("OPENAI_API_KEY"),
)

llm_competitor = llm.with_structured_output(
    CompetitorAnalysisPayload, method="function_calling"
)


def retrieve_competitor_docs_node(state: CompetitorAnalysisState) -> Dict[str, Any]:
    startup_name = state["startup_name"]
    domain = state.get("target_domain", "robotics")
    k = state.get("max_documents", 5)

    company_queries = [
        f"{startup_name} 경쟁사 대비 차별화 기술 우위 해자 AMR 물류",
        f"{startup_name} 고객사 파트너십 포지셔닝 시장 선점 투자 유치",
        f"{startup_name} RaaS 상용화 TRL 기술 완성도 경쟁력 독창성",
    ]
    company_docs, company_errors = agentic_retrieve(
        queries=company_queries,
        collection_name=build_collection_name("robotics", domain),
        k=k,
        llm=llm,
    )

    report_queries = [
        f"{domain} AMR 창고 자동화 경쟁 구도 차별화 포지셔닝 최우수",
        f"{startup_name} 시장 세그먼트 독보적 포지션 해자 비교 분석",
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
        f"경쟁사 문서 {len(docs)}건 검색 완료 (관련성 평가 통과)"
        if evidence_available
        else "경쟁사 문서 검색 실패 또는 관련 문서 없음"
    )

    return {
        "retrieved_docs": docs,
        "rag_errors": rag_errors,
        "evidence_available": evidence_available,
        "messages": [{"role": "system", "content": status_message}],
    }


def analyze_competitors_node(state: CompetitorAnalysisState) -> Dict[str, Any]:
    startup_name = state["startup_name"]
    startup_info = state.get("startup_info", {})
    tech_analysis = state.get("tech_analysis", {})
    risk_assessment = state.get("risk_assessment", {})
    team_assessment = state.get("team_assessment", {})
    docs = state.get("retrieved_docs", [])
    rag_errors = state.get("rag_errors", [])

    if not docs:
        return {
            "competitor_analysis": build_insufficient_competitor_analysis(
                startup_name, rag_errors
            ),
            "messages": [
                {
                    "role": "assistant",
                    "content": "근거 문서가 부족해 경쟁사 분석을 보수적으로 정리했습니다.",
                }
            ],
        }

    docs_text = "\n\n".join(docs[:12])
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """당신은 로보틱스·자동화 산업의 경쟁 전략 및 투자 분석 전문가입니다.
목표는 이 스타트업이 경쟁 우위 측면에서 최고 투자 대상인지 판단하는 것입니다.
대상 스타트업과 동일 세그먼트에서 실제로 경쟁하거나 대체될 수 있는 기업을 중심으로
비교 분석을 수행하세요.

비교표에는 가능하면 다음 축을 포함하세요.
- 핵심 제품/기술 스택
- 목표 고객/산업
- 상용화 단계
- 가격·비즈니스 모델
- 주요 고객사/파트너십
- 지역/주력 시장

점수 기준:
- scores.differentiation: 1=범용·모방 / 3=일부 차별화 / 5=명확한 우위
- scores.moat: 1=낮음 / 3=단일 요인 / 5=복합 해자

이 기업이 경쟁사 대비 지속 가능한 해자를 보유하고 있는지 중점적으로 평가하세요.
문서에 없는 세부 내용은 추측하지 말고 보수적으로 정리하세요.
비교표는 루트의 columns/rows가 아니라 comparison_table.columns / comparison_table.rows에 넣으세요.""",
            ),
            (
                "human",
                """스타트업: {startup_name}
도메인: {domain}
스타트업 정보:
{startup_info}

기술 분석 요약:
{tech_summary}

리스크 등급:
{risk_grade}

팀 평가 요약:
{team_summary}

관련 문서:
{docs}

위 정보를 바탕으로 경쟁 구도를 분석하세요.""",
            ),
        ]
    )

    result: CompetitorAnalysisPayload = (prompt | llm_competitor).invoke(
        {
            "startup_name": startup_name,
            "domain": state.get("target_domain", "robotics"),
            "startup_info": str(startup_info),
            "tech_summary": tech_analysis.get("summary", ""),
            "risk_grade": risk_assessment.get("overall_risk_grade", "미확인"),
            "team_summary": team_assessment.get("summary", ""),
            "docs": docs_text,
        }
    )

    competitor_analysis = _normalize_competitor_analysis(
        startup_name=startup_name,
        payload=result.model_dump(),
        rag_errors=rag_errors,
        evidence_available=True,
    )

    return {
        "competitor_analysis": competitor_analysis,
        "messages": [{"role": "assistant", "content": "경쟁사 비교 분석 완료"}],
    }


def build_competitor_analysis_graph() -> StateGraph:
    graph = StateGraph(CompetitorAnalysisState)

    graph.add_node("retrieve_competitor_docs", retrieve_competitor_docs_node)
    graph.add_node("analyze_competitors", analyze_competitors_node)

    graph.add_edge(START, "retrieve_competitor_docs")
    graph.add_edge("retrieve_competitor_docs", "analyze_competitors")
    graph.add_edge("analyze_competitors", END)

    return graph.compile()


competitor_analysis_graph = build_competitor_analysis_graph()


def run_competitor_analysis(
    startup_name: str,
    startup_info: Dict[str, Any],
    tech_analysis: Optional[Dict[str, Any]] = None,
    risk_assessment: Optional[Dict[str, Any]] = None,
    team_assessment: Optional[Dict[str, Any]] = None,
    target_domain: str = "robotics",
    max_documents: int = 5,
    max_pages_per_document: int = 10,
) -> Dict[str, Any]:
    initial_state: CompetitorAnalysisState = {
        "startup_name": startup_name,
        "startup_info": startup_info,
        "tech_analysis": tech_analysis or {},
        "risk_assessment": risk_assessment or {},
        "team_assessment": team_assessment or {},
        "target_domain": target_domain,
        "max_documents": max_documents,
        "max_pages_per_document": max_pages_per_document,
        "retrieved_docs": [],
        "rag_errors": [],
        "evidence_available": False,
        "competitor_analysis": {},
        "messages": [],
    }

    final_state = competitor_analysis_graph.invoke(initial_state)
    return final_state["competitor_analysis"]
