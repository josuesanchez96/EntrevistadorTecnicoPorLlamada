"use client";

import { useEffect, useRef } from "react";
import styles from "./AudioVisualizer.module.css";

interface AudioVisualizerProps {
  analyser: AnalyserNode | null;
  isActive: boolean;
  isSpeaking: boolean; // true cuando el AI está hablando
}

export default function AudioVisualizer({
  analyser,
  isActive,
  isSpeaking,
}: AudioVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    const BAR_COUNT = 48;
    const BAR_GAP = 3;
    const barWidth = (W - BAR_GAP * (BAR_COUNT - 1)) / BAR_COUNT;

    const draw = () => {
      animFrameRef.current = requestAnimationFrame(draw);
      ctx.clearRect(0, 0, W, H);

      if (!isActive) {
        // Línea de silencio
        ctx.beginPath();
        ctx.strokeStyle = "rgba(99, 179, 255, 0.2)";
        ctx.lineWidth = 2;
        ctx.moveTo(0, H / 2);
        ctx.lineTo(W, H / 2);
        ctx.stroke();
        return;
      }

      let dataArray: Uint8Array;
      if (analyser) {
        dataArray = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(dataArray);
      } else {
        // Animación decorativa cuando no hay analyser real
        dataArray = new Uint8Array(BAR_COUNT);
        for (let i = 0; i < BAR_COUNT; i++) {
          dataArray[i] = Math.random() * 80 + 20;
        }
      }

      const step = Math.floor(dataArray.length / BAR_COUNT);

      for (let i = 0; i < BAR_COUNT; i++) {
        const value = dataArray[i * step] / 255;
        const barH = Math.max(4, value * H * 0.85);
        const x = i * (barWidth + BAR_GAP);
        const y = (H - barH) / 2;

        // Gradiente por barra
        const gradient = ctx.createLinearGradient(0, y, 0, y + barH);
        if (isSpeaking) {
          gradient.addColorStop(0, "rgba(6, 182, 212, 0.9)");
          gradient.addColorStop(1, "rgba(59, 130, 246, 0.5)");
        } else {
          gradient.addColorStop(0, "rgba(59, 130, 246, 0.9)");
          gradient.addColorStop(1, "rgba(139, 92, 246, 0.5)");
        }

        ctx.fillStyle = gradient;
        const radius = Math.min(barWidth / 2, 4);
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barH, radius);
        ctx.fill();
      }
    };

    draw();
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [analyser, isActive, isSpeaking]);

  return (
    <canvas
      ref={canvasRef}
      className={styles.canvas}
      width={480}
      height={80}
      aria-label="Visualizador de audio"
      aria-hidden="true"
    />
  );
}
