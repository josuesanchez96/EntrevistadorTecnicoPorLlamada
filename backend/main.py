"""
main.py
Servidor principal FastAPI:
  - POST  /api/upload         → Ingesta de CV y Vacante, creación de sesión
  - GET   /api/session/{id}   → Estado de la sesión
  - POST  /api/session/{id}/end → Finalización y generación de reporte
  - WS    /ws/interview/{id}  → Pipeline de audio bidireccional en tiempo real
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from audio_clients import AssemblyAIStreamingClient, synthesize_audio
from graph import continuar_entrevista, finalizar_entrevista, iniciar_entrevista
from rag_engine import build_vector_store
from session_store import store as session_store

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Entrevistador Técnico por IA",
    description="API para entrevistas técnicas simuladas por voz usando IA.",
    version="1.0.0",
)

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints REST
# ─────────────────────────────────────────────────────────────────────────────


@app.post("/api/upload", summary="Cargar CV y Vacante para iniciar una sesión")
async def upload_documents(
    cv_file: UploadFile = File(..., description="Archivo del CV (PDF, DOCX o TXT)"),
    jd_text: str = Form(..., description="Texto de la descripción de la vacante"),
):
    """
    Recibe el CV del candidato y la descripción del puesto.
    Genera embeddings y crea el almacén vectorial FAISS.
    Retorna el session_id para conectarse al WebSocket de la entrevista.
    """
    if not cv_file.filename:
        raise HTTPException(status_code=400, detail="El archivo de CV es requerido.")
    if not jd_text.strip():
        raise HTTPException(status_code=400, detail="La descripción de la vacante es requerida.")

    session_id = str(uuid.uuid4())
    logger.info("Nueva sesión creada: %s | CV: %s", session_id, cv_file.filename)

    try:
        cv_bytes = await cv_file.read()
        vector_store, cv_text, jd_text_clean = await asyncio.to_thread(
            build_vector_store, cv_bytes, cv_file.filename, jd_text
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Error construyendo almacén vectorial: %s", exc)
        raise HTTPException(status_code=500, detail="Error procesando los documentos.")

    # Persistir en el almacén de sesiones
    session = session_store.create(session_id, cv_text, jd_text_clean)
    session_store.update(session_id, vector_store=vector_store)

    return {
        "session_id": session_id,
        "status": "ready",
        "message": "Documentos procesados exitosamente. Conecta al WebSocket para iniciar la entrevista.",
    }


@app.get("/api/session/{session_id}", summary="Consultar estado de una sesión")
async def get_session(session_id: str):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    return {
        "session_id": session_id,
        "finished": session.finished,
        "has_report": session.report is not None,
        "report": session.report,
    }


@app.post("/api/session/{session_id}/end", summary="Finalizar entrevista y generar reporte")
async def end_session(session_id: str):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    if session.finished:
        return {"session_id": session_id, "report": session.report}

    if session.graph_state is None:
        raise HTTPException(status_code=400, detail="La entrevista no ha iniciado aún.")

    try:
        resultado = await asyncio.to_thread(finalizar_entrevista, session.graph_state)
        reporte = resultado.get("reporte")
        session_store.update(session_id, graph_state=resultado, finished=True, report=reporte)
    except Exception as exc:
        logger.exception("Error generando reporte para sesión %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Error generando el reporte.")

    return {"session_id": session_id, "report": reporte}


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket — Pipeline de Audio
# ─────────────────────────────────────────────────────────────────────────────


async def _send_json(ws: WebSocket, data: dict) -> None:
    """Envía un mensaje JSON por el WebSocket de forma segura."""
    try:
        await ws.send_text(json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


async def _send_bytes(ws: WebSocket, data: bytes) -> None:
    """Envía bytes de audio por el WebSocket de forma segura."""
    try:
        await ws.send_bytes(data)
    except Exception:
        pass


def _ultimo_mensaje_agente(messages: list) -> str:
    from langchain_core.messages import AIMessage

    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and (msg.content or "").strip():
            return str(msg.content).strip()
    return ""


@app.websocket("/ws/interview/{session_id}")
async def websocket_interview(ws: WebSocket, session_id: str):
    """
    WebSocket principal de la entrevista.
    Protocolo:
      Cliente → Server (binario): fragmentos de audio PCM16 a 16kHz mono
      Cliente → Server (JSON): {"type": "end_interview"} | {"type": "ping"}
      Server → Cliente (JSON):  mensajes de estado y transcripción
      Server → Cliente (binario): audio MP3 sintetizado por Cartesia
    """
    await ws.accept()
    logger.info("WS conectado para sesión: %s", session_id)

    session = session_store.get(session_id)
    if not session:
        await _send_json(ws, {"type": "error", "message": "Sesión no encontrada."})
        await ws.close()
        return

    transcript_queue: asyncio.Queue[str] = asyncio.Queue()
    graph_state: dict = {}
    transcript_state: dict[str, str] = {"last_sent": "", "last_queued": ""}

    async def _handle_transcript_message(msg: dict) -> None:
        msg_type = msg.get("type", "")
        if msg_type == "Turn":
            is_final = msg.get("end_of_turn", False)
            text = msg.get("transcript", "").strip()
        elif msg_type in ("PartialTranscript", "FinalTranscript"):
            text = msg.get("text", "").strip()
            is_final = msg_type == "FinalTranscript"
        else:
            return

        if text and text != transcript_state["last_sent"]:
            logger.info("AssemblyAI: '%s' (final=%s)", text, is_final)
            await _send_json(ws, {"type": "transcript", "text": text, "is_final": is_final})
            transcript_state["last_sent"] = text

        if is_final and text and text != transcript_state["last_queued"]:
            transcript_state["last_queued"] = text
            logger.info("Encolando respuesta del candidato: '%s'", text)
            await transcript_queue.put(text)

    async def audio_to_transcript_task():
        chunk_count = 0
        interview_ended = False

        async def read_transcripts_loop(aai: AssemblyAIStreamingClient):
            try:
                async for msg in aai.transcripts():
                    await _handle_transcript_message(msg)
            except asyncio.CancelledError:
                raise

        try:
            while not interview_ended:
                async with AssemblyAIStreamingClient() as aai:
                    reader = asyncio.create_task(read_transcripts_loop(aai))
                    aai_dead = False
                    try:
                        while not interview_ended and not aai_dead:
                            try:
                                message = await ws.receive()
                                if message.get("type") == "websocket.disconnect":
                                    raise WebSocketDisconnect(code=message.get("code", 1000))
                            except WebSocketDisconnect:
                                interview_ended = True
                                await aai.terminate()
                                break

                            if "bytes" in message and message["bytes"]:
                                chunk_count += 1
                                if chunk_count % 10 == 0:
                                    logger.info("Audio micrófono: %d fragmentos", chunk_count)
                                if not await aai.send_audio(message["bytes"]):
                                    logger.warning("AssemblyAI desconectado; reconectando...")
                                    aai_dead = True
                                    break

                            elif "text" in message and message["text"]:
                                try:
                                    data = json.loads(message["text"])
                                except json.JSONDecodeError:
                                    continue
                                msg_type = data.get("type", "")
                                if msg_type == "end_interview":
                                    interview_ended = True
                                    await aai.terminate()
                                    await transcript_queue.put("__END__")
                                    break
                                elif msg_type == "ping":
                                    await _send_json(ws, {"type": "pong"})
                                elif msg_type == "utterance_end":
                                    await aai.force_endpoint()
                    finally:
                        reader.cancel()
                        try:
                            await reader
                        except asyncio.CancelledError:
                            pass
                    if interview_ended:
                        break
        except WebSocketDisconnect:
            pass

    async def agent_response_task():
        nonlocal graph_state
        while True:
            try:
                user_text = await asyncio.wait_for(transcript_queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                break

            if user_text == "__END__":
                await _send_json(ws, {"type": "agent_thinking"})
                try:
                    if graph_state.get("messages"):
                        final_state = await asyncio.to_thread(finalizar_entrevista, graph_state)
                        reporte = final_state.get("reporte")
                        session_store.update(
                            session_id, graph_state=final_state, finished=True, report=reporte
                        )
                        await _send_json(ws, {"type": "report", "data": reporte})
                except Exception as exc:
                    logger.exception("Error generando reporte: %s", exc)
                break

            if not user_text.strip() or not graph_state.get("messages"):
                continue

            await _send_json(ws, {"type": "agent_thinking"})
            try:
                graph_state = await asyncio.to_thread(
                    continuar_entrevista, graph_state, user_text
                )
                session_store.update(session_id, graph_state=graph_state)
                texto = _ultimo_mensaje_agente(graph_state.get("messages", []))
                if texto:
                    await _send_json(ws, {"type": "agent_message", "text": texto})
                    await _send_json(ws, {"type": "tts_start", "text": texto})
                    try:
                        audio = await synthesize_audio(texto)
                        await _send_bytes(ws, audio)
                    except Exception as exc:
                        logger.warning("Error TTS: %s", exc)
                    await _send_json(ws, {"type": "tts_end"})
                transcript_state["last_queued"] = ""
            except Exception as exc:
                logger.exception("Error respuesta agente: %s", exc)
                await _send_json(ws, {"type": "error", "message": "Error procesando tu respuesta."})

    async def send_initial_greeting() -> bool:
        nonlocal graph_state
        await _send_json(ws, {"type": "agent_thinking"})
        try:
            graph_state = await asyncio.to_thread(
                iniciar_entrevista, session_id, session.cv_text, session.jd_text
            )
            session_store.update(session_id, graph_state=graph_state)
        except Exception as exc:
            logger.exception("Error iniciando entrevista: %s", exc)
            await _send_json(ws, {"type": "error", "message": "Error iniciando la entrevista."})
            return False

        texto = _ultimo_mensaje_agente(graph_state.get("messages", []))
        if not texto:
            return True
        await _send_json(ws, {"type": "tts_start", "text": texto})
        try:
            audio = await synthesize_audio(texto)
            await _send_bytes(ws, audio)
            logger.info("Saludo TTS enviado (%d bytes).", len(audio))
        except Exception as exc:
            logger.warning("Error TTS saludo: %s", exc)
        await _send_json(ws, {"type": "tts_end"})
        return True

    async def run_pipeline():
        await asyncio.gather(audio_to_transcript_task(), agent_response_task())

    pipeline_task = asyncio.create_task(run_pipeline())
    try:
        if not await send_initial_greeting():
            pipeline_task.cancel()
            try:
                await pipeline_task
            except asyncio.CancelledError:
                pass
            await ws.close()
            return
        await pipeline_task
    except asyncio.CancelledError:
        logger.info("Tareas WS canceladas: %s", session_id)
    except WebSocketDisconnect:
        logger.info("WebSocket desconectado: %s", session_id)
    except Exception as exc:
        logger.exception("Error inesperado en WS: %s", exc)
    finally:
        logger.info("WS cerrado para sesión: %s", session_id)
        try:
            await ws.close()
        except Exception:
            pass


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", summary="Health check")
async def health():
    return {"status": "ok", "service": "Entrevistador Técnico por IA"}
