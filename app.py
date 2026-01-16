import os
import json
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse
import websockets

load_dotenv()

ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")

app = FastAPI()

# 1) Twilio hits this when the call starts
@app.post("/voice")
async def voice(_: Request):
    print(">>> /voice HIT <<<")
    twiml = VoiceResponse()
    twiml.say("Hi. Start speaking after the beep.")
    twiml.pause(length=1)

    connect = twiml.connect()
    # IMPORTANT: this must be a public wss:// URL (ngrok gives you one)
    connect.stream(url="wss://tereasa-unscabbed-leonard.ngrok-free.dev/ws/twilio")

    return Response(str(twiml), media_type="text/xml")


def eleven_realtime_stt_url() -> str:
    # ElevenLabs Realtime STT WebSocket endpoint
    # Try mulaw_8000 first because Twilio sends μ-law 8k audio.
    # If you see input_error, switch to pcm_16000 and add transcoding.
    return (
        "wss://api.elevenlabs.io/v1/speech-to-text/realtime"
        "?model_id=scribe_v2_realtime"
        "&language_code=en"
        "&audio_format=mulaw_8000"
        "&commit_strategy=vad"
    )


# 2) Twilio connects here via <Stream url="wss://.../ws/twilio">
@app.websocket("/ws/twilio")
async def ws_twilio(ws: WebSocket):
    await ws.accept()

    try:
        async with websockets.connect(
            eleven_realtime_stt_url(),
            extra_headers=[("xi-api-key", ELEVEN_API_KEY)],
        ) as eleven_ws:

            async def forward_twilio_audio_to_eleven():
                """Read Twilio WS events; forward media payloads to ElevenLabs STT."""
                while True:
                    raw = await ws.receive_text()
                    msg = json.loads(raw)

                    if msg.get("event") == "media":
                        # Twilio payload is base64 audio
                        audio_b64 = msg["media"]["payload"]
                        await eleven_ws.send(json.dumps({
                            "message_type": "input_audio_chunk",
                            "audio_base_64": audio_b64,
                        }))

                    if msg.get("event") == "stop":
                        break

            async def read_eleven_transcripts():
                """Print transcripts from ElevenLabs."""
                while True:
                    raw = await eleven_ws.recv()
                    msg = json.loads(raw)

                    mtype = msg.get("message_type")

                    if mtype == "partial_transcript":
                        # uncomment if you want live partials
                        # print("partial:", msg.get("text", ""))
                        pass

                    if mtype == "committed_transcript":
                        print("YOU SAID:", msg.get("text", ""))

                    if mtype in ("input_error", "transcriber_error", "auth_error", "error"):
                        print("ElevenLabs error:", msg)

            await asyncio.gather(
                forward_twilio_audio_to_eleven(),
                read_eleven_transcripts(),
            )

    except WebSocketDisconnect:
        return
