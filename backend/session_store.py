"""
session_store.py
Almacenamiento en memoria de sesiones de entrevista.
Cada sesión guarda el almacén vectorial FAISS y el estado del grafo LangGraph.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class InterviewSession:
    """Datos de una sesión de entrevista activa."""

    session_id: str
    cv_text: str = ""
    jd_text: str = ""
    # El objeto VectorStore de FAISS para esta sesión
    vector_store: Optional[Any] = None
    # Estado acumulado de la conversación (lista de mensajes del grafo)
    graph_state: Optional[dict] = None
    # Indica si la entrevista ya terminó
    finished: bool = False
    # Reporte estructurado final (dict serializable)
    report: Optional[dict] = None


class SessionStore:
    """
    Almacén de sesiones con bloqueo por hilo para concurrencia básica.
    En producción, reemplazar con Redis u otro backend persistente.
    """

    def __init__(self) -> None:
        self._store: dict[str, InterviewSession] = {}
        self._lock = threading.Lock()

    def create(self, session_id: str, cv_text: str, jd_text: str) -> InterviewSession:
        session = InterviewSession(
            session_id=session_id,
            cv_text=cv_text,
            jd_text=jd_text,
        )
        with self._lock:
            self._store[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[InterviewSession]:
        with self._lock:
            return self._store.get(session_id)

    def update(self, session_id: str, **kwargs: Any) -> None:
        with self._lock:
            session = self._store.get(session_id)
            if session:
                for k, v in kwargs.items():
                    setattr(session, k, v)

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._store.pop(session_id, None)

    def exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._store


# Instancia global compartida por toda la app
store = SessionStore()
