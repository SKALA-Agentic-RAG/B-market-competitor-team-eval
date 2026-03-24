"""
스타트업 투자 평가 시스템 진입점

사용법:
    python main.py                          # 기본 실행 (robotics, 3개 스타트업)
    python main.py --domain healthcare      # 도메인 변경
    python main.py --max-iter 5 --max-docs 15
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from orchestrator import run_evaluation
from pdf_report import export_json_report_to_pdf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="스타트업 투자 평가 파이프라인",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=3,
        dest="max_iterations",
        help="최대 평가 스타트업 수",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=10,
        dest="max_documents",
        help="RAG 쿼리당 최대 검색 문서 수",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=10,
        dest="max_candidates",
        help="탐색 단계에서 확보할 후보 스타트업 수",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="결과를 저장할 JSON 파일 경로 (동일 이름의 PDF도 함께 생성)",
    )
    return parser.parse_args()


def print_summary(evaluations: list) -> None:
    print(f"\n{'='*60}")
    print(f" 평가 완료: {len(evaluations)}개 스타트업")
    print(f"{'='*60}")

    best = max(evaluations, key=lambda e: e.get("investment_score", 0), default=None)

    for ev in evaluations:
        name     = ev.get("startup_name", "?")
        decision = ev.get("investment_decision", {}).get("decision", "?")
        score    = ev.get("investment_score", 0)
        tech     = ev.get("tech_analysis", {}).get("tech_score", "N/A")
        risk     = ev.get("risk_assessment", {}).get("overall_risk_grade", "N/A")
        is_best  = best and name == best.get("startup_name")

        decision_icon = {"invest": "✅", "pass": "❌"}.get(decision, "?")
        best_tag = " ★ 최고 투자 대상" if is_best else ""
        print(f"  {decision_icon}  {name}{best_tag}")
        print(f"      투자판단: {decision} | 종합점수: {score} | 기술점수: {tech} | 리스크: {risk}")

    if best:
        print(f"\n{'*'*60}")
        print(f"  ★ 최고 투자 대상: {best.get('startup_name')}  (종합점수: {best.get('investment_score', 0)})")
        print(f"{'*'*60}")
    print()


def main() -> None:
    args = parse_args()

    print(
        f"\n[시작] 도메인=robotics (고정) | 후보={args.max_candidates}개 | "
        f"평가최대={args.max_iterations}개 | 문서수={args.max_documents}"
    )
    print("파이프라인 실행 중...\n")

    try:
        final_state = run_evaluation(
            target_domain="robotics",
            max_iterations=args.max_iterations,
            max_candidates=args.max_candidates,
            max_documents=args.max_documents,
        )
    except Exception as e:
        print(f"[오류] 파이프라인 실행 실패: {e}", file=sys.stderr)
        sys.exit(1)

    evaluations = final_state.get("evaluations", [])
    print_summary(evaluations)

    best = max(evaluations, key=lambda e: e.get("investment_score", 0), default=None)
    output_data = {
        "best_startup": best.get("startup_name") if best else None,
        "evaluations": evaluations,
    }
    result_json = json.dumps(output_data, ensure_ascii=False, indent=2)

    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"evaluation_{timestamp}.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result_json, encoding="utf-8")
    print(f"[저장] 결과 파일: {output_path}")

    try:
        pdf_path = export_json_report_to_pdf(output_data, output_path)
        print(f"[저장] PDF 보고서: {pdf_path}")
    except Exception as e:
        print(f"[경고] PDF 보고서 생성 실패: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
