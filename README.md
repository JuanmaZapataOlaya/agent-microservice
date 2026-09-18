# FindMyPet Agent Microservice

Microservicio FastAPI stateless para RAG conversacional en Render. Supabase es la única persistencia: sesiones, mensajes y pgvector. El frontend sólo llama a la Supabase Edge Function; ningún cliente conoce Render, Portkey o Gemini.

## Componentes y flujo

```text
Vue -> Edge Function (JWT + validación) -> FastAPI
                                      -> sesión Supabase
                                      -> embedding Portkey -> pgvector
                                      -> DeepAgent/LLMProvider -> Portkey -> Gemini
                                      -> {message, action, payload}
```

`api` contiene HTTP, `agent` la orquestación y el action planner, `rag` prompts y recuperación, `ingest` Markdown/chunking, `providers` la abstracción LLM (la implementación es Portkey), `repositories` Supabase, `services` casos de uso, `models` contratos y `core` configuración.

## RAG y memoria

La configuración base usa `text-embedding-004` mediante Portkey, vector de 768 dimensiones, chunks de 800 palabras con 120 de solapamiento, `top-k=5` y umbral coseno `0.72`. Ajustar con evaluación real; los valores no son universales. El historial recupera 20 mensajes por sesión y cada request comprueba `expires_at`. La limpieza se ejecuta cada 15 minutos mediante `pg_cron`; el borrado en cascada elimina mensajes.

El prompt marca documentos como datos no confiables y el resultado se valida con Pydantic contra una allowlist. Las acciones son intenciones para Vue, nunca tools de backend.

## Pruebas locales paso a paso

### 1. Requisitos

- Python 3.11 o superior, o Docker Desktop.
- Un proyecto Supabase con `pgvector` disponible.
- Una API key de Portkey y un modelo configurado en Portkey.
- PowerShell en Windows.

### 2. Configurar variables de entorno

Desde la raíz del proyecto:

```powershell
Copy-Item .env.example .env
notepad .env
```

Completar como mínimo:

```env
BASE_URL=https://api.portkey.ai/v1
PORTKEY_API_KEY=tu_api_key_de_portkey
PORTKEY_MODEL=@dsvertex/gemini-3.5-flash-lite
EMBEDDING_MODEL=text-embedding-004
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key
EDGE_SHARED_SECRET=un_secreto_largo_para_pruebas
INGEST_API_KEY=otra_clave_larga_para_pruebas
```

`SUPABASE_SERVICE_ROLE_KEY` y ambas claves internas son sólo para el backend. No las expongas en Vue, en el navegador ni en un repositorio.

### 3. Preparar Supabase

En Supabase abre **SQL Editor**, pega el contenido de `supabase/schema.sql` y ejecútalo. Esto crea las tablas de sesiones, mensajes y conocimiento, el índice vectorial, la función de búsqueda y la limpieza TTL.

Comprueba que la dimensión del embedding sea compatible con el SQL:

```sql
select vector_dims(embedding)
from knowledge_chunks
limit 1;
```

El proyecto está configurado para embeddings de 768 dimensiones. Si el modelo de embeddings seleccionado devuelve otra dimensión, hay que cambiar `vector(768)` y la función SQL antes de ingerir documentos.

### 4. Ejecutar el agente

#### Opción A: Docker

```powershell
docker compose up --build
```

#### Opción B: Python

```powershell
python -m pip install -e .
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

En otra terminal, comprobar el servicio:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Respuesta esperada:

```json
{"status":"ok"}
```

### 5. Ingerir un documento Markdown

Crea un archivo de prueba:

```powershell
New-Item -ItemType Directory -Force .\knowledge | Out-Null
@'
# Hoteles para mascotas

El hotel Patitas Felices acepta perros y gatos con reserva previa.
El horario de atención es de lunes a sábado.
'@ | Set-Content -Encoding utf8 .\knowledge\hoteles.md
```

Envía el documento directamente al agente local:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/ingest" `
  -H "x-ingest-key: otra_clave_larga_para_pruebas" `
  -F "file=@knowledge\hoteles.md;type=text/markdown"
```

La respuesta debe indicar el nombre del documento y el número de chunks creados:

```json
{"document_name":"hoteles.md","chunks":1}
```

La ingesta elimina primero los chunks anteriores con el mismo nombre, por lo que repetir la prueba es idempotente a nivel de documento.

### 6. Crear una sesión

En pruebas directas contra FastAPI se usa un `user_id` de prueba. La Edge Function sustituye ese valor por el usuario autenticado de Supabase.

```powershell
$headers = @{
  "Content-Type" = "application/json"
  "x-edge-secret" = "un_secreto_largo_para_pruebas"
}
$session = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/session/start" `
  -Headers $headers `
  -Body '{"user_id":"local-test-user"}'
$session
$sessionId = $session.session_id
```

### 7. Enviar una pregunta RAG

```powershell
$body = @{
  session_id = $sessionId
  message = "¿Qué hoteles aceptan mascotas?"
} | ConvertTo-Json

$answer = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/chat" `
  -Headers $headers `
  -Body $body
$answer | ConvertTo-Json -Depth 10
```

La respuesta tiene siempre esta forma:

```json
{
  "session_id": "uuid",
  "message": "El hotel Patitas Felices acepta perros y gatos...",
  "action": null,
  "payload": {},
  "correlation_id": "uuid"
}
```

Para cerrar la sesión:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/session/end?session_id=$sessionId" `
  -Headers @{"x-edge-secret"="un_secreto_largo_para_pruebas"}
```

Estas llamadas directas son únicamente para desarrollo. En producción Vue debe invocar la Edge Function, que valida el JWT y oculta los headers internos.

## Configuración y despliegue

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Aplicar `supabase/schema.sql`. En Render, usar `render.yaml`, configurar secretos (`PORTKEY_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `EDGE_SHARED_SECRET`, `INGEST_API_KEY`) y establecer `AGENT_SERVICE_URL` en los secrets de la Edge Function. `/health` es el health check. Un solo worker evita estado local; escalar horizontalmente es seguro porque no hay memoria en proceso.

## Contratos

`POST /chat`, `/session/start`, `/session/end`, `/ingest` y `GET /health` están detrás de headers internos, salvo health. La Edge Function autentica el JWT de Supabase antes de reenviar. La respuesta de chat siempre es:

```json
{"message":"texto","action":null,"payload":{}}
```

Acciones permitidas: `OPEN_HOTEL_MODULE`, `OPEN_PET_PROFILE`, `CONTACT_SUPPORT`.

## Operación

Los logs deben recolectarse como JSON en Render; cada request propaga `x-correlation-id`. El rate limit debe mantenerse distribuido (Postgres/Edge) al crecer; `slowapi` local no debe ser la fuente de verdad. El cuello de botella típico será latencia/coste de embeddings y Portkey, seguido por consultas vectoriales. Usar HNSW, batch ingestion, caché externo de embeddings y paginación de historial antes de aumentar Render.

El proveedor carga `BASE_URL` y `PORTKEY_API_KEY` desde `.env` mediante `pydantic-settings`:

```python
Portkey(
    base_url=settings.base_url,
    api_key=settings.portkey_api_key,
)
```