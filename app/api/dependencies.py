from fastapi import Header, HTTPException
from app.core.config import get_settings


async def verify_edge(x_edge_secret: str = Header(default="")) -> None:
    if x_edge_secret != get_settings().edge_shared_secret:
        raise HTTPException(status_code=401, detail="Invalid gateway credentials")


async def verify_ingest(x_ingest_key: str = Header(default="")) -> None:
    if x_ingest_key != get_settings().ingest_api_key:
        raise HTTPException(status_code=401, detail="Invalid ingestion credentials")
