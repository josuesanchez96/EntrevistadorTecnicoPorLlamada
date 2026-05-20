import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Asegurar que el path incluya el directorio actual
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from graph import iniciar_entrevista, continuar_entrevista
from rag_engine import build_vector_store
from session_store import store as session_store

async def test_full_turn():
    print("Testing full interview turn (Initial -> Human Response -> Agent Answer)...")
    cv_text = "Josue Hernandez: Senior Python Developer with experience in FastAPI and LangChain."
    jd_text = "Se busca desarrollador Python Senior con experiencia en bases de datos y APIs."
    session_id = "test-session-999"
    
    # 1. Crear sesión y RAG
    print("\n1. Building vector store...")
    vector_store, cv_clean, jd_clean = build_vector_store(cv_text.encode('utf-8'), "cv.txt", jd_text)
    session = session_store.create(session_id, cv_clean, jd_clean)
    session_store.update(session_id, vector_store=vector_store)
    
    # 2. Iniciar entrevista (Saludo)
    print("\n2. Starting interview (agent's greeting)...")
    try:
        state1 = iniciar_entrevista(session_id, cv_clean, jd_clean)
        session_store.update(session_id, graph_state=state1)
        
        # Mostrar el saludo
        from langchain_core.messages import AIMessage
        saludo = next((m.content for m in reversed(state1.get("messages", [])) if isinstance(m, AIMessage) and m.content), None)
        print(f"Agent: '{saludo}'")
        
        # 3. Enviar respuesta del candidato
        respuesta = "Hola Rodrigo, gracias por la bienvenida. Sí, tengo bastante experiencia con Python. He trabajado los últimos 4 años con FastAPI creando APIs de alto rendimiento y usando bases de datos como PostgreSQL. En mi último proyecto lideré el diseño de microservicios asíncronos."
        print(f"\n3. Sending candidate response: '{respuesta}'...")
        
        state2 = continuar_entrevista(state1, respuesta)
        session_store.update(session_id, graph_state=state2)
        
        # Mostrar la respuesta del agente
        agent_answer = next((m.content for m in reversed(state2.get("messages", [])) if isinstance(m, AIMessage) and m.content), None)
        print(f"Agent Response: '{agent_answer}'")
        print("\nSUCCESS! The full turn completed without exceptions.")
        
    except Exception as e:
        import traceback
        print("\nERROR DURING CONVERSATION TURN:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_turn())
