"""
audio_clients.py
Clientes asíncronos para AssemblyAI (STT vía WebSockets) y Cartesia (TTS).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import AsyncIterator

import httpx

logger = logging.getLogger(__name__)

ASSEMBLYAI_API_KEY = os.environ.get("ASSEMBLYAI_API_KEY", "")
ASSEMBLYAI_SPEECH_MODEL = os.environ.get(
    "ASSEMBLYAI_SPEECH_MODEL", "universal-streaming-multilingual"
)
ASSEMBLYAI_STREAMING_LANGUAGE = os.environ.get("ASSEMBLYAI_STREAMING_LANGUAGE", "multi")

CARTESIA_API_KEY = os.environ.get("CARTESIA_API_KEY", "")
CARTESIA_VOICE_ID = os.environ.get(
    "CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091"
)

# 50 ms mínimo @ 16 kHz PCM16 mono
MIN_PCM_CHUNK_BYTES = 1600


class AssemblyAIStreamingClient:
    WS_URL = "wss://streaming.assemblyai.com/v3/ws"

    def __init__(self) -> None:
        self._ws = None
        self._transcript_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._reader_task: asyncio.Task | None = None
        self._alive = False

    async def __aenter__(self) -> "AssemblyAIStreamingClient":
        import websockets

        params = (
            f"?sample_rate=16000"
            f"&encoding=pcm_s16le"
            f"&speech_model={ASSEMBLYAI_SPEECH_MODEL}"
            f"&min_turn_silence=700"
            f"&include_partial_turns=true"
        )
        if ASSEMBLYAI_STREAMING_LANGUAGE == "multi":
            params += "&language_detection=true"
        elif ASSEMBLYAI_STREAMING_LANGUAGE:
            params += f"&language_code={ASSEMBLYAI_STREAMING_LANGUAGE}"

        url = f"{self.WS_URL}{params}"
        headers = {"Authorization": ASSEMBLYAI_API_KEY}

        self._ws = await websockets.connect(url, additional_headers=headers)
        self._alive = True
        logger.info("AssemblyAI WS conectado.")
        self._reader_task = asyncio.create_task(self._read_loop())
        return self

    async def __aexit__(self, *args) -> None:
        self._alive = False
        if self._reader_task:
            self._reader_task.cancel()
        if self._ws:
            await self._ws.close()
        logger.info("AssemblyAI WS cerrado.")

    @property
    def is_alive(self) -> bool:
        return self._alive

    async def _read_loop(self) -> None:
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                    await self._transcript_queue.put(msg)
                except json.JSONDecodeError:
                    pass
        except Exception as exc:
            logger.warning("Error en bucle AssemblyAI: %s", exc)
        finally:
            self._alive = False
            await self._transcript_queue.put({"type": "SessionTerminated"})

    async def send_audio(self, pcm_bytes: bytes) -> bool:
        if not self._alive or not self._ws:
            return False
        if len(pcm_bytes) < MIN_PCM_CHUNK_BYTES:
            return True
        try:
            await self._ws.send(pcm_bytes)
            return True
        except Exception as exc:
            self._alive = False
            logger.warning("Error enviando audio a AssemblyAI: %s", exc)
            return False

    async def force_endpoint(self) -> None:
        if self._ws and self._alive:
            try:
                await self._ws.send(json.dumps({"type": "ForceEndpoint"}))
            except Exception as exc:
                logger.warning("Error ForceEndpoint: %s", exc)

    async def terminate(self) -> None:
        if self._ws:
            try:
                await self._ws.send(json.dumps({"type": "Terminate"}))
            except Exception as exc:
                logger.warning("Error terminate AssemblyAI: %s", exc)

    async def transcripts(self) -> AsyncIterator[dict]:
        while True:
            msg = await self._transcript_queue.get()
            if msg.get("type") == "SessionTerminated":
                break
            yield msg


CARTESIA_TTS_URL = "https://api.cartesia.ai/tts/bytes"


async def synthesize_with_cartesia(text: str) -> bytes:
    if not CARTESIA_API_KEY:
        raise RuntimeError("CARTESIA_API_KEY no configurada.")

    payload = {
        "model_id": "sonic-2",
        "transcript": text,
        "voice": {"mode": "id", "id": CARTESIA_VOICE_ID},
        "output_format": {"container": "mp3", "encoding": "mp3", "sample_rate": 44100},
        "language": "es",
    }
    headers = {
        "X-API-Key": CARTESIA_API_KEY,
        "Cartesia-Version": "2025-04-16",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(CARTESIA_TTS_URL, json=payload, headers=headers)
        response.raise_for_status()
        audio_bytes = response.content

    logger.info("Cartesia TTS: %d bytes para '%s...'", len(audio_bytes), text[:40])
    return audio_bytes
