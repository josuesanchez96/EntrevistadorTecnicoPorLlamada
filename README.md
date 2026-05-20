# 🎙️ Entrevistador Técnico por Llamada · IA

Plataforma de entrevistas técnicas simuladas por voz usando Inteligencia Artificial. El sistema recibe el CV de un candidato y una descripción de puesto, y conduce una entrevista técnica realista en español con voz hiperrealista, finalizando con un reporte de evaluación estructurado.

---

## 🏗️ Arquitectura del Sistema

```
Frontend (Next.js 14)
    │ POST /api/upload → Envía CV y JD
    │ WS ws://localhost:8000/ws/interview/{session_id}
    ▼
Backend (FastAPI + Python)
    ├── Motor RAG (FAISS + OpenAI Embeddings)
    │       CV y JD → chunks → embeddings → FAISS
    ├── Agente LangGraph (GPT-4o)
    │       Entrevistador "Rodrigo" con tool calling
    │       herramienta: consultar_perfil_candidato
    ├── AssemblyAI STT (WebSocket Streaming)
    │       Audio del navegador → Transcripción en tiempo real
    └── Cartesia TTS
            Respuesta del agente → Audio MP3 → Navegador
```

### Flujo completo de la entrevista:
1. El candidato sube su **CV** (PDF/DOCX/TXT) y pega la **descripción del puesto**.
2. El backend genera embeddings con OpenAI y construye un índice **FAISS** por sesión.
3. El candidato es redirigido a la **sala de entrevista** y concede acceso al micrófono.
4. Un **WebSocket** bidireccional conecta el navegador con el backend.
5. El audio del micrófono se convierte a **PCM16 @ 16kHz** via `AudioWorklet` y se envía por WS.
6. El backend lo reenvía en streaming a **AssemblyAI** y recibe la transcripción.
7. La transcripción se envía al **Agente LangGraph** (GPT-4o + tool calling).
8. El agente puede usar `consultar_perfil_candidato` para búsqueda semántica en el CV/JD.
9. La respuesta del agente se sintetiza con **Cartesia TTS** y se envía como audio MP3 al navegador.
10. Al finalizar, el **nodo de reporte** genera una evaluación estructurada con Pydantic.

---

## 📋 Requisitos Previos

- **Python** 3.11 o superior
- **Node.js** 18 o superior (con npm)
- Cuentas activas y API Keys de:
  - [OpenAI](https://platform.openai.com/)
  - [AssemblyAI](https://www.assemblyai.com/)
  - [Cartesia](https://cartesia.ai/)

---

## 🚀 Instalación y Ejecución

### 1. Clonar o ubicarse en el proyecto

```powershell
cd "c:\PROYECTOS Y EJERCICIOS\Entrevistador técnico por llamada"
```

### 2. Configurar el Backend

```powershell
cd backend

# Crear entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

#### Configurar variables de entorno del backend

```powershell
# Copiar la plantilla
copy .env.example .env
```

Edita el archivo `.env` con tus credenciales reales:

```env
OPENAI_API_KEY=sk-...
ASSEMBLYAI_API_KEY=tu_clave_assemblyai
ASSEMBLYAI_SPEECH_MODEL=universal-streaming-multilingual
ASSEMBLYAI_STREAMING_LANGUAGE=multi
CARTESIA_API_KEY=tu_clave_cartesia
CARTESIA_VOICE_ID=a0e99841-438c-4a64-b679-ae501e7d6091
FRONTEND_URL=http://localhost:3000
```

> **Nota sobre CARTESIA_VOICE_ID**: El ID `a0e99841-438c-4a64-b679-ae501e7d6091` corresponde a una voz masculina profesional del catálogo de Cartesia. Puedes explorar otras voces en el [Playground de Cartesia](https://play.cartesia.ai/). Para español, busca voces con el tag `es` o `spanish`.

#### Iniciar el servidor backend

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

El backend estará disponible en: `http://localhost:8000`
Documentación automática: `http://localhost:8000/docs`

---

### 3. Configurar el Frontend

```powershell
# Desde la raíz del proyecto
cd frontend

# Instalar dependencias
npm install
```

#### Iniciar el servidor de desarrollo

```powershell
npm run dev
```

El frontend estará disponible en: `http://localhost:3000`

---

## 🎯 Uso de la Aplicación

1. Abre `http://localhost:3000` en tu navegador.
2. **Carga tu CV** arrastrándolo o haciendo clic en la zona de carga (PDF, DOCX o TXT).
3. **Pega la descripción del puesto** en el área de texto.
4. Haz clic en **"🎙️ Iniciar Entrevista"** y espera a que se procesen los documentos (~5-10 seg).
5. En la sala de entrevista, **permite el acceso al micrófono** cuando el navegador lo solicite.
6. El entrevistador "Rodrigo" te saludará y comenzará la entrevista.
7. **Habla cuando veas "🎙️ Habla ahora"** en el visualizador.
8. La entrevista dura entre 10-15 minutos (7-8 preguntas).
9. Haz clic en **"🏁 Finalizar Entrevista"** para terminar y obtener tu reporte.
10. El **reporte de evaluación** aparecerá con puntajes, fortalezas y recomendación.

---

## 🔧 Estructura de Archivos

```
entrevistador-tecnico/
├── backend/
│   ├── main.py           # FastAPI app, endpoints REST y WebSocket
│   ├── rag_engine.py     # Ingesta, chunking, embeddings FAISS
│   ├── tools.py          # @tool consultar_perfil_candidato
│   ├── graph.py          # LangGraph StateGraph completo
│   ├── audio_clients.py  # AssemblyAI STT + Cartesia TTS
│   ├── session_store.py  # Almacén de sesiones en memoria
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx                    # Página de inicio con formulario
│   │   │   ├── page.module.css
│   │   │   ├── globals.css
│   │   │   └── interview/[sessionId]/
│   │   │       └── page.tsx                # Sala de entrevista dinámica
│   │   ├── components/
│   │   │   ├── UploadForm.tsx              # Carga de CV y JD
│   │   │   ├── InterviewRoom.tsx           # Componente principal de la entrevista
│   │   │   ├── AudioVisualizer.tsx         # Visualizador de barras de frecuencia
│   │   │   ├── TranscriptFeed.tsx          # Feed de transcripción en vivo
│   │   │   └── ReportModal.tsx             # Modal con reporte estructurado
│   │   └── lib/
│   │       └── websocket.ts                # Hook de WebSocket + código AudioWorklet
│   ├── package.json
│   ├── next.config.ts
│   └── tsconfig.json
│
└── README.md
```

---

## 🛠️ Decisiones Técnicas Clave

| Componente | Tecnología | Razón |
|---|---|---|
| **STT** | AssemblyAI WS Streaming | Latencia mínima, multilingüe, alta precisión |
| **TTS** | Cartesia Sonic-2 | Voz hiperrealista en español, baja latencia |
| **Agent** | LangGraph StateGraph | Conversación con estado, tool calling, structured output |
| **RAG** | FAISS + OpenAI `text-embedding-3-small` | Búsqueda semántica local sin servidor externo |
| **Audio Capture** | Web AudioWorklet | PCM16 en tiempo real sin bloqueo del hilo principal |
| **Backend** | FastAPI async | Soporte nativo de WebSockets y asincronía completa |

---

## ⚠️ Resolución de Problemas Comunes

### `Error: No se pudo extraer texto del CV`
- Asegúrate de que el PDF no esté protegido con contraseña.
- Prueba convirtiendo el CV a TXT plano.

### `Error accediendo al micrófono`
- Asegúrate de acceder via `http://localhost:3000` (no IP).
- Verifica que el navegador tenga permiso de micrófono para localhost.

### `WebSocket connection failed`
- Verifica que el backend esté corriendo en el puerto 8000.
- Revisa que no haya firewall bloqueando el puerto.

### Respuestas del agente en inglés
- Verifica el `SYSTEM_PROMPT_ENTREVISTADOR` en `graph.py` — está configurado explícitamente para español.
- El modelo GPT-4o a veces puede responder en el idioma del CV si este está en inglés.

---

## 📄 Licencia

MIT — Proyecto educativo para demostración de IA conversacional por voz.
