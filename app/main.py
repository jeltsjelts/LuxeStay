import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from dotenv import load_dotenv

load_dotenv()

HOTEL_AGENT_ENDPOINT = os.getenv("HOTEL_AGENT_ENDPOINT")
HOTEL_AGENT_API_KEY = os.getenv("HOTEL_AGENT_API_KEY")

app = FastAPI(title="LuxeStay AI Agent Portal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Caminho do ficheiro HTML
BASE_DIR = Path(__file__).resolve().parent
HTML_PATH = BASE_DIR / "templates" / "index.html"

if not HTML_PATH.exists():
    HTML_PATH = Path("app/templates/index.html")

@app.get("/", response_class=HTMLResponse)
async def home():
    """Lê e retorna o HTML diretamente sem usar templates Jinja2."""
    if not HTML_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ficheiro index.html nao encontrado em: {HTML_PATH}"
        )
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@app.post("/api/v1/chat")
async def conversar_com_agente(
    mensagem: Optional[str] = Form(None),
    arquivo: Optional[UploadFile] = File(None)
):
    if not mensagem and not arquivo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie uma mensagem de texto ou ficheiro."
        )

    if not HOTEL_AGENT_ENDPOINT or not HOTEL_AGENT_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="HOTEL_AGENT_ENDPOINT ou HOTEL_AGENT_API_KEY nao estao definidos no .env"
        )

    headers = {
        "api-key": HOTEL_AGENT_API_KEY,
        "Authorization": f"Bearer {HOTEL_AGENT_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            payload = {
                "input": mensagem or "Olá",
                "stream": False
            }

            response = await client.post(
                HOTEL_AGENT_ENDPOINT,
                json=payload,
                headers=headers
            )

            if response.status_code == 400:
                payload_fallback = {
                    "messages": [{"role": "user", "content": mensagem or "Olá"}]
                }
                response = await client.post(
                    HOTEL_AGENT_ENDPOINT,
                    json=payload_fallback,
                    headers=headers
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Erro Azure ({response.status_code}): {response.text}"
                )

            res_json = response.json()
            
            resposta_texto = None
            if "output" in res_json:
                resposta_texto = res_json["output"]
            elif "choices" in res_json:
                resposta_texto = res_json["choices"][0]["message"]["content"]
            elif "response" in res_json:
                resposta_texto = res_json["response"]
            elif "message" in res_json:
                resposta_texto = res_json["message"]

            return {"resposta": resposta_texto or "Resposta recebida do LuxeStay."}

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timeout na ligacao com o Azure Foundry."
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno: {str(exc)}"
        )
