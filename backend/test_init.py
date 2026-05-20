import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from graph import iniciar_entrevista
from rag_engine import build_vector_store
from session_store import store as session_store

async def test():
    cv_text = "Soy ingeniero de software con 5 años de experiencia."
    jd_text = "Se busca ingeniero con 3 años de experiencia en Python."
    session_id = "test-123"
    
    print("Building vector store...")
    vector_store, cv_clean, jd_clean = build_vector_store(cv_text.encode('utf-8'), "cv.txt", jd_text)
    
    session = session_store.create(session_id, cv_clean, jd_clean)
    session_store.update(session_id, vector_store=vector_store)
    
    print("Starting interview...")
    try:
        res = iniciar_entrevista(session_id, cv_clean, jd_clean)
        print("Success:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
