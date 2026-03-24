import re
from typing import Any, Dict, Literal
from typing_extensions import TypedDict

from state import InvestmentDecision, StartupEvaluationState


CATEGORY_WEIGHTS = {
    "tech": 0.25,
    "market": 0.25,
    "team": 0.20,
    "competitive": 0.15,
    "risk": 0.15,
}

INVEST_THRESHOLD = 70.0


# ── 스코어 헬퍼 ────────────────────────────────────────────────────────────

def _clamp_score(value: Any, default: float = 1.0) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return default
    return max(1.0, min(5.0, score))


def _average(scores: list) -> float:
    return sum(scores) / len(scores) if scores else 1.0


def _contains_any(text: str, keywords: tuple) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _risk_grade_to_score(grade: Any) -> float:
    mapping = {
        "상": 1.0, "high": 1.0,
        "중": 3.0, "medium": 3.0, "med": 3.0,
        "하": 5.0, "low": 5.0,
    }
    if grade is None:
        return 1.0
    return mapping.get(str(grade).strip().lower(), 1.0)


def _extract_runway_months(*texts: Any):
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
    combined = " ".join([
        str(tech_analysis.get("ip_status") or ""),
        str(tech_analysis.get("differentiation") or ""),
        " ".join(str(item) for item in tech_analysis.get("strengths", [])),
    ])
    tech_score = tech_analysis.get("tech_score")
    if _contains_any(combined, ("독보", "독점", "patent", "특허", "proprietary", "고유", "차별화 우위")) or (
        tech_score is not None and float(tech_score) >= 85
    ):
        return 5.0
    if _contains_any(combined, ("차별", "강점", "우위", "개선", "independent", "in-house", "차별화")) or (
        tech_score is not None and float(tech_score) >= 60
    ):
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
        bool(indicators.get(key)) for key in ("dof", "payload", "reach", "speed", "power_source")
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


def _score_market_metrics(market_analysis: Dict[str, Any]) -> Dict[str, float]:
    if market_analysis.get("assessment_status") != "completed":
        return {"tam": 1.0, "cagr": 1.0, "demand_validation": 1.0}
    scores = market_analysis.get("scores", {}) or {}
    return {
        "tam": _clamp_score(scores.get("tam")),
        "cagr": _clamp_score(scores.get("cagr")),
        "demand_validation": _clamp_score(scores.get("demand_validation")),
    }


def _score_team_metrics(team_assessment: Dict[str, Any]) -> Dict[str, float]:
    if (
        team_assessment.get("assessment_status") != "completed"
        or not team_assessment.get("data_sufficient", True)
    ):
        return {"domain_expertise": 1.0, "team_completeness": 1.0, "funding_track": 1.0}
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
    market_analysis = current_evaluation.get("market_analysis", {}) or {}
    team_assessment = current_evaluation.get("team_assessment", {}) or {}
    competitor_analysis = current_evaluation.get("competitor_analysis", {}) or {}
    risk_assessment = current_evaluation.get("risk_assessment", {}) or {}

    category_metrics = {
        "tech": {
            "core_tech_originality": _score_tech_originality(tech_analysis),
            "trl": _score_tech_trl(tech_analysis),
            "hw_sw_integration": _score_hw_sw_integration(tech_analysis),
        },
        "market": _score_market_metrics(market_analysis),
        "team": _score_team_metrics(team_assessment),
        "competitive": _score_competitive_metrics(competitor_analysis),
        "risk": _score_risk_metrics(risk_assessment),
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
        "market_evidence": market_analysis.get("assessment_status") == "completed",
        "team_evidence": team_assessment.get("assessment_status") == "completed",
        "team_data_sufficient": bool(team_assessment.get("data_sufficient", True)),
        "competitive_evidence": competitor_analysis.get("assessment_status") == "completed",
        "risk_evidence": risk_assessment.get("assessment_status") == "completed",
    }
    breakdown["data_quality"] = {
        "critical_data_missing": not all([
            evidence_flags["tech_evidence"],
            evidence_flags["market_evidence"],
            evidence_flags["team_data_sufficient"],
            evidence_flags["competitive_evidence"],
            evidence_flags["risk_evidence"],
        ]),
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
            "기술 {tech:.2f}, 시장 {market:.2f}, 팀 {team:.2f}, 경쟁 {competitive:.2f}, 리스크 {risk:.2f}"
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


# ── TypedDict ─────────────────────────────────────────────────────────────

class InvestmentDecisionComputation(TypedDict):
    decision: Literal["invest", "pass"]
    investment_score: float
    confidence: float
    rationale: str
    score_breakdown: Dict[str, Any]


class InvestmentDecisionNodeOutput(TypedDict):
    investment_score: float
    score_breakdown: Dict[str, Any]
    investment_decision: InvestmentDecision


def run_investment_decision_agent(
    current_evaluation: StartupEvaluationState,
) -> InvestmentDecisionComputation:
    return run_investment_decision(current_evaluation)  # type: ignore[return-value]


def investment_decision_node(state: StartupEvaluationState) -> InvestmentDecisionNodeOutput:
    result = run_investment_decision_agent(state)
    return {
        "investment_score": result.get("investment_score", 0.0),
        "score_breakdown": result.get("score_breakdown", {}),
        "investment_decision": {
            "decision": result.get("decision", "pass"),
            "confidence": result.get("confidence", 0.0),
            "rationale": result.get("rationale", ""),
        },
    }
