import asyncio
import websockets
import json
import httpx

async def run_pipeline_test():
    print("Starting pipeline test...")
    backend_url = "http://localhost:8000"
    ws_url = "ws://localhost:8000/ws/interview"
    
    # 1. Crear una sesión mediante upload mock
    print("\n1. Creating session via mock upload...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Usamos texto simple simulando CV y JD
        files = {
            "cv_file": ("cv.txt", b"Josue Hernandez: Senior Python Developer with experience in FastAPI.", "text/plain")
        }
        data = {
            "jd_text": "Se busca desarrollador Python Senior con experiencia en APIs y bases de datos."
        }
        response = await client.post(f"{backend_url}/api/upload", files=files, data=data)
        if response.status_code != 200:
            print("Failed to upload mock CV. Status:", response.status_code, response.text)
            return
        
        session_id = response.json()["session_id"]
        print(f"Session created successfully: {session_id}")

    # 2. Conectar al WebSocket
    print(f"\n2. Connecting to WebSocket at {ws_url}/{session_id}...")
    try:
        async with websockets.connect(f"{ws_url}/{session_id}") as ws:
            print("WebSocket connected successfully!")
            
            # Recibir saludo inicial
            print("\nWaiting for greeting from agent...")
            while True:
                msg = await ws.recv()
                if isinstance(msg, bytes):
                    # Recibimos trozo de audio del saludo
                    print(f"Received audio chunk: {len(msg)} bytes")
                else:
                    data = json.loads(msg)
                    print(f"Received JSON: {data}")
                    if data.get("type") == "tts_end":
                        print("Greeting playback finished (tts_end received)!")
                        break
            
            # 3. Enviar audio simulado de respuesta (5 segundos de PCM 16kHz 16-bit Mono = 160000 bytes)
            print("\n3. Sending 5 seconds of simulated client voice audio (silence PCM)...")
            chunk_size = 3200  # 100ms de audio
            # Enviamos pcm en silencio
            pcm_chunk = b"\x00" * chunk_size
            
            for i in range(50):
                await ws.send(pcm_chunk)
                await asyncio.sleep(0.1)  # 100ms
                if i % 10 == 0:
                    print(f"Sent {i*100}ms of audio...")
            
            print("Finished sending audio. Waiting for transcript and reply...")
            
            # Esperar transcripción y respuesta del agente
            # AssemblyAI no transcribirá silencio real como texto en español,
            # pero comprobaremos si nos da algún mensaje de transcripción o timeout
            for _ in range(5):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    if isinstance(msg, bytes):
                        print(f"Received agent audio bytes: {len(msg)}")
                    else:
                        print(f"Received agent JSON: {json.loads(msg)}")
                except asyncio.TimeoutError:
                    print("Timeout waiting for message. No response from backend.")
                    break
                    
    except Exception as e:
        print("Exception during WS connection:", e)

if __name__ == "__main__":
    asyncio.run(run_pipeline_test())
