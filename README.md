# FindMyPet Agent Microservice

Microservicio FastAPI stateless para conversaciones con RAG. Supabase almacena las sesiones, los mensajes y los vectores; Portkey proporciona los embeddings y el modelo de lenguaje.

## Probar el agente paso a paso

Esta guía prueba el servicio directamente contra FastAPI en local. En producción, el frontend debe llamar a la Supabase Edge Function, no a este servicio directamente.

### 1. Requisitos

- Python 3.11 o superior, o Docker Desktop.
- Un proyecto Supabase con `pgvector` habilitado.
- Una API key y un modelo configurado en Portkey.
- PowerShell en Windows (los comandos también se pueden adaptar a Bash).

### 2. Instalar dependencias y configurar el entorno

Desde la raíz del repositorio:

```powershell
python -m pip install -e .
Copy-Item .env.example .env
notepad .env
```

Completa `.env` con los valores de tu proyecto:

```env
BASE_URL=url de portkey
PORTKEY_API_KEY=tu_api_key_de_portkey
PORTKEY_MODEL=@dsvertex/gemini-3.5-flash-lite
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key
EDGE_SHARED_SECRET=un_secreto_largo_para_pruebas
INGEST_API_KEY=otra_clave_larga_para_pruebas
```

Conserva el resto de valores de `.env.example` salvo que necesites ajustarlos. Las variables `SUPABASE_SERVICE_ROLE_KEY`, `EDGE_SHARED_SECRET` e `INGEST_API_KEY` son privadas: no las expongas en el frontend ni las subas al repositorio.

### 3. Preparar la base de datos

En el **SQL Editor** de Supabase, ejecuta el contenido de [`supabase/schema.sql`](supabase/schema.sql). El script crea las tablas, el índice vectorial, la función de búsqueda y la limpieza de sesiones expiradas.

El esquema espera embeddings de 1536 dimensiones, que es la dimensión predeterminada de `@azure-openai/text-embedding-3-small`. Comprueba la dimensión después de ingerir un documento:

```sql
select vector_dims(embedding)
from knowledge_chunks
limit 1;
```

### 4. Levantar el servicio

Elige una de estas opciones.

#### Opción A: Python

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Opción B: Docker

```powershell
docker compose up --build
```

Deja esa terminal ejecutándose. Si usas Docker, el archivo `.env` se carga automáticamente mediante `docker-compose.yml`.

### 5. Comprobar el estado de la API

En otra terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Respuesta esperada:

```json
{"status":"ok"}
```

Si esta llamada falla, revisa primero los logs de la terminal donde levantaste el servicio y confirma que `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY` sean válidos.

### 6. Ingerir un documento de prueba

Crea un documento Markdown con información que el agente pueda consultar:

```powershell
New-Item -ItemType Directory -Force .\knowledge | Out-Null
@'
# Hoteles para mascotas

El hotel Patitas Felices acepta perros y gatos con reserva previa.
El horario de atención es de lunes a sábado.
'@ | Set-Content -Encoding utf8 .\knowledge\hoteles.md
```

Usa en el header el mismo valor de `INGEST_API_KEY` que guardaste en `.env`:

```powershell
$ingestKey = "otra_clave_larga_para_pruebas"

curl.exe -X POST "http://127.0.0.1:8000/ingest" `
  -H "x-ingest-key: $ingestKey" `
  -F "file=@knowledge\DB_Conocimiento.md;type=text/markdown"
```

Respuesta esperada:

```json
{"document_name":"hoteles.md","chunks":1}
```

La ingesta reemplaza los chunks anteriores con el mismo nombre, por lo que puedes repetir este paso durante las pruebas.

### 7. Crear una sesión

Las rutas internas requieren el header `x-edge-secret`. En esta prueba, usa el mismo valor de `EDGE_SHARED_SECRET` de `.env`:

```powershell
$edgeSecret = "un_secreto_largo_para_pruebas"
$headers = @{
  "Content-Type" = "application/json"
  "x-edge-secret" = $edgeSecret
}

$session = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/session/start" `
  -Headers $headers `
  -Body '{"user_id":"local-test-user"}'

$session | ConvertTo-Json
$sessionId = $session.session_id
```

Guarda el valor de `session_id`; se necesita para consultar al agente y cerrar la sesión.

### 8. Enviar una pregunta al agente

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

La respuesta debe incluir el contexto del documento ingerido y tener esta estructura:

```json
{
  "session_id": "uuid",
  "message": "El hotel Patitas Felices acepta perros y gatos...",
  "action": null,
  "payload": {},
  "correlation_id": "uuid"
}
```

También puedes probar una intención de búsqueda, reporte o tutorial, por ejemplo `Busca un perro perdido cerca de Bogotá`, `Quiero reportar una mascota encontrada` o `¿Qué funcionalidades tiene la aplicación?`. Las acciones permitidas son `FIND_PET`, `REPORT_PET` y `RUN_TUTORIAL`. Esta última devuelve la respuesta sobre las funcionalidades y permite que el frontend abra el tutorial guiado.

### 9. Cerrar la sesión

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/session/end?session_id=$sessionId" `
  -Headers @{"x-edge-secret" = $edgeSecret}
```

Si levantaste el servicio con Docker, detenlo al terminar:

```powershell
docker compose down
```

## Cliente de pruebas `prueba.py`

`app\agent\prueba.py` automatiza el flujo completo desde la terminal: comprueba la API, ingiere un documento, crea una sesión, permite conversar con el agente y cierra la sesión al finalizar. El script lee `EDGE_SHARED_SECRET` e `INGEST_API_KEY` desde el archivo `.env` de la raíz.

### Requisitos

Antes de ejecutar el cliente:

1. Configura `.env` con las claves necesarias.
2. Ejecuta el esquema de Supabase.
3. Levanta el microservicio en otra terminal:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

4. Confirma que existe el documento predeterminado:

```powershell
Test-Path .\knowledge\DB_Conocimiento.md
```

La ruta predeterminada es `knowledge\DB_Conocimiento.md`, relativa a la raíz del proyecto.

### Ejecutar desde la raíz del proyecto

Sitúate en la raíz de `agent-microservice` y ejecuta:

```powershell
python .\app\agent\prueba.py
```

El script comprobará `/health`, ingerirá el documento predeterminado, creará una sesión y mostrará:

```text
Escribe preguntas para el agente. Usa 'salir' para terminar.
```

Escribe preguntas y pulsa Enter. Para finalizar:

```text
salir
```

También reconoce `exit` y `quit`.

### Ejecutar desde la carpeta `app\agent`

```powershell
Set-Location .\app\agent
python .\prueba.py
```

### Ver todos los comandos disponibles

```powershell
python .\app\agent\prueba.py --help
```

Si estás dentro de `app\agent`:

```powershell
python .\prueba.py --help
```

### Usar un documento diferente

Desde la raíz del proyecto:

```powershell
python .\app\agent\prueba.py `
  --file .\knowledge\otro_documento.md
```

Desde `app\agent`:

```powershell
python .\prueba.py `
  --file ..\..\knowledge\otro_documento.md
```

El archivo debe ser Markdown o texto válido en UTF-8.

### Omitir la ingesta

Usa esta opción si el documento ya fue cargado en Supabase y solo quieres conversar:

Desde la raíz:

```powershell
python .\app\agent\prueba.py --skip-ingest
```

Desde `app\agent`:

```powershell
python .\prueba.py --skip-ingest
```

### Cambiar la URL del servicio

Para probar otro puerto o un despliegue remoto:

```powershell
python .\app\agent\prueba.py `
  --url http://127.0.0.1:9000
```

También puedes definir `AGENT_URL` en `.env`:

```env
AGENT_URL=http://127.0.0.1:8000
```

El parámetro `--url` tiene prioridad sobre `AGENT_URL`.

### Combinaciones frecuentes

Usar otro documento sin volver a ingerirlo no es necesario; si se usa `--skip-ingest`, el parámetro `--file` se ignora:

```powershell
# Ingerir otro documento y conversar
python .\app\agent\prueba.py --file .\knowledge\reportes.md

# Usar el conocimiento existente en otro puerto
python .\app\agent\prueba.py --skip-ingest --url http://127.0.0.1:9000
```

Si aparece `Falta EDGE_SHARED_SECRET` o `Falta INGEST_API_KEY`, revisa `.env` y reinicia el servicio después de modificarlo. Si aparece un error de conexión, confirma que Uvicorn esté ejecutándose y que la URL indicada sea correcta.

## Arquitectura y flujo

```text
Vue -> Supabase Edge Function (JWT + validación) -> FastAPI
                                                   -> sesión Supabase
                                                   -> embedding Portkey -> pgvector
                                                   -> DeepAgent/LLMProvider -> Portkey -> Gemini
                                                   -> {message, action, payload}
```

`api` contiene HTTP; `agent` la orquestación y el action planner; `rag` los prompts y la recuperación; `ingest` la carga y división de Markdown; `providers` la abstracción LLM; `repositories` el acceso a Supabase; `services` los casos de uso; `models` los contratos; y `core` la configuración.

## RAG y memoria

La configuración base usa `@azure-openai/text-embedding-3-small` con `encoding_format="float"`, vectores de 1536 dimensiones, chunks de 350 caracteres con 40 de solapamiento, `top-k=5` y umbral coseno `0.62`. El splitter recursivo prioriza párrafos, saltos de línea, oraciones y espacios para conservar la estructura Markdown y evitar cortes innecesarios. Si una consulta del dominio no encuentra chunks con ese umbral, se reintenta con un umbral 0.15 menor. Los saludos y mensajes fuera del dominio se responden con guardrails regex sin llamar al proveedor de embeddings ni al modelo. El historial recupera hasta 20 mensajes por sesión y cada request comprueba `expires_at`. La limpieza de sesiones expiradas se ejecuta mediante `pg_cron`.

El prompt trata los documentos como datos no confiables y la respuesta se valida con Pydantic contra una allowlist. Las acciones son intenciones para Vue, nunca herramientas de backend.

## Contratos HTTP

| Método | Ruta | Autenticación |
|---|---|---|
| `GET` | `/health` | Ninguna |
| `POST` | `/session/start` | `x-edge-secret` |
| `POST` | `/session/end` | `x-edge-secret` |
| `POST` | `/chat` | `x-edge-secret` |
| `POST` | `/ingest` | `x-ingest-key` |

La Edge Function autentica el JWT de Supabase antes de reenviar las solicitudes y oculta los headers internos. En producción, configura `AGENT_SERVICE_URL` en sus secrets y aplica `supabase/schema.sql` antes de desplegar en Render con `render.yaml`.

## Operación

Los logs se emiten como JSON y cada request puede propagar `x-correlation-id`. El rate limit debe mantenerse distribuido mediante Postgres o la Edge Function al escalar. El cuello de botella típico es la latencia y el coste de embeddings y Portkey, seguido por las consultas vectoriales.
