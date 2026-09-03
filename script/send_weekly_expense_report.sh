#!/usr/bin/env bash
# 역할: 오늘 날짜를 기준으로 주간 가계부 리포트를 즉시 실행합니다.
# 기본 실행은 OpenAI 분석 후 Telegram 전송이며, --dry-run은 전송 없이 집계만 출력합니다.
# 환경변수는 프로젝트 밖의 weekly-report.env에서 읽습니다.
# 사용법: ./script/send_weekly_expense_report.sh [--dry-run] [--date YYYY-MM-DD]
set -euo pipefail
cd /home/kim/http-server
ENV_FILE=/home/kim/.config/http-server/weekly-report.env
if [[ ! -s "$ENV_FILE" ]]; then echo "환경 파일이 없습니다: $ENV_FILE" >&2; exit 1; fi
set -a
. "$ENV_FILE"
set +a
exec /home/kim/http-server/.venv/bin/python /home/kim/http-server/weekly_report.py "$@"
