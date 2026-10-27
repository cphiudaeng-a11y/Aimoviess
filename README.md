# AI Film Studio — EP.2 (preparation / dry run)

This is a **local web starter**, not a deployed public website. The default `/preflight` does not call xAI or incur credits. No paid generation has been started.

## Install and run

Requires Python 3.10+ and ffmpeg on PATH.

```bash
cd ai_film_studio_ep2
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000, click "โหลด EP.2 ตัวอย่างที่เตรียมไว้", then "ตรวจสอบ...". No API key is needed for preflight.

## Paid mode (NOT performed)

Before paid mode, set `XAI_API_KEY` and a long, random `STUDIO_ADMIN_TOKEN` as environment variables **on the server**, not in chat or JSON. The interface requires a second explicit approval phrase and maximum budget >= estimated cost. These gates prevent accidental starts but **do not enforce an actual provider-side spending cap**: failed requests, retries, inputs, and additional services may incur charges. Do not expose this starter directly to the public internet; use HTTPS, authentication, persistent job storage, and production queue workers first. Thread jobs are lost on restart. Do not share secrets in screenshots.

Model `grok-imagine-video-1.5-lite` at 480p is estimated $6 for 300s. Full model at 720p is $42, before retries and extras. xAI returns temporary video URLs; this app downloads them immediately. Thai audio and lip-sync are requested in prompts but not guaranteed; no separate TTS or lip-sync correction is implemented. Final duration depends on actual generated clips. The server creates a normalized MP4 using ffmpeg.

Google Drive upload is optional and uses `GOOGLE_DRIVE_ACCESS_TOKEN` (OAuth bearer token with upload scope) on the server. This is distinct from the ChatGPT Google Drive connection; the connection cannot be silently reused by this standalone app. Tokens expire and production systems should use secure OAuth refresh handling. If missing, output stays on the server for authenticated download.

API: POST `/preflight` with project/model/resolution; POST `/start` additionally requires `X-Studio-Admin-Token` and approval phrase. GET `/status/{id}`; POST `/cancel/{id}` (cancel cannot refund already-submitted work).

## Source documentation
https://docs.x.ai/developers/model-capabilities/video/generation
https://docs.x.ai/developers/pricing
