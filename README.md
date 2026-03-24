# AI Startup Investment Evaluation Agent

본 프로젝트는 로보틱스(Robotics) 도메인 스타트업에 대한 투자 가능성을 자동으로 평가하는 멀티 에이전트 시스템을 설계하고 구현한 실습 프로젝트입니다.

## Overview

- **Objective** : AI 스타트업의 기술력, 팀 역량, 경쟁력, 리스크를 기준으로 투자 적합성을 자동 분석
- **Method** : Multi-Agent System + Agentic RAG (LangGraph 기반 상태 그래프)
- **Tools** : ChromaDB (벡터 검색), OpenAI GPT-4o-mini (LLM), BAAI/bge-m3 (임베딩)

## Features

- PDF 자료 기반 정보 추출 (IR 자료, 시장 리포트, 특허 명세서, 규제 문서 등)
- 4개 평가 항목 가중 점수화 → 투자 / 보류 자동 판단 (임계값 70점)
- 기술력·팀·경쟁력·리스크 병렬 분석으로 처리 속도 최적화
- 투자 승인 스타트업 대상 구조화 보고서 자동 생성 (9개 섹션)

## Tech Stack

| Category  | Details                                          |
|-----------|--------------------------------------------------|
| Framework | LangGraph, LangChain, Python 3.11                |
| LLM       | GPT-4o-mini via OpenAI API                       |
| Retrieval | ChromaDB (벡터 DB), Agentic RAG (관련성 재평가)  |
| Embedding | BAAI/bge-m3 (multilingual, 최대 8,192 토큰)      |
| Package   | uv (가상환경 및 의존성 관리)                     |

## Agents

| 에이전트 | 역할 | RAG |
|---|---|---|
| **스타트업 탐색** | 후보 스타트업 리스트 추출 및 기본 정보 수집 | O |
| **기술력 분석** | 핵심 기술 지표(TRL, DoF, AI 알고리즘 등) 추출 및 평가 | O |
| **팀/창업자 평가** | 창업자 경력, 팀 구성, 펀딩 이력 평가 | X |
| **리스크 평가** | 규제(ISO 10218), 수출, 시장, 재무 리스크 등급 산정 | O |
| **경쟁사 비교** | 주요 경쟁사 대비 차별성 및 해자(Moat) 분석 | O |
| **투자 판단** | 4개 항목 가중 점수 집계 → 투자/보류 결정 | X |
| **보고서 생성** | 9개 섹션 구조의 투자 평가 보고서 작성 | X |
| **보고서 검토** | 필수 섹션 누락 여부 및 데이터 완결성 검토 | X |

## Architecture

```
START
  └─► 스타트업 탐색 에이전트
        └─► (후보별 반복)
              └─► [병렬] 기술력 분석 / 팀 평가
                    └─► 리스크 평가
                          └─► 경쟁사 비교
                                └─► 투자 판단 에이전트
                                      ├─ invest ─► 보고서 생성 ─► 보고서 검토 ─► 완료
                                      └─ pass  ─────────────────────────────────► 완료
```

## Scoring

4개 항목을 1~5점으로 평가 후 가중 합산 → 100점 만점

| 평가 항목 | 가중치 | 세부 지표 | 세부 지표별 기준 |
|---|---|---|---|
| 기술력 | **35%** | 핵심기술 독창성 | 1=모방 수준 / 3=일부 차별화 / 5=독보적 IP |
|  |  | 기술 성숙도 (TRL) | 1=TRL 1~3 / 3=TRL 4~6 / 5=TRL 7~9 |
|  |  | HW+SW 통합 역량 | 1=SW만 / 3=일부 통합 / 5=완전 수직계열화 |
| 팀 | **25%** | 창업자 도메인 전문성 | 1=비전공 / 3=관련 경력 / 5=석박사+산업경험 |
|  |  | 팀 완성도 (기술·사업·운영) | 1=1인팀 / 3=일부 구성 / 5=풀팀 완비 |
|  |  | 투자·파트너십 유치 이력 | 1=없음 / 3=시드 유치 / 5=Series A 이상 |
| 경쟁력 | **20%** | 경쟁사 대비 차별화 포인트 | 1=동일 / 3=일부 차별화 / 5=명확한 해자 |
|  |  | 진입장벽 (특허, 데이터 등) | 1=없음 / 3=일부 / 5=복합적 해자 |
| 리스크 | **20%** | 규제 리스크 (안전·수출) | 1=높음(불확실) / 3=보통 / 5=낮음(명확) |
|  |  | 재무 지속가능성 (런웨이) | 1=<6개월 / 3=12개월 / 5=>24개월 |

- **투자 임계값** : 70점 이상 + 핵심 데이터 충족 → `invest`
- **Veto 조건** : 단일 항목 평균 1.0점 시 총점 무관 `pass`

## Directory Structure

```
agentic-rag/
├── agents/
│   ├── agentic_rag.py                  # RAG 검색 공통 모듈
│   ├── startup_exploration_agent.py    # 스타트업 탐색
│   ├── tech_analysis_agent.py          # 기술력 분석
│   ├── team_eval_agent.py              # 팀/창업자 평가
│   ├── risk_assessment_agent.py        # 리스크 평가
│   ├── competitor_analysis_agent.py    # 경쟁사 비교
│   ├── investment_decision_agent.py    # 투자 판단
│   ├── report_generation_agent.py      # 보고서 생성
│   └── report_review_agent.py          # 보고서 검토
├── state.py                            # 공통 State 정의 (LangGraph)
├── orchestrator.py                     # 전체 파이프라인 오케스트레이터
├── main.py                             # 실행 진입점
├── pyproject.toml                      # 의존성 선언 (uv)
└── .env                                # API 키 설정 (OPENAI_API_KEY 등)
```

## Knowledge Base (RAG 컬렉션)

| 컬렉션 | 용도 | 필요 문서 예시 |
|---|---|---|
| `investment_reports_robotics` | 업계 공통 리포트 | CB Insights 로봇 시장 보고서, KOTRA 스타트업 동향 |
| `robotics_robotics` | 스타트업별 원천 데이터 | 제품 사양서, 특허 명세서, IR 자료, 인증 보도자료 |

## Getting Started

```bash
# 1. 의존성 설치 (uv 사용)
uv sync

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일에 OPENAI_API_KEY 입력

# 3. 실행
uv run python main.py

# 옵션
uv run python main.py --max-iter 3 --max-docs 10 --max-candidates 10

# 결과 파일로 저장
uv run python main.py --output result.json
```

## Contributors

| 팀원 | 담당 에이전트 | 역할 |
|------|--------------|------|
| 담당자 A | 스타트업 탐색 / 기술력 분석 / 리스크 평가 | RAG 파이프라인 구축 및 데이터 수집·기술 분석 에이전트 구현 |
| 담당자 B | 경쟁사 비교 / 팀·창업자 평가 | 경쟁·팀 평가 에이전트 구현 및 평가 기준 설계 |
| 담당자 C | 투자 판단 / 보고서 생성 / 보고서 검토 | 투자 판단 로직·보고서 통합 에이전트 구현 및 오케스트레이터 설계 |
| 담당자 D | - | 자료 조사 및 Knowledge Base 문서 임베딩 |