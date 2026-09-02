# Raspberry Pi HTTP Event API

Flask API for receiving command events locally or through a Cloudflare Quick Tunnel.

## Setup

```bash
cd ~/http-server
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export API_BEARER_TOKEN='replace-with-a-long-random-secret'
python app.py
```

`API_BEARER_TOKEN` is strongly recommended. When it is set, every request needs
an exactly matching `Authorization: Bearer ...` header. The token is not stored
in this project. Without it, authentication is disabled for local development.

## Local test

```bash
curl -X POST http://localhost:8080/event \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $API_BEARER_TOKEN" \
  -d '{"command":"capture","message":"local test"}'
```

Expected response:

```json
{"result":"ok"}
```

The Flask log includes `Capture command received`.

## Cloudflare Quick Tunnel

In another terminal, while Flask is running:

```bash
./bin/cloudflared tunnel --url http://localhost:8080
```

Use the emitted `https://xxxxx.trycloudflare.com` URL for an external request:

```bash
curl -X POST https://xxxxx.trycloudflare.com/event \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $API_BEARER_TOKEN" \
  -d '{"command":"capture","message":"external test"}'
```

Quick Tunnel URLs are temporary. Stop both processes when testing ends.
