# 현재 운영 구조와 테스트

## 구조

```text
Telegram → telegram-ledger.service (Long Polling) → SQLite
                                                     ↑
브라우저 → Cloudflare Named Tunnel → http-server.service (Flask)

weekly-report.timer → weekly-report.service → OpenAI Responses API → Telegram
```

Telegram 수신에는 Tunnel·webhook·포트포워딩이 필요하지 않습니다. Tunnel은 웹 대시보드 외부 접속에만 사용합니다.

## 서비스

```text
http-server.service          Flask 웹/API (8080)
telegram-ledger.service      Telegram getUpdates 봇
http-server-tunnel.service   고정 Cloudflare Tunnel
weekly-report.timer           매주 월요일 09:00
```

부팅 후 자동 시작하려면 한 번 설정합니다.

```bash
sudo loginctl enable-linger kim
```

상태 확인:

```bash
~/http-server/script/check_server.sh
```

## Telegram 테스트

```text
/help
8 스타벅스 5500
```

사용자 ID allowlist는 `~/.config/http-server/telegram.env`의 `TELEGRAM_ALLOWED_USER_IDS`에서 관리합니다.

## 주간 리포트 테스트

집계만 확인(OpenAI·Telegram 호출 없음):

```bash
cd ~/http-server
.venv/bin/python weekly_report.py --dry-run --date 2026-09-03
```

이 경우 current는 `2026-08-31~2026-09-03`, previous는 `2026-08-24~2026-08-30`입니다. 자동 실행 수동 테스트는 다음과 같습니다.

```bash
systemctl --user start weekly-report.service
journalctl --user -u weekly-report.service -n 50 --no-pager
```

`OPENAI_API_KEY`는 `~/.config/http-server/weekly-report.env`에만 보관합니다. `weekly_report.py`는 API 오류가 나도 예외를 기록하고 0으로 종료하여 다른 서비스를 중단하지 않습니다.

## 웹 API

```text
GET  /                 대시보드
GET  /api/expenses      지출 조회
GET  /api/statistics    통계
PUT  /api/expenses/id  수정
DELETE /api/expenses/id 삭제
POST /event            기존 capture API (Bearer 인증)
```

## 스크립트

```text
script/check_server.sh       운영 서비스 상태
script/run_services.sh       운영 서비스 시작
script/send_report_now.sh    오늘 기준 리포트 실행
script/watch_server.sh       운영 로그 follow
```
