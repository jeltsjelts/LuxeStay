import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Form, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from dotenv import load_dotenv

# Carrega as variáveis do .env
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

# Descobre o caminho correto do arquivo HTML no container/servidor
BASE_DIR = Path(__file__).resolve().parent
html_file_path = BASE_DIR / "templates" / "index.html"

# Fallback de caminho caso a estrutura de pastas mude no Render
if not html_file_path.exists():
    html_file_path = Path("app/templates/index.html")

@app.get("/", response_class=FileResponse)
async def home():
    """Serve a página HTML diretamente, eliminando incompatibilidades do Jinja2."""
    if not html_file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo HTML não encontrado no caminho: {html_file_path}"
        )
    return FileResponse(html_file_path)

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
            detail="Variáveis HOTEL_AGENT_ENDPOINT ou HOTEL_AGENT_API_KEY não foram encontradas no .env."
        )

    headers = {
        "api-key": HOTEL_AGENT_API_KEY,
        "Authorization": f"Bearer {HOTEL_AGENT_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            
            # Payload para a API do Azure Foundry Responses
            payload = {
                "input": mensagem or "Olá",
                "stream": False
            }

            response = await client.post(
                HOTEL_AGENT_ENDPOINT,
                json=payload,
                headers=headers
            )

            # Fallback para o formato 'messages' caso o endpoint exija
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
                    detail=f"Erro no agente Azure ({response.status_code}): {response.text}"
                )

            res_json = response.json()
            
            # Extração flexível da resposta recebida
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
            detail="Tempo limite excedido ao comunicar com o Azure Foundry."
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno: {str(exc)}"
        )
