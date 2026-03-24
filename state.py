from typing import Dict, Any, List, Optional, Literal
from typing_extensions import TypedDict

# 투자 결정 상태를 명확히 제한하기 위한 Literal 타입 정의
InvestmentDecision = Literal["투자", "보류", "부결"]

class StartupEvaluationState(TypedDict):
    """개별 스타트업 평가를 위한 상태 정의"""
    
    # 평가 대상 스타트업명
    startup_name: str
    
    # 기본정보 (company, founded, funding 등)
    startup_info: Dict[str, Any]
    
    # 기술 분석 결과
    tech_analysis: Dict[str, Any]
    
    # 시장성 분석 결과
    market_analysis: Dict[str, Any]
    
    # 경쟁사 분석 결과
    competitor_analysis: Dict[str, Any]
    
    # 최종 투자 점수 (100점 만점 환산)
    investment_score: float
    
    # '투자' | '보류' | '부결'
    investment_decision: InvestmentDecision
    
    # 스타트업별 요약 보고서 내용(또는 섹션 텍스트)
    report_content: str
    
    # LLM 대화/검증 로그 (주로 반려 사유 등 기록용)
    messages: List[Dict[str, Any]]
    
    # RAG 검색 문헌 출처 리스트 (보고서 생성 에이전트의 Citation 번호 매칭 용도)
    references: List[str]
    
    # 각 카테고리별 평가 점수 산정 근거 (LLM이 추출한 이유를 저장하여 보고서 작성 시 활용)
    evaluation_reasoning: Dict[str, str]


class GlobalEvaluationState(TypedDict):
    """전체 그래프 흐름 및 멀티 스타트업 관리를 위한 글로벌 상태 정의"""
    
    # 아직 평가하지 않은 후보 스타트업 목록
    pending_startups: List[str]
    
    # 현재 평가 중인 스타트업 (루프 제어용)
    current_startup: Optional[str]
    
    # 지금까지 평가한 스타트업 결과 누적 (여러 번 반복 평가)
    evaluations: List[StartupEvaluationState]
    
    # 최종(전체) 보고서 내용
    final_report_content: str
    
    # 보고서 평가 에이전트(Step 10)가 보고서 생성 에이전트에게 보내는 재작성 피드백 전달용
    review_feedback: Optional[str]
    
    # 현재 그래프 실행 ID / 추적용
    run_id: str
    
    # 안전장치/가드레일: 반복 횟수 제한 (예: 재작성 최대 3회)
    max_iterations: int
    
    # 현재까지 수행한 반복 횟수
    iteration_count: int
    
    # RAG 문서 제한 (과제 규칙 enforce를 위한 필드)
    max_documents: int
    max_pages_per_document: int
    
    # 하드 가드레일 (예: 총 200p 제한)
    max_total_pages: int
    
    # 보고서 파일명 규칙용 (과제 제출 포맷 맞추기, 예: "14")
    output_class: str
    
    # 스타트업 레이블 (예: "Name1+Name2+Name3+Name4")
    output_startup_label: str