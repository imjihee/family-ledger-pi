# Raspberry Pi Flask API + Cloudflare Quick Tunnel 작업 기록

## 목표 구조

```text
외부 서버
  ↓ HTTPS
Cloudflare Quick Tunnel (`https://xxxxx.trycloudflare.com`)
  ↓ outbound Cloudflare Tunnel
Raspberry Pi
  ↓ localhost:8080
Flask API (`POST /event`)
  ↓
JSON parsing → Command Handler
```

Cloudflare Tunnel은 Raspberry Pi에서 Cloudflare로 나가는(outbound) 연결을
사용한다. 따라서 ipTIME 포트포워딩, 기존 SSH `2200 → 22` 설정, DuckDNS,
개인 도메인은 변경하거나 사용하지 않았다.

## 환경 확인 결과

| 항목 | 결과 |
| --- | --- |
| 운영체제 | Ubuntu 24.04.4 LTS |
| 아키텍처 | ARM64 (`aarch64`) |
| Python | 3.12.3 |
| pip | 24.0 (시스템) |
| Flask | 3.1.3 (프로젝트 가상환경) |
| cloudflared | 2026.8.2 (공식 ARM64 바이너리) |

`cloudflared`는 시스템 전역 경로가 아니라 프로젝트의
`~/http-server/bin/cloudflared`에 설치되어 있다. 따라서 명령은
`./bin/cloudflared`로 실행한다.

## 프로젝트 구성

```text
http-server/
├── app.py
├── config.py
├── handlers/
│   ├── __init__.py
│   └── capture.py
├── requirements.txt
├── README.md
├── bin/
│   └── cloudflared
└── docs/
    └── SETUP_AND_TEST.md
```

## API 동작

### `POST /event`

요청 예시:

```json
{
  "command": "capture",
  "message": "take a picture"
}
```

- `command`와 `message`는 필수 문자열이다.
- 지원 명령은 현재 `capture`뿐이다.
- `capture`는 카메라 제어 전의 mock handler이며 Flask 로그에
  `Capture command received`를 출력한다.
- 성공 시 `200`과 `{"result":"ok"}`를 반환한다.
- JSON이 아니거나 형식이 올바르지 않으면 `400`을 반환한다.
- 필수 필드가 없거나 지원하지 않는 명령이면 `400`을 반환한다.

## Bearer Token 인증

`API_BEARER_TOKEN` 환경변수를 설정하면 모든 요청에 다음 헤더가 필요하다.

```text
Authorization: Bearer <API_BEARER_TOKEN 값>
```

일치하지 않거나 누락되면 `401 Unauthorized`를 반환한다. 토큰은 프로젝트
파일이나 Git에 저장하지 않는다. Quick Tunnel을 열 때는 항상 충분히 긴 임의의
값을 설정한다.

## 재실행 방법

### 1. Flask 실행

첫 번째 터미널에서 실행한다.

```bash
cd ~/http-server
export API_BEARER_TOKEN='충분히-길고-임의적인-비밀-토큰'
.venv/bin/python app.py
```

Flask는 `0.0.0.0:8080`에서 리스닝한다.

### 2. 로컬 요청 테스트

두 번째 터미널에서 실행한다.

```bash
curl -X POST http://localhost:8080/event \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $API_BEARER_TOKEN" \
  -d '{"command":"capture","message":"local test"}'
```

기대 응답:

```json
{"result":"ok"}
```

Flask 터미널에는 다음 로그가 표시된다.

```text
Capture command received
```

### 3. Cloudflare Quick Tunnel 실행

Flask를 계속 실행한 상태에서 다른 터미널에 실행한다.

```bash
cd ~/http-server
./bin/cloudflared tunnel --url http://localhost:8080
```

출력되는 `https://xxxxx.trycloudflare.com` 주소는 실행할 때마다 달라지는 임시
URL이다. 이 URL은 `cloudflared` 프로세스를 종료하면 더 이상 사용할 수 없다.

### 4. 외부 HTTPS 요청

외부 서버에서 아래 요청을 실행한다. `URL`과 토큰을 실제 값으로 교체한다.

```bash
curl -X POST https://xxxxx.trycloudflare.com/event \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer 실제-비밀-토큰' \
  -d '{"command":"capture","message":"external test"}'
```

## 완료된 검증

| 검증 | 결과 |
| --- | --- |
| Flask `0.0.0.0:8080` 기동 | 성공 |
| 인증된 로컬 `capture` 요청 | `200 {"result":"ok"}` |
| capture handler 로그 | `Capture command received` 확인 |
| 인증 누락 요청 | `401 Unauthorized` |
| 잘못된 JSON 요청 | `400 Bad Request` |
| Quick Tunnel 생성 및 Cloudflare 연결 | 성공 |
| Quick Tunnel HTTPS `capture` 요청 | `200 {"result":"ok"}` 및 Flask 로그 확인 |
| 잘못된 토큰의 Quick Tunnel 요청 | `401 Unauthorized` |

## 이번 단계에서 하지 않은 작업

- systemd 자동 실행
- 고정(named) Cloudflare Tunnel
- Cloudflare 계정 기반 설정
- 사용자 도메인 연결
- production WSGI 서버 및 production deployment
- HTTPS 인증서 직접 관리

테스트가 끝나면 Flask와 `cloudflared` 프로세스를 `Ctrl+C`로 종료하여 임시 API
노출을 끝낸다.
