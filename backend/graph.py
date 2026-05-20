"""
graph.py
Definición completa del grafo LangGraph para el agente entrevistador.
Incluye: Estado, Nodos, Bordes condicionales y Nodo de Reporte Estructurado.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from tools import consultar_perfil_candidato

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Modelos Pydantic para el Reporte Estructurado Final
# ─────────────────────────────────────────────────────────────────────────────


class PuntajeDetallado(BaseModel):
    """Puntuación numérica con justificación."""

    puntaje: int = Field(..., ge=0, le=10, description="Puntaje del 0 al 10.")
    justificacion: str = Field(..., description="Razón de la calificación otorgada.")


class ReporteEvaluacionCandidato(BaseModel):
    """Reporte estructurado de evaluación del candidato al finalizar la entrevista."""

    nombre_candidato: str = Field(
        ..., description="Nombre completo del candidato extraído del CV."
    )
    puesto_evaluado: str = Field(
        ..., description="Título del puesto al que aplica el candidato."
    )
    puntaje_general: PuntajeDetallado = Field(
        ..., description="Evaluación global del desempeño en la entrevista."
    )
    puntaje_tecnico: PuntajeDetallado = Field(
        ..., description="Evaluación de conocimientos técnicos demostrados."
    )
    puntaje_comunicacion: PuntajeDetallado = Field(
        ..., description="Evaluación de claridad y habilidades de comunicación."
    )
    puntaje_ajuste_cultural: PuntajeDetallado = Field(
        ..., description="Evaluación del ajuste a la cultura y valores del puesto."
    )
    fortalezas: list[str] = Field(
        ..., description="Lista de 3 a 5 puntos fuertes del candidato."
    )
    areas_de_mejora: list[str] = Field(
        ..., description="Lista de 2 a 4 áreas donde el candidato puede mejorar."
    )
    recomendacion: Literal[
        "Contratar", "Considerar para segunda entrevista", "No recomendado"
    ] = Field(..., description="Decisión final de contratación.")
    resumen_ejecutivo: str = Field(
        ...,
        description="Resumen narrativo en 3-5 oraciones sobre el desempeño del candidato.",
    )
    preguntas_realizadas: list[str] = Field(
        ..., description="Lista de las preguntas clave que se realizaron durante la entrevista."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Estado del Grafo
# ─────────────────────────────────────────────────────────────────────────────


class InterviewState(dict):
    """
    Estado compartido a través de los nodos del grafo.
    Campos principales:
        messages:           Historial completo de mensajes (LangGraph lo gestiona).
        session_id:         ID de la sesión activa.
        cv_text:            Texto completo del CV del candidato.
        jd_text:            Texto completo de la vacante.
        turno:              Número de turno de la entrevista (incrementa con cada respuesta).
        max_turnos:         Máximo de preguntas a realizar antes de finalizar.
        entrevista_activa:  Flag para saber si el usuario ya terminó la entrevista.
        reporte:            Diccionario con el reporte final generado.
    """


# ─────────────────────────────────────────────────────────────────────────────
# Prompts del sistema
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_ENTREVISTADOR = """\
Eres Rodrigo, un entrevistador técnico experto con 15 años de experiencia en reclutamiento de talento tecnológico. 
Hablas únicamente en español y tienes un tono profesional, cálido y analítico.

Tu objetivo es conducir una entrevista técnica estructurada. Cuentas con acceso al CV del candidato 
y a la descripción de la vacante. Usa la herramienta `consultar_perfil_candidato` cuando necesites 
verificar o profundizar en algún detalle del perfil o de los requisitos del puesto.

Guía de la entrevista:
1. Saluda al candidato por su nombre (extraído del CV) y preséntate brevemente.
2. Realiza preguntas técnicas progresivas relacionadas con la vacante (del 5 al 7 preguntas).
3. Ajusta la profundidad de tus preguntas según las respuestas del candidato.
4. Realiza al menos una pregunta de situación o comportamiento (ej. "Cuéntame de un reto...").
5. Permite que el candidato haga preguntas al final.
6. Cuando sea momento de terminar, di que la entrevista ha concluido y agradece al candidato.

Reglas importantes:
- Haz UNA pregunta a la vez. Espera la respuesta antes de continuar.
- Sé conciso en tus preguntas (máx. 2-3 oraciones).
- No menciones que eres una IA a menos que el candidato lo pregunte directamente.
- Mantén el contexto de respuestas anteriores para hacer preguntas de seguimiento coherentes.
- NUNCA digas que no tienes acceso al CV o a la vacante: el texto completo está en el contexto de abajo.
- En el primer mensaje, saluda por el nombre del candidato (del CV) y NO uses herramientas.

CONTEXTO INICIAL:
CV del candidato:
{cv_text}

Descripción de la vacante:
{jd_text}
"""

MAX_TURNOS_DEFAULT = 8


# ─────────────────────────────────────────────────────────────────────────────
# Nodos del Grafo
# ─────────────────────────────────────────────────────────────────────────────

def _get_llm_with_tools():
    """Instancia el LLM con las herramientas disponibles."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7, streaming=False)
    return llm.bind_tools([consultar_perfil_candidato])


def _get_llm_sin_herramientas():
    return ChatOpenAI(model="gpt-4o", temperature=0.7, streaming=False)


def _build_system_prompt(cv_text: str, jd_text: str) -> str:
    return SYSTEM_PROMPT_ENTREVISTADOR.format(
        cv_text=cv_text[:3000] if cv_text.strip() else "(CV no disponible)",
        jd_text=jd_text[:2000] if jd_text.strip() else "(Vacante no disponible)",
    )


def generar_saludo_inicial(session_id: str, cv_text: str, jd_text: str) -> AIMessage:
    """Saludo inicial sin herramientas (evita error de acceso al perfil)."""
    if not cv_text.strip():
        logger.warning("CV vacío al generar saludo para sesión %s", session_id)

    system_content = _build_system_prompt(cv_text, jd_text)
    instruccion = (
        "\n\nESTE ES TU PRIMER MENSAJE. Saluda al candidato por su nombre (del CV), "
        "preséntate como Rodrigo y haz tu primera pregunta técnica sobre la vacante. "
        "Usa únicamente el contexto anterior; no digas que te falta información."
    )
    response: AIMessage = _get_llm_sin_herramientas().invoke(
        [SystemMessage(content=system_content + instruccion)]
    )
    logger.info(
        "Saludo inicial sesión %s (%d chars).",
        session_id,
        len(response.content or ""),
    )
    return response


def nodo_entrevistador(state: dict) -> dict:
    """
    Nodo principal del agente entrevistador.
    Genera la siguiente pregunta o respuesta del entrevistador.
    """
    cv_text = state.get("cv_text", "")
    jd_text = state.get("jd_text", "")
    messages: list[BaseMessage] = state.get("messages", [])
    turno = state.get("turno", 0)

    system_content = _build_system_prompt(cv_text, jd_text)

    full_messages = [SystemMessage(content=system_content)] + messages

    llm = _get_llm_with_tools()
    response: AIMessage = llm.invoke(full_messages)

    logger.info(
        "Nodo entrevistador (turno %d): respuesta generada (%d chars).",
        turno,
        len(response.content or ""),
    )

    return {
        **state,
        "messages": messages + [response],
        "turno": turno + 1,
    }


def nodo_herramientas(state: dict) -> dict:
    """Nodo que ejecuta las herramientas solicitadas por el agente."""
    tool_node = ToolNode(tools=[consultar_perfil_candidato])
    result = tool_node.invoke(state)

    messages = state.get("messages", [])
    new_messages = result.get("messages", [])

    for msg in new_messages:
        if hasattr(msg, "content") and msg.content:
            preview = str(msg.content)[:80].replace("\n", " ")
            logger.info("Herramienta respondió: %s...", preview)

    return {
        **state,
        "messages": messages + new_messages,
    }


def nodo_generar_reporte(state: dict) -> dict:
    """
    Nodo final: genera el reporte estructurado de evaluación usando Pydantic + LLM.
    """
    messages: list[BaseMessage] = state.get("messages", [])
    cv_text = state.get("cv_text", "")
    jd_text = state.get("jd_text", "")

    # Construir historial de la entrevista como texto
    historial = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            historial.append(f"Candidato: {msg.content}")
        elif isinstance(msg, AIMessage) and msg.content:
            historial.append(f"Entrevistador: {msg.content}")

    historial_str = "\n".join(historial)

    prompt_reporte = f"""
Analiza la siguiente entrevista técnica completa y genera un reporte de evaluación detallado.

=== CV DEL CANDIDATO ===
{cv_text[:2000]}

=== DESCRIPCIÓN DE LA VACANTE ===
{jd_text[:1500]}

=== TRANSCRIPCIÓN DE LA ENTREVISTA ===
{historial_str}

Basándote en toda la información anterior, genera un reporte de evaluación objetivo y profesional.
Sé específico con los ejemplos del candidato mencionados en la entrevista.
"""

    llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
    structured_llm = llm.with_structured_output(ReporteEvaluacionCandidato)

    try:
        reporte: ReporteEvaluacionCandidato = structured_llm.invoke(prompt_reporte)
        reporte_dict = reporte.model_dump()
        logger.info("Reporte estructurado generado exitosamente.")
    except Exception as exc:
        logger.error("Error generando reporte estructurado: %s", exc)
        reporte_dict = {"error": str(exc)}

    return {
        **state,
        "messages": messages,
        "reporte": reporte_dict,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Bordes Condicionales
# ─────────────────────────────────────────────────────────────────────────────


def decidir_siguiente_paso(state: dict) -> str:
    """
    Decide el siguiente nodo después del entrevistador:
    - Si hay tool_calls pendientes → 'herramientas'
    - Si la entrevista fue marcada como terminada → 'generar_reporte'
    - Si se alcanzó el máximo de turnos → 'generar_reporte'
    - En otro caso → continuar en el mismo nodo (entrevistador)
    """
    messages = state.get("messages", [])
    turno = state.get("turno", 0)
    max_turnos = state.get("max_turnos", MAX_TURNOS_DEFAULT)
    entrevista_activa = state.get("entrevista_activa", True)

    # Verificar si el último mensaje tiene tool_calls
    if messages:
        ultimo = messages[-1]
        if isinstance(ultimo, AIMessage) and getattr(ultimo, "tool_calls", None):
            return "herramientas"

    if not entrevista_activa or turno >= max_turnos:
        return "generar_reporte"

    return END


# ─────────────────────────────────────────────────────────────────────────────
# Construcción del Grafo
# ─────────────────────────────────────────────────────────────────────────────


def build_interview_graph() -> Any:
    """Construye y compila el grafo de entrevista."""
    graph = StateGraph(dict)

    # Nodos
    graph.add_node("entrevistador", nodo_entrevistador)
    graph.add_node("herramientas", nodo_herramientas)
    graph.add_node("generar_reporte", nodo_generar_reporte)

    # Bordes
    graph.set_entry_point("entrevistador")

    graph.add_conditional_edges(
        "entrevistador",
        decidir_siguiente_paso,
        {
            "herramientas": "herramientas",
            "generar_reporte": "generar_reporte",
            END: END,
        },
    )

    # Después de ejecutar herramientas, volver al entrevistador
    graph.add_edge("herramientas", "entrevistador")

    # El reporte final termina el grafo
    graph.add_edge("generar_reporte", END)

    return graph.compile()


# Instancia del grafo compilado (se reutiliza por todas las sesiones)
interview_graph = build_interview_graph()


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────


def iniciar_entrevista(session_id: str, cv_text: str, jd_text: str) -> dict:
    """Genera el saludo inicial sin ejecutar el grafo con herramientas."""
    saludo = generar_saludo_inicial(session_id, cv_text, jd_text)
    return {
        "messages": [saludo],
        "session_id": session_id,
        "cv_text": cv_text,
        "jd_text": jd_text,
        "turno": 1,
        "max_turnos": MAX_TURNOS_DEFAULT,
        "entrevista_activa": True,
        "reporte": None,
    }


def continuar_entrevista(graph_state: dict, respuesta_candidato: str) -> dict:
    """
    Continúa la entrevista con la respuesta del candidato.
    Actualiza el historial de mensajes y ejecuta el siguiente nodo del grafo.
    """
    messages = graph_state.get("messages", [])
    messages = messages + [HumanMessage(content=respuesta_candidato)]

    updated_state = {**graph_state, "messages": messages}
    resultado = interview_graph.invoke(updated_state)
    return resultado


def finalizar_entrevista(graph_state: dict) -> dict:
    """
    Marca la entrevista como finalizada y genera el reporte estructurado.
    """
    updated_state = {**graph_state, "entrevista_activa": False}
    resultado = interview_graph.invoke(updated_state)
    return resultado
