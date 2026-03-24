import json
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from state import GlobalEvaluationState

def report_generation_node(state: GlobalEvaluationState) -> Dict[str, Any]:
    """보고서 생성 노드: LLM(gpt-4.1-nano)을 이용해 문맥이 연결된 보고서 작성"""
    print("\n==== [GENERATE REPORT] ====\n")
    
    evaluations = state.get("evaluations", [])
    passed_startups = [e for e in evaluations if e.get("investment_decision") == "투자"]
    
    llm = ChatOpenAI(model="gpt-4.1-nano", temperature=0.2)
    system_prompt_role = "당신은 물류 로보틱스(AGV, AMR 등) 전문 투자 심사역입니다."
    
    # 데이터 직렬화 및 프롬프트 분기
    if passed_startups:
        startups_data = []
        for s in passed_startups:
            startups_data.append({
                "startup_name": s.get("startup_name"),
                "startup_info": s.get("startup_info"),
                "tech_analysis": s.get("tech_analysis", {}),
                "market_analysis": s.get("market_analysis", {}),
                "competitor_analysis": s.get("competitor_analysis", {}),
                "investment_score": s.get("investment_score"),
                "evaluation_reasoning": s.get("evaluation_reasoning", {}), # 근거 추가 활용
                "references": s.get("references", ["내부 분석 데이터", "시장 조사 보고서"])
            })
        data_str = json.dumps(startups_data, ensure_ascii=False, indent=2)
        
        human_prompt = f"""아래 제공된 스타트업 분석 데이터를 바탕으로 [최종 투자 승인 기업 상세 보고서]를 작성하세요.

[분석 데이터]
{data_str}

[작성 지침]
1. 다음 9가지 목차를 반드시 포함하여 순서대로 작성하세요: SUMMARY (핵심 요약), 기업 개요, 핵심 기술 분석, 시장 분석, 경쟁 분석, 투자 평가, 위험 요소, 결론 및 투자 권고, REFERENCE.
2. 본문 내의 모든 주요 분석, 평가, 수치 정보 뒤에는 반드시 데이터 출처를 나타내는 인덱스(예: [1], [2])를 기재하세요.
3. 'REFERENCE' 섹션에는 본문에 사용된 인덱스 번호와 분석 데이터에 포함된 참조 문헌(references 필드)을 정확히 매칭하여 나열하세요.
4. 승인된 스타트업이 여러 곳일 경우, 각각의 보고서를 작성하되 하나의 문서로 자연스럽게 연결하세요.
"""
    else:
        rejected_data = []
        for s in evaluations:
            reason = s.get("messages", [{"content": "기준 미달"}])[-1]["content"] if s.get("messages") else "기준 미달"
            rejected_data.append({
                "startup_name": s.get("startup_name"),
                "investment_score": s.get("investment_score"),
                "rejection_reason": reason
            })
        data_str = json.dumps(rejected_data, ensure_ascii=False, indent=2)
        
        human_prompt = f"""심사한 모든 스타트업이 투자 보류 판정을 받았습니다. 아래 데이터를 바탕으로 [전체 스타트업 투자 반려 사유 요약 보고서]를 작성하세요.

[분석 데이터]
{data_str}

[작성 지침]
1. 각 기업명, 최종 점수, 구체적인 반려 사유를 명시하세요.
2. 반려 사유 및 점수 내용 뒤에 [1] 형태의 참조 인덱스를 달아주세요.
3. 하단 'REFERENCE' 섹션에 [1] 투자판단 에이전트 분석 결과 등으로 출처를 기재하여 형식적 완결성을 맞추세요.
"""

    # 재작성 피드백 주입 로직 (Global State의 review_feedback 변수 활용)
    review_feedback = state.get("review_feedback")
    if review_feedback:
        print("==== [APPLYING REWRITE FEEDBACK] ====")
        human_prompt += f"""

[이전 평가 반려 사유 및 수정 지시사항]
{review_feedback}

위 지시사항을 철저히 반영하여 이전 보고서의 부족한 부분을 수정 및 보완하여 다시 작성하세요.
"""

    # Chain 구성 및 실행
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt_role),
        ("human", human_prompt)
    ])
    
    rag_chain = prompt_template | llm | StrOutputParser()
    report_text = rag_chain.invoke({})

    # 보고서를 다시 생성했으므로 review_feedback 상태는 초기화(None)하여 다음 검토에 대비
    return {"final_report_content": report_text, "review_feedback": None}