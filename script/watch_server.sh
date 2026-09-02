#!/usr/bin/env bash

# Flask HTTP API 서버의 실시간 로그를 확인합니다.
# - journalctl : systemd 서비스 로그를 조회
# - --user     : 현재 사용자(kim)의 user service 로그 조회
# - -u         : 특정 서비스(http-server.service)의 로그만 조회
# - -f         : 새로운 로그가 발생할 때마다 실시간으로 출력 (follow)

journalctl --user -u http-server.service -f
