"use client";

import styles from "./ReportModal.module.css";

interface PuntajeDetallado {
  puntaje: number;
  justificacion: string;
}

interface ReporteData {
  nombre_candidato: string;
  puesto_evaluado: string;
  puntaje_general: PuntajeDetallado;
  puntaje_tecnico: PuntajeDetallado;
  puntaje_comunicacion: PuntajeDetallado;
  puntaje_ajuste_cultural: PuntajeDetallado;
  fortalezas: string[];
  areas_de_mejora: string[];
  recomendacion: "Contratar" | "Considerar para segunda entrevista" | "No recomendado";
  resumen_ejecutivo: string;
  preguntas_realizadas: string[];
}

interface ReportModalProps {
  report: ReporteData | null;
  onClose: () => void;
}

const RECOMENDACION_CONFIG = {
  "Contratar": { color: "var(--clr-success)", icon: "✅", badge: styles.badgeGreen },
  "Considerar para segunda entrevista": { color: "var(--clr-warning)", icon: "🔄", badge: styles.badgeYellow },
  "No recomendado": { color: "var(--clr-error)", icon: "❌", badge: styles.badgeRed },
};

function ScoreDial({ score, label, justificacion }: { score: number; label: string; justificacion: string }) {
  const pct = (score / 10) * 100;
  const color = score >= 7 ? "var(--clr-success)" : score >= 5 ? "var(--clr-warning)" : "var(--clr-error)";

  return (
    <div className={styles.scoreCard} title={justificacion}>
      <div className={styles.scoreCircle} style={{ "--score-color": color } as React.CSSProperties}>
        <svg viewBox="0 0 42 42" className={styles.scoreSvg}>
          <circle cx="21" cy="21" r="18" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="3" />
          <circle
            cx="21" cy="21" r="18" fill="none"
            stroke={color} strokeWidth="3"
            strokeDasharray={`${pct * 1.131} 113.1`}
            strokeLinecap="round"
            transform="rotate(-90 21 21)"
            style={{ transition: "stroke-dasharray 1s ease" }}
          />
        </svg>
        <span className={styles.scoreNumber}>{score}</span>
      </div>
      <span className={styles.scoreLabel}>{label}</span>
    </div>
  );
}

export default function ReportModal({ report, onClose }: ReportModalProps) {
  if (!report) return null;

  const recConfig = RECOMENDACION_CONFIG[report.recomendacion] ?? RECOMENDACION_CONFIG["No recomendado"];

  const handlePrint = () => window.print();

  return (
    <div className={styles.overlay} role="dialog" aria-modal="true" aria-label="Reporte de evaluación">
      <div className={styles.modal}>
        {/* Header */}
        <div className={styles.header}>
          <div>
            <h2 className={styles.title}>📊 Reporte de Evaluación</h2>
            <p className={styles.subtitle}>
              <strong>{report.nombre_candidato}</strong> — {report.puesto_evaluado}
            </p>
          </div>
          <div className={styles.headerActions}>
            <button id="print-report-btn" className="btn-secondary" onClick={handlePrint} aria-label="Imprimir reporte">
              🖨️ Imprimir
            </button>
            <button id="close-report-btn" className={styles.closeBtn} onClick={onClose} aria-label="Cerrar reporte">
              ✕
            </button>
          </div>
        </div>

        <div className={styles.body}>
          {/* Recomendación */}
          <div className={`${styles.recomendacion} ${recConfig.badge}`}>
            <span className={styles.recIcon}>{recConfig.icon}</span>
            <div>
              <p className={styles.recLabel}>Recomendación final</p>
              <p className={styles.recText}>{report.recomendacion}</p>
            </div>
          </div>

          {/* Puntajes */}
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Puntajes</h3>
            <div className={styles.scoresGrid}>
              <ScoreDial score={report.puntaje_general.puntaje} label="General" justificacion={report.puntaje_general.justificacion} />
              <ScoreDial score={report.puntaje_tecnico.puntaje} label="Técnico" justificacion={report.puntaje_tecnico.justificacion} />
              <ScoreDial score={report.puntaje_comunicacion.puntaje} label="Comunicación" justificacion={report.puntaje_comunicacion.justificacion} />
              <ScoreDial score={report.puntaje_ajuste_cultural.puntaje} label="Ajuste Cultural" justificacion={report.puntaje_ajuste_cultural.justificacion} />
            </div>
          </section>

          {/* Resumen ejecutivo */}
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Resumen Ejecutivo</h3>
            <p className={styles.resumen}>{report.resumen_ejecutivo}</p>
          </section>

          {/* Fortalezas y Mejoras */}
          <div className={styles.twoCol}>
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>✅ Fortalezas</h3>
              <ul className={styles.chipList}>
                {report.fortalezas.map((f, i) => (
                  <li key={i} className={`${styles.chip} ${styles.chipGreen}`}>{f}</li>
                ))}
              </ul>
            </section>
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>📈 Áreas de Mejora</h3>
              <ul className={styles.chipList}>
                {report.areas_de_mejora.map((a, i) => (
                  <li key={i} className={`${styles.chip} ${styles.chipYellow}`}>{a}</li>
                ))}
              </ul>
            </section>
          </div>

          {/* Preguntas realizadas */}
          {report.preguntas_realizadas?.length > 0 && (
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>❓ Preguntas Realizadas</h3>
              <ol className={styles.questionList}>
                {report.preguntas_realizadas.map((q, i) => (
                  <li key={i} className={styles.question}>{q}</li>
                ))}
              </ol>
            </section>
          )}

          {/* Justificaciones detalladas */}
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>📝 Justificaciones Detalladas</h3>
            <div className={styles.justificaciones}>
              {[
                { label: "General", data: report.puntaje_general },
                { label: "Técnico", data: report.puntaje_tecnico },
                { label: "Comunicación", data: report.puntaje_comunicacion },
                { label: "Ajuste Cultural", data: report.puntaje_ajuste_cultural },
              ].map(({ label, data }) => (
                <div key={label} className={styles.justItem}>
                  <span className={styles.justLabel}>{label}:</span>
                  <span className={styles.justText}>{data.justificacion}</span>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
