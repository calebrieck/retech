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
        "&audio_format=ulaw_8000"
        "&commit_strategy=vad"
    )


# 2) Twilio connects here via <Stream url="wss://.../ws/twilio">
@app.websocket("/ws/twilio")
async def ws_twilio(ws: WebSocket):
    await ws.accept()

    url = eleven_realtime_stt_url()
    print("Eleven WS URL:", url)

    try:
        async with websockets.connect(
            url,
            additional_headers=[("xi-api-key", ELEVEN_API_KEY)],
        ) as eleven_ws:
            print("Connected to ElevenLabs")

            # Try a start/init message
            await eleven_ws.send(json.dumps({"message_type": "start"}))

            async def forward_twilio_audio_to_eleven():
                while True:
                    raw = await ws.receive_text()
                    msg = json.loads(raw)

                    if msg.get("event") == "media":
                        await eleven_ws.send(json.dumps({
                            "message_type": "input_audio_chunk",
                            "audio_base_64": msg["media"]["payload"],
                        }))

                    if msg.get("event") == "stop":
                        break

            async def read_eleven_transcripts():
                try:
                    # Print first message from server (often contains config/error)
                    first = await eleven_ws.recv()
                    print("Eleven first msg:", first)

                    while True:
                        raw = await eleven_ws.recv()
                        msg = json.loads(raw)
                        print("Eleven msg:", msg)
                except websockets.ConnectionClosed as e:
                    print("Eleven WS closed:", e.code, e.reason)

            await asyncio.gather(forward_twilio_audio_to_eleven(), read_eleven_transcripts())

    except WebSocketDisconnect:
        print("Twilio websocket disconnected")
