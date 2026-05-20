import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Asegurar que el path incluya el directorio actual
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_engine import build_vector_store

def test_build():
    print("Testing build_vector_store...")
    cv_content = b"Josue CV: Senior Python Developer with 6 years of experience."
    jd_content = "Job Description: We need a Python developer who knows LangGraph, OpenAI, and WebSockets."
    
    try:
        vector_store, cv_clean, jd_clean = build_vector_store(
            cv_content, 
            "josue_cv.txt", 
            jd_content
        )
        print("SUCCESS! FAISS vector store created.")
        print(f"CV text length: {len(cv_clean)}")
        print(f"JD text length: {len(jd_clean)}")
    except Exception as e:
        import traceback
        print("ERROR:")
        traceback.print_exc()

if __name__ == "__main__":
    test_build()
