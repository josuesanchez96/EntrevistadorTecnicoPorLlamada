import httpx
import asyncio

async def test_live_post():
    print("Making real POST request to http://localhost:8000/api/upload ...")
    
    # Archivo PDF falso (pero estructurado de forma básica en bytes)
    mock_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 50 >>\nstream\nBT /F1 12 Tf 70 700 Td (Hola, soy Josue, Ingeniero Python) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000056 00000 n\n0000000111 00000 n\n0000000212 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n313\n%%EOF"
    
    files = {
        "cv_file": ("cv_prueba.pdf", mock_pdf_content, "application/pdf")
    }
    data = {
        "jd_text": "Se busca ingeniero con experiencia en Python y desarrollo de agentes con LangGraph."
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post("http://localhost:8000/api/upload", files=files, data=data)
            print(f"Status Code: {response.status_code}")
            print("Response Headers:", response.headers)
            print("Response Text:", response.text)
    except Exception as e:
        import traceback
        print("Network / Request Error:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_live_post())
