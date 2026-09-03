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


def no_spending_summary(stats):
    period = stats["current"]["period"]
    return f"이번 주 ({period['start']} ~ {period['end']}) 지출이 없습니다."


def build_prompt(stats):
    data = {key: stats[key] for key in ("current", "previous", "change_percent")}
    current_zero = stats["current"]["total"] == 0
    previous_zero = stats["previous"]["total"] == 0
    if current_zero:
        instructions = """당신은 우리 가족의 가계부를 알려주는 소비 분석 어시스턴트입니다.
이번 주 지출이 0원이라는 사실을 중심으로 짧고 친근하게 안내하세요.
전주 지출이 있더라도 비교 평가나 억지스러운 제안은 하지 마세요.
제공된 숫자를 그대로 사용하고, 원본 거래내역은 제공되지 않았습니다.
Telegram 메시지로 150자 이내로 작성하세요."""
    elif previous_zero:
        instructions = """당신은 우리 가족의 가계부를 간단히 분석하는 소비 분석 어시스턴트입니다.
이번 주 총 지출과 주요 카테고리를 짧게 요약하고, 절약이 필요해 보이는 부분이 있을 때만 근거와 함께 권고하세요. 실천 가능한 제안은 최대 1개만 작성하세요.
지난주 지출이 0원이므로 전주 대비 비교나 증감 평가를 하지 마세요.
제공된 숫자를 그대로 사용하고 추측하지 마세요. Telegram 메시지로 250자 이내로 작성하세요."""
    else:
        instructions = """당신은 우리 가족의 가계부를 분석하고 평가하는 소비 분석 어시스턴트입니다.
Python에서 계산한 지출 통계를 바탕으로 지난주 소비를 객관적으로 평가하세요.
전체 지출 수준과 전주 대비 변화, 가장 많이 지출한 카테고리, 크게 증가·감소한 지출,
잘한 점과 아쉬운 점, 이번 주에 실천할 구체적인 제안을 고려하세요.
단순 나열이 아닌 판단과 의견을 제시하세요. 절약이 필요하다고 판단되면 어떤 카테고리에서 왜 절약할지 구체적으로 권고하세요. 다만 데이터만으로 알 수 없는 사정은 추측하지 마세요.
숫자는 Python 계산값을 그대로 사용하고 원본 거래내역은 제공되지 않았습니다.
친근한 한국어 Telegram 메시지로 500자 이내 작성하세요."""
    return instructions + "\n\n[집계 데이터]\n" + json.dumps(data, ensure_ascii=False)

def generate_summary(stats, client_factory=OpenAI):
    client = client_factory(api_key=os.environ["OPENAI_API_KEY"])
    max_tokens = 200 if stats["current"]["total"] == 0 else 300 if stats["previous"]["total"] == 0 else 500
    response = client.responses.create(model=os.environ.get("OPENAI_MODEL", "gpt-5.6-luna"), input=build_prompt(stats), max_output_tokens=max_tokens)
    usage = getattr(response, "usage", None)
    if usage:
        log.info("OpenAI usage input=%s output=%s total=%s", getattr(usage, "input_tokens", None), getattr(usage, "output_tokens", None), getattr(usage, "total_tokens", None))
    return (response.output_text or "주간 리포트를 생성하지 못했습니다.").strip()[:500]


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
        send_telegram(generate_summary(stats), stats["chat_ids"])
        log.info("Weekly report sent to %d chats", len(stats["chat_ids"]))
    except Exception:
        log.exception("Weekly report failed; existing services are unaffected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
