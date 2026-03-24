from __future__ import annotations

from typing import Any, Dict, List

from src.config import AppConfig
from src.graph.state import GlobalEvaluationState
from src.tools.fetch import fetch_url_text
from src.tools.web_search import web_search_tool

# ── 프롬프트 (담당자 B: 팀/창업자 평가 — RAG 없음, 공개 웹 근거 수집) ─────────
# 협업 시 다른 팀원의 에이전트와 합칠 때: 이 모듈은 FAISS/retriever 에 의존하지 않습니다.

TEAM_SYSTEM_PROMPT = """당신은 벤처 투자 심사역 출신의 **창업팀·인력 due diligence** 전문가입니다.
공개 정보만으로(웹 검색으로 수집된 스니펫) 스타트업 **창업자·핵심 인력**을 평가하고,
반드시 아래 JSON 형식으로만 응답하십시오. (한국어)

## 원칙
- 학력·경력·이전 회사·특허·언론 인용은 **수집된 스니펫에 근거가 있을 때만** 단정하십시오.
- 근거가 부족하면 점수를 보수적으로 주고 `data_sufficient`: false, `hold_reason`을 채우십시오.
- 환각 금지: 스니펫에 없는 학교명·경력은 invent 하지 마십시오.

## JSON 스키마
{
  "scores": {
    "domain_expertise":   <1~5 number, 로보틱스/해당 도메인 전문성>,
    "team_completeness":  <1~5 number, 팀 구성(하드웨어·SW·비즈·운영 등) 완성도>,
    "funding_track":      <1~5 number, 투자 유치·그랜트·전략 파트너십 이력>
  },
  "founders": [
    {
      "name": "<이름 또는 '불명'>",
      "role": "<CEO/CTO 등>",
      "education": "<스니펫에 나온 학력만, 없으면 '스니펫 미확인'>",
      "career_highlights": ["<스니펫 기반 경력 bullet>"],
      "public_signals": ["<언론·수상·논문 등 스니펫 근거>"]
    }
  ],
  "key_hires_or_advisors": ["<핵심 채용·자문 — 스니펫 근거 있을 때만>"],
  "founders_summary": "<창업자 중심 2~4문장 요약>",
  "team_structure": "<현재 팀 규모·기능 배분 — 알려진 범위에서>",
  "advisors": ["<자문·보드 — 확인된 경우만>"],
  "summary": "<투자 관점 팀 역량 평가 3~4문장>",
  "data_sufficient": <true | false>,
  "hold_reason": "<data_sufficient가 false일 때 필수. 예: '창업자 공개 프로필 부재'>",
  "evidence_notes": [
    {"claim": "<주장>", "source_title": "<출처 페이지 제목>", "url": "<URL>", "snippet": "<짧은 인용>"}
  ]
}

## 점수 기준
- domain_expertise: 1=관련성 낮음 / 3=관련 산업 경력 / 5=해당 분야 깊은 전문성(논문·특허·핵심 직무)
- team_completeness: 1=1인 또는 역할 공백 / 3=핵심 일부 충원 / 5=핵심 역할 균형
- funding_track: 1=공개 투자 이력 없음 / 3=시드·그랜트 / 5=후속 라운드·신뢰할 LP

scores는 1.0~5.0 숫자. 근거 없이 높은 점수를 주지 마십시오."""

TEAM_USER_PROMPT = """## 평가 대상
- 스타트업: **{startup_name}**
- 도메인: **{domain}**{subdomain_hint}

## 스타트업 탐색 에이전트가 수집한 기본 정보 (참고)
{startup_info_block}

## 웹에서 수집한 공개 스니펫 (RAG 아님 — 순서 무관)
{context}

## 지시
1) 위 스니펫과 기본 정보만 사용해 JSON을 채우십시오.
2) 스니펫에 창업자 이름이 없으면 founders는 비우고 data_sufficient=false 로 처리할 수 있습니다.
3) evidence_notes에는 반드시 위 스니펫에 대응하는 URL을 넣으십시오."""


def _startup_info_block(info: Dict[str, Any]) -> str:
    if not info:
        return "(탐색 단계 정보 없음)"
    lines = [f"- {k}: {v}" for k, v in info.items() if v not in (None, "", [], {})]
    return "\n".join(lines) if lines else "(탐색 단계 정보 없음)"


def _gather_team_public_context(config: AppConfig, startup_name: str) -> str:
    """
    RAG(벡터 인덱스) 없이 웹 검색·페이지 일부 텍스트만으로 컨텍스트를 만든다.
    스모크 테스트에서는 이 함수를 monkeypatch 하여 네트워크를 끊을 수 있다.
    """
    sub = (config.target_subdomain or "").replace("_", " ")
    queries: List[str] = [
        f"{startup_name} founders CEO CTO LinkedIn",
        f"{startup_name} team startup robotics funding founders background",
        f"{startup_name} crunchbase pitchbook team",
        f'"{startup_name}" robotics founder interview',
    ]
    if sub:
        queries.insert(1, f"{startup_name} {sub} company leadership")

    chunks: List[str] = []
    seen_url: set[str] = set()
    max_urls = min(6, max(4, config.max_documents + 2))

    for q in queries:
        if len(seen_url) >= max_urls:
            break
        results = web_search_tool(q, max_results=config.web_max_results)
        for r in results:
            url = (r.get("url") or "").strip()
            title = r.get("title") or ""
            if not url or url in seen_url:
                continue
            body = fetch_url_text(url)
            if not body:
                continue
            seen_url.add(url)
            snippet = body[:3500].replace("\n", " ")
            chunks.append(f"### URL: {url}\n**제목**: {title}\n**본문 일부**:\n{snippet}\n")
            if len(seen_url) >= max_urls:
                break

    return "\n".join(chunks) if chunks else "(웹 스니펫 수집 실패 — 공개 정보 부족)"


def _call_llm(config: AppConfig, startup_name: str, startup_info: Dict[str, Any], context_str: str) -> Dict[str, Any]:
    import json

    try:
        from openai import OpenAI

        client = OpenAI(api_key=config.openai_api_key or None)
        subdomain_hint = f" / 세부도메인: {config.target_subdomain}" if config.target_subdomain else ""
        user_msg = TEAM_USER_PROMPT.format(
            startup_name=startup_name,
            domain=config.target_domain,
            subdomain_hint=subdomain_hint,
            startup_info_block=_startup_info_block(startup_info),
            context=context_str[:12000],
        )
        response = client.chat.completions.create(
            model=config.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": TEAM_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
        raw = json.loads(response.choices[0].message.content or "{}")
        return _normalize_team_payload(raw, startup_name)
    except Exception:
        return _fallback_team_analysis(startup_name)


def _normalize_team_payload(raw: Dict[str, Any], startup_name: str) -> Dict[str, Any]:
    scores = raw.get("scores") or {}
    out = dict(raw)
    out["scores"] = {
        "domain_expertise": float(scores.get("domain_expertise", 2.0)),
        "team_completeness": float(scores.get("team_completeness", 2.0)),
        "funding_track": float(scores.get("funding_track", 2.0)),
    }
    out.setdefault("founders", [])
    out.setdefault("key_hires_or_advisors", [])
    out.setdefault("advisors", [])
    out.setdefault("evidence_notes", [])
    if "data_sufficient" not in raw:
        out["data_sufficient"] = bool(out.get("founders") or out.get("summary"))
    out.setdefault("hold_reason", None)
    out.setdefault("summary", f"{startup_name} 팀 평가")
    return out


def _fallback_team_analysis(startup_name: str) -> Dict[str, Any]:
    return {
        "scores": {"domain_expertise": 2.0, "team_completeness": 2.0, "funding_track": 2.0},
        "founders": [],
        "key_hires_or_advisors": [],
        "founders_summary": "분석 불가 (LLM 미연결)",
        "team_structure": "",
        "advisors": [],
        "summary": f"{startup_name} 팀 분석 (LLM 미연결 상태)",
        "data_sufficient": True,
        "hold_reason": None,
        "evidence_notes": [],
    }


def team_eval_agent(state: GlobalEvaluationState) -> Dict[str, Any]:
    """
    RAG X — 벡터스토어 없이 웹 검색 스니펫 + startup_info 로 평가.
    읽기: current_startup, current_evaluation.startup_info, target_domain
    쓰기: current_evaluation["team_analysis"], (옵션) hold_reason
    """
    startup = state.get("current_startup") or ""
    if not startup:
        return {}

    config = AppConfig(
        target_domain=state.get("target_domain") or "robotics",
        target_subdomain=state.get("target_subdomain") or "",
        max_documents=state.get("max_documents", 4),
    )

    current = dict(state.get("current_evaluation") or {})
    startup_info = dict(current.get("startup_info") or {})

    context_str = _gather_team_public_context(config, startup)
    team_analysis = _call_llm(config, startup, startup_info, context_str)

    current["team_analysis"] = team_analysis

    if not team_analysis.get("data_sufficient", True):
        current["hold_reason"] = team_analysis.get("hold_reason") or "팀·창업자 공개 정보 부족"

    return {"current_evaluation": current}
