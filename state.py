"""
공통 State 정의
StartupEvaluationState, GlobalEvaluationState
"""

from typing import Annotated, Any, Dict, List, Literal, Optional
from typing_extensions import NotRequired, TypedDict
from langgraph.graph.message import add_messages


class InvestmentDecision(TypedDict):
    decision: Literal["invest", "pass"]
    confidence: float
    rationale: str


class AgentInputState(TypedDict):
    startup_name: str
    startup_info: Dict[str, Any]
    target_domain: str
    target_subdomain: NotRequired[str]
    max_documents: int
    messages: Annotated[list, add_messages]


class StartupEvaluationState(TypedDict):
    startup_name: str
    startup_info: Dict[str, Any]
    tech_analysis: Dict[str, Any]
    team_assessment: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    competitor_analysis: Dict[str, Any]
    investment_score: float
    score_breakdown: NotRequired[Dict[str, Any]]
    investment_decision: InvestmentDecision
    report_content: str
    report_review: NotRequired[Dict[str, Any]]
    hold_reason: NotRequired[str]
    messages: Annotated[list, add_messages]


class GlobalEvaluationState(TypedDict):
    target_domain: Literal["agriculture", "climate", "energy", "robotics", "healthcare", "manufacturing", "logistics", "construction", "defense"]
    target_subdomain: NotRequired[str]
    pending_startups: List[str]
    startup_info_map: Dict[str, Dict[str, Any]]  # startup_name → 기본 정보 (탐색 에이전트 출력)
    current_startup: Optional[str]
    current_evaluation: Dict[str, Any]           # 현재 처리 중인 스타트업 평가 (노드 간 누적)
    evaluations: List[StartupEvaluationState]
    final_report_content: str
    run_id: str
    max_iterations: int
    max_candidates: int
    iteration_count: int
    max_documents: int
    max_pages_per_document: int
    max_total_pages: int
    output_class: str
    output_startup_label: str
