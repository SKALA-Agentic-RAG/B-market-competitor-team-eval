from __future__ import annotations

from typing import Any, Dict, List

from src.config import AppConfig
from src.graph.state import GlobalEvaluationState
from src.rag.retriever import build_faiss_retriever, retrieve_context
from src.tools.fetch import fetch_url_text
from src.tools.web_search import web_search_tool

# ── 프롬프트 (담당자 B: 경쟁사 비교 — 비교 표 중심, RAG) ─────────────────────

COMPETITOR_SYSTEM_PROMPT = """당신은 로보틱스·자동화 산업의 경쟁 전략 및 투자 분석 전문가입니다.
대상 스타트업과 **동일 세그먼트**에서 실제로 경쟁하거나 대체될 수 있는 기업 3~5곳을 선정해 비교하십시오.
반드시 아래 JSON 형식으로만 응답하십시오. (한국어)

## JSON 스키마
{
  "scores": {
    "differentiation": <1~5 number, 경쟁사 대비 제품·기술·비즈니스 모델 차별화>,
    "moat":            <1~5 number, 진입장벽(특허·데이터·고객 lock-in·규제·자본 등)>
  },
  "target_segment": "<이 비교가 가정하는 시장 세그먼트 (예: 휴머노이드 물류, AMR 등)>",
  "comparison_table": {
    "columns": ["항목", "대상_스타트업", "경쟁사A", "경쟁사B", "경쟁사C"],
    "rows": [
      {
        "항목": "<비교축 예: 핵심 제품/기술>",
        "대상_스타트업": "<한 줄 요약>",
        "경쟁사A": "...",
        "경쟁사B": "...",
        "경쟁사C": "..."
      }
    ]
  },
  "competitors": [
    {
      "name": "<경쟁사명>",
      "segment": "<같은 풀에서의 포지션>",
      "tech_spec": "<핵심 스펙·스택>",
      "price_range": "<공개된 가격대 또는 '비공개'>",
      "customers": "<대표 고객·사례>",
      "differentiator": "<이 경쟁사의 강점/약점 한 줄>"
    }
  ],
  "our_advantages":    ["<대상 스타트업의 상대적 강점>"],
  "our_disadvantages": ["<상대적 약점·격차>"],
  "summary":           "<경쟁 구도·윈 확률 요약 3~4문장>",
  "evidence": [
    {"claim": "<근거 주장>", "source_title": "<출처명>", "url": "<URL>"}
  ]
}

## 비교표(comparison_table.rows)에 반드시 포함 권장 항목
- 핵심 제품/기술 스택
- 목표 고객/산업
- 상용화 단계(TRL/출시 여부)
- 가격·비즈니스 모델(구독/CAPEX 등, 알 수 없으면 '불명')
- 지역(본사·주력 시장)

## 점수 기준
- differentiation: 1=범용·모방 / 3=일부 차별화 / 5=명확한 우위·니치 지배력
- moat: 1=낮음 / 3=단일 요인(특허 등) / 5=복합 해자

scores 값은 1.0~5.0 숫자로 하십시오."""

COMPETITOR_USER_PROMPT = """## 평가 대상
- 스타트업: **{startup_name}**
- 도메인: **{domain}**{subdomain_hint}

## 다른 에이전트 산출 (참고만, 모순 시 [참고 문서] 우선)
[기술 평가 요약]
{tech_summary}

[리스크 등급]
{risk_grade}

[팀 역량 요약]
{team_summary}

## 지시
[참고 문서]는 RAG로 검색된 근거입니다. `evidence`에는 실제 URL이 있는 출처만 포함하십시오.

[참고 문서]
{context}
"""


def _fetch_docs(config: AppConfig, startup_name: str) -> List[Dict[str, Any]]:
    sub = (config.target_subdomain or "").replace("_", " ")
    queries = [
        f"{startup_name} vs competitors robotics comparison",
        f"{startup_name} alternative companies market share",
        f"robotics {sub} leading companies startups benchmark".strip(),
        f"{startup_name} competitive landscape funding",
    ]
    seen_urls: set[str] = set()
    docs: List[Dict[str, Any]] = []

    for q in queries:
        if len(docs) >= config.max_documents:
            break
        results = web_search_tool(q, max_results=max(3, config.web_max_results // 2))
        for r in results:
            url = (r.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            text = fetch_url_text(url)
            if not text:
                continue
            seen_urls.add(url)
            docs.append(
                {"text": text, "metadata": {"title": r.get("title", ""), "url": url, "query": q}}
            )
            if len(docs) >= config.max_documents:
                break
    return docs


def _call_llm(
    config: AppConfig,
    startup_name: str,
    tech_summary: str,
    risk_grade: str,
    team_summary: str,
    context_str: str,
) -> Dict[str, Any]:
    import json

    try:
        from openai import OpenAI

        client = OpenAI(api_key=config.openai_api_key or None)
        subdomain_hint = f" / 세부도메인: {config.target_subdomain}" if config.target_subdomain else ""
        user_msg = COMPETITOR_USER_PROMPT.format(
            startup_name=startup_name,
            domain=config.target_domain,
            subdomain_hint=subdomain_hint,
            tech_summary=tech_summary[:2000],
            risk_grade=risk_grade,
            team_summary=team_summary[:1200],
            context=context_str[:6000],
        )
        response = client.chat.completions.create(
            model=config.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": COMPETITOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
        raw = json.loads(response.choices[0].message.content or "{}")
        return _normalize_competitor_payload(raw)
    except Exception:
        return {
            "scores": {"differentiation": 2.0, "moat": 2.0},
            "target_segment": "",
            "comparison_table": {"columns": [], "rows": []},
            "competitors": [],
            "our_advantages": [],
            "our_disadvantages": [],
            "summary": f"{startup_name} 경쟁 분석 (LLM 미연결 상태)",
            "evidence": [],
        }


def _normalize_competitor_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    scores = raw.get("scores") or {}
    out = dict(raw)
    out["scores"] = {
        "differentiation": float(scores.get("differentiation", 2.0)),
        "moat": float(scores.get("moat", 2.0)),
    }
    out.setdefault("comparison_table", {"columns": [], "rows": []})
    out.setdefault("competitors", [])
    out.setdefault("evidence", [])
    return out


def competitor_analysis_agent(state: GlobalEvaluationState) -> Dict[str, Any]:
    """
    기술·리스크·팀 분석 결과를 참고하고, RAG 근거로 경쟁 구도를 분석한다.
    읽기: current_startup, current_evaluation(tech/risk/team_analysis), target_subdomain
    쓰기: current_evaluation["competitor_analysis"]
    """
    startup = state.get("current_startup") or ""
    if not startup:
        return {}

    config = AppConfig(
        target_domain=state.get("target_domain") or "robotics",
        target_subdomain=state.get("target_subdomain") or "",
        max_documents=state.get("max_documents", 4),
        max_pages_per_document=state.get("max_pages_per_document", 50),
        max_total_pages=state.get("max_total_pages", 200),
    )
    current = dict(state.get("current_evaluation") or {})

    tech_summary = str((current.get("tech_analysis") or {}).get("summary", ""))
    risk_grade = str((current.get("risk_analysis") or {}).get("risk_grade", "중"))
    team_summary = str((current.get("team_analysis") or {}).get("summary", ""))

    docs = _fetch_docs(config, startup)
    try:
        vectorstore = build_faiss_retriever(config, docs)
    except Exception:
        vectorstore = None

    rag_query = (
        f"{startup} competitors differentiation moat pricing customers "
        f"{config.target_subdomain or ''} robotics"
    )
    contexts = retrieve_context(config, vectorstore, query=rag_query.strip(), k=6)
    context_str = "\n\n".join(
        f"[{c.get('title', '')}] {c.get('text', '')[:900]}" for c in contexts
    ) or "(검색·RAG 컨텍스트 없음)"

    competitor_analysis = _call_llm(
        config, startup, tech_summary, risk_grade, team_summary, context_str
    )

    current["competitor_analysis"] = competitor_analysis
    return {"current_evaluation": current}
