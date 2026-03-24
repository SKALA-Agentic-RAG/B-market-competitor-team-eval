from __future__ import annotations

from typing import Any, Dict, List

from src.config import AppConfig
from src.graph.state import GlobalEvaluationState
from src.rag.retriever import build_faiss_retriever, retrieve_context
from src.tools.fetch import fetch_url_text
from src.tools.web_search import web_search_tool

# ── 프롬프트 템플릿 (담당자 B: 시장성 평가 — TAM / SAM / SOM 중심) ───────────

MARKET_SYSTEM_PROMPT = """당신은 로보틱스·자동화 시장 전문 투자 분석가입니다.
주어진 스타트업의 **시장성**을 분석하고, 반드시 아래 JSON 형식으로만 응답하십시오.
(한국어로 작성. 숫자·단위는 출처와 함께 명시; 불확실하면 가정을 분리해 기술)

## TAM / SAM / SOM 정의 (분석 시 반드시 구분)
- **TAM (Total Addressable Market)**: 이상적으로 전체 잠재 수요가 형성하는 시장 규모
- **SAM (Serviceable Addressable Market)**: 제품·채널·규제·지역 등으로 **실제로 공략 가능한** 시장 부분
- **SOM (Serviceable Obtainable Market)**: 단기~중기(예: 3~5년) **현실적으로 점유 가능한** 매출 규모

## JSON 스키마
{
  "scores": {
    "tam":               <1~5 number, 목표 시장(TAM) 규모·매력>,
    "cagr":              <1~5 number, 시장 성장률(CAGR) 전망>,
    "demand_validation": <1~5 number, 고객 수요·매출·PO·파일럿 등 검증 수준>
  },
  "tam_estimate": {
    "value_usd": "<예: $12B (2024E) 또는 범위>",
    "scope": "<어떤 지역·세그먼트를 TAM으로 봤는지>",
    "methodology": "<top-down / bottom-up / 혼합 + 간단 근거>",
    "notes": "<한계·불확실성>"
  },
  "sam_estimate": {
    "value_usd": "<SAM 금액 또는 범위>",
    "filters": "<채널·규제·지역·고객 세그먼트 등 SAM 산정 시 적용한 필터>",
    "rationale": "<왜 이 규모가 현실적인지 1~2문장>"
  },
  "som_estimate": {
    "horizon_years": <3~5 등 숫자>,
    "value_usd": "<해당 기간 SOM 매출 잠재>",
    "penetration_assumption": "<시장 점유·고객 수 가정>",
    "rationale": "<근거 1~2문장>"
  },
  "cagr_estimate": "<시장·세그먼트 CAGR % 및 출처/연도>",
  "demand_drivers": ["<수요 동인1>", "<수요 동인2>"],
  "buyer_personas": ["<주요 구매자/의사결정자 유형>"],
  "summary": "<시장성 종합 요약 3~5문장 (TAM→SAM→SOM 논리로 연결)>",
  "market_risks": ["<시장·경쟁·규제 관련 리스크>"],
  "evidence": [
    {"claim": "<근거 주장>", "source_title": "<출처명>", "url": "<URL>"}
  ]
}

## 점수 기준 (1~5)
- tam: 1=소규모·니치 / 3=수십억~수백억 달러급 의미 있는 TAM / 5=대규모 구조적 성장 시장
- cagr: 1=<5% 또는 정체 / 3=약 10~20% / 5=구조적 고성장(예: 25%+)
- demand_validation: 1=아이디어 단계 / 3=유료 파일럿·LOI 다수 / 5=반복 매출·명확한 unit economics

출력 시 scores의 값은 반드시 1.0 이상 5.0 이하의 숫자로 하십시오."""

MARKET_USER_PROMPT = """## 평가 대상
- 스타트업: **{startup_name}**
- 도메인: **{domain}**{subdomain_hint}

## 지시
아래 [참고 문서]는 웹에서 수집·청킹·검색(RAG)된 근거입니다. 이를 우선 활용하고,
문서에 없는 부분은 업계 상식으로 **명시적 가정** 하에 추정하되, `evidence`에는
반드시 실제 URL이 있는 출처만 넣으십시오 (추측만 있는 주장은 evidence에 넣지 마십시오).

[참고 문서]
{context}
"""


def _fetch_docs(config: AppConfig, startup_name: str) -> List[Dict[str, Any]]:
    """시장 규모·성장·수요 관련 페이지를 수집 (RAG 인덱싱용)."""
    sub = (config.target_subdomain or "").replace("_", " ")
    queries = [
        f"{startup_name} market size revenue customers robotics",
        f"{startup_name} TAM SAM addressable market forecast",
        f"robotics {sub} market size CAGR 2024 2030".strip(),
        f"{startup_name} funding round valuation industrial automation",
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


def _call_llm(config: AppConfig, startup_name: str, context_str: str) -> Dict[str, Any]:
    import json

    try:
        from openai import OpenAI

        client = OpenAI(api_key=config.openai_api_key or None)
        subdomain_hint = f" / 세부도메인: {config.target_subdomain}" if config.target_subdomain else ""
        user_msg = MARKET_USER_PROMPT.format(
            startup_name=startup_name,
            domain=config.target_domain,
            subdomain_hint=subdomain_hint,
            context=context_str[:8000],
        )
        response = client.chat.completions.create(
            model=config.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": MARKET_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
        raw = json.loads(response.choices[0].message.content or "{}")
        return _normalize_market_payload(raw, startup_name)
    except Exception:
        return _fallback_market_analysis(startup_name)


def _normalize_market_payload(raw: Dict[str, Any], startup_name: str) -> Dict[str, Any]:
    """LLM 출력을 보고서·다운스트림이 기대하는 형태로 정리."""
    scores = raw.get("scores") or {}
    out = dict(raw)
    out["scores"] = {
        "tam": float(scores.get("tam", 2.0)),
        "cagr": float(scores.get("cagr", 2.0)),
        "demand_validation": float(scores.get("demand_validation", 2.0)),
    }
    # 하위 호환: 문자열 tam_estimate 가 오면 보고서용 필드로 복제
    if isinstance(raw.get("tam_estimate"), str):
        out["tam_estimate_legacy"] = raw["tam_estimate"]
        out["tam_estimate"] = {
            "value_usd": raw["tam_estimate"],
            "scope": "",
            "methodology": "",
            "notes": "",
        }
    if "sam_estimate" in raw and isinstance(raw["sam_estimate"], str):
        out["sam_estimate"] = {"value_usd": raw["sam_estimate"], "filters": "", "rationale": ""}
    if "som_estimate" in raw and isinstance(raw["som_estimate"], str):
        out["som_estimate"] = {
            "horizon_years": 3,
            "value_usd": raw["som_estimate"],
            "penetration_assumption": "",
            "rationale": "",
        }
    out.setdefault("evidence", [])
    out.setdefault("summary", f"{startup_name} 시장성 요약")
    return out


def _fallback_market_analysis(startup_name: str) -> Dict[str, Any]:
    return {
        "scores": {"tam": 2.0, "cagr": 2.0, "demand_validation": 2.0},
        "tam_estimate": {
            "value_usd": "N/A",
            "scope": "",
            "methodology": "LLM 미연결",
            "notes": "실제 API 연결 후 재분석 필요",
        },
        "sam_estimate": {"value_usd": "N/A", "filters": "", "rationale": ""},
        "som_estimate": {
            "horizon_years": 3,
            "value_usd": "N/A",
            "penetration_assumption": "",
            "rationale": "",
        },
        "cagr_estimate": "N/A (LLM 미연결)",
        "demand_drivers": [],
        "buyer_personas": [],
        "summary": f"{startup_name} 시장성 분석 (LLM 미연결 상태)",
        "market_risks": ["LLM 미연결 — 실제 시장 분석 필요"],
        "evidence": [],
    }


def market_eval_agent(state: GlobalEvaluationState) -> Dict[str, Any]:
    """
    읽기: current_startup, target_domain, target_subdomain
    쓰기: current_evaluation["market_analysis"]
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

    docs = _fetch_docs(config, startup)
    try:
        vectorstore = build_faiss_retriever(config, docs)
    except Exception:
        vectorstore = None

    rag_query = (
        f"{startup} robotics TAM SAM SOM market size CAGR demand pilots customers "
        f"{config.target_subdomain or ''}"
    )
    contexts = retrieve_context(config, vectorstore, query=rag_query.strip(), k=6)
    context_str = "\n\n".join(
        f"[{c.get('title', '')}] {c.get('text', '')[:900]}" for c in contexts
    ) or "(검색·RAG 컨텍스트 없음 — 프롬프트 가정 모드로 분석하십시오.)"

    market_analysis = _call_llm(config, startup, context_str)

    current = dict(state.get("current_evaluation") or {})
    current["market_analysis"] = market_analysis
    return {"current_evaluation": current}
