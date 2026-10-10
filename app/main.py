import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
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

HTML_PATH = Path(__file__).resolve().parent / "templates" / "index.html"

if not HTML_PATH.exists():
    HTML_PATH = Path("app/templates/index.html")

@app.get("/", response_class=HTMLResponse)
async def home():
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
            detail="Envie uma mensagem de texto ou arquivo."
        )

    if not HOTEL_AGENT_ENDPOINT or not HOTEL_AGENT_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="HOTEL_AGENT_ENDPOINT ou HOTEL_AGENT_API_KEY nao estao definidos no .env"
        )

    # Injeta a api-version correta para a API de Agentes (2025-11-15-preview)
    endpoint_url = HOTEL_AGENT_ENDPOINT
    if "api-version=" not in endpoint_url:
        delimiter = "&" if "?" in endpoint_url else "?"
        endpoint_url = f"{endpoint_url}{delimiter}api-version=2025-11-15-preview"

# Cabeçalho oficial e exclusivo para chaves da API do Azure AI Foundry
    headers = {
        "api-key": HOTEL_AGENT_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            payload = {
                "input": mensagem or "Olá",
                "stream": False
            }

            response = await client.post(
                endpoint_url,
                json=payload,
                headers=headers
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Erro no Azure ({response.status_code}): {response.text}"
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Erro no Azure ({response.status_code}): {response.text}"
                )

            res_json = response.json()
            
            resposta_texto = None
            if "output" in res_json:
                if isinstance(res_json["output"], str):
                    resposta_texto = res_json["output"]
                elif isinstance(res_json["output"], list) and len(res_json["output"]) > 0:
                    resposta_texto = str(res_json["output"][0])
            elif "choices" in res_json and len(res_json["choices"]) > 0:
                resposta_texto = res_json["choices"][0]["message"]["content"]
            elif "response" in res_json:
                resposta_texto = res_json["response"]
            elif "message" in res_json:
                resposta_texto = res_json["message"]

            return {"resposta": resposta_texto or "Agente LuxeStay respondeu com sucesso."}

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Tempo limite excedido na resposta do agente Azure."
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno: {str(exc)}"
        )
