# Raspberry Pi 가족 가계부

Telegram 봇으로 지출을 입력하고 SQLite와 Flask 웹 대시보드에서 확인하는 가족용 가계부입니다. Telegram은 webhook이 아닌 Long Polling이며, 웹 접속만 고정 Cloudflare Tunnel을 사용합니다.

## 입력 형식

```text
카테고리번호 내용 금액(숫자만)
```

```text
1 식비       2 여가       3 통신/구독       4 경조사
5 쇼핑       6 주거/생활  7 저축/투자       8 커피
```

예: `8 스타벅스 5500`

## 실행

의존성 설치:

```bash
cd ~/http-server
.venv/bin/pip install -r requirements.txt
```

운영 서비스 전체 시작:

```bash
./script/run_services.sh
```

상태·로그:

```bash
./script/check_server.sh
./script/watch_server.sh
```

## 웹 대시보드

Cloudflare 고정 주소의 `/`에서 로그인 후 지출 목록, 월·사용자·카테고리 필터, 통계, 인라인 수정·삭제를 사용할 수 있습니다. Flask는 로컬 `localhost:8080`에서 동작하고 외부 접속은 Named Tunnel이 전달합니다.

## 주간 OpenAI 리포트

`weekly_report.py`는 매주 월요일 09:00에 실행됩니다. Python이 현재 주(월요일~오늘)와 지난 주(월요일~일요일)의 합계·카테고리·사용자·일평균·증감률을 계산하고, 집계 JSON만 OpenAI Responses API에 전달합니다. 생성된 500자 이내 요약은 DB에 저장된 가족 Telegram chat ID로 보냅니다.

환경 파일을 설정한 뒤 timer를 활성화합니다.

```bash
nano ~/.config/http-server/weekly-report.env
systemctl --user daemon-reload
systemctl --user enable --now weekly-report.timer
```

실제 전송 없이 계산만 확인:

```bash
./script/send_weekly_expense_report.sh --dry-run
```

오늘 기준 실제 전송:

```bash
./script/send_weekly_expense_report.sh
```

## 비밀·데이터 파일

다음은 프로젝트 외부에 있으며 Git에 커밋하지 않습니다.

```text
~/.config/http-server/api.env
~/.config/http-server/telegram.env
~/.config/http-server/weekly-report.env
~/.config/http-server/ledger.sqlite3
```

`.gitignore`는 환경 파일, SQLite DB, Python 캐시와 Pi 전용 바이너리를 제외합니다.
