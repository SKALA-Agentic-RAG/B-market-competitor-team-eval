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

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from langgraph.graph import StateGraph, START, END

from state import GlobalEvaluationState
from agents.competitor_analysis_agent import run_competitor_analysis
from agents.team_eval_agent import run_team_assessment
from agents.startup_exploration_agent import run_startup_exploration
from agents.tech_analysis_agent import run_tech_analysis
from agents.risk_assessment_agent import run_risk_assessment
from agents.report_generation_agent import run_report_generation as external_run_report_generation
from agents.report_review_agent import run_report_review as external_run_report_review

CATEGORY_WEIGHTS = {
    "tech": 0.35,
    "team": 0.25,
    "competitive": 0.20,
    "risk": 0.20,
}

INVEST_THRESHOLD = 70.0


def _clamp_score(value: Any, default: float = 1.0) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return default
    return max(1.0, min(5.0, score))


def _average(scores: list[float]) -> float:
    return sum(scores) / len(scores) if scores else 1.0


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _risk_grade_to_score(grade: Any) -> float:
    mapping = {
        "상": 1.0,
        "high": 1.0,
        "중": 3.0,
        "medium": 3.0,
        "med": 3.0,
        "하": 5.0,
        "low": 5.0,
    }
    if grade is None:
        return 1.0
    return mapping.get(str(grade).strip().lower(), 1.0)


def _extract_runway_months(*texts: Any) -> float | None:
    combined = " ".join(str(text or "") for text in texts)
    patterns = [
        r"(\d+(?:\.\d+)?)\s*(?:개월|달)",
        r"(\d+(?:\.\d+)?)\s*(?:months?|mos?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, combined, flags=re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    return None


def _score_tech_originality(tech_analysis: Dict[str, Any]) -> float:
    rubric_score = (
        ((tech_analysis.get("rubric_scores") or {}).get("core_tech_originality") or {}).get("score")
    )
    if rubric_score is not None:
        return _clamp_score(rubric_score)

    if tech_analysis.get("assessment_status") != "completed":
        return 1.0

    combined = " ".join(
        [
            str(tech_analysis.get("ip_status") or ""),
            str(tech_analysis.get("differentiation") or ""),
            " ".join(str(item) for item in tech_analysis.get("strengths", [])),
        ]
    )
    tech_score = tech_analysis.get("tech_score")

    if _contains_any(
        combined,
        ("독보", "독점", "patent", "특허", "proprietary", "고유", "차별화 우위"),
    ) or (tech_score is not None and float(tech_score) >= 85):
        return 5.0

    if _contains_any(
        combined,
        ("차별", "강점", "우위", "개선", "independent", "in-house", "차별화"),
    ) or (tech_score is not None and float(tech_score) >= 60):
        return 3.0

    return 1.0


def _score_tech_trl(tech_analysis: Dict[str, Any]) -> float:
    rubric_score = (
        ((tech_analysis.get("rubric_scores") or {}).get("trl") or {}).get("score")
    )
    if rubric_score is not None:
        return _clamp_score(rubric_score)

    trl_level = tech_analysis.get("trl_level")
    if trl_level is None:
        return 1.0
    try:
        trl = int(trl_level)
    except (TypeError, ValueError):
        return 1.0

    if trl >= 7:
        return 5.0
    if trl >= 4:
        return 3.0
    return 1.0


def _score_hw_sw_integration(tech_analysis: Dict[str, Any]) -> float:
    rubric_score = (
        ((tech_analysis.get("rubric_scores") or {}).get("hw_sw_integration") or {}).get("score")
    )
    if rubric_score is not None:
        return _clamp_score(rubric_score)

    if tech_analysis.get("assessment_status") != "completed":
        return 1.0

    indicators = tech_analysis.get("core_tech_indicators", {}) or {}
    hardware_signals = sum(
        bool(indicators.get(key))
        for key in ("dof", "payload", "reach", "speed", "power_source")
    )
    hardware_signals += 1 if indicators.get("sensors") else 0

    software_signals = sum(
        bool(indicators.get(key)) for key in ("autonomy_level", "communication")
    )
    software_signals += 1 if indicators.get("ai_algorithms") else 0

    if hardware_signals >= 3 and software_signals >= 2:
        return 5.0
    if hardware_signals >= 1 and software_signals >= 1:
        return 3.0
    return 1.0


def _score_team_metrics(team_assessment: Dict[str, Any]) -> Dict[str, float]:
    if (
        team_assessment.get("assessment_status") != "completed"
        or not team_assessment.get("data_sufficient", True)
    ):
        return {
            "domain_expertise": 1.0,
            "team_completeness": 1.0,
            "funding_track": 1.0,
        }

    scores = team_assessment.get("scores", {}) or {}
    return {
        "domain_expertise": _clamp_score(scores.get("domain_expertise")),
        "team_completeness": _clamp_score(scores.get("team_completeness")),
        "funding_track": _clamp_score(scores.get("funding_track")),
    }


def _score_competitive_metrics(competitor_analysis: Dict[str, Any]) -> Dict[str, float]:
    if competitor_analysis.get("assessment_status") != "completed":
        return {"differentiation": 1.0, "moat": 1.0}

    scores = competitor_analysis.get("scores", {}) or {}
    return {
        "differentiation": _clamp_score(scores.get("differentiation")),
        "moat": _clamp_score(scores.get("moat")),
    }


def _score_risk_metrics(risk_assessment: Dict[str, Any]) -> Dict[str, float]:
    rubric_scores = risk_assessment.get("rubric_scores") or {}
    regulatory_rubric = (rubric_scores.get("regulatory_risk") or {}).get("score")
    runway_rubric = (rubric_scores.get("runway") or {}).get("score")
    if regulatory_rubric is not None and runway_rubric is not None:
        return {
            "regulatory": _clamp_score(regulatory_rubric),
            "runway": _clamp_score(runway_rubric),
        }

    if risk_assessment.get("assessment_status") != "completed":
        return {"regulatory": 1.0, "runway": 1.0}

    regulatory = risk_assessment.get("regulatory_risks", {}) or {}
    market_risks = risk_assessment.get("market_risks", {}) or {}

    regulatory_scores = [
        _risk_grade_to_score(regulatory.get("iso_10218_risk_grade")),
        _risk_grade_to_score(regulatory.get("safety_cert_risk_grade")),
        _risk_grade_to_score(regulatory.get("export_risk_grade")),
        _risk_grade_to_score(regulatory.get("trl_risk_grade")),
    ]

    runway_months = _extract_runway_months(
        market_risks.get("burn_rate_risk"),
        market_risks.get("funding_dependency"),
        risk_assessment.get("investment_caution"),
    )
    if runway_months is not None:
        if runway_months >= 24:
            runway_score = 5.0
        elif runway_months >= 12:
            runway_score = 3.0
        else:
            runway_score = 1.0
    else:
        runway_score = _risk_grade_to_score(market_risks.get("financial_risk_grade"))

    return {
        "regulatory": _average(regulatory_scores),
        "runway": runway_score,
    }


def _build_score_breakdown(current_evaluation: Dict[str, Any]) -> Dict[str, Any]:
    tech_analysis = current_evaluation.get("tech_analysis", {}) or {}
    team_assessment = current_evaluation.get("team_assessment", {}) or {}
    competitor_analysis = current_evaluation.get("competitor_analysis", {}) or {}
    risk_assessment = current_evaluation.get("risk_assessment", {}) or {}

    tech_metrics = {
        "core_tech_originality": _score_tech_originality(tech_analysis),
        "trl": _score_tech_trl(tech_analysis),
        "hw_sw_integration": _score_hw_sw_integration(tech_analysis),
    }
    team_metrics = _score_team_metrics(team_assessment)
    competitive_metrics = _score_competitive_metrics(competitor_analysis)
    risk_metrics = _score_risk_metrics(risk_assessment)

    category_metrics = {
        "tech": tech_metrics,
        "team": team_metrics,
        "competitive": competitive_metrics,
        "risk": risk_metrics,
    }

    breakdown: Dict[str, Any] = {}
    total_score = 0.0
    for category, metrics in category_metrics.items():
        average_score = _average(list(metrics.values()))
        weighted_score = average_score * CATEGORY_WEIGHTS[category] * 20
        total_score += weighted_score
        breakdown[category] = {
            "weight": CATEGORY_WEIGHTS[category],
            "average_score": round(average_score, 2),
            "weighted_score": round(weighted_score, 2),
            "metrics": {key: round(value, 2) for key, value in metrics.items()},
        }

    evidence_flags = {
        "tech_evidence": tech_analysis.get("assessment_status") == "completed",
        "team_evidence": team_assessment.get("assessment_status") == "completed",
        "team_data_sufficient": bool(team_assessment.get("data_sufficient", True)),
        "competitive_evidence": competitor_analysis.get("assessment_status") == "completed",
        "risk_evidence": risk_assessment.get("assessment_status") == "completed",
    }

    breakdown["data_quality"] = {
        "critical_data_missing": not all(
            [
                evidence_flags["tech_evidence"],
                evidence_flags["team_data_sufficient"],
                evidence_flags["competitive_evidence"],
                evidence_flags["risk_evidence"],
            ]
        ),
        "evidence_flags": evidence_flags,
        "hold_reason": current_evaluation.get("hold_reason"),
    }
    breakdown["total_score"] = round(total_score, 2)

    return breakdown


def run_investment_decision(current_evaluation: Dict[str, Any]) -> Dict[str, Any]:
    """평가표 기준으로 세부 점수를 집계해 투자 판단을 계산합니다."""
    breakdown = _build_score_breakdown(current_evaluation)
    total_score = breakdown["total_score"]
    critical_data_missing = breakdown["data_quality"]["critical_data_missing"]
    category_averages = {
        category: data["average_score"]
        for category, data in breakdown.items()
        if category in CATEGORY_WEIGHTS
    }
    veto_categories = [name for name, value in category_averages.items() if value <= 1.0]

    if veto_categories:
        decision = "pass"
    elif total_score >= INVEST_THRESHOLD and not critical_data_missing:
        decision = "invest"
    else:
        decision = "pass"

    evidence_flags = breakdown["data_quality"]["evidence_flags"]
    evidence_ratio = sum(1.0 for flag in evidence_flags.values() if flag) / len(evidence_flags)

    if decision == "invest":
        margin = min(1.0, max(0.0, (total_score - INVEST_THRESHOLD) / 20.0))
    else:
        margin = min(1.0, max(0.0, (INVEST_THRESHOLD - total_score) / 20.0))

    confidence = round(
        max(0.35, min(0.95, 0.45 + (0.30 * evidence_ratio) + (0.20 * margin))),
        2,
    )

    strongest_category = max(category_averages, key=category_averages.get)
    weakest_category = min(category_averages, key=category_averages.get)

    rationale_parts = [
        f"총점 {total_score:.2f}/100",
        (
            "기술 {tech:.2f}, 팀 {team:.2f}, 경쟁 {competitive:.2f}, 리스크 {risk:.2f}"
        ).format(**category_averages),
        f"강점 카테고리: {strongest_category}",
        f"보완 필요 카테고리: {weakest_category}",
    ]
    if veto_categories:
        rationale_parts.append(
            "거부권 발동: 단일 카테고리 1점(평균 1.0) 발생으로 총점과 무관하게 보류"
        )
        rationale_parts.append(f"과락 카테고리: {', '.join(veto_categories)}")
    if critical_data_missing:
        rationale_parts.append("핵심 근거 데이터가 일부 부족해 투자 승인은 보수적으로 보류")
    if current_evaluation.get("hold_reason"):
        rationale_parts.append(f"보류 사유: {current_evaluation['hold_reason']}")

    return {
        "decision": decision,
        "investment_score": total_score,
        "confidence": confidence,
        "rationale": " | ".join(rationale_parts),
        "score_breakdown": breakdown,
    }


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
    """기술력 분석 / 팀 평가를 병렬로 실행합니다."""
    startup_name = state["current_startup"]
    startup_info = state.get("startup_info_map", {}).get(startup_name, {})
    domain = state["target_domain"]
    max_docs = state.get("max_documents", 5)

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_tech = executor.submit(run_tech_analysis, startup_name, startup_info, domain, max_docs)
        future_team = executor.submit(run_team_assessment, startup_name, startup_info, domain, max_docs)

        tech_result = future_tech.result()
        team_result = future_team.result()

    current = {**state.get("current_evaluation", {})}
    current["tech_analysis"]   = tech_result
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
