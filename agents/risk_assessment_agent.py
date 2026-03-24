"""
리스크 평가 에이전트 (Risk Assessment Agent)
- 안전 규제 리스크 (ISO 10218, CE/UL 인증)
- 수출 규제 리스크 (EAR, ITAR, 전략물자)
- 시장/경쟁/재무 리스크
- 리스크 등급 산정 (상/중/하)
"""

import os
from typing import Any, Dict, List, Literal, Optional
from typing_extensions import TypedDict
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from state import AgentInputState
from agents.agentic_rag import agentic_retrieve, build_collection_name


# ────────────────────────────────────────────
# State
# ────────────────────────────────────────────

RiskGrade = Literal["상", "중", "하"]


class RiskAssessmentState(AgentInputState):
    tech_analysis: Dict[str, Any]          # 기술력 분석 에이전트 출력 (선택적 입력)
    retrieved_docs: List[str]
    rag_errors: List[str]
    evidence_available: bool
    regulatory_risks: Dict[str, Any]       # 안전/수출 규제 리스크
    market_risks: Dict[str, Any]           # 시장/경쟁/재무 리스크
    risk_assessment: Dict[str, Any]        # 최종 출력


# ────────────────────────────────────────────
# Pydantic 출력 스키마
# ────────────────────────────────────────────

class RegulatoryRiskAssessment(BaseModel):
    """규제 리스크 평가"""
    # 안전 규제
    iso_10218_compliance: str = Field(..., description="ISO 10218 (산업용 로봇 안전) 준수 현황")
    iso_10218_risk_grade: RiskGrade = Field(..., description="ISO 10218 리스크 등급")
    ce_ul_status: str = Field(..., description="CE/UL 인증 현황")
    safety_cert_risk_grade: RiskGrade = Field(..., description="안전 인증 리스크 등급")
    other_safety_standards: List[str] = Field(default_factory=list, description="기타 안전 규격 (ISO 13849, IEC 62061 등)")

    # 수출 규제
    ear_classification: Optional[str] = Field(None, description="EAR(Export Administration Regulations) 분류")
    itar_applicable: bool = Field(..., description="ITAR 적용 여부")
    strategic_material_risk: str = Field(..., description="전략물자 해당 가능성")
    export_risk_grade: RiskGrade = Field(..., description="수출 규제 리스크 등급")
    target_markets: List[str] = Field(default_factory=list, description="주요 진출 예정 시장")

    # TRL 기반 규제 리스크
    trl_regulatory_gap: str = Field(..., description="현재 TRL과 상용화 규제 요건 간 격차")
    trl_risk_grade: RiskGrade = Field(..., description="TRL 기반 규제 리스크 등급")

    regulatory_risk_score: float = Field(
        ...,
        ge=1,
        le=5,
        description="규제 리스크 점수 (1=높음/불확실, 3=보통, 5=낮음/명확)",
    )
    regulatory_risk_rationale: str = Field(
        ...,
        description="규제 리스크 점수 산정 근거",
    )
    regulatory_summary: str = Field(..., description="규제 리스크 종합 요약")


class MarketRiskAssessment(BaseModel):
    """시장/경쟁/재무 리스크 평가"""
    # 시장 리스크
    market_size_risk: str = Field(..., description="목표 시장 규모 및 성장성 리스크")
    market_timing_risk: str = Field(..., description="시장 진입 타이밍 리스크")
    market_risk_grade: RiskGrade = Field(..., description="시장 리스크 등급")

    # 경쟁 리스크
    key_competitors: List[str] = Field(default_factory=list, description="주요 경쟁사")
    competitive_moat: str = Field(..., description="경쟁 해자(Moat) 현황")
    competition_risk_grade: RiskGrade = Field(..., description="경쟁 리스크 등급")

    # 재무 리스크
    burn_rate_risk: str = Field(..., description="번 레이트 및 런웨이 리스크")
    funding_dependency: str = Field(..., description="외부 자금 의존도")
    revenue_model_risk: str = Field(..., description="수익 모델 검증 현황")
    financial_risk_grade: RiskGrade = Field(..., description="재무 리스크 등급")
    runway_months: Optional[float] = Field(
        None,
        description="추정 가능한 런웨이 개월 수 (명확한 수치가 없으면 null)",
    )
    runway_score: float = Field(
        ...,
        ge=1,
        le=5,
        description="재무 지속가능성(런웨이) 점수 (1=<6개월, 3=12개월, 5=>24개월)",
    )
    runway_rationale: str = Field(..., description="런웨이 점수 산정 근거")

    market_risk_summary: str = Field(..., description="시장/경쟁/재무 리스크 종합 요약")


class OverallRiskSummary(BaseModel):
    """종합 리스크 평가"""
    overall_risk_grade: RiskGrade = Field(..., description="종합 리스크 등급")
    risk_score: float = Field(..., ge=0, le=100, description="리스크 점수 (높을수록 위험, 0~100)")
    top_risks: List[str] = Field(..., description="상위 3대 리스크 항목")
    mitigation_strategies: List[str] = Field(..., description="리스크 완화 전략 (항목별)")
    investment_caution: str = Field(..., description="투자 시 주의사항")
    overall_summary: str = Field(..., description="리스크 평가 종합 요약 (3~5문장)")


def build_insufficient_regulatory_risks() -> Dict[str, Any]:
    """근거 문서가 없을 때 규제 리스크 평가를 보류합니다."""
    return {
        "assessment_status": "insufficient_evidence",
        "iso_10218_compliance": None,
        "iso_10218_risk_grade": None,
        "ce_ul_status": None,
        "safety_cert_risk_grade": None,
        "other_safety_standards": [],
        "ear_classification": None,
        "itar_applicable": None,
        "strategic_material_risk": None,
        "export_risk_grade": None,
        "target_markets": [],
        "trl_regulatory_gap": "근거 문서가 없어 규제 격차를 평가하지 않았습니다.",
        "trl_risk_grade": None,
        "regulatory_risk_score": None,
        "regulatory_risk_rationale": "근거 문서가 없어 규제 리스크 점수를 산정하지 않았습니다.",
        "regulatory_summary": "RAG에서 유효한 규제 문서를 확보하지 못해 규제 리스크 평가를 수행하지 않았습니다.",
    }


def build_insufficient_market_risks() -> Dict[str, Any]:
    """근거 문서가 없을 때 시장 리스크 평가를 보류합니다."""
    return {
        "assessment_status": "insufficient_evidence",
        "market_size_risk": None,
        "market_timing_risk": None,
        "market_risk_grade": None,
        "key_competitors": [],
        "competitive_moat": None,
        "competition_risk_grade": None,
        "burn_rate_risk": None,
        "funding_dependency": None,
        "revenue_model_risk": None,
        "financial_risk_grade": None,
        "runway_months": None,
        "runway_score": None,
        "runway_rationale": "근거 문서가 없어 런웨이 점수를 산정하지 않았습니다.",
        "market_risk_summary": "RAG에서 유효한 시장/경쟁/재무 문서를 확보하지 못해 리스크 평가를 수행하지 않았습니다.",
    }


def build_risk_rubric_scores(
    regulatory: Dict[str, Any],
    market: Dict[str, Any],
) -> Dict[str, Any]:
    """리스크 평가표 2개 항목을 1~5 점수로 정리합니다."""
    regulatory_score = regulatory.get("regulatory_risk_score")
    runway_score = market.get("runway_score")

    rubric_scores = {
        "regulatory_risk": {
            "score": regulatory_score,
            "rationale": regulatory.get("regulatory_risk_rationale"),
        },
        "runway": {
            "score": runway_score,
            "rationale": market.get("runway_rationale"),
            "runway_months": market.get("runway_months"),
        },
    }

    valid_scores = [
        float(score)
        for score in (regulatory_score, runway_score)
        if score is not None
    ]
    rubric_average = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else None
    rubric_risk_score = round(rubric_average * 20, 2) if rubric_average is not None else None

    rubric_scores["rubric_average"] = rubric_average
    rubric_scores["rubric_risk_score"] = rubric_risk_score
    return rubric_scores


# ────────────────────────────────────────────
# LLM 초기화
# ────────────────────────────────────────────

llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
    temperature=0,
    api_key=os.environ.get("OPENAI_API_KEY"),
)

llm_regulatory = llm.with_structured_output(
    RegulatoryRiskAssessment, method="function_calling"
)
llm_market = llm.with_structured_output(
    MarketRiskAssessment, method="function_calling"
)
llm_overall = llm.with_structured_output(
    OverallRiskSummary, method="function_calling"
)


# ────────────────────────────────────────────
# 노드 함수
# ────────────────────────────────────────────

def retrieve_risk_docs_node(state: RiskAssessmentState) -> Dict[str, Any]:
    """리스크 평가 관련 문서를 RAG로 검색합니다."""
    startup_name = state["startup_name"]
    domain = state.get("target_domain", "robotics")
    k = state.get("max_documents", 5)

    queries = [
        f"{startup_name} 안전 규제 인증 ISO 준수 약점 리스크 취약점",
        f"{startup_name} 수출 규제 전략물자 지정학 리스크 낮음 투자 유리",
        f"{startup_name} 재무 런웨이 시리즈 투자 자금 안정성 상용화",
    ]

    docs, rag_errors = agentic_retrieve(
        queries=queries,
        collection_name=build_collection_name("robotics", domain),
        k=k,
        llm=llm,
    )

    evidence_available = bool(docs)
    status_message = (
        f"리스크 관련 문서 {len(docs)}건 검색 완료 (관련성 평가 통과)"
        if evidence_available
        else "리스크 관련 문서 검색 실패 또는 관련 문서 없음"
    )

    return {
        "retrieved_docs": docs,
        "rag_errors": rag_errors,
        "evidence_available": evidence_available,
        "messages": [{"role": "system", "content": status_message}],
    }


def assess_regulatory_risk_node(state: RiskAssessmentState) -> Dict[str, Any]:
    """안전 규제 및 수출 규제 리스크를 평가합니다."""
    startup_name = state["startup_name"]
    startup_info = state.get("startup_info", {})
    tech_analysis = state.get("tech_analysis", {})
    docs = state.get("retrieved_docs", [])

    if not docs:
        return {
            "regulatory_risks": build_insufficient_regulatory_risks(),
            "messages": [{"role": "assistant", "content": "근거 문서가 없어 규제 리스크 평가를 보류했습니다."}],
        }

    docs_text = "\n\n".join(docs[:10])
    trl_level = tech_analysis.get("trl_level", "미확인")

    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 로봇 산업 규제 전문가입니다.
목표는 이 스타트업이 규제 리스크 측면에서 최고 투자 대상인지 판단하는 것입니다.
규제 리스크가 낮고 투자에 유리한 요소를 중점적으로 파악하세요.

주요 평가 항목:
1. 안전 규제: ISO 10218 (산업용 로봇), ISO/TS 15066 (협동로봇), ISO 13849, IEC 62061
2. 인증: CE 마킹 (유럽), UL (북미), KCs (한국)
3. 수출 규제: EAR (미국 수출관리규정), ITAR (국제무기거래규정), 전략물자관리원
4. TRL 규제 격차: 현재 기술 성숙도와 상용화 규제 요건 간 격차
5. 규제 리스크 점수: 1=높음(불확실) / 3=보통 / 5=낮음(명확)

리스크 등급 기준:
- 상: 즉각적 대응 필요, 사업 진행 심각한 장애
- 중: 주의 필요, 일정/비용 영향 가능
- 하: 관리 가능, 현재 진행 중이거나 해결됨

반드시 `regulatory_risk_score`와 `regulatory_risk_rationale`을 함께 반환하세요."""),
        ("human", """스타트업: {startup_name}
스타트업 정보: {startup_info}
현재 TRL 수준: {trl_level}

관련 문서:
{docs}

안전 규제 및 수출 규제 리스크를 평가하세요."""),
    ])

    result: RegulatoryRiskAssessment = (prompt | llm_regulatory).invoke({
        "startup_name": startup_name,
        "startup_info": str(startup_info),
        "trl_level": trl_level,
        "docs": docs_text,
    })

    return {
        "regulatory_risks": result.model_dump(),
        "messages": [{"role": "assistant", "content": "규제 리스크 평가 완료"}],
    }


def assess_market_risk_node(state: RiskAssessmentState) -> Dict[str, Any]:
    """시장/경쟁/재무 리스크를 평가합니다."""
    startup_name = state["startup_name"]
    startup_info = state.get("startup_info", {})
    docs = state.get("retrieved_docs", [])

    if not docs:
        return {
            "market_risks": build_insufficient_market_risks(),
            "messages": [{"role": "assistant", "content": "근거 문서가 없어 시장/경쟁/재무 리스크 평가를 보류했습니다."}],
        }

    docs_text = "\n\n".join(docs[:10])

    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 스타트업 투자 분석 전문가입니다.
목표는 이 스타트업이 시장/경쟁/재무 리스크 측면에서 최고 투자 대상인지 판단하는 것입니다.
리스크가 낮고 투자 회수 가능성이 높은 요소를 중점적으로 파악하세요.

평가 항목:
1. 시장 리스크: TAM/SAM/SOM 규모, 성장률, 시장 진입 타이밍
2. 경쟁 리스크: 주요 경쟁사, 진입장벽, 경쟁 우위
3. 재무 리스크: 번 레이트, 런웨이, 수익화 가능성, 자금 조달 이력
4. 런웨이 점수: 1=<6개월 / 3=12개월 / 5=>24개월

리스크 등급 기준:
- 상: 즉각적 대응 필요, 투자 회수 심각한 위험
- 중: 주의 필요, 모니터링 권장
- 하: 관리 가능, 일반적 수준의 리스크

문서에 런웨이 개월 수가 직접 있으면 `runway_months`에 넣고, 없으면 null로 두되
가용 근거를 바탕으로 보수적으로 `runway_score`와 `runway_rationale`을 작성하세요."""),
        ("human", """스타트업: {startup_name}
스타트업 정보: {startup_info}

관련 문서:
{docs}

시장, 경쟁, 재무 리스크를 평가하세요."""),
    ])

    result: MarketRiskAssessment = (prompt | llm_market).invoke({
        "startup_name": startup_name,
        "startup_info": str(startup_info),
        "docs": docs_text,
    })

    return {
        "market_risks": result.model_dump(),
        "messages": [{"role": "assistant", "content": "시장/경쟁/재무 리스크 평가 완료"}],
    }


def compile_risk_report_node(state: RiskAssessmentState) -> Dict[str, Any]:
    """모든 리스크를 종합하여 최종 리스크 평가를 생성합니다."""
    startup_name = state["startup_name"]
    regulatory = state.get("regulatory_risks", {})
    market = state.get("market_risks", {})
    rag_errors = state.get("rag_errors", [])
    evidence_available = state.get("evidence_available", False)
    rubric_scores = build_risk_rubric_scores(regulatory, market)

    if not evidence_available:
        risk_assessment = {
            "startup_name": startup_name,
            "assessment_status": "insufficient_evidence",
            "evidence_available": False,
            "rag_errors": rag_errors,
            "regulatory_risks": regulatory,
            "market_risks": market,
            "rubric_scores": rubric_scores,
            "overall_risk_grade": None,
            "risk_score": None,
            "top_risks": ["RAG 문서 부재로 종합 리스크를 산정하지 않았습니다."],
            "mitigation_strategies": [
                "Chroma 컬렉션과 임베딩 적재 상태를 확인한 뒤 재평가",
                "규제, 시장, 경쟁, 재무 근거 문서를 먼저 확보",
            ],
            "investment_caution": "근거 문서가 없는 상태에서는 투자 판단에 사용하면 안 됩니다.",
            "overall_summary": "리스크 평가에 필요한 근거 문서를 확보하지 못해 종합 리스크 등급과 점수를 산정하지 않았습니다.",
        }

        return {
            "risk_assessment": risk_assessment,
            "messages": [{"role": "assistant", "content": "근거 문서가 없어 종합 리스크 평가를 보류했습니다."}],
        }

    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 종합 리스크 평가 전문가입니다.
목표는 이 스타트업이 종합 리스크 측면에서 최고 투자 대상인지 판단하는 것입니다.
규제/시장/경쟁/재무 리스크를 종합하여 최종 투자 리스크 등급을 산정하고,
리스크가 낮아 투자하기 유리한 근거를 중점적으로 서술하세요.

종합 리스크 등급 산정 기준:
- 상: 복수의 '상' 등급 리스크 존재 또는 치명적 단일 리스크
- 중: '상' 1개 또는 복수의 '중' 등급 리스크
- 하: 대부분 '하' 등급이며 관리 가능한 수준"""),
        ("human", """스타트업: {startup_name}

규제 리스크:
{regulatory}

시장/경쟁/재무 리스크:
{market}

종합 리스크 평가를 수행하고 투자자를 위한 리스크 요약을 작성하세요."""),
    ])

    result: OverallRiskSummary = (prompt | llm_overall).invoke({
        "startup_name": startup_name,
        "regulatory": str(regulatory),
        "market": str(market),
    })

    # 최종 risk_assessment 딕셔너리 구성
    risk_assessment = {
        "startup_name": startup_name,
        "assessment_status": "completed",
        "evidence_available": True,
        "rag_errors": rag_errors,
        "regulatory_risks": regulatory,
        "market_risks": market,
        "rubric_scores": rubric_scores,
        "overall_risk_grade": result.overall_risk_grade,
        "risk_score": result.risk_score,
        "top_risks": result.top_risks,
        "mitigation_strategies": result.mitigation_strategies,
        "investment_caution": result.investment_caution,
        "overall_summary": result.overall_summary,
    }

    return {
        "risk_assessment": risk_assessment,
        "messages": [{"role": "assistant", "content": f"리스크 평가 완료: 종합 등급 {result.overall_risk_grade}"}],
    }


# ────────────────────────────────────────────
# 그래프 구성
# ────────────────────────────────────────────

def build_risk_assessment_graph() -> StateGraph:
    graph = StateGraph(RiskAssessmentState)

    graph.add_node("retrieve_risk_docs", retrieve_risk_docs_node)
    graph.add_node("assess_regulatory_risk", assess_regulatory_risk_node)
    graph.add_node("assess_market_risk", assess_market_risk_node)
    graph.add_node("compile_risk_report", compile_risk_report_node)

    graph.add_edge(START, "retrieve_risk_docs")
    graph.add_edge("retrieve_risk_docs", "assess_regulatory_risk")
    graph.add_edge("assess_regulatory_risk", "assess_market_risk")
    graph.add_edge("assess_market_risk", "compile_risk_report")
    graph.add_edge("compile_risk_report", END)

    return graph.compile()


risk_assessment_graph = build_risk_assessment_graph()


# ────────────────────────────────────────────
# 실행 헬퍼
# ────────────────────────────────────────────

def run_risk_assessment(
    startup_name: str,
    startup_info: Dict[str, Any],
    tech_analysis: Optional[Dict[str, Any]] = None,
    target_domain: str = "robotics",
    max_documents: int = 5,
) -> Dict[str, Any]:
    """
    리스크 평가 에이전트를 실행합니다.

    Args:
        tech_analysis: 기술력 분석 에이전트 출력 (있으면 TRL 기반 규제 리스크 평가에 활용)

    Returns:
        risk_assessment: 투자 리스크 평가 딕셔너리
    """
    initial_state: RiskAssessmentState = {
        "startup_name": startup_name,
        "startup_info": startup_info,
        "tech_analysis": tech_analysis or {},
        "target_domain": target_domain,
        "max_documents": max_documents,
        "retrieved_docs": [],
        "rag_errors": [],
        "evidence_available": False,
        "regulatory_risks": {},
        "market_risks": {},
        "risk_assessment": {},
        "messages": [],
    }

    final_state = risk_assessment_graph.invoke(initial_state)
    return final_state["risk_assessment"]


# ────────────────────────────────────────────
# 실행 예시
# ────────────────────────────────────────────

if __name__ == "__main__":
    result = run_risk_assessment(
        startup_name="Rainbow Robotics",
        startup_info={
            "description": "협동로봇 및 이족보행 로봇 개발 스타트업",
            "founded": 2011,
            "location": "대한민국",
            "funding": "Series B",
        },
        target_domain="robotics",
    )

    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
