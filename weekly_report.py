"""Weekly household report: local aggregation, OpenAI interpretation, Telegram delivery."""
import argparse
import json
import logging
import os
import sqlite3
import urllib.parse
import urllib.request
from datetime import date, timedelta
from openai import OpenAI
from ledger import DB_PATH
from telegram_http import urlopen

log = logging.getLogger("weekly_report")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def week_bounds(reference=None):
    """Return current Monday..today and previous Monday..Sunday."""
    today = reference or date.today()
    current_start = today - timedelta(days=today.weekday())
    previous_start = current_start - timedelta(days=7)
    previous_end = current_start - timedelta(days=1)
    return current_start, today, previous_start, previous_end


def _aggregate(conn, start, end):
    rows = conn.execute("SELECT category,telegram_user_id,substr(created_at,1,10),amount FROM expenses WHERE substr(created_at,1,10) BETWEEN ? AND ?", (start.isoformat(), end.isoformat())).fetchall()
    cats, users, days = {}, {}, {}
    for category, user_id, spent_day, amount in rows:
        category = category or "기타"
        name = "지희" if user_id == 8631664727 else "광래" if user_id == 8806961376 else str(user_id)
        amount = int(amount)
        cats[category] = cats.get(category, 0) + amount
        users[name] = users.get(name, 0) + amount
        days[spent_day] = days.get(spent_day, 0) + amount
    total = sum(days.values())
    day_count = (end - start).days + 1
    return {"total": total, "transaction_count": len(rows), "daily_average": round(total / day_count), "category_totals": dict(sorted(cats.items(), key=lambda x: x[1], reverse=True)), "user_totals": dict(sorted(users.items(), key=lambda x: x[1], reverse=True)), "daily_totals": dict(sorted(days.items())), "period": {"start": start.isoformat(), "end": end.isoformat()}}


def collect_statistics(reference=None):
    current_start, current_end, previous_start, previous_end = week_bounds(reference)
    with sqlite3.connect(DB_PATH) as conn:
        current = _aggregate(conn, current_start, current_end)
        previous = _aggregate(conn, previous_start, previous_end)
        chats = [row[0] for row in conn.execute("SELECT DISTINCT telegram_chat_id FROM expenses WHERE telegram_chat_id IS NOT NULL")]
    change = None if previous["total"] == 0 else round((current["total"] - previous["total"]) / previous["total"] * 100, 1)
    return {"current": current, "previous": previous, "change_percent": change, "chat_ids": chats}


REPORT_TEMPLATE = """📊 우리 가족 주간 가계부
📅 {current_start} ~ {current_end}

💰 이번 주 지출: {current_total:,}원
📈 전주 대비: {change_amount:+,}원 ({change_percent:+.1f}%)

🏷️ 주요 지출
{categories}

💬 소비 분석
{llm_analysis}"""

NO_PREVIOUS_TEMPLATE = """📊 우리 가족 주간 가계부
📅 {current_start} ~ {current_end}

💰 이번 주 지출: {current_total:,}원

🏷️ 주요 지출
{categories}

💬 소비 분석
{llm_analysis}"""

NO_SPENDING_TEMPLATE = """📊 우리 가족 주간 가계부
📅 {current_start} ~ {current_end}

💰 이번 주 지출: 0원

이번 주 지출이 없습니다."""


def _category_lines(stats, limit=3):
    items = list(stats["current"].get("category_totals", {}).items())[:limit]
    return "\n".join(f"• {category}: {amount:,}원" for category, amount in items) or "• 없음"


def build_report_message(stats, llm_analysis=""):
    current = stats["current"]
    period = current["period"]
    if current["total"] == 0:
        return NO_SPENDING_TEMPLATE.format(current_start=period["start"], current_end=period["end"])
    values = {"current_start": period["start"], "current_end": period["end"], "current_total": current["total"], "categories": _category_lines(stats), "llm_analysis": llm_analysis.strip()}
    previous_total = stats["previous"]["total"]
    if previous_total == 0:
        return NO_PREVIOUS_TEMPLATE.format(**values)
    change_amount = current["total"] - previous_total
    change_percent = stats["change_percent"]
    return REPORT_TEMPLATE.format(**values, change_amount=change_amount, change_percent=change_percent)


def build_prompt(stats):
    data = {key: stats[key] for key in ("current", "previous", "change_percent")}
    if stats["current"]["total"] == 0:
        instructions = """소비 분석 문장만 작성하세요. 이번 주 지출이 없다는 상황을 짧고 친근하게 설명하세요. 제목, 날짜, 금액, 카테고리, 퍼센트, 숫자, 인사말, 제안은 작성하지 마세요. 100자 이내 한국어로 답하세요."""
    elif stats["previous"]["total"] == 0:
        instructions = """소비 분석 문장만 작성하세요. 이번 주 소비에서 관찰되는 점과 절약이 필요해 보이는 부분이 있을 때의 짧은 권고를 작성하세요. 지난주와 비교하지 마세요. 제목, 날짜, 금액, 퍼센트, 숫자, 별도 카테고리 목록은 작성하지 마세요. 180자 이내 한국어로 답하세요."""
    else:
        instructions = """소비 분석 문장만 작성하세요. 지난주 소비를 객관적으로 평가하고, 잘한 점·아쉬운 점·절약이 필요한 부분과 근거·이번 주 실천 제안을 포함하세요. 제목, 날짜, 금액, 퍼센트, 숫자, 카테고리별 금액 목록은 작성하지 마세요. 제공된 집계만 사용하고 사정을 추측하지 마세요. 350자 이내 한국어로 답하세요."""
    return instructions + "\n\n[Python 집계 데이터]\n" + json.dumps(data, ensure_ascii=False)


def generate_analysis(stats, client_factory=OpenAI):
    if stats["current"]["total"] == 0:
        log.info("Current period has no spending; skipping OpenAI analysis")
        return ""
    client = client_factory(api_key=os.environ["OPENAI_API_KEY"])
    max_tokens = 250 if stats["previous"]["total"] == 0 else 450
    response = client.responses.create(model=os.environ.get("OPENAI_MODEL", "gpt-5.6-luna"), input=build_prompt(stats), max_output_tokens=max_tokens)
    usage = getattr(response, "usage", None)
    if usage:
        log.info("OpenAI usage input=%s output=%s total=%s", getattr(usage, "input_tokens", None), getattr(usage, "output_tokens", None), getattr(usage, "total_tokens", None))
    return (response.output_text or "").strip()[:500]


def generate_summary(stats, client_factory=OpenAI):
    """Backward-compatible name for callers of the former analysis function."""
    return generate_analysis(stats, client_factory)

def send_telegram(text, chat_ids):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chat_id in chat_ids:
        request = urllib.request.Request(url, data=urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode())
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        if not result.get("ok"):
            raise RuntimeError(result)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--date", help="reference date YYYY-MM-DD")
    args = parser.parse_args(argv)
    try:
        stats = collect_statistics(date.fromisoformat(args.date) if args.date else None)
        if args.dry_run:
            print(json.dumps(stats, ensure_ascii=False, indent=2))
            return 0
        send_telegram(build_report_message(stats, generate_analysis(stats)), stats["chat_ids"])
        log.info("Weekly report sent to %d chats", len(stats["chat_ids"]))
    except Exception:
        log.exception("Weekly report failed; existing services are unaffected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
