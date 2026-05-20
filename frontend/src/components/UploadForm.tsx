"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import styles from "./UploadForm.module.css";

type UploadState = "idle" | "uploading" | "error";

export default function UploadForm() {
  const router = useRouter();
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [jdText, setJdText] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (file: File | null) => {
    if (!file) return;
    const name = file.name.toLowerCase();
    if (name.endsWith(".doc") && !name.endsWith(".docx")) {
      setErrorMsg(
        "El formato .doc (Word antiguo) no está soportado. Guarda el archivo como .docx en Word."
      );
      return;
    }
    const allowed = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"];
    const allowedExt = [".pdf", ".docx", ".txt"];
    const hasAllowedExt = allowedExt.some((ext) => name.endsWith(ext));
    if (!allowed.includes(file.type) && !hasAllowedExt) {
      setErrorMsg("Formato no soportado. Usa PDF, DOCX o TXT.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setErrorMsg("El archivo no puede superar los 10 MB.");
      return;
    }
    setErrorMsg("");
    setCvFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    handleFileChange(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cvFile) { setErrorMsg("Por favor, sube tu CV."); return; }
    if (!jdText.trim()) { setErrorMsg("Por favor, ingresa la descripción del puesto."); return; }

    setUploadState("uploading");
    setErrorMsg("");

    try {
      const formData = new FormData();
      formData.append("cv_file", cvFile);
      formData.append("jd_text", jdText);

      const res = await fetch("/api/upload", { method: "POST", body: formData });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Error al procesar los documentos.");
      }
      const { session_id } = await res.json();
      router.push(`/interview/${session_id}`);
    } catch (err: unknown) {
      setUploadState("error");
      setErrorMsg(err instanceof Error ? err.message : "Error desconocido. Intenta de nuevo.");
    }
  };

  const isSubmitting = uploadState === "uploading";

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>
      {/* CV Upload */}
      <div className={styles.section}>
        <label className="label">
          <span className={styles.labelIcon}>📄</span> Curriculum Vitae (CV)
        </label>
        <div
          className={`${styles.dropzone} ${isDragging ? styles.dragging : ""} ${cvFile ? styles.hasFile : ""}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
          aria-label="Zona de carga de CV"
        >
          <input
            ref={fileInputRef}
            id="cv-file-input"
            type="file"
            accept=".pdf,.docx,.txt"
            className={styles.hiddenInput}
            onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
          />
          {cvFile ? (
            <div className={styles.fileInfo}>
              <span className={styles.fileIcon}>✅</span>
              <span className={styles.fileName}>{cvFile.name}</span>
              <span className={styles.fileSize}>({(cvFile.size / 1024).toFixed(0)} KB)</span>
            </div>
          ) : (
            <div className={styles.dropzoneContent}>
              <div className={styles.uploadIcon}>⬆️</div>
              <p className={styles.dropzoneText}>Arrastra tu CV aquí o <strong>haz clic para seleccionar</strong></p>
              <p className={styles.dropzoneHint}>PDF, DOCX o TXT · Máx. 10 MB</p>
            </div>
          )}
        </div>
      </div>

      {/* JD Text */}
      <div className={styles.section}>
        <label htmlFor="jd-textarea" className="label">
          <span className={styles.labelIcon}>💼</span> Descripción del Puesto (Job Description)
        </label>
        <textarea
          id="jd-textarea"
          className="input-field"
          placeholder="Pega aquí la descripción completa del puesto al que aplicas: requisitos, responsabilidades, stack tecnológico requerido..."
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          rows={8}
          required
        />
        <span className={styles.charCount}>{jdText.length} caracteres</span>
      </div>

      {/* Error */}
      {errorMsg && (
        <div className={styles.errorBanner} role="alert" aria-live="polite">
          <span>⚠️</span> {errorMsg}
        </div>
      )}

      {/* Submit */}
      <button
        id="start-interview-btn"
        type="submit"
        className="btn-primary"
        disabled={isSubmitting}
        style={{ width: "100%", padding: "16px", fontSize: "1rem" }}
      >
        {isSubmitting ? (
          <>
            <span className="spinner" />
            Procesando documentos...
          </>
        ) : (
          <>
            🎙️ Iniciar Entrevista
          </>
        )}
      </button>

      {isSubmitting && (
        <p className={styles.processingNote}>
          Generando embeddings y preparando el agente de IA. Esto puede tardar unos segundos...
        </p>
      )}
    </form>
  );
}
