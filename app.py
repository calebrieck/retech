import os
import json
import asyncio
from typing import Set

from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
import websockets

load_dotenv()

ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

app = FastAPI()
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


CLIENTS: Set[WebSocket] = set()
CLIENTS_LOCK = asyncio.Lock()


async def broadcast(payload: dict) -> None:
    """
    Send a JSON message to every connected /ws/client subscriber.
    Removes dead connections.
    """
    msg = json.dumps(payload)
    async with CLIENTS_LOCK:
        clients = list(CLIENTS)

    dead = []
    for client_ws in clients:
        try:
            await client_ws.send_text(msg)
        except Exception:
            dead.append(client_ws)

    if dead:
        async with CLIENTS_LOCK:
            for d in dead:
                CLIENTS.discard(d)


@app.websocket("/ws/client")
async def ws_client(ws: WebSocket):
    """
    Your notebook connects here to receive live transcript events.
    """
    await ws.accept()
    async with CLIENTS_LOCK:
        CLIENTS.add(ws)

    try:
        # Keep the socket open; ignore any incoming messages
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with CLIENTS_LOCK:
            CLIENTS.discard(ws)


# ----------------------------
# Outbound call trigger
# ----------------------------
@app.post("/call-me")
async def call_me():
    call = twilio_client.calls.create(
        to="+14046443252",
        from_="+18886444317",
        url="https://tereasa-unscabbed-leonard.ngrok-free.dev/voice",
    )
    print("Outbound call initiated. SID:", call.sid)
    return {"status": "calling", "sid": call.sid}


# ----------------------------
# Twilio webhook (TwiML) Connects
# ----------------------------
# This is like the control plane
@app.post("/voice")
async def voice(_: Request):
    print(">>> /voice HIT <<<")
    twiml = VoiceResponse()
    twiml.say("Hi. Start speaking after the beep. beeeeeep")
    twiml.pause(length=1)

    connect = twiml.connect()
    connect.stream(url="wss://tereasa-unscabbed-leonard.ngrok-free.dev/ws/twilio") #when the call connects twilio is told to stream audio to this ws endpoint

    return Response(str(twiml), media_type="text/xml")


def eleven_realtime_stt_url() -> str:
    return (
        "wss://api.elevenlabs.io/v1/speech-to-text/realtime"
        "?model_id=scribe_v2_realtime"
        "&language_code=en"
        "&audio_format=ulaw_8000"
        "&commit_strategy=vad"
    )


def extract_text_and_final(msg: dict) -> tuple[str, bool] | None:
    """
    Eleven's realtime schema can vary by version. This is a best-effort extractor.
    After you see a real message, you can tighten this to the exact fields.

    Returns (text, is_final) or None if no transcript text found.
    """
    text = (
        msg.get("text")
        or msg.get("transcript")
        or msg.get("data", {}).get("text")
        or msg.get("data", {}).get("transcript")
        or ""
    )
    if not text:
        return None

    is_final = bool(
        msg.get("is_final")
        or msg.get("final")
        or msg.get("data", {}).get("is_final")
        or msg.get("data", {}).get("final")
        or msg.get("type") in {"final", "transcript_final"}
    )
    return text, is_final


# ----------------------------
# Twilio Media Stream WS
# ----------------------------
#This is like the data plane
@app.websocket("/ws/twilio")
async def ws_twilio(ws: WebSocket):
    await ws.accept()
    print("Twilio websocket connected")

    url = eleven_realtime_stt_url()
    print("Eleven WS URL:", url)

    call_sid = None
    stream_sid = None

    try:
        async with websockets.connect(
            url,
            additional_headers=[("xi-api-key", ELEVEN_API_KEY)],
        ) as eleven_ws:
            print("Connected to ElevenLabs")

            # Some realtime APIs expect a start/init; harmless if ignored
            await eleven_ws.send(json.dumps({"message_type": "start"}))

            async def forward_twilio_audio_to_eleven():
                nonlocal call_sid, stream_sid
                while True:
                    raw = await ws.receive_text()
                    msg = json.loads(raw)

                    event = msg.get("event")

                    if event == "start":
                        start = msg.get("start", {})
                        call_sid = start.get("callSid")
                        stream_sid = start.get("streamSid")
                        print("Twilio start:", {"callSid": call_sid, "streamSid": stream_sid})
                        await broadcast({
                            "source": "twilio",
                            "event": "start",
                            "call_sid": call_sid,
                            "stream_sid": stream_sid,
                        })

                    elif event == "media":
                        await eleven_ws.send(json.dumps({
                            "message_type": "input_audio_chunk",
                            "audio_base_64": msg["media"]["payload"],
                        }))

                    elif event == "stop":
                        print("Twilio stop received")
                        await broadcast({
                            "source": "twilio",
                            "event": "stop",
                            "call_sid": call_sid,
                            "stream_sid": stream_sid,
                        })
                        break

            async def read_eleven_transcripts():
                try:
                    first = await eleven_ws.recv()
                    # send first message to notebook too (often contains config/error)
                    try:
                        first_msg = json.loads(first)
                    except Exception:
                        first_msg = {"raw": first}

                    await broadcast({
                        "source": "eleven",
                        "event": "first_message",
                        "call_sid": call_sid,
                        "stream_sid": stream_sid,
                        "message": first_msg,
                    })
                    print("Eleven first msg:", first)

                    while True:
                        raw = await eleven_ws.recv()
                        msg = json.loads(raw)

                        extracted = extract_text_and_final(msg)
                        if extracted is not None:
                            text, is_final = extracted
                            await broadcast({
                                "source": "eleven",
                                "event": "transcript",
                                "call_sid": call_sid,
                                "stream_sid": stream_sid,
                                "text": text,
                                "is_final": is_final,
                                "raw": msg, 
                            })
                        else:
                            # still forward non-transcript messages for debugging
                            await broadcast({
                                "source": "eleven",
                                "event": "message",
                                "call_sid": call_sid,
                                "stream_sid": stream_sid,
                                "raw": msg,
                            })

                except websockets.ConnectionClosed as e:
                    print("Eleven WS closed:", e.code, e.reason)
                    await broadcast({
                        "source": "eleven",
                        "event": "closed",
                        "call_sid": call_sid,
                        "stream_sid": stream_sid,
                        "code": e.code,
                        "reason": e.reason,
                    })

            await asyncio.gather(
                forward_twilio_audio_to_eleven(),
                read_eleven_transcripts(),
            )

    except WebSocketDisconnect:
        print("Twilio websocket disconnected")
    except Exception as e:
        print("Error in ws_twilio:", repr(e))
        await broadcast({
            "source": "server",
            "event": "error",
            "call_sid": call_sid,
            "stream_sid": stream_sid,
            "error": repr(e),
        })
        try:
            await ws.close()
        except Exception:
            pass
