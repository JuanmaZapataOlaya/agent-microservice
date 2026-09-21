"""Terminal client for testing the FindMyPet agent locally.

Run from this directory with:
    python prueba.py
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parents[1]


def load_dotenv() -> None:
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    headers: dict[str, str] | None = None,
) -> object:
    payload = None
    request_headers = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=payload,
        headers=request_headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=60) as response:
            content = response.read()
            return json.loads(content) if content else None
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"No se pudo conectar con el agente: {exc.reason}") from exc


def ingest_file(base_url: str, file_path: Path, ingest_key: str) -> object:
    boundary = f"----FindMyPetBoundary{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(file_path.name)[0] or "text/markdown"
    file_content = file_path.read_bytes()
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="file"; '
                f'filename="{file_path.name}"\r\n'
            ).encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            file_content,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    request = Request(
        f"{base_url.rstrip('/')}/ingest",
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "x-ingest-key": ingest_key,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            return json.loads(response.read())
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"No se pudo conectar con el agente: {exc.reason}") from exc


def print_result(label: str, result: object) -> None:
    print(f"\n{label}:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Prueba interactiva del agente FindMyPet")
    parser.add_argument("--url", default=os.getenv("AGENT_URL", "http://127.0.0.1:8000"))
    parser.add_argument(
        "--file",
        type=Path,
        default=PROJECT_ROOT / "knowledge" / "DB_Conocimiento.md",
        help="Documento Markdown que se enviará a /ingest",
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="No ingerir documento; usa el conocimiento ya cargado",
    )
    args = parser.parse_args()

    edge_secret = os.getenv("EDGE_SHARED_SECRET", "")
    ingest_key = os.getenv("INGEST_API_KEY", "")
    if not edge_secret:
        print("Falta EDGE_SHARED_SECRET en .env", file=sys.stderr)
        return 1
    if not args.skip_ingest and not ingest_key:
        print("Falta INGEST_API_KEY en .env", file=sys.stderr)
        return 1

    try:
        print_result("Health", request_json(args.url, "/health"))

        if not args.skip_ingest:
            if not args.file.is_file():
                print(f"No existe el archivo: {args.file}", file=sys.stderr)
                return 1
            print_result("Ingesta", ingest_file(args.url, args.file, ingest_key))

        headers = {"x-edge-secret": edge_secret}
        session = request_json(
            args.url,
            "/session/start",
            method="POST",
            body={"user_id": "terminal-test-user"},
            headers=headers,
        )
        print_result("Sesión", session)
        session_id = session["session_id"]  # type: ignore[index]

        print("\nEscribe preguntas para el agente. Usa 'salir' para terminar.")
        while True:
            question = input("\nTú: ").strip()
            if question.lower() in {"salir", "exit", "quit"}:
                break
            if not question:
                continue
            answer = request_json(
                args.url,
                "/chat",
                method="POST",
                body={"session_id": session_id, "message": question},
                headers=headers,
            )
            print_result("Agente", answer)

        request_json(
            args.url,
            f"/session/end?session_id={session_id}",
            method="POST",
            headers=headers,
        )
        print("\nSesión cerrada.")
        return 0
    except (RuntimeError, KeyError, OSError, KeyboardInterrupt) as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
