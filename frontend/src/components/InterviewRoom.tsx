"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useInterviewWebSocket, WORKLET_CODE, WsMessage } from "@/lib/websocket";
import AudioVisualizer from "./AudioVisualizer";
import TranscriptFeed, { TranscriptEntry } from "./TranscriptFeed";
import ReportModal from "./ReportModal";
import styles from "./InterviewRoom.module.css";

type RoomStatus =
  | "connecting"      // Conectando al WS
  | "active"          // Entrevista en progreso
  | "ai_thinking"     // Agente procesando respuesta
  | "ai_speaking"     // Cartesia TTS reproduciendo
  | "listening"       // Esperando respuesta del candidato
  | "ended";          // Entrevista terminada

interface InterviewRoomProps {
  sessionId: string;
}

export default function InterviewRoom({ sessionId }: InterviewRoomProps) {
  // ── Estado ────────────────────────────────────────────────────────────────
  const [roomStatus, setRoomStatus] = useState<RoomStatus>("connecting");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [partialText, setPartialText] = useState("");
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [showReport, setShowReport] = useState(false);
  const [micActive, setMicActive] = useState(false);
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);

  const roomStatusRef = useRef<RoomStatus>("connecting");

  // Mantener roomStatusRef sincronizado
  useEffect(() => {
    roomStatusRef.current = roomStatus;
  }, [roomStatus]);

  // ── Refs de audio ─────────────────────────────────────────────────────────
  const audioCtxRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const isTtsFinishedRef = useRef(true);
  const ttsAudioRef = useRef<HTMLAudioElement | null>(null);
  const hasSpokenRef = useRef(false);
  const silenceStartRef = useRef<number | null>(null);
  const utteranceEndSentRef = useRef(false);
  const interviewEndedRef = useRef(false);
  const playNextAudioRef = useRef<(() => void) | null>(null);

  const resetUtteranceDetection = useCallback(() => {
    hasSpokenRef.current = false;
    silenceStartRef.current = null;
    utteranceEndSentRef.current = false;
  }, []);

  const addEntry = useCallback((speaker: "candidato" | "entrevistador", text: string) => {
    if (!text.trim()) return;
    setTranscript((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random()}`,
        speaker,
        text: text.trim(),
        timestamp: new Date(),
      },
    ]);
  }, []);

  const onTtsPlaybackEnded = useCallback(() => {
    isPlayingRef.current = false;
    if (audioQueueRef.current.length === 0 && isTtsFinishedRef.current) {
      setRoomStatus("listening");
      resetUtteranceDetection();
    } else {
      playNextAudioRef.current?.();
    }
  }, [resetUtteranceDetection]);

  const playNextAudio = useCallback(() => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;
    isPlayingRef.current = true;
    const bytes = audioQueueRef.current.shift()!;
    const url = URL.createObjectURL(new Blob([bytes], { type: "audio/mpeg" }));

    if (ttsAudioRef.current) {
      ttsAudioRef.current.pause();
    }
    const audio = new Audio(url);
    ttsAudioRef.current = audio;
    audio.onended = () => {
      URL.revokeObjectURL(url);
      onTtsPlaybackEnded();
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      onTtsPlaybackEnded();
    };
    audio.play().catch(() => {
      URL.revokeObjectURL(url);
      onTtsPlaybackEnded();
    });
  }, [onTtsPlaybackEnded]);

  useEffect(() => {
    playNextAudioRef.current = playNextAudio;
  }, [playNextAudio]);

  // ── Handlers de WS ────────────────────────────────────────────────────────
  const handleMessage = useCallback((msg: WsMessage) => {
    switch (msg.type) {
      case "agent_thinking":
        setRoomStatus("ai_thinking");
        resetUtteranceDetection();
        break;

      case "agent_message":
        if (msg.text) addEntry("entrevistador", msg.text as string);
        break;

      case "tts_start":
        setRoomStatus("ai_speaking");
        isTtsFinishedRef.current = false;
        resetUtteranceDetection();
        if (msg.text) addEntry("entrevistador", msg.text as string);
        break;

      case "tts_end":
        isTtsFinishedRef.current = true;
        if (!isPlayingRef.current && audioQueueRef.current.length === 0) {
          setRoomStatus("listening");
          resetUtteranceDetection();
        }
        break;

      case "transcript":
        if (msg.is_final) {
          setPartialText("");
          if (msg.text) addEntry("candidato", msg.text as string);
        } else {
          setPartialText(msg.text as string ?? "");
        }
        break;

      case "report":
        interviewEndedRef.current = true;
        setReport(msg.data as Record<string, unknown>);
        setRoomStatus("ended");
        setShowReport(true);
        break;

      case "error":
        console.error("Error del servidor:", msg.message);
        break;
    }
  }, [addEntry, resetUtteranceDetection]);

  const handleAudio = useCallback((bytes: ArrayBuffer) => {
    audioQueueRef.current.push(bytes.slice(0));
    playNextAudio();
  }, [playNextAudio]);

  const shouldReconnect = useCallback(() => !interviewEndedRef.current, []);

  const { status: wsStatus, connect, disconnect, sendAudio, sendJSON } =
    useInterviewWebSocket({
      sessionId,
      onMessage: handleMessage,
      onAudio: handleAudio,
      shouldReconnect,
    });

  // ── Micrófono y AudioWorklet ──────────────────────────────────────────────
  const startMicrophone = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
      micStreamRef.current = stream;

      const ctx = new AudioContext();
      audioCtxRef.current = ctx;

      // Crear analyser para visualización
      const analyserNode = ctx.createAnalyser();
      analyserNode.fftSize = 256;
      analyserRef.current = analyserNode;
      setAnalyser(analyserNode);

      // Registrar AudioWorklet como Blob URL
      const blob = new Blob([WORKLET_CODE], { type: "application/javascript" });
      const blobUrl = URL.createObjectURL(blob);
      await ctx.audioWorklet.addModule(blobUrl);
      URL.revokeObjectURL(blobUrl);

      const source = ctx.createMediaStreamSource(stream);
      sourceNodeRef.current = source;
      source.connect(analyserNode);

      const worklet = new AudioWorkletNode(ctx, "pcm-processor");
      workletNodeRef.current = worklet;
      source.connect(worklet);

      // Enviar PCM por WebSocket
      worklet.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
        if (roomStatusRef.current === "listening") {
          sendAudio(e.data);
        }
      };

      setMicActive(true);
    } catch (err) {
      console.error("Error accediendo al micrófono:", err);
      alert("No se pudo acceder al micrófono. Por favor, permite el acceso y recarga la página.");
    }
  }, [sendAudio]);

  const stopMicrophone = useCallback(() => {
    workletNodeRef.current?.disconnect();
    sourceNodeRef.current?.disconnect();
    micStreamRef.current?.getTracks().forEach((t) => t.stop());
    micStreamRef.current = null;
    setMicActive(false);
    setAnalyser(null);
  }, []);

  // ── Inicialización ────────────────────────────────────────────────────────
  useEffect(() => {
    connect();
    return () => {
      stopMicrophone();
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    if (wsStatus === "open") {
      setRoomStatus("active");
      startMicrophone();
    } else if (wsStatus === "error" || wsStatus === "closed") {
      stopMicrophone();
    }
  }, [wsStatus, startMicrophone, stopMicrophone]);

  useEffect(() => {
    if (roomStatus !== "listening" || !analyserRef.current || !micActive) return;
    let rafId = 0;
    const tick = () => {
      const node = analyserRef.current;
      if (!node || roomStatusRef.current !== "listening") return;
      const bins = new Uint8Array(node.frequencyBinCount);
      node.getByteFrequencyData(bins);
      const level = bins.reduce((a, b) => a + b, 0) / bins.length;
      if (level > 18) {
        hasSpokenRef.current = true;
        silenceStartRef.current = null;
        utteranceEndSentRef.current = false;
      } else if (hasSpokenRef.current && !utteranceEndSentRef.current) {
        const now = Date.now();
        if (silenceStartRef.current === null) silenceStartRef.current = now;
        else if (now - silenceStartRef.current >= 1400) {
          utteranceEndSentRef.current = true;
          sendJSON({ type: "utterance_end" });
        }
      }
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, [roomStatus, micActive, sendJSON]);

  const handleEndInterview = useCallback(() => {
    interviewEndedRef.current = true;
    sendJSON({ type: "end_interview" });
    stopMicrophone();
    setRoomStatus("ai_thinking");
  }, [sendJSON, stopMicrophone]);

  // ── Etiquetas de estado (ocultas para el candidato, visibles para debugging) ──
  const statusLabels: Record<RoomStatus, string> = {
    connecting: "Conectando...",
    active: "Entrevista activa",
    ai_thinking: "Procesando...",
    ai_speaking: "Rodrigo está hablando",
    listening: "Escuchando...",
    ended: "Entrevista finalizada",
  };

  const statusIndicator: Record<RoomStatus, string> = {
    connecting: styles.statusConnecting,
    active: styles.statusActive,
    ai_thinking: styles.statusThinking,
    ai_speaking: styles.statusSpeaking,
    listening: styles.statusListening,
    ended: styles.statusEnded,
  };

  return (
    <div className={styles.room}>
      {/* Header oculto para el candidato (solo status técnico) */}
      {/* data-hidden-controls: las etiquetas de control de síntesis se ocultan dinámicamente */}
      <header className={styles.header} data-hidden-controls="true" aria-hidden="true" style={{ display: "none" }}>
        <span>WS: {wsStatus}</span>
        <span>Estado: {roomStatus}</span>
        <span>Mic: {micActive ? "on" : "off"}</span>
      </header>

      {/* Panel principal visible */}
      <div className={styles.mainPanel}>
        {/* Avatar del entrevistador */}
        <div className={styles.interviewerSection}>
          <div className={`${styles.avatarRing} ${roomStatus === "ai_speaking" ? styles.avatarSpeaking : ""}`}>
            <div className={styles.avatar}>
              <span className={styles.avatarInitial}>R</span>
            </div>
          </div>
          <div className={styles.interviewerInfo}>
            <h2 className={styles.interviewerName}>Rodrigo</h2>
            <p className={styles.interviewerRole}>Entrevistador Técnico · IA</p>
          </div>

          {/* Status visible (narrado, no técnico) */}
          <div className={`${styles.statusPill} ${statusIndicator[roomStatus]}`}>
            {roomStatus === "ai_thinking" && <span className="spinner" style={{ width: 12, height: 12, borderWidth: 1.5 }} />}
            {roomStatus === "ai_speaking" && <span className={styles.speakingDot} />}
            {roomStatus === "listening" && <span className={styles.listeningDot} />}
            <span className={styles.statusText}>
              {roomStatus === "connecting" && "Conectando..."}
              {roomStatus === "ai_thinking" && "Pensando..."}
              {roomStatus === "ai_speaking" && "Hablando"}
              {roomStatus === "listening" && "Escuchándote"}
              {roomStatus === "ended" && "Entrevista finalizada"}
            </span>
          </div>
        </div>

        {/* Visualizador de audio */}
        <div className={styles.visualizerSection}>
          <AudioVisualizer
            analyser={analyser}
            isActive={micActive && roomStatus === "listening"}
            isSpeaking={roomStatus === "ai_speaking"}
          />
          <p className={styles.visualizerLabel}>
            {roomStatus === "listening"
              ? "🎙️ Habla ahora, te estoy escuchando"
              : roomStatus === "ai_speaking"
              ? "🔊 Escucha la pregunta antes de responder"
              : ""}
          </p>
        </div>

        {/* Controles */}
        <div className={styles.controls}>
          {roomStatus !== "ended" ? (
            <button
              id="end-interview-btn"
              className="btn-danger"
              onClick={handleEndInterview}
              disabled={roomStatus === "connecting" || roomStatus === "ai_thinking"}
            >
              🏁 Finalizar Entrevista
            </button>
          ) : (
            <button
              id="view-report-btn"
              className="btn-primary"
              onClick={() => setShowReport(true)}
            >
              📊 Ver Reporte de Evaluación
            </button>
          )}
        </div>
      </div>

      {/* Panel de transcripción */}
      <div className={styles.transcriptPanel}>
        <div className={styles.transcriptHeader}>
          <h3 className={styles.transcriptTitle}>Transcripción</h3>
          <span className={styles.transcriptCount}>{transcript.length} mensajes</span>
        </div>
        <div className={styles.transcriptFeed}>
          <TranscriptFeed entries={transcript} partialText={partialText} />
        </div>
      </div>

      {/* Modal de reporte */}
      {showReport && (
        <ReportModal
          report={report as Parameters<typeof ReportModal>[0]["report"]}
          onClose={() => setShowReport(false)}
        />
      )}
    </div>
  );
}
