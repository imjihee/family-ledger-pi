#!/usr/bin/env bash

# Flask HTTP API 서버가 실행 중인지 확인합니다.
systemctl --user is-active http-server.service
