import UploadForm from "@/components/UploadForm";
import styles from "./page.module.css";

export default function HomePage() {
  return (
    <main className={styles.main}>
      {/* Fondo decorativo */}
      <div className={styles.bgDecor} aria-hidden="true">
        <div className={styles.bgOrb1} />
        <div className={styles.bgOrb2} />
        <div className={styles.bgGrid} />
      </div>

      {/* Hero Section */}
      <section className={styles.hero}>
        <div className={styles.heroBadge}>
          <span className={styles.heroBadgeDot} />
          Entrevistador Técnico por IA · En Español
        </div>

        <h1 className={styles.heroTitle}>
          Tu próxima entrevista técnica,{" "}
          <span className="text-gradient">practicada con IA</span>
        </h1>

        <p className={styles.heroSubtitle}>
          Sube tu CV y la descripción del puesto. Nuestro agente de IA conducirá
          una entrevista técnica realista por voz y te entregará un reporte de
          evaluación estructurado al finalizar.
        </p>

        {/* Feature chips */}
        <div className={styles.features}>
          {[
            { icon: "🎙️", label: "Voz en tiempo real" },
            { icon: "🤖", label: "Agente con contexto" },
            { icon: "🔍", label: "Búsqueda semántica en tu CV" },
            { icon: "📊", label: "Reporte estructurado" },
          ].map(({ icon, label }) => (
            <div key={label} className={styles.featureChip}>
              <span>{icon}</span>
              <span>{label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Upload Card */}
      <section className={styles.uploadSection} aria-label="Formulario de carga de documentos">
        <div className={`${styles.uploadCard} glass-card`}>
          <div className={styles.uploadCardHeader}>
            <h2 className={styles.uploadCardTitle}>Comenzar Entrevista</h2>
            <p className={styles.uploadCardDesc}>
              Carga tu CV y la vacante para que el agente de IA se prepare.
              La entrevista tomará entre 10 y 15 minutos.
            </p>
          </div>
          <UploadForm />
        </div>
      </section>

      {/* Tech stack badges */}
      <section className={styles.techStack} aria-label="Tecnologías utilizadas">
        <p className={styles.techLabel}>Impulsado por</p>
        <div className={styles.techBadges}>
          {["OpenAI GPT-4o", "AssemblyAI STT", "Cartesia TTS", "LangGraph", "FAISS"].map((t) => (
            <span key={t} className={`badge badge-blue ${styles.techBadge}`}>{t}</span>
          ))}
        </div>
      </section>
    </main>
  );
}
