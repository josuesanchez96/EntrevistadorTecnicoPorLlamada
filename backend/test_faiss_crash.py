import sys
print("Python version:", sys.version)

try:
    print("Importing FAISS and LangChain Community vectorstores...")
    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings
    from dotenv import load_dotenv
    load_dotenv()

    print("Initializing OpenAIEmbeddings...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    print("Building FAISS index from a single text...")
    # Esto llamará a la biblioteca C++ subyacente de FAISS
    texts = ["Hola mundo, esto es una prueba de FAISS."]
    db = FAISS.from_texts(texts, embedding=embeddings)
    
    print("FAISS index created successfully!")
    print("Vector Store Type:", type(db))
    print("SUCCESS! FAISS did not crash.")
except Exception as e:
    import traceback
    print("Python Exception caught:")
    traceback.print_exc()
