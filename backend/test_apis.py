import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Asegurar que el path incluya el directorio actual
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audio_clients import AssemblyAIStreamingClient, synthesize_audio
import logging

logging.basicConfig(level=logging.INFO)

async def test_cartesia():
    print("Testing Cartesia/OpenAI TTS...")
    try:
        audio_bytes = await synthesize_audio("Hola, probando conexión.")
        print(f"Cartesia Success: Generated {len(audio_bytes)} bytes of audio.")
        return True
    except Exception as e:
        print(f"Cartesia Error: {e}")
        return False

async def test_assemblyai():
    print("Testing AssemblyAI Streaming WS connection...")
    try:
        async with AssemblyAIStreamingClient() as client:
            print("AssemblyAI Success: Connection established successfully!")
            # Enviar un fragmento de audio vacío de prueba (1 segundo de silencio)
            # 16000 muestras por segundo * 2 bytes por muestra (pcm_s16le) = 32000 bytes
            silence = b'\x00' * 32000
            await client.send_audio(silence)
            print("AssemblyAI Success: Sample audio packet sent.")
            await client.terminate()
            print("AssemblyAI Success: Terminate packet sent.")
        return True
    except Exception as e:
        print(f"AssemblyAI Error: {e}")
        return False

async def main():
    cartesia_ok = await test_cartesia()
    print("-" * 50)
    aai_ok = await test_assemblyai()
    
    print("=" * 50)
    if cartesia_ok and aai_ok:
        print("ALL APIS ARE WORKING CORRECTLY!")
    else:
        print("SOME APIS FAILED. PLEASE CHECK THE ERRORS ABOVE.")

if __name__ == "__main__":
    asyncio.run(main())
