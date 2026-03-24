"""
팀 평가 에이전트 (Team Evaluation Agent)
- startup_info 기반 창업팀/리더십 평가 (비RAG)
- 창업자 전문성, 팀 완성도, 자금 조달 이력 평가
- 팀 평가 결과를 team_assessment로 정리
"""

import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from state import AgentInputState


class TeamEvalState(AgentInputState):
    team_assessment: Dict[str, Any]


class TeamScores(BaseModel):
    domain_expertise: float = Field(
        2.0, ge=1.0, le=5.0, description="로보틱스/해당 도메인 전문성"
    )
    team_completeness: float = Field(
        2.0, ge=1.0, le=5.0, description="하드웨어·SW·비즈·운영 등 팀 구성 완성도"
    )
    funding_track: float = Field(
        2.0, ge=1.0, le=5.0, description="투자 유치·그랜트·전략 파트너십 이력"
    )


class FounderProfile(BaseModel):
    name: str = Field(default="불명")
    role: str = Field(default="")
    education: str = Field(default="스니펫 미확인")
    career_highlights: List[str] = Field(default_factory=list)
    public_signals: List[str] = Field(default_factory=list)


class EvidenceNote(BaseModel):
    claim: str = Field(default="")
    source_title: str = Field(default="")
    url: str = Field(default="")
    snippet: str = Field(default="")


class TeamAssessmentPayload(BaseModel):
    scores: TeamScores = Field(default_factory=TeamScores)
    founders: List[FounderProfile] = Field(default_factory=list)
    key_hires_or_advisors: List[str] = Field(default_factory=list)
    founders_summary: str = Field(default="")
    team_structure: str = Field(default="")
    advisors: List[str] = Field(default_factory=list)
    summary: str = Field(default="")
    data_sufficient: bool = Field(default=True)
    hold_reason: Optional[str] = Field(default=None)
    evidence_notes: List[EvidenceNote] = Field(default_factory=list)


def _normalize_team_assessment(
    startup_name: str,
    payload: Dict[str, Any],
    source_note: str,
) -> Dict[str, Any]:
    scores = payload.get("scores") or {}

    return {
        "startup_name": startup_name,
        "assessment_status": "completed",
        "evidence_available": bool(payload.get("data_sufficient", True)),
        "rag_errors": [],
        "source_note": source_note,
        "scores": {
            "domain_expertise": float(scores.get("domain_expertise", 2.0)),
            "team_completeness": float(scores.get("team_completeness", 2.0)),
            "funding_track": float(scores.get("funding_track", 2.0)),
        },
        "founders": payload.get("founders", []),
        "key_hires_or_advisors": payload.get("key_hires_or_advisors", []),
        "founders_summary": payload.get("founders_summary", ""),
        "team_structure": payload.get("team_structure", ""),
        "advisors": payload.get("advisors", []),
        "summary": payload.get("summary") or f"{startup_name} 팀 평가 요약",
        "data_sufficient": bool(payload.get("data_sufficient", True)),
        "hold_reason": payload.get("hold_reason")
        or (
            "창업자·핵심 인력 공개 정보 부족"
            if not bool(payload.get("data_sufficient", True))
            else None
        ),
        "evidence_notes": payload.get("evidence_notes", []),
    }


llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
    temperature=0,
    api_key=os.environ.get("OPENAI_API_KEY"),
)

llm_team = llm.with_structured_output(
    TeamAssessmentPayload, method="function_calling"
)


def analyze_team_node(state: TeamEvalState) -> Dict[str, Any]:
    startup_name = state["startup_name"]
    startup_info = state.get("startup_info", {})
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """당신은 벤처 투자 심사역 출신의 창업팀 due diligence 전문가입니다.
제공된 스타트업 기본 정보(startup_info)만 사용해 창업자와 핵심 인력을 평가하세요.

원칙:
- 문서에 없는 학교명·경력은 추측하지 마세요.
- 근거가 부족하면 data_sufficient=false 와 hold_reason을 명시하세요.
- 점수는 근거 대비 보수적으로 부여하세요.

점수 기준:
- domain_expertise: 1=관련성 낮음 / 3=관련 산업 경력 / 5=깊은 전문성
- team_completeness: 1=역할 공백 큼 / 3=핵심 일부 충원 / 5=핵심 역할 균형
- funding_track: 1=공개 투자 이력 미약 / 3=시드·그랜트 / 5=후속 라운드·강한 투자자""",
            ),
            (
                "human",
                """스타트업: {startup_name}
도메인: {domain}
스타트업 정보:
{startup_info}

위 정보를 바탕으로 팀 역량을 평가하세요.""",
            ),
        ]
    )

    result: TeamAssessmentPayload = (prompt | llm_team).invoke(
        {
            "startup_name": startup_name,
            "domain": state.get("target_domain", "robotics"),
            "startup_info": str(startup_info),
        }
    )

    team_assessment = _normalize_team_assessment(
        startup_name=startup_name,
        payload=result.model_dump(),
        source_note="startup_info_only",
    )

    return {
        "team_assessment": team_assessment,
        "messages": [{"role": "assistant", "content": "팀 평가 완료"}],
    }


def build_team_eval_graph() -> StateGraph:
    graph = StateGraph(TeamEvalState)

    graph.add_node("analyze_team", analyze_team_node)

    graph.add_edge(START, "analyze_team")
    graph.add_edge("analyze_team", END)

    return graph.compile()


team_eval_graph = build_team_eval_graph()


def run_team_assessment(
    startup_name: str,
    startup_info: Dict[str, Any],
    target_domain: str = "robotics",
    max_documents: int = 5,
    max_pages_per_document: int = 10,
) -> Dict[str, Any]:
    initial_state: TeamEvalState = {
        "startup_name": startup_name,
        "startup_info": startup_info,
        "target_domain": target_domain,
        "max_documents": max_documents,
        "team_assessment": {},
        "messages": [],
    }

    final_state = team_eval_graph.invoke(initial_state)
    return final_state["team_assessment"]


def run_team_eval(
    startup_name: str,
    startup_info: Dict[str, Any],
    target_domain: str = "robotics",
    max_documents: int = 5,
    max_pages_per_document: int = 10,
) -> Dict[str, Any]:
    return run_team_assessment(
        startup_name=startup_name,
        startup_info=startup_info,
        target_domain=target_domain,
        max_documents=max_documents,
        max_pages_per_document=max_pages_per_document,
    )
