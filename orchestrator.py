"""
오케스트레이터 (Startup Evaluation Orchestrator)
GlobalEvaluationState를 기반으로 전체 평가 파이프라인을 조율합니다.

파이프라인:
  스타트업 탐색
    → init_next_startup          (pending_startups에서 하나 꺼냄)
    → parallel_analysis          (기술력 + 시장성 + 팀 병렬 실행)
    → risk_assessment            (리스크 평가)
    → competitor_analysis        (경쟁사 비교)
    → investment_decision        (투자 판단)
        ├─ invest/watch → report_generation → report_review → finalize
        └─ pass         → finalize
    → finalize_startup           (evaluations에 적재, 루프 제어)
    → [pending 남음?] → init_next_startup 으로 반복
    → [없음] → END
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from langgraph.graph import StateGraph, START, END

from state import GlobalEvaluationState
from agents.competitor_analysis_agent import run_competitor_analysis
from agents.market_eval_agent import run_market_assessment
from agents.team_eval_agent import run_team_assessment
from agents.startup_exploration_agent import run_startup_exploration
from agents.tech_analysis_agent import run_tech_analysis
from agents.risk_assessment_agent import run_risk_assessment
from agents.investment_decision_agent import run_investment_decision
from agents.report_generation_agent import run_report_generation as external_run_report_generation
from agents.report_review_agent import run_report_review as external_run_report_review


def run_report_generation(current_evaluation: Dict[str, Any]) -> str:
    """보고서 생성 에이전트 모듈을 호출합니다."""
    return external_run_report_generation(current_evaluation)


def run_report_review(report_content: str, current_evaluation: Dict[str, Any]) -> Dict[str, Any]:
    """보고서 검토 에이전트 모듈을 호출합니다."""
    return external_run_report_review(report_content, current_evaluation)


# ── 노드 함수 ──────────────────────────────────────────────────────────────

def explore_startups_node(state: GlobalEvaluationState) -> Dict[str, Any]:
    """Chroma RAG로 후보 스타트업을 탐색하고 pending_startups를 채웁니다."""
    result = run_startup_exploration(
        target_domain=state["target_domain"],
        top_k_candidates=state.get("max_candidates", state.get("max_iterations", 5)),
        max_documents=state.get("max_documents", 10),
    )
    return {
        "pending_startups": result["pending_startups"],
        "startup_info_map": result["startup_info_map"],
        "iteration_count": 0,
        "evaluations": [],
        "current_evaluation": {},
    }


def init_next_startup_node(state: GlobalEvaluationState) -> Dict[str, Any]:
    """pending_startups에서 다음 스타트업을 꺼내 current_startup으로 설정합니다."""
    pending = list(state.get("pending_startups", []))
    current = pending.pop(0)
    startup_info = state.get("startup_info_map", {}).get(current, {})

    return {
        "current_startup": current,
        "pending_startups": pending,
        "current_evaluation": {
            "startup_name": current,
            "startup_info": startup_info,
        },
    }


def parallel_analysis_node(state: GlobalEvaluationState) -> Dict[str, Any]:
    """기술력 분석 / 시장성 평가 / 팀 평가를 병렬로 실행합니다."""
    startup_name = state["current_startup"]
    startup_info = state.get("startup_info_map", {}).get(startup_name, {})
    domain = state["target_domain"]
    max_docs = state.get("max_documents", 5)

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_tech = executor.submit(run_tech_analysis, startup_name, startup_info, domain, max_docs)
        future_market = executor.submit(run_market_assessment, startup_name, startup_info, domain, max_docs)
        future_team = executor.submit(run_team_assessment, startup_name, startup_info, domain, max_docs)

        tech_result = future_tech.result()
        market_result = future_market.result()
        team_result = future_team.result()

    current = {**state.get("current_evaluation", {})}
    current["tech_analysis"]   = tech_result
    current["market_analysis"] = market_result
    current["team_assessment"] = team_result

    return {"current_evaluation": current}


def risk_assessment_node(state: GlobalEvaluationState) -> Dict[str, Any]:
    """리스크 평가를 실행합니다. 기술력 분석 결과를 입력으로 활용합니다."""
    startup_name = state["current_startup"]
    startup_info = state.get("startup_info_map", {}).get(startup_name, {})
    current = state.get("current_evaluation", {})
    tech_analysis = current.get("tech_analysis", {})

    risk_result = run_risk_assessment(
        startup_name=startup_name,
        startup_info=startup_info,
        tech_analysis=tech_analysis,
        target_domain=state["target_domain"],
        max_documents=state.get("max_documents", 5),
    )

    current = {**current, "risk_assessment": risk_result}
    return {"current_evaluation": current}


def competitor_analysis_node(state: GlobalEvaluationState) -> Dict[str, Any]:
    """경쟁사 비교 분석을 실행합니다."""
    startup_name = state["current_startup"]
    startup_info = state.get("startup_info_map", {}).get(startup_name, {})
    current = state.get("current_evaluation", {})

    competitor_result = run_competitor_analysis(
        startup_name=startup_name,
        startup_info=startup_info,
        tech_analysis=current.get("tech_analysis", {}),
        risk_assessment=current.get("risk_assessment", {}),
        team_assessment=current.get("team_assessment", {}),
        target_domain=state["target_domain"],
        max_documents=state.get("max_documents", 5),
    )

    current = {**current, "competitor_analysis": competitor_result}
    return {"current_evaluation": current}


def investment_decision_node(state: GlobalEvaluationState) -> Dict[str, Any]:
    """5개 항목 가중 점수화 후 투자/보류/부결을 결정합니다."""
    current = state.get("current_evaluation", {})
    decision_result = run_investment_decision(current)

    current = {
        **current,
        "investment_score": decision_result.get("investment_score", 0.0),
        "score_breakdown": decision_result.get("score_breakdown", {}),
        "investment_decision": {
            "decision":   decision_result.get("decision", "pass"),
            "confidence": decision_result.get("confidence", 0.0),
            "rationale":  decision_result.get("rationale", ""),
        },
    }
    return {"current_evaluation": current}


def report_generation_node(state: GlobalEvaluationState) -> Dict[str, Any]:
    """투자 승인된 스타트업의 보고서를 생성합니다."""
    current = state.get("current_evaluation", {})
    report = run_report_generation(current)
    current = {**current, "report_content": report}
    return {"current_evaluation": current}


def report_review_node(state: GlobalEvaluationState) -> Dict[str, Any]:
    """생성된 보고서를 검토하고 승인/피드백을 반환합니다."""
    current = state.get("current_evaluation", {})
    review = run_report_review(current.get("report_content", ""), current)

    # 검토 피드백을 current_evaluation에 기록 (보고서 수정 루프는 향후 확장)
    current = {**current, "report_review": review}
    return {"current_evaluation": current}


def finalize_startup_node(state: GlobalEvaluationState) -> Dict[str, Any]:
    """현재 스타트업 평가를 evaluations에 추가하고 루프 카운터를 증가시킵니다."""
    evaluations = list(state.get("evaluations", []))
    current = state.get("current_evaluation", {})

    if current:
        evaluations.append(current)

    return {
        "evaluations": evaluations,
        "current_startup": None,
        "current_evaluation": {},
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


# ── 조건부 엣지 함수 ───────────────────────────────────────────────────────

def route_after_explore(state: GlobalEvaluationState) -> str:
    """탐색 결과가 있으면 평가 시작, 없으면 종료."""
    if state.get("pending_startups"):
        return "has_candidates"
    return "no_candidates"


def route_after_decision(state: GlobalEvaluationState) -> str:
    """
    투자 판단 결과에 따라 분기:
      invest  → 보고서 생성
      pass    → 보고서 없이 다음 스타트업으로
    """
    current = state.get("current_evaluation", {})
    decision = current.get("investment_decision", {}).get("decision", "pass")
    if decision == "invest":
        return "generate_report"
    return "skip_report"


def route_after_finalize(state: GlobalEvaluationState) -> str:
    """남은 스타트업이 있고 반복 한도 미달이면 계속."""
    iteration_count = state.get("iteration_count", 0)
    max_iterations  = state.get("max_iterations", 10)

    if state.get("pending_startups") and iteration_count < max_iterations:
        return "next_startup"
    return "done"


# ── 그래프 구성 ────────────────────────────────────────────────────────────

def build_orchestrator() -> StateGraph:
    graph = StateGraph(GlobalEvaluationState)

    # 노드 등록
    graph.add_node("explore_startups",      explore_startups_node)
    graph.add_node("init_next_startup",     init_next_startup_node)
    graph.add_node("parallel_analysis",     parallel_analysis_node)
    graph.add_node("risk_assessment",       risk_assessment_node)
    graph.add_node("competitor_analysis",   competitor_analysis_node)
    graph.add_node("investment_decision",   investment_decision_node)
    graph.add_node("report_generation",     report_generation_node)
    graph.add_node("report_review",         report_review_node)
    graph.add_node("finalize_startup",      finalize_startup_node)

    # 엣지 연결
    graph.add_edge(START, "explore_startups")

    graph.add_conditional_edges(
        "explore_startups",
        route_after_explore,
        {"has_candidates": "init_next_startup", "no_candidates": END},
    )

    graph.add_edge("init_next_startup",   "parallel_analysis")
    graph.add_edge("parallel_analysis",   "risk_assessment")
    graph.add_edge("risk_assessment",     "competitor_analysis")
    graph.add_edge("competitor_analysis", "investment_decision")

    graph.add_conditional_edges(
        "investment_decision",
        route_after_decision,
        {"generate_report": "report_generation", "skip_report": "finalize_startup"},
    )

    graph.add_edge("report_generation", "report_review")
    graph.add_edge("report_review",     "finalize_startup")

    graph.add_conditional_edges(
        "finalize_startup",
        route_after_finalize,
        {"next_startup": "init_next_startup", "done": END},
    )

    return graph.compile()


orchestrator = build_orchestrator()


# ── 실행 헬퍼 ──────────────────────────────────────────────────────────────

def run_evaluation(
    target_domain: str = "robotics",
    target_subdomain: str = "",
    max_iterations: int = 5,
    max_candidates: int = 10,
    max_documents: int = 10,
    max_pages_per_document: int = 20,
    max_total_pages: int = 200,
    output_class: str = "",
    output_startup_label: str = "",
) -> GlobalEvaluationState:
    """
    전체 스타트업 평가 파이프라인을 실행합니다.

    Returns:
        GlobalEvaluationState: evaluations 리스트에 각 스타트업 평가 결과 포함
    """
    import uuid

    initial_state: GlobalEvaluationState = {
        "target_domain":          target_domain,
        "target_subdomain":       target_subdomain,
        "pending_startups":       [],
        "startup_info_map":       {},
        "current_startup":        None,
        "current_evaluation":     {},
        "evaluations":            [],
        "final_report_content":   "",
        "run_id":                 str(uuid.uuid4()),
        "max_iterations":         max_iterations,
        "max_candidates":         max_candidates,
        "iteration_count":        0,
        "max_documents":          max_documents,
        "max_pages_per_document": max_pages_per_document,
        "max_total_pages":        max_total_pages,
        "output_class":           output_class,
        "output_startup_label":   output_startup_label,
    }

    return orchestrator.invoke(initial_state)


# ── 실행 예시 ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    final_state = run_evaluation(
        max_iterations=3,
        max_documents=10,
    )

    print(f"\n=== 평가 완료: {len(final_state['evaluations'])}개 스타트업 ===\n")
    for ev in final_state["evaluations"]:
        name     = ev.get("startup_name", "?")
        decision = ev.get("investment_decision", {}).get("decision", "?")
        score    = ev.get("investment_score", 0)
        print(f"  {name}: {decision} (score={score})")

    print(json.dumps(final_state["evaluations"], ensure_ascii=False, indent=2))
