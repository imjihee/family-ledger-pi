"""Telegram long-polling bot for the household expense ledger."""
import json
import logging
import os
import time
import urllib.parse
import urllib.request

from ledger import add_expense, parse_expense

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED = {int(x) for x in os.environ.get("TELEGRAM_ALLOWED_USER_IDS", "").split(",") if x.strip().isdigit()}
API = f"https://api.telegram.org/bot{TOKEN}/"


def api(method, **params):
    body = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(urllib.request.Request(API + method, data=body), timeout=45) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError(result)
    return result["result"]


def reply(chat_id, text):
    api("sendMessage", chat_id=chat_id, text=text)


def handle(message):
    user = message.get("from", {})
    user_id, chat_id = user.get("id"), message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()
    if not user_id or not chat_id:
        return
    if text == "/id":
        reply(chat_id, f"내 Telegram 사용자 ID는 {user_id} 입니다.")
        return
    if user_id not in ALLOWED:
        reply(chat_id, f"⛔ 등록되지 않은 사용자입니다. 관리자에게 이 ID를 전달하세요: {user_id}")
        return
    command = text.split()[0].split("@")[0] if text else ""
    if command in ("/start", "/help", "start", "help", "도움말"):
        reply(chat_id, "입력 형식: 카테고리번호 내용 금액(숫자만)\n1 식비\n2 여가\n3 통신/구독\n4 경조사\n5 쇼핑\n6 주거/생활\n7 저축/투자\n8 커피\n예: 8 스타벅스 5500")
        return
    parsed = parse_expense(text)
    if not parsed:
        reply(chat_id, "입력 형식이 올바르지 않습니다.\n카테고리번호 내용 금액(숫자만)\n1 식비  2 여가  3 통신/구독  4 경조사  5 쇼핑  6 주거/생활\n7 저축/투자\n8 커피\n예: 8 스타벅스 5500")
        return
    description, amount, category = parsed
    add_expense(user_id, chat_id, parsed, user.get("first_name"))
    reply(chat_id, f"✅ {description} {amount:,}원 등록했습니다.\n카테고리: {category}")


def main():
    offset = None
    log.info("Telegram bot started; %d allowed users", len(ALLOWED))
    while True:
        try:
            updates = api("getUpdates", timeout=30, **({"offset": offset} if offset else {}))
            for update in updates:
                offset = update["update_id"] + 1
                if "message" in update:
                    handle(update["message"])
        except Exception:
            log.exception("Telegram polling failed")
            time.sleep(5)


if __name__ == "__main__":
    main()

