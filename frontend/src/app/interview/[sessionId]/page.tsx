import { Metadata } from "next";
import InterviewRoom from "@/components/InterviewRoom";

interface Props {
  params: { sessionId: string };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  return {
    title: `Entrevista en curso — Entrevistador Técnico IA`,
    description: "Sala de entrevista técnica simulada por voz con inteligencia artificial.",
  };
}

export default function InterviewPage({ params }: Props) {
  return <InterviewRoom sessionId={params.sessionId} />;
}
