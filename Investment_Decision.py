import json
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from state import StartupEvaluationState

# LLM이 출력할 점수 및 근거 스키마 정의 (항목별 근거 분리)
class InvestmentScores(BaseModel):
    tech_score: int = Field(description="기술력 점수 (1~5점)")
    tech_reasoning: str = Field(description="기술력 점수 부여 근거 (1~2문장)")
    
    market_score: int = Field(description="시장성 점수 (1~5점)")
    market_reasoning: str = Field(description="시장성 점수 부여 근거 (1~2문장)")
    
    team_score: int = Field(description="팀 역량 점수 (1~5점)")
    team_reasoning: str = Field(description="팀 역량 점수 부여 근거 (1~2문장)")
    
    comp_score: int = Field(description="경쟁력 점수 (1~5점)")
    comp_reasoning: str = Field(description="경쟁력 점수 부여 근거 (1~2문장)")
    
    risk_score: int = Field(description="리스크 점수 (1~5점)")
    risk_reasoning: str = Field(description="리스크 점수 부여 근거 (1~2문장)")

def investment_decision_node(state: StartupEvaluationState) -> Dict[str, Any]:
    """투자 판단 노드: LLM을 통한 정성적 점수/근거 평가 + Python 로직을 통한 가중치/과락 판별"""
    startup_name = state.get("startup_name", "Unknown")
    print(f"\n==== [INVESTMENT DECISION: {startup_name}] ====\n")
    
    # 1. LLM 초기화 및 구조화된 출력 설정
    llm = ChatOpenAI(model="gpt-4.1-nano", temperature=0)
    structured_llm = llm.with_structured_output(InvestmentScores)

    # 2. 분석 데이터 취합
    analysis_data = {
        "tech_analysis": state.get("tech_analysis", {}),
        "market_analysis": state.get("market_analysis", {}),
        "team_info": state.get("startup_info", {}),
        "competitor_analysis": state.get("competitor_analysis", {})
    }
    
    # 3. 프롬프트 작성 (물류 로보틱스 도메인 적용)
    system_prompt = """당신은 물류 로보틱스(AGV, AMR, 자동화 창고 시스템 등) 전문 투자 심사역입니다. 
제공된 분석 데이터를 바탕으로 아래의 평가 지표에 따라 각 카테고리별로 1점, 3점, 5점 중 하나의 점수를 부여하고, 해당 점수를 부여한 명확한 근거를 제시하세요.

[평가 지표]
1. 기술력 (Tech)
   - 핵심 기술 독창성: 1=모방 수준 / 3=일부 차별화 / 5=독보적 IP
   - 기술 성숙도: 1=TRL 1~3 / 3=TRL 4~6 / 5=TRL 7~9
   - HW+SW 통합 역량: 1=SW만 / 3=일부 통합 / 5=완전 수직계열화
   * 세 항목을 종합하여 1~5점 사이의 대표 점수 1개와 근거 산출.

2. 시장성 (Market)
   - 목표 시장 규모(TAM): 1=<$100M / 3=$1B 수준 / 5=>$10B
   - 시장 성장률(CAGR): 1=<5% / 3=10~20% / 5=>30%
   - 고객 수요 검증: 1=없음 / 3=파일럿 중 / 5=매출 발생
   * 세 항목을 종합하여 1~5점 사이의 대표 점수 1개와 근거 산출.

3. 팀 역량 (Team)
   - 창업자 도메인 전문성: 1=비전공 / 3=관련 경력 / 5=석박사+산업경험
   - 팀 완성도: 1=1인팀 / 3=일부 구성 / 5=풀팀 완비
   - 투자·파트너십 이력: 1=없음 / 3=시드 유치 / 5=Series A 이상
   * 세 항목을 종합하여 1~5점 사이의 대표 점수 1개와 근거 산출.

4. 경쟁력 (Competitive)
   - 경쟁사 대비 차별화 포인트: 1=동일 / 3=일부 차별화 / 5=명확한 해자
   - 진입장벽: 1=없음 / 3=일부 / 5=복합적 해자
   * 두 항목을 종합하여 1~5점 사이의 대표 점수 1개와 근거 산출.

5. 리스크 (Risk)
   - 규제 리스크: 1=높음(불확실) / 3=보통 / 5=낮음(명확)
   - 재무 지속가능성: 1=<6개월 / 3=12개월 / 5=>24개월
   * 두 항목을 종합하여 1~5점 사이의 대표 점수 1개와 근거 산출."""

    human_prompt = f"""다음은 {startup_name}에 대한 분석 데이터입니다.
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}

위 데이터를 바탕으로 각 부문의 점수와 근거를 평가해 주세요."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", human_prompt)
    ])

    # 4. LLM 평가 실행 (점수 및 항목별 근거 추출)
    print("==== [LLM EVALUATING SCORES & REASONING] ====")
    chain = prompt | structured_llm
    llm_scores: InvestmentScores = chain.invoke({})
    
    s_tech = llm_scores.tech_score
    s_market = llm_scores.market_score
    s_team = llm_scores.team_score
    s_comp = llm_scores.comp_score
    s_risk = llm_scores.risk_score
    scores = [s_tech, s_market, s_team, s_comp, s_risk]

    # 5. 파이썬 로직을 통한 엄격한 산술 계산 및 과락 판별
    print("==== [CALCULATING FINAL SCORE & VETO CHECK] ====")
    rejection_reason = ""

    # 거부권(Veto) 로직: 단일 카테고리 1점 발생 시 총점 무관 즉시 "보류"
    if any(s <= 1 for s in scores):
        decision = "보류"
        # 1점을 받은 카테고리 식별
        failed_categories = []
        if s_tech <= 1: failed_categories.append("기술력")
        if s_market <= 1: failed_categories.append("시장성")
        if s_team <= 1: failed_categories.append("팀 역량")
        if s_comp <= 1: failed_categories.append("경쟁력")
        if s_risk <= 1: failed_categories.append("리스크")
        
        rejection_reason = f"필수 조건 미달(과락): {', '.join(failed_categories)} 부문 1점 발생. (총점 무관 즉시 보류)"
        final_score = (sum(scores) / len(scores)) * 20 # 참고용 단순 평균
        
    else:
        # 가중치 합산: Tech 25%, Market 25%, Team 20%, Comp 15%, Risk 15%
        total_weighted = (
            (s_tech * 0.25) + 
            (s_market * 0.25) + 
            (s_team * 0.20) + 
            (s_comp * 0.15) + 
            (s_risk * 0.15)
        )
        final_score = round(total_weighted * 20, 2) # 100점 만점 환산
        
        # 70점 이상 투자, 미만 보류
        if final_score >= 70:
            decision = "투자"
        else:
            decision = "보류"
            rejection_reason = f"총점 미달: {final_score}점으로 기준치(70점)에 도달하지 못함."

    # 6. 메시지(이력) 업데이트
    messages = state.get("messages", [])
    if rejection_reason:
        messages.append({"role": "assistant", "content": rejection_reason})

    print(f"Scores -> Tech:{s_tech}, Market:{s_market}, Team:{s_team}, Comp:{s_comp}, Risk:{s_risk}")
    print(f"Final Decision: {decision} | Final Score: {final_score}")

    return {
        "investment_score": final_score,
        "investment_decision": decision,
        "messages": messages,
        # 항목별 평가 근거를 State에 저장
        "evaluation_reasoning": {
            "tech_reasoning": llm_scores.tech_reasoning,
            "market_reasoning": llm_scores.market_reasoning,
            "team_reasoning": llm_scores.team_reasoning,
            "comp_reasoning": llm_scores.comp_reasoning,
            "risk_reasoning": llm_scores.risk_reasoning
        },
        # 각 분석 딕셔너리에 점수 매핑
        "tech_analysis": {**state.get("tech_analysis", {}), "score": s_tech},
        "market_analysis": {**state.get("market_analysis", {}), "score": s_market},
        "competitor_analysis": {**state.get("competitor_analysis", {}), "score": s_comp},
        "startup_info": {**state.get("startup_info", {}), "team_score": s_team, "risk_score": s_risk}
    }