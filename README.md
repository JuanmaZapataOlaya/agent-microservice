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
