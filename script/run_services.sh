#!/usr/bin/env bash
# 역할: 운영에 필요한 사용자 systemd 서비스와 주간 리포트 timer를 시작합니다.
# 재부팅 후 자동 시작은 sudo loginctl enable-linger kim 설정에 의존합니다.
# 사용법: ./script/run_services.sh
set -euo pipefail
# 로그인 후 운영 서비스 전체를 시작합니다. linger가 설정되어 있으면 부팅 시 자동 시작됩니다.
systemctl --user daemon-reload
systemctl --user start http-server.service telegram-ledger.service http-server-tunnel.service weekly-report.timer
systemctl --user --no-pager --full status http-server.service telegram-ledger.service http-server-tunnel.service weekly-report.timer
