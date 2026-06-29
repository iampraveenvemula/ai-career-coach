import os
import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import httpx

router = APIRouter()

# Default Ollama URL; can be overridden via environment variable
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

@router.post("/ollama/chat")
async def ollama_chat(request: Request):
    """Proxy OpenAI‑compatible chat completion requests to Ollama.
    The request body is forwarded to `${OLLAMA_URL}/api/chat` and the response
    is streamed back to the client.
    """
    try:
        # Read the incoming JSON payload
        payload = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Ollama expects a slightly different field name for the model; map if needed
    if "model" not in payload:
        raise HTTPException(status_code=400, detail="Missing 'model' field in payload")

    ollama_endpoint = f"{OLLAMA_URL}/api/chat"
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            response = await client.post(
                ollama_endpoint,
                json=payload,
                headers={"Accept": "application/json"},
                stream=True,
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Error communicating with Ollama: {exc}")

        # If Ollama returns a non‑200 status, forward the error
        if response.status_code != 200:
            content = await response.aread()
            raise HTTPException(status_code=response.status_code, detail=content.decode())

        # Stream the response back to the client
        return StreamingResponse(response.aiter_raw(), media_type="application/json")
