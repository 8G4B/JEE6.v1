"""
python -m scripts.training
python -m scripts.training --output training_data.jsonl --min-confidence 0.8

출력 형식 (JSONL - OpenAI chat format):
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.database.Session import get_db_session
from src.domain.models.LangFeedback import LangFeedback
from sqlalchemy import and_


SYSTEM_MSG = "너는 디스코드 봇 JEE6이야. 사용자의 메시지를 분석해서 JSON으로 응답해."


def build_assistant_response(row: LangFeedback) -> str | None:
    if row.correct_response:
        return row.correct_response

    action = row.parsed_action

    if action == "ignore":
        return '{"ignore": true}'

    if action == "reply":
        if row.llm_raw_response:
            try:
                parsed = json.loads(row.llm_raw_response.strip())
                if "reply" in parsed:
                    return json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError:
                pass
        return None

    if action == "tool":
        if not row.tool_name:
            return None
        args = json.loads(row.tool_args) if row.tool_args else {}
        return json.dumps({"tool": row.tool_name, "args": args}, ensure_ascii=False)

    return None


def get_confidence(row: LangFeedback) -> float:
    score = 0.5

    if row.label == "correct":
        return 1.0
    if row.label in ("wrong_tool", "should_ignore", "should_respond"):
        return 0.0 
    if row.tool_success is True:
        score += 0.3
    elif row.tool_success is False:
        score -= 0.3

    if row.signal in ("cmd_fallback", "ignored_then_retry"):
        score -= 0.4

    return max(0.0, min(1.0, score))


def export(output_path: str, min_confidence: float = 0.5):
    rows_exported = 0
    rows_skipped = 0

    with get_db_session() as db:
        rows = db.query(LangFeedback).filter(
            LangFeedback.parsed_action.in_(["tool", "reply", "ignore"])
        ).order_by(LangFeedback.created_at).all()

        with open(output_path, "w", encoding="utf-8") as f:
            for row in rows:
                confidence = get_confidence(row)
                if confidence < min_confidence:
                    rows_skipped += 1
                    continue

                assistant_response = build_assistant_response(row)
                if not assistant_response:
                    rows_skipped += 1
                    continue

                entry = {
                    "messages": [
                        {"role": "system", "content": SYSTEM_MSG},
                        {"role": "user", "content": row.user_message},
                        {"role": "assistant", "content": assistant_response},
                    ]
                }

                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                rows_exported += 1

    print(f"내보내기 완료: {rows_exported}개 학습 샘플 (건너뜀: {rows_skipped}개)")
    print(f"출력 파일: {output_path}")

    if rows_exported < 100:
        print(f"경고: 학습 샘플이 {rows_exported}개로 적습니다. 최소 200개 이상 수집을 권장합니다.")


def stats():
    with get_db_session() as db:
        total = db.query(LangFeedback).count()
        tools = db.query(LangFeedback).filter(LangFeedback.parsed_action == "tool").count()
        replies = db.query(LangFeedback).filter(LangFeedback.parsed_action == "reply").count()
        ignores = db.query(LangFeedback).filter(LangFeedback.parsed_action == "ignore").count()
        signals = db.query(LangFeedback).filter(LangFeedback.parsed_action == "signal").count()
        labeled = db.query(LangFeedback).filter(LangFeedback.label.isnot(None)).count()
        success = db.query(LangFeedback).filter(LangFeedback.tool_success == True).count()
        fail = db.query(LangFeedback).filter(LangFeedback.tool_success == False).count()

    print(f"=== 피드백 통계 ===")
    print(f"전체: {total}")
    print(f"  도구 호출: {tools} (성공: {success}, 실패: {fail})")
    print(f"  일반 응답: {replies}")
    print(f"  무시: {ignores}")
    print(f"  신호: {signals}")
    print(f"  수동 라벨: {labeled}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LangFeedback → 학습 데이터 변환")
    parser.add_argument("--output", "-o", default="training_data.jsonl", help="출력 파일 경로")
    parser.add_argument("--min-confidence", "-c", type=float, default=0.5, help="최소 신뢰도 (0~1)")
    parser.add_argument("--stats", action="store_true", help="통계만 출력")
    args = parser.parse_args()

    if args.stats:
        stats()
    else:
        export(args.output, args.min_confidence)
