"""
기술력 분석 에이전트 (Technology Analysis Agent)
- 특허/논문/공식 사이트에서 핵심 기술 지표 추출
- TRL(기술성숙도) 평가
- 기술적 강점/약점 요약
"""

import os
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field, field_validator

from state import AgentInputState
from agents.agentic_rag import agentic_retrieve, build_collection_name


# ────────────────────────────────────────────
# State
# ────────────────────────────────────────────

class TechAnalysisState(AgentInputState):
    max_pages_per_document: int
    retrieved_docs: List[str]
    rag_errors: List[str]
    evidence_available: bool
    core_tech_indicators: Dict[str, Any]
    tech_maturity: Dict[str, Any]
    tech_analysis: Dict[str, Any]          # 최종 출력 → StartupEvaluationState.tech_analysis


# ────────────────────────────────────────────
# Pydantic 출력 스키마
# ────────────────────────────────────────────

class CoreTechIndicators(BaseModel):
    """로봇 핵심 기술 지표"""
    dof: Optional[str] = Field(None, description="자유도(Degrees of Freedom)")
    payload: Optional[str] = Field(None, description="최대 가반하중")
    reach: Optional[str] = Field(None, description="작업 반경")
    speed: Optional[str] = Field(None, description="동작 속도")
    autonomy_level: Optional[str] = Field(None, description="자율화 수준 (원격조종/반자율/완전자율)")
    ai_algorithms: List[str] = Field(default_factory=list, description="사용 AI 알고리즘 목록")
    sensors: List[str] = Field(default_factory=list, description="탑재 센서 목록")
    communication: Optional[str] = Field(None, description="통신 방식")
    power_source: Optional[str] = Field(None, description="전원 방식")

    @field_validator("ai_algorithms", "sensors", mode="before")
    @classmethod
    def _coerce_list_fields(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item is not None]
        return [str(value)]


class TechMaturityAssessment(BaseModel):
    """기술성숙도(TRL) 평가"""
    core_tech_originality_score: float = Field(
        ..., ge=1, le=5, description="핵심 기술 독창성 점수 (1=모방 수준 / 3=일부 차별화 / 5=독보적 IP)"
    )
    core_tech_originality_rationale: str = Field(
        ..., description="핵심 기술 독창성 점수 산정 근거"
    )
    trl_level: int = Field(..., ge=1, le=9, description="TRL 단계 (1~9)")
    trl_rationale: str = Field(..., description="TRL 판단 근거")
    trl_score: float = Field(
        ..., ge=1, le=5, description="기술 성숙도 점수 (1=TRL 1~3 / 3=TRL 4~6 / 5=TRL 7~9)"
    )
    hw_sw_integration_score: float = Field(
        ..., ge=1, le=5, description="HW+SW 통합 역량 점수 (1=SW만 / 3=일부 통합 / 5=완전 수직계열화)"
    )
    hw_sw_integration_rationale: str = Field(
        ..., description="HW+SW 통합 역량 점수 산정 근거"
    )
    strengths: List[str] = Field(default_factory=list, description="기술적 강점")
    weaknesses: List[str] = Field(default_factory=list, description="기술적 약점")
    differentiation: str = Field(..., description="경쟁사 대비 기술 차별점")
    ip_status: Optional[str] = Field(None, description="특허/IP 현황")
    tech_score: float = Field(..., ge=0, le=100, description="기술력 종합 점수 (0~100)")
    score_rationale: str = Field(..., description="점수 산정 근거")
    summary: str = Field(..., description="기술력 분석 요약 (3~5문장)")

    @field_validator("strengths", "weaknesses", mode="before")
    @classmethod
    def _coerce_summary_lists(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item is not None]
        return [str(value)]


def build_empty_core_tech_indicators() -> Dict[str, Any]:
    """근거 문서가 없을 때 사용하는 기본 기술 지표."""
    return {
        "dof": None,
        "payload": None,
        "reach": None,
        "speed": None,
        "autonomy_level": None,
        "ai_algorithms": [],
        "sensors": [],
        "communication": None,
        "power_source": None,
    }


def build_insufficient_tech_maturity(rag_errors: List[str]) -> Dict[str, Any]:
    """근거 문서 부족 시 기술 성숙도 분석을 명시적으로 보류합니다."""
    summary = "RAG에서 유효한 기술 문서를 확보하지 못해 TRL과 기술 점수를 평가하지 않았습니다."
    if rag_errors:
        summary += " 문서 적재 상태와 컬렉션 구성을 먼저 확인한 뒤 재실행이 필요합니다."

    return {
        "core_tech_originality_score": None,
        "core_tech_originality_rationale": "근거 문서가 없어 핵심 기술 독창성을 평가하지 않았습니다.",
        "trl_level": None,
        "trl_rationale": "근거 문서가 없어 TRL을 산정하지 않았습니다.",
        "trl_score": None,
        "hw_sw_integration_score": None,
        "hw_sw_integration_rationale": "근거 문서가 없어 HW+SW 통합 역량을 평가하지 않았습니다.",
        "strengths": [],
        "weaknesses": [],
        "differentiation": None,
        "ip_status": None,
        "tech_score": None,
        "score_rationale": "근거 문서 부족으로 점수 산정을 수행하지 않았습니다.",
        "summary": summary,
    }


def build_tech_rubric_scores(maturity: Dict[str, Any]) -> Dict[str, Any]:
    """기술력 평가표 3개 항목을 1~5 점수로 정리합니다."""
    originality_score = maturity.get("core_tech_originality_score")
    trl_score = maturity.get("trl_score")
    integration_score = maturity.get("hw_sw_integration_score")

    rubric_scores = {
        "core_tech_originality": {
            "score": originality_score,
            "rationale": maturity.get("core_tech_originality_rationale"),
        },
        "trl": {
            "score": trl_score,
            "rationale": maturity.get("trl_rationale"),
        },
        "hw_sw_integration": {
            "score": integration_score,
            "rationale": maturity.get("hw_sw_integration_rationale"),
        },
    }

    valid_scores = [
        float(score)
        for score in (originality_score, trl_score, integration_score)
        if score is not None
    ]
    rubric_average = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else None
    rubric_tech_score = round(rubric_average * 20, 2) if rubric_average is not None else None

    rubric_scores["rubric_average"] = rubric_average
    rubric_scores["rubric_tech_score"] = rubric_tech_score
    return rubric_scores


# ────────────────────────────────────────────
# LLM 초기화
# ────────────────────────────────────────────

llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
    temperature=0,
    api_key=os.environ.get("OPENAI_API_KEY"),
)

llm_indicators = llm.with_structured_output(
    CoreTechIndicators, method="function_calling"
)
llm_maturity = llm.with_structured_output(
    TechMaturityAssessment, method="function_calling"
)


# ────────────────────────────────────────────
# 노드 함수
# ────────────────────────────────────────────

def retrieve_tech_docs_node(state: TechAnalysisState) -> Dict[str, Any]:
    """기술 관련 문서를 RAG로 검색합니다."""
    startup_name = state["startup_name"]
    domain = state.get("target_domain", "robotics")
    k = state.get("max_documents", 5)

    queries = [
        f"{startup_name} TRL 기술 완성도 HW SW 통합도 핵심 독창성 강점",
        f"{startup_name} 자율주행 레벨 AI 알고리즘 DoF Payload SLAM 센서",
        f"{startup_name} 상용화 고객사 투자 유치 물류 자동화 AMR 성장",
    ]

    docs, rag_errors = agentic_retrieve(
        queries=queries,
        collection_name=build_collection_name("robotics", domain),
        k=k,
        llm=llm,
    )

    evidence_available = bool(docs)
    status_message = (
        f"기술 문서 {len(docs)}건 검색 완료 (관련성 평가 통과)"
        if evidence_available
        else "기술 문서 검색 실패 또는 관련 문서 없음"
    )

    return {
        "retrieved_docs": docs,
        "rag_errors": rag_errors,
        "evidence_available": evidence_available,
        "messages": [{"role": "system", "content": status_message}],
    }


def analyze_tech_indicators_node(state: TechAnalysisState) -> Dict[str, Any]:
    """검색된 문서에서 핵심 기술 지표를 추출합니다."""
    startup_name = state["startup_name"]
    docs = state.get("retrieved_docs", [])
    startup_info = state.get("startup_info", {})

    if not docs:
        return {
            "core_tech_indicators": build_empty_core_tech_indicators(),
            "messages": [{"role": "assistant", "content": "근거 문서가 없어 핵심 기술 지표 추출을 중단했습니다."}],
        }

    docs_text = "\n\n".join(docs[:10])  # 상위 10건

    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 로봇공학 전문가입니다.
목표는 이 스타트업이 최고 투자 대상이 될 수 있는지 판단하기 위해 기술적 경쟁 우위를 정확하게 파악하는 것입니다.
제공된 문서에서 로봇 시스템의 핵심 기술 지표를 정확하게 추출하세요.
수치가 명시되지 않은 경우 null로 표시하고, 추측하지 마세요."""),
        ("human", """스타트업: {startup_name}
스타트업 정보: {startup_info}

관련 문서:
{docs}

이 기업의 기술이 경쟁사 대비 우위를 가질 수 있는지 판단할 수 있도록 핵심 기술 지표를 추출하세요."""),
    ])

    result: CoreTechIndicators = (prompt | llm_indicators).invoke({
        "startup_name": startup_name,
        "startup_info": str(startup_info),
        "docs": docs_text,
    })

    return {
        "core_tech_indicators": result.model_dump(),
        "messages": [{"role": "assistant", "content": "핵심 기술 지표 추출 완료"}],
    }


def assess_tech_maturity_node(state: TechAnalysisState) -> Dict[str, Any]:
    """TRL 평가 및 기술적 강점/약점을 분석합니다."""
    startup_name = state["startup_name"]
    indicators = state.get("core_tech_indicators", {})
    docs = state.get("retrieved_docs", [])
    rag_errors = state.get("rag_errors", [])

    if not docs:
        return {
            "tech_maturity": build_insufficient_tech_maturity(rag_errors),
            "messages": [{"role": "assistant", "content": "근거 문서가 없어 TRL 평가를 보류했습니다."}],
        }

    docs_text = "\n\n".join(docs[:10])

    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 기술성숙도(TRL) 평가 전문가입니다.
목표는 이 스타트업이 기술력 측면에서 최고 투자 대상인지 판단하는 것입니다.

TRL 기준:
- TRL 1~3: 기초연구 (개념 검증, 실험실 수준)
- TRL 4~6: 프로토타입 (파일럿 테스트, 실증 환경)
- TRL 7~9: 상용화 (실제 운용, 양산 가능)

기술력 세부 평가 기준:
- 핵심 기술 독창성: 1=모방 수준 / 3=일부 차별화 / 5=독보적 IP
- 기술 성숙도 점수: 1=TRL 1~3 / 3=TRL 4~6 / 5=TRL 7~9
- HW+SW 통합 역량: 1=SW만 / 3=일부 통합 / 5=완전 수직계열화

기술적 강점이 타 경쟁사 대비 실질적인 해자(moat)가 되는지 중점적으로 평가하세요.
각 점수는 반드시 1~5 숫자로 반환하고, 점수 근거를 함께 설명하세요."""),
        ("human", """스타트업: {startup_name}

추출된 기술 지표:
{indicators}

관련 문서:
{docs}

이 기업이 기술력 면에서 최고 투자 대상이 될 수 있는지 판단할 수 있도록 TRL 평가 및 기술력 종합 분석을 수행하세요."""),
    ])

    result: TechMaturityAssessment = (prompt | llm_maturity).invoke({
        "startup_name": startup_name,
        "indicators": str(indicators),
        "docs": docs_text,
    })

    return {
        "tech_maturity": result.model_dump(),
        "messages": [{"role": "assistant", "content": f"TRL 평가 완료: TRL {result.trl_level}"}],
    }


def compile_tech_report_node(state: TechAnalysisState) -> Dict[str, Any]:
    """분석 결과를 최종 tech_analysis 딕셔너리로 정리합니다."""
    startup_name = state["startup_name"]
    indicators = state.get("core_tech_indicators", {})
    maturity = state.get("tech_maturity", {})
    rag_errors = state.get("rag_errors", [])
    evidence_available = state.get("evidence_available", False)
    rubric_scores = build_tech_rubric_scores(maturity)
    rubric_tech_score = rubric_scores.get("rubric_tech_score")

    score_rationale_parts = []
    if rubric_scores.get("rubric_average") is not None:
        score_rationale_parts.append(
            (
                "기술력 세부 항목 평균 "
                f"{rubric_scores['rubric_average']:.2f}/5 × 20 = {rubric_tech_score:.2f}/100"
            )
        )
    if maturity.get("score_rationale"):
        score_rationale_parts.append(str(maturity.get("score_rationale")))

    tech_analysis = {
        "startup_name": startup_name,
        "assessment_status": "completed" if evidence_available else "insufficient_evidence",
        "evidence_available": evidence_available,
        "rag_errors": rag_errors,
        "core_tech_indicators": indicators,
        "rubric_scores": rubric_scores,
        "trl_level": maturity.get("trl_level"),
        "trl_rationale": maturity.get("trl_rationale"),
        "strengths": maturity.get("strengths", []),
        "weaknesses": maturity.get("weaknesses", []),
        "differentiation": maturity.get("differentiation"),
        "ip_status": maturity.get("ip_status"),
        "tech_score": rubric_tech_score if rubric_tech_score is not None else maturity.get("tech_score"),
        "score_rationale": " | ".join(score_rationale_parts) if score_rationale_parts else maturity.get("score_rationale"),
        "summary": maturity.get("summary"),
    }

    return {
        "tech_analysis": tech_analysis,
        "messages": [{"role": "assistant", "content": "기술력 분석 보고서 작성 완료"}],
    }


# ────────────────────────────────────────────
# 그래프 구성
# ────────────────────────────────────────────

def build_tech_analysis_graph() -> StateGraph:
    graph = StateGraph(TechAnalysisState)

    graph.add_node("retrieve_tech_docs", retrieve_tech_docs_node)
    graph.add_node("analyze_tech_indicators", analyze_tech_indicators_node)
    graph.add_node("assess_tech_maturity", assess_tech_maturity_node)
    graph.add_node("compile_tech_report", compile_tech_report_node)

    graph.add_edge(START, "retrieve_tech_docs")
    graph.add_edge("retrieve_tech_docs", "analyze_tech_indicators")
    graph.add_edge("analyze_tech_indicators", "assess_tech_maturity")
    graph.add_edge("assess_tech_maturity", "compile_tech_report")
    graph.add_edge("compile_tech_report", END)

    return graph.compile()


tech_analysis_graph = build_tech_analysis_graph()


# ────────────────────────────────────────────
# 실행 헬퍼
# ────────────────────────────────────────────

def run_tech_analysis(
    startup_name: str,
    startup_info: Dict[str, Any],
    target_domain: str = "robotics",
    max_documents: int = 5,
    max_pages_per_document: int = 10,
) -> Dict[str, Any]:
    """
    기술력 분석 에이전트를 실행합니다.

    Returns:
        tech_analysis: StartupEvaluationState.tech_analysis에 할당 가능한 딕셔너리
    """
    initial_state: TechAnalysisState = {
        "startup_name": startup_name,
        "startup_info": startup_info,
        "target_domain": target_domain,
        "max_documents": max_documents,
        "max_pages_per_document": max_pages_per_document,
        "retrieved_docs": [],
        "rag_errors": [],
        "evidence_available": False,
        "core_tech_indicators": {},
        "tech_maturity": {},
        "tech_analysis": {},
        "messages": [],
    }

    final_state = tech_analysis_graph.invoke(initial_state)
    return final_state["tech_analysis"]


# ────────────────────────────────────────────
# 실행 예시
# ────────────────────────────────────────────

if __name__ == "__main__":
    result = run_tech_analysis(
        startup_name="Rainbow Robotics",
        startup_info={
            "description": "협동로봇 및 이족보행 로봇 개발 스타트업",
            "founded": 2011,
            "location": "대한민국",
        },
        target_domain="robotics",
    )

    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
