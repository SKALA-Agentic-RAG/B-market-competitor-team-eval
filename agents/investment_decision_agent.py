from typing import Any, Dict, Literal
from typing_extensions import TypedDict

from orchestrator import run_investment_decision
from state import InvestmentDecision, StartupEvaluationState


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
    """오케스트레이터 규약(decision/investment_score/confidence/rationale)을 따르는 투자판단 래퍼."""
    return run_investment_decision(current_evaluation)  # type: ignore[return-value]


def investment_decision_node(state: StartupEvaluationState) -> InvestmentDecisionNodeOutput:
    """입력 state에서 평가 데이터를 읽어 현재 파이프라인 형식으로 반환합니다."""
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