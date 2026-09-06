# Vbee TTS integration

Vbee is isolated from the legal/Zalo AI core. The chatbot continues to work even when Vbee is not configured.

## Render environment variables

Required:

- `VBEE_APP_ID` — App ID created at Vbee API dashboard.
- `VBEE_ACCESS_TOKEN` — Bearer/JWT token issued for that Vbee App.
- `VBEE_VOICE_CODE` — Voice code copied from Vbee AIVoice voice library. For the public-address use case, select a Northern Vietnamese voice and copy its API voice code.
- `VBEE_TTS_API_TOKEN` — Internal token protecting quota-consuming `/api/tts` endpoints. Generate a long random value; never commit it.
- `VBEE_CALLBACK_SECRET` — Long random value embedded only in the callback URL so forged callbacks are rejected. Never commit it.

Optional defaults:

- `VBEE_API_BASE=https://vbee.vn/api/v1`
- `VBEE_AUDIO_TYPE=mp3`
- `VBEE_SPEED_RATE=0.95`
- `VBEE_BITRATE=128`
- `VBEE_MAX_CHARS=10000`
- `VBEE_TIMEOUT_SECONDS=15`

## Endpoints

### Health

`GET /vbee/health`

Returns only configuration state, never secrets.

### Create audio

`POST /api/tts`

Header:

`Authorization: Bearer <VBEE_TTS_API_TOKEN>`

JSON body:

```json
{
  "text": "Kính thưa toàn thể Nhân dân!",
  "speed_rate": 0.95,
  "audio_type": "mp3"
}
```

The server forwards the request to Vbee asynchronously and returns `request_id`.

### Check audio

`GET /api/tts/<request_id>`

Use the same `Authorization` header. When finished, the response includes Vbee's `audio_link`.

### Vbee callback

`POST /vbee/callback?key=<VBEE_CALLBACK_SECRET>`

This URL is generated automatically by the server and supplied to Vbee. Do not expose the callback secret publicly.

## Public-address recommended starting settings

For a clear commune loudspeaker/newsreader style, start with:

- Northern Vietnamese voice in the Vbee voice library
- `VBEE_SPEED_RATE=0.90` to `0.95`
- MP3, 128 kbps

Use punctuation and paragraph breaks for natural pauses. Markdown bold markers are stripped automatically before synthesis.
