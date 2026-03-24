from typing import Dict, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from state import GlobalEvaluationState

# 평가를 위한 데이터 모델 정의
class ReportEvaluation(BaseModel):
    """보고서 품질 및 제약조건 준수 여부를 평가하는 구조화된 출력"""
    decision: str = Field(
        description="모든 기준을 충족하면 '승인', 하나라도 미달하거나 인덱스 오류가 있으면 '반려'"
    )
    feedback: str = Field(
        description="반려 시 어느 부분이 부족했는지(예: 3번 인덱스 부재 등) 상세 사유. 승인 시 빈 문자열"
    )

def report_review_node(state: GlobalEvaluationState) -> Dict[str, Any]:
    """보고서 평가 노드: Structured Output을 활용한 엄격한 자기 평가"""
    print("\n==== [CHECK REPORT QUALITY & CONSTRAINTS] ====\n")
    
    report_content = state.get("final_report_content", "")
    iteration = state.get("iteration_count", 0)

    # 평가용 LLM 초기화 (환각 최소화를 위해 temperature=0)
    llm = ChatOpenAI(model="gpt-4.1-nano", temperature=0)
    structured_llm_grader = llm.with_structured_output(ReportEvaluation)

    system_prompt = "당신은 전문 투자 보고서 검수관입니다. 보고서를 엄격히 평가하여 '승인' 또는 '반려'를 결정하세요."
    human_prompt = f"""[평가 대상 보고서]
{report_content}

[평가 기준]
1. 목차 준수: 아래 9개 항목이 모두 포함되었는가?
   - SUMMARY, 기업 개요, 핵심 기술 분석, 시장 분석, 경쟁 분석, 투자 평가, 위험 요소, 결론 및 투자 권고, REFERENCE
2. 기업 정보 충분성: '기업 개요'에 이름, 설립일, 설립자 등 구체적 정보가 담겨 있는가?
3. 근거 및 출처 확인: 기술, 시장, 경쟁, 투자 평가 섹션에 점수를 뒷받침하는 구체적 근거가 있는가?
4. 참조 인덱스 정합성 (CRITICAL):
   - 본문 내의 모든 주장 뒤에 [n] 형태의 인덱스가 붙어 있는가?
   - 본문의 인덱스 번호가 'REFERENCE' 섹션의 번호와 정확히 일치하며 존재하는가?

위 모든 내용 중 한 가지라도 통과하지 못하거나, 인덱스가 매칭되지 않으면 즉시 '반려'하세요.
"""

    grade_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", human_prompt)
    ])

    # 체인 실행
    review_chain = grade_prompt | structured_llm_grader
    evaluation: ReportEvaluation = review_chain.invoke({})

    is_approved = (evaluation.decision == "승인")

    # 분기 로직: 재작성 필요 여부 판단
    if not is_approved and iteration < 3:
        print(f"==== [GRADE: REPORT REJECTED] Reason: {evaluation.feedback} ====")
        # 보고서 내용은 그대로 두고, 피드백만 review_feedback에 담아 반환
        return {
            "iteration_count": iteration + 1,
            "run_id": "RETRY_REQUIRED",
            "review_feedback": evaluation.feedback
        }

    if is_approved:
        print("==== [GRADE: REPORT APPROVED] ====")
    else:
        print("==== [GRADE: MAX RETRIES REACHED. FORCED PASS] ====")
        
    final_status = "APPROVED" if is_approved else "FAILED_AFTER_RETRIES"
    
    # 통과 혹은 강제 통과 시 피드백 변수는 빈 상태로 둠
    return {
        "run_id": final_status,
        "iteration_count": iteration,
        "review_feedback": None
    }