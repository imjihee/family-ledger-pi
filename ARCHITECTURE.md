# 가족 가계부 시스템 구조

## 목적

가족이 Telegram 봇에 지출을 보내면 Raspberry Pi가 이를 SQLite에 저장하고,
휴대폰이나 PC의 웹 대시보드에서 지출 내역과 통계를 확인하는 시스템이다.

## 전체 흐름

```text
Telegram 사용자
  │  카테고리번호 내용 금액
  ▼
Telegram Bot API (Long Polling)
  ▲
Raspberry Pi: telegram_bot.py
  │  사용자 확인 · 입력 파싱 · 저장
  ▼
SQLite: ledger.sqlite3
  ▲                         │
  │                         ▼
Flask: app.py  ◀────── ledger.py
  │  웹 화면 · 조회 API · 수정/삭제 API
  ▼
Cloudflare Tunnel
  ▼
휴대폰 / PC 브라우저
```

## 프로젝트 파일

```text
http-server/
├── app.py              Flask 웹 대시보드와 API
├── config.py           환경변수 기반 Flask 설정
├── telegram_bot.py     Telegram Long Polling 봇
├── ledger.py           SQLite 저장·조회·통계 로직
├── handlers/           기존 HTTP capture 기능
├── requirements.txt    Python 의존성
├── README.md            기존 HTTP API 안내
└── ARCHITECTURE.md      이 문서
```

## Telegram 입력

봇은 webhook이 아닌 Long Polling을 사용한다. Raspberry Pi가 Telegram API에
`getUpdates(timeout=30)` 요청을 보내고, 새 메시지가 오거나 30초가 지나면
다음 요청을 보낸다. 따라서 외부에서 Pi로 들어오는 Telegram 포트나 Tunnel은
필요하지 않다.

입력 형식은 다음과 같다.

```text
카테고리번호 내용 금액
```

```text
1 식비
2 여가
3 통신/구독
4 경조사
5 쇼핑
6 주거/생활
7 저축/투자
8 커피
```

예시:

```text
2 스타벅스 5500
1 점심 12000
```

Telegram 사용자 ID는 allowlist로 확인한다. 등록되지 않은 사용자는 저장할 수
없고, `/id` 명령으로 자신의 Telegram 사용자 ID를 확인할 수 있다.

## 데이터 저장

지출은 다음 SQLite 파일에 저장된다.

```text
/home/kim/.config/http-server/ledger.sqlite3
```

이 DB는 Telegram 봇과 Flask 웹 서버가 함께 사용한다. 웹에서 수정·삭제하면
같은 SQLite 데이터가 변경된다.

## 웹 대시보드

Flask는 다음 기능을 제공한다.

```text
GET  /                         웹 대시보드
GET  /login                    로그인 화면
GET  /api/expenses             지출 목록
GET  /api/statistics           통계
PUT  /api/expenses/<id>        지출 수정
DELETE /api/expenses/<id>      지출 삭제
POST /event                    기존 capture HTTP API
```

외부 접속은 Cloudflare Tunnel이 담당한다.

```text
브라우저 → Cloudflare → Tunnel → Flask (localhost:8080)
```

Telegram 수신 경로와 웹 대시보드 접속 경로는 서로 독립적이다.

## 자동 시작 서비스

사용자 systemd 서비스가 다음 프로세스를 관리한다.

```text
http-server.service          Flask 웹 서버
telegram-ledger.service      Telegram Polling 봇
http-server-tunnel.service   Cloudflare Tunnel
weekly-report.timer           일요일 19:00 주간 OpenAI 리포트
```

`loginctl enable-linger kim`이 설정되어 있으면 Raspberry Pi를 재부팅한 뒤
로그인하지 않아도 위 서비스가 자동으로 시작된다.

## 비밀 설정

다음 파일은 GitHub에 올리면 안 된다.

```text
/home/kim/.config/http-server/api.env
/home/kim/.config/http-server/telegram.env
/home/kim/.config/http-server/ledger.sqlite3
```

- `api.env`: 웹 로그인/API 설정
- `telegram.env`: Telegram Bot Token과 사용자 allowlist
- `ledger.sqlite3`: 실제 가족 지출 데이터

이 프로젝트의 `.gitignore`는 환경 파일, SQLite DB, Python 캐시를 제외한다.

## GitHub에 올릴 때

프로젝트 코드만 올린다.

```bash
cd /home/kim/http-server
git init
git add .
git status
```

`git status`에서 토큰, `.env` 파일, `ledger.sqlite3`가 보이면 커밋하지 말고
먼저 `.gitignore` 규칙을 확인한다.

## 주간 OpenAI 리포트

`weekly_report.py`가 매주 일요일 19:00에 현재 주(월요일~오늘)와 지난 주(월~일)를 SQLite에서 집계한다. 총액, 거래 건수, 일평균, 카테고리별·사용자별 합계, 일별 합계와 전주 대비 증감률만 OpenAI Responses API에 전달한다. 원본 거래 목록과 DB 파일은 전달하지 않는다.

systemd 구성:

```text
weekly-report.timer   매주 일요일 19:00 실행
weekly-report.service 1회성 Python 작업
```

`--dry-run` 옵션은 OpenAI와 Telegram을 호출하지 않고 집계 JSON만 출력하므로 테스트에 사용한다.
