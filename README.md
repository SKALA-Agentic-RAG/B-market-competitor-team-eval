# AI Startup Investment Evaluation Agent

본 프로젝트는 물류/창고 로봇(Logistics/Warehouse Robotics) 세부 도메인 스타트업에 대한 투자 가능성을 자동으로 평가하는 멀티 에이전트 시스템을 설계하고 구현한 실습 프로젝트입니다.

## Overview

- **Objective** : AI 스타트업의 기술력, 시장성, 팀 역량, 경쟁력, 리스크를 기준으로 투자 적합성을 자동 분석
- **Method** : Multi-Agent System + Agentic RAG (LangGraph 기반 상태 그래프)
- **Domain Focus** : 광범위한 로보틱스 전체가 아닌 `물류/창고 로봇` 세부분야에 초점을 맞춘 투자 심사
- **Tools** : ChromaDB (벡터 검색), OpenAI GPT-4.1-mini (LLM), BAAI/bge-m3 (임베딩)

## Features

- PDF/Markdown 자료 기반 정보 추출 (IR 자료, 시장 리포트, 경쟁사 분석, 규제 문서 등)
- 물류/창고 로봇 도메인에 맞춘 평가 지표 적용 (ROI, 페이로드, WMS 연동, 상용화 단계 등)
- 기술력·시장성·팀/창업자 역량 병렬 분석 후 리스크/경쟁사 심층 평가
- 종합 점수 70점 이상이면 투자 가능한 수준으로 판단
- 구조화 보고서 자동 생성 후 보고서 검토 에이전트로 최종 품질 확인

## Tech Stack

| Category  | Details                                          |
|-----------|--------------------------------------------------|
| Framework | LangGraph, LangChain, Python 3.11                |
| LLM       | GPT-4.1-mini via OpenAI API                      |
| Retrieval | ChromaDB (벡터 DB), RAG 기반 문서 검색           |
| Embedding | BAAI/bge-m3 (multilingual, 최대 8,192 토큰)      |
| Package   | uv (가상환경 및 의존성 관리)                     |

## Agents

| 에이전트 | 역할 | RAG |
|---|---|---|
| **스타트업 탐색** | 후보 스타트업 리스트 추출 및 기본 정보 수집 | O |
| **기술력 분석** | 핵심 기술 지표(TRL, DoF, AI 알고리즘 등) 추출 및 평가 | O |
| **시장성 평가** | TAM/SAM/SOM, CAGR, 수직 시장 수요, 고객 검증 신호 분석 | O |
| **팀/창업자 평가** | 창업자 경력, 팀 구성, 펀딩 이력 평가 | X |
| **리스크 평가** | 규제(ISO 10218), 수출, 시장, 재무 리스크 등급 산정 | O |
| **경쟁사 비교** | 주요 경쟁사 대비 차별성 및 해자(Moat) 분석 | O |
| **투자 판단** | 5개 항목 가중 점수 집계 → 투자/보류 결정 | X |
| **보고서 생성** | 9개 섹션 구조의 투자 평가 보고서 작성 | X |
| **보고서 검토** | 필수 섹션 누락 여부 및 데이터 완결성 검토 | X |

## Architecture Updates (2026-03-24)

### 1. 타겟 도메인 구체화 및 세분화

- **AS-IS** : 광범위한 `로보틱스(Robotics)` 도메인 전체
- **TO-BE** : `물류/창고 로봇` 중심 세부 도메인
- **사유** : 기존 로보틱스 도메인은 범위가 넓어 에이전트의 분석 기준이 모호해질 수 있어, 명확한 시장 수요와 평가 지표(ROI, 페이로드, WMS 연동 등)를 가진 물류/창고 로봇으로 범위를 좁혀 분석의 깊이와 전문성을 강화했습니다.

### 2. 신규 에이전트 추가 (품질 관리 강화)

- **추가된 에이전트** : 보고서 검토 에이전트
- **사유** : 최종 생성된 투자 평가 보고서의 논리적 오류를 검출하고, 물류 도메인에 맞는 일관성 있는 품질을 보장하기 위해 파이프라인 후반부에 최종 검수 역할을 추가했습니다.

### 3. Graph 구조 전면 개편

- 기존의 단순 순차/병렬 구조를 실제 투자 심사 프로세스와 유사한 4단계 Phase 기반 아키텍처로 재구성했습니다.
- **Phase 1 (Discovery & Parallel Analysis)** : 스타트업 탐색 후 기술력, 시장성, 팀/창업자 역량을 병렬 분석
- **Phase 2 (Evaluation & Deep Dive)** : 초기 데이터 기반 리스크 평가 및 경쟁사 심층 비교
- **Phase 3 (Final Decision)** : 종합 평가 결과 기반 최종 `투자/보류` 결정
- **Phase 4 (Output & Quality Control)** : 보고서 생성 후 보고서 검토 에이전트의 피드백 루프로 최종 결과물 승인

## Architecture

```
START
  └─► 스타트업 탐색 에이전트
        └─► (후보별 반복)
              └─► Phase 1. Discovery & Parallel Analysis
                    └─► [병렬] 기술력 분석 / 시장성 평가 / 팀 평가
                          └─► Phase 2. Evaluation & Deep Dive
                                └─► 리스크 평가
                                      └─► 경쟁사 비교
                                            └─► Phase 3. Final Decision
                                                  └─► 투자 판단 에이전트
                                                        └─► Phase 4. Output & Quality Control
                                                              ├─ invest ─► 보고서 생성 ─► 보고서 검토 ─► 완료
                                                              └─ pass  ─────────────────────────────────► 완료
```

## Scoring

5개 항목을 1~5점으로 평가 후 가중 합산하여 100점 만점으로 환산합니다.

| 평가 항목 | 가중치 | 세부 지표 | 세부 지표별 기준 |
|---|---|---|---|
| 기술력 | **25%** | 핵심기술 독창성 | 1=모방 수준 / 3=일부 차별화 / 5=독보적 IP |
|  |  | 기술 성숙도 (TRL) | 1=TRL 1~3 / 3=TRL 4~6 / 5=TRL 7~9 |
|  |  | HW+SW 통합 역량 | 1=SW만 / 3=일부 통합 / 5=완전 수직계열화 |
| 시장성 | **25%** | TAM | 1=<$100M / 3=$1B 수준 / 5=>$10B |
|  |  | CAGR | 1=<5% / 3=10~20% / 5=>30% |
|  |  | 고객 수요 검증 | 1=없음 / 3=파일럿 중 / 5=매출 발생 |
| 팀 | **20%** | 창업자 도메인 전문성 | 1=비전공 / 3=관련 경력 / 5=깊은 산업 전문성 |
|  |  | 팀 완성도 (기술·사업·운영) | 1=역할 공백 큼 / 3=핵심 일부 충원 / 5=핵심 역할 균형 |
|  |  | 투자·파트너십 유치 이력 | 1=공개 이력 미약 / 3=시드·그랜트 / 5=후속 라운드·강한 투자자 |
| 경쟁력 | **15%** | 경쟁사 대비 차별화 포인트 | 1=동일 / 3=일부 차별화 / 5=명확한 해자 |
|  |  | 진입장벽 (특허, 데이터 등) | 1=없음 / 3=일부 / 5=복합적 해자 |
| 리스크 | **15%** | 규제 리스크 (안전·수출) | 1=높음(불확실) / 3=보통 / 5=낮음(명확) |
|  |  | 재무 지속가능성 (런웨이) | 1=<6개월 / 3=12개월 / 5=>24개월 |

- **판단 기준** : 종합 점수 `70점 이상`이면 투자 가능한 수준, 즉 `괜찮다`고 판단하여 `invest`
- **보류 기준** : 종합 점수 `70점 미만`이면 `pass`
- **참고 사항** : 핵심 데이터가 일부 부족한 경우에도 총점 기준은 유지하되, 최종 rationale에 주의 문구를 남깁니다.

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
| `robotics` | 스타트업별 원천 데이터 | 제품 사양서, 특허 명세서, IR 자료, 인증 보도자료 |

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

## Chroma Ingest (Markdown → Embedding)

두 개의 지식 베이스 문서를 `BAAI/bge-m3`로 임베딩해, 프로젝트 루트의 `./chroma_db`에 저장합니다.

- 입력 문서:
  - `document_1_fixed_sources.md` → `investment_reports_robotics`
  - `tech_analysis_knowledge_base_with_sources.md` → `robotics`
- 스크립트: `scripts/ingest_markdown_to_chroma.py`

```bash
# 기존 컬렉션 초기화 후 재적재
python scripts/ingest_markdown_to_chroma.py --domain robotics --persist-dir ./chroma_db --clear
```

### 저장/열람 검증

아래 코드는 컬렉션 건수(count), 샘플 문서(peek), 유사도 검색 결과(query)를 확인합니다.

```bash
python - <<'PY'
from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

persist = Path("./chroma_db").resolve()
emb = HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",
    model_kwargs={"device":"cpu"},
    encode_kwargs={"normalize_embeddings":True},
)

for name, q in [
    ("investment_reports_robotics", "market trend and startup funding"),
    ("robotics", "TRL ISO 10218 robot safety risk"),
]:
    vs = Chroma(collection_name=name, embedding_function=emb, persist_directory=str(persist))
    print(f"[{name}] count=", vs._collection.count())
    print(f"[{name}] peek_ids=", vs._collection.peek(limit=2).get("ids", []))
    docs = vs.similarity_search(q, k=2)
    print(f"[{name}] query_top1=", (docs[0].page_content[:120] if docs else ""))

print("persist_dir=", persist)
print("sqlite_exists=", (persist / "chroma.sqlite3").exists())
PY
```

## Contributors

| 팀원 | 역할 |
|------|------|
| 권익주 | 에이전트 엔지니어(각 에이전트 코드 개발), RAG(Embedding 모델 튜닝) |
| 김규리 | RAG 엔지니어(학습 문서 수집 및 전처리, Vector DB 구축) |
| 이지수 | 아키텍처(Agent 아키텍처 설계, Graph 흐름 설계) |
| 전아린 | 에이전트 엔지니어(각 에이전트 코드 개발, API 통합 (웹 검색, LLM)) |
