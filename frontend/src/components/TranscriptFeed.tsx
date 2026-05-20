"use client";

import { useEffect, useRef } from "react";
import styles from "./TranscriptFeed.module.css";

export interface TranscriptEntry {
  id: string;
  speaker: "candidato" | "entrevistador";
  text: string;
  isPartial?: boolean;
  timestamp: Date;
}

interface TranscriptFeedProps {
  entries: TranscriptEntry[];
  partialText?: string;
}

export default function TranscriptFeed({ entries, partialText }: TranscriptFeedProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries, partialText]);

  const formatTime = (date: Date) =>
    date.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });

  return (
    <div className={styles.feed} role="log" aria-live="polite" aria-label="Transcripción de la entrevista">
      {entries.length === 0 && !partialText && (
        <div className={styles.empty}>
          <span className={styles.emptyIcon}>💬</span>
          <p>La transcripción de la entrevista aparecerá aquí...</p>
        </div>
      )}

      {entries.map((entry) => (
        <div
          key={entry.id}
          className={`${styles.entry} ${
            entry.speaker === "entrevistador" ? styles.entrevistador : styles.candidato
          }`}
        >
          <div className={styles.header}>
            <span className={styles.speaker}>
              {entry.speaker === "entrevistador" ? "🤖 Rodrigo (IA)" : "🎙️ Tú"}
            </span>
            <span className={styles.time}>{formatTime(entry.timestamp)}</span>
          </div>
          <p className={styles.text}>{entry.text}</p>
        </div>
      ))}

      {/* Texto parcial en tiempo real */}
      {partialText && (
        <div className={`${styles.entry} ${styles.candidato} ${styles.partial}`}>
          <div className={styles.header}>
            <span className={styles.speaker}>🎙️ Tú</span>
            <span className={styles.partialBadge}>escuchando...</span>
          </div>
          <p className={styles.text}>{partialText}</p>
        </div>
      )}

      <div ref={bottomRef} aria-hidden="true" />
    </div>
  );
}
