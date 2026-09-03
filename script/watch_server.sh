#!/usr/bin/env bash
# 역할: Flask, Telegram, Cloudflare Tunnel의 systemd 로그를 실시간으로 보여줍니다.
# 종료: Ctrl+C (서비스는 종료되지 않고 로그 보기만 중단됩니다.)
# 사용법: ./script/watch_server.sh
set -euo pipefail
# Flask, Telegram, Tunnel 서비스 로그를 함께 확인합니다.
exec journalctl --user -u http-server.service -u telegram-ledger.service -u http-server-tunnel.service -f
