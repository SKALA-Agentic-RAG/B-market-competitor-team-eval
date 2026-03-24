from typing_extensions import NotRequired, TypedDict

from state import StartupEvaluationState


class ReportReviewResult(TypedDict):
    approved: bool
    feedback: str


class ReportReviewNodeState(TypedDict):
    current_evaluation: NotRequired[StartupEvaluationState]
    report_review: NotRequired[ReportReviewResult]


class ReportReviewNodeOutput(TypedDict):
    current_evaluation: NotRequired[StartupEvaluationState]
    report_review: NotRequired[ReportReviewResult]


# 설계 목차에 맞춘 필수 섹션 목록
REQUIRED_SECTIONS = [
    "SUMMARY",
    "기업 개요",
    "핵심 기술 분석",
    "시장 분석",
    "경쟁사 분석",
    "투자 평가",
    "위험 요소",
    "결론 및 투자 권고",
    "REFERENCE",
]


def run_report_review(
    report_content: str,
    current_evaluation: StartupEvaluationState,
) -> ReportReviewResult:
    """
    생성된 보고서가 설계 목차(9개 섹션)를 충족하는지 검토합니다.
    Returns: {"approved": bool, "feedback": str}
    """
    content = report_content or ""
    missing = [section for section in REQUIRED_SECTIONS if section not in content]

    if missing:
        return {
            "approved": False,
            "feedback": f"필수 섹션 누락: {', '.join(missing)}",
        }

    # 핵심 데이터 존재 여부 추가 검토
    warnings = []
    score = current_evaluation.get("investment_score", 0.0)
    if score == 0.0:
        warnings.append("종합 점수가 0점 — 평가 데이터 확인 필요")

    decision = (current_evaluation.get("investment_decision") or {}).get("decision")
    if not decision:
        warnings.append("투자 판단 결과 누락")

    if warnings:
        return {
            "approved": True,
            "feedback": "형식 검토 통과 (경고: " + "; ".join(warnings) + ")",
        }

    return {"approved": True, "feedback": "형식 검토 통과"}


def report_review_node(state: ReportReviewNodeState) -> ReportReviewNodeOutput:
    """기존 노드 스타일 호환 래퍼."""
    if "current_evaluation" in state:
        current = state["current_evaluation"]
        review = run_report_review(current.get("report_content", ""), current)
        current = {**current, "report_review": review}
        return {"current_evaluation": current}
    return {"report_review": {"approved": False, "feedback": "검토 대상이 없습니다."}}
