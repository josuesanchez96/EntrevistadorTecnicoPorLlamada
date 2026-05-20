"""
tools.py
Herramientas de LangChain disponibles para el agente entrevistador.
"""

from __future__ import annotations

from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from session_store import store as session_store


@tool
def consultar_perfil_candidato(
    consulta: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """
    Realiza una búsqueda semántica en el CV y la descripción de vacante del candidato.

    Úsala cuando necesites verificar habilidades, experiencia o requisitos del puesto.
    """
    from rag_engine import similarity_search

    session_id = state.get("session_id", "")
    session = session_store.get(session_id) if session_id else None
    vs = session.vector_store if session else None

    if vs is None:
        return "Error: El perfil del candidato no está disponible en esta sesión."

    resultados = similarity_search(vs, consulta, k=5)
    if not resultados:
        return "No se encontraron fragmentos relevantes para la consulta proporcionada."

    return "\n\n".join(
        f"[Fragmento {i}]\n{texto}" for i, texto in enumerate(resultados, start=1)
    )
