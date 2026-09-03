#!/usr/bin/env bash
# 역할: Raspberry Pi에서 실행해야 하는 전체 사용자 서비스의 상태를 확인합니다.
# 대상: Flask 웹 서버, Telegram Polling 봇, Cloudflare Tunnel, 주간 리포트 timer.
# 사용법: ./script/check_server.sh
set -euo pipefail
# 운영에 필요한 사용자 서비스와 주간 리포트 타이머 상태를 확인합니다.
systemctl --user is-active http-server.service telegram-ledger.service http-server-tunnel.service weekly-report.timer
