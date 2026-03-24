from typing_extensions import NotRequired, TypedDict

from state import StartupEvaluationState


class ReportGenerationNodeState(TypedDict):
    current_evaluation: NotRequired[StartupEvaluationState]
    report_content: NotRequired[str]


class ReportGenerationNodeOutput(TypedDict):
    current_evaluation: NotRequired[StartupEvaluationState]
    report_content: NotRequired[str]


def _fmt_list(items: list, indent: str = "  - ") -> str:
    if not items:
        return f"{indent}정보 없음"
    return "\n".join(f"{indent}{item}" for item in items)


def _fmt_grade(grade: str | None) -> str:
    return grade if grade else "정보 없음"


def _scorecard_table(score_breakdown: dict) -> str:
    category_names = {
        "tech": "기술력",
        "market": "시장성",
        "team": "팀/창업자",
        "competitive": "경쟁력",
        "risk": "리스크",
    }
    lines = [
        "| 평가 항목 | 가중치 | 세부 점수 | 가중 점수 |",
        "|---|---|---|---|",
    ]
    for key, label in category_names.items():
        data = score_breakdown.get(key, {})
        weight = int((data.get("weight", 0)) * 100)
        avg = data.get("average_score", 0)
        weighted = data.get("weighted_score", 0)
        lines.append(f"| {label} | {weight}% | {avg:.2f} / 5.00 | {weighted:.2f} |")

    total = score_breakdown.get("total_score", 0)
    lines.append(f"| **합계** | **100%** | — | **{total:.2f} / 100** |")
    return "\n".join(lines)


def run_report_generation(current_evaluation: StartupEvaluationState) -> str:
    """
    설계 목차(9개 섹션)에 맞춰 투자 평가 보고서를 생성합니다.
    """
    startup_name = current_evaluation.get("startup_name", "Unknown")
    startup_info = current_evaluation.get("startup_info", {}) or {}
    decision_obj = current_evaluation.get("investment_decision", {}) or {}
    decision = decision_obj.get("decision", "pass")
    confidence = decision_obj.get("confidence", 0.0)
    rationale = decision_obj.get("rationale", "정보 없음")
    score = current_evaluation.get("investment_score", 0.0)
    score_breakdown = current_evaluation.get("score_breakdown", {}) or {}

    tech = current_evaluation.get("tech_analysis", {}) or {}
    market = current_evaluation.get("market_analysis", {}) or {}
    comp = current_evaluation.get("competitor_analysis", {}) or {}
    team = current_evaluation.get("team_assessment", {}) or {}
    risk = current_evaluation.get("risk_assessment", {}) or {}

    decision_kr = "투자" if decision == "invest" else "보류"
    decision_icon = "✅" if decision == "invest" else "❌"

    # ── 1. SUMMARY ─────────────────────────────────────────────────────────
    summary_lines = [
        f"# {startup_name} 투자 평가 보고서\n",
        "## 1. SUMMARY\n",
        f"- **투자 판단:** {decision_icon} {decision_kr}",
        f"- **종합 점수:** {score:.2f} / 100",
        f"- **신뢰도:** {confidence:.0%}",
        f"- **판단 근거:** {rationale}",
    ]
    tech_summary = tech.get("summary", "")
    market_summary = market.get("summary", "")
    if tech_summary:
        summary_lines.append(f"- **기술:** {tech_summary}")
    if market_summary:
        summary_lines.append(f"- **시장:** {market_summary}")

    # ── 2. 기업 개요 ────────────────────────────────────────────────────────
    founded = startup_info.get("founded") or startup_info.get("founded_year", "정보 없음")
    funding = startup_info.get("funding") or startup_info.get("total_funding", "정보 없음")
    products = startup_info.get("products") or startup_info.get("product_description", "정보 없음")
    hq = startup_info.get("headquarters") or startup_info.get("location", "정보 없음")
    stage = startup_info.get("funding_stage") or startup_info.get("stage", "정보 없음")

    overview_lines = [
        "\n## 2. 기업 개요\n",
        f"| 항목 | 내용 |",
        f"|---|---|",
        f"| 회사명 | {startup_name} |",
        f"| 설립연도 | {founded} |",
        f"| 본사 위치 | {hq} |",
        f"| 투자 유치 현황 | {funding} |",
        f"| 투자 단계 | {stage} |",
        f"| 제품/서비스 | {products} |",
    ]

    # ── 3. 핵심 기술 분석 ───────────────────────────────────────────────────
    trl = tech.get("trl_level", "정보 없음")
    ip_status = tech.get("ip_status", "정보 없음")
    differentiation = tech.get("differentiation", "정보 없음")
    tech_score = tech.get("tech_score", "N/A")
    strengths = tech.get("strengths", [])
    weaknesses = tech.get("weaknesses", [])
    indicators = tech.get("core_tech_indicators", {}) or {}

    tech_lines = [
        "\n## 3. 핵심 기술 분석\n",
        f"- **기술력 종합 점수:** {tech_score} / 100",
        f"- **TRL (기술성숙도):** {trl} / 9",
        f"- **특허/IP 현황:** {ip_status}",
        f"- **기술 차별점:** {differentiation}",
    ]
    if indicators:
        tech_lines.append("\n**핵심 기술 지표**\n")
        for field, label in [
            ("dof", "자유도(DoF)"), ("payload", "가반하중"), ("reach", "작업 반경"),
            ("autonomy_level", "자율화 수준"), ("ai_algorithms", "AI 알고리즘"),
            ("sensors", "탑재 센서"), ("power_source", "전원 방식"),
        ]:
            val = indicators.get(field)
            if val:
                val_str = ", ".join(val) if isinstance(val, list) else val
                tech_lines.append(f"  - {label}: {val_str}")

    if strengths:
        tech_lines.append("\n**기술적 강점**")
        tech_lines.append(_fmt_list(strengths))
    if weaknesses:
        tech_lines.append("\n**기술적 약점**")
        tech_lines.append(_fmt_list(weaknesses))

    # ── 4. 시장 분석 ────────────────────────────────────────────────────────
    market_scores = market.get("scores", {}) or {}
    tam_score = market_scores.get("tam", "N/A")
    cagr_score = market_scores.get("cagr", "N/A")
    demand_score = market_scores.get("demand_validation", "N/A")
    market_detail = market.get("market_detail", {}) or {}
    tam_val = market_detail.get("tam") or market.get("tam", "정보 없음")
    cagr_val = market_detail.get("cagr") or market.get("cagr", "정보 없음")

    market_lines = [
        "\n## 4. 시장 분석\n",
        f"- **TAM:** {tam_val}  (평가 점수: {tam_score} / 5)",
        f"- **CAGR:** {cagr_val}  (평가 점수: {cagr_score} / 5)",
        f"- **수요 검증 점수:** {demand_score} / 5",
        f"\n{market.get('summary', '시장 분석 정보 없음')}",
    ]

    # ── 5. 경쟁사 분석 ────────────────────────────────────────────────────────
    comp_scores = comp.get("scores", {}) or {}
    diff_score = comp_scores.get("differentiation", "N/A")
    moat_score = comp_scores.get("moat", "N/A")
    competitors_list = comp.get("competitors", []) or comp.get("key_competitors", [])

    comp_lines = [
        "\n## 5. 경쟁사 분석\n",
        f"- **차별성 점수:** {diff_score} / 5",
        f"- **경쟁 해자(Moat) 점수:** {moat_score} / 5",
    ]
    if competitors_list:
        comp_lines.append("\n**주요 경쟁사**")
        comp_lines.append(_fmt_list(competitors_list))
    comp_lines.append(f"\n{comp.get('summary', '경쟁사 분석 정보 없음')}")

    # ── 6. 투자 평가 (Scorecard) ─────────────────────────────────────────────
    invest_lines = [
        "\n## 6. 투자 평가\n",
    ]
    if score_breakdown:
        invest_lines.append(_scorecard_table(score_breakdown))
    else:
        invest_lines.append(f"종합 점수: {score:.2f} / 100")

    veto = score_breakdown.get("data_quality", {}).get("critical_data_missing", False)
    if veto:
        invest_lines.append("\n> ⚠️ 핵심 평가 데이터 일부 부족으로 보수적 판단 적용")

    # ── 7. 위험 요소 ────────────────────────────────────────────────────────
    reg_risks = risk.get("regulatory_risks", {}) or {}
    mkt_risks = risk.get("market_risks", {}) or {}
    top_risks = risk.get("top_risks", [])
    mitigations = risk.get("mitigation_strategies", [])
    overall_grade = _fmt_grade(risk.get("overall_risk_grade"))

    risk_lines = [
        "\n## 7. 위험 요소\n",
        f"- **종합 리스크 등급:** {overall_grade}",
        f"- **안전 규제 (ISO 10218):** {_fmt_grade(reg_risks.get('iso_10218_risk_grade'))}",
        f"- **수출 규제:** {_fmt_grade(reg_risks.get('export_risk_grade'))}",
        f"- **시장 리스크:** {_fmt_grade(mkt_risks.get('market_risk_grade'))}",
        f"- **경쟁 리스크:** {_fmt_grade(mkt_risks.get('competition_risk_grade'))}",
        f"- **재무 리스크:** {_fmt_grade(mkt_risks.get('financial_risk_grade'))}",
    ]
    if top_risks:
        risk_lines.append("\n**주요 리스크 항목**")
        risk_lines.append(_fmt_list(top_risks))
    if mitigations:
        risk_lines.append("\n**리스크 완화 전략**")
        risk_lines.append(_fmt_list(mitigations))
    caution = risk.get("investment_caution", "")
    if caution:
        risk_lines.append(f"\n**투자 시 주의사항:** {caution}")

    # ── 8. 결론 및 투자 권고 ─────────────────────────────────────────────────
    conclusion_lines = [
        "\n## 8. 결론 및 투자 권고\n",
        f"**최종 투자 판단: {decision_icon} {decision_kr}**\n",
        f"- 종합 점수 **{score:.2f}점** (임계값: 70점)",
        f"- 신뢰도: {confidence:.0%}",
        f"\n{rationale}",
    ]
    team_summary = team.get("summary", "")
    if team_summary:
        conclusion_lines.append(f"\n**팀 평가:** {team_summary}")

    # ── 9. REFERENCE ───────────────────────────────────────────────────────
    sources = []
    for agent_result in [tech, market, comp, risk]:
        for key in ("sources", "references", "source_documents"):
            val = agent_result.get(key, [])
            if isinstance(val, list):
                sources.extend(val)
    sources = list(dict.fromkeys(sources))  # 중복 제거

    ref_lines = ["\n## 9. REFERENCE\n"]
    if sources:
        ref_lines.append(_fmt_list(sources))
    else:
        ref_lines.append("  - 내부 에이전트 분석 결과 (RAG 기반 문서 검색)")

    # ── 조합 ───────────────────────────────────────────────────────────────
    all_sections = (
        summary_lines
        + overview_lines
        + tech_lines
        + market_lines
        + comp_lines
        + invest_lines
        + risk_lines
        + conclusion_lines
        + ref_lines
    )
    return "\n".join(all_sections)


def report_generation_node(state: ReportGenerationNodeState) -> ReportGenerationNodeOutput:
    """기존 노드 스타일 호환 래퍼."""
    if "current_evaluation" in state:
        current = state["current_evaluation"]
        report = run_report_generation(current)
        current = {**current, "report_content": report}
        return {"current_evaluation": current}
    return {"report_content": ""}
