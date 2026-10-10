import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import httpx
from dotenv import load_dotenv

# Carrega as variáveis do .env na raiz
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

# Caminho absoluto para a pasta templates evitar o erro 500 no Render
BASE_DIR = Path(__file__).resolve().parent
templates_path = BASE_DIR / "templates"

if not templates_path.exists():
    # Fallback caso a estrutura esteja com app na raiz do container
    templates_path = Path("app/templates")

templates = Jinja2Templates(directory=str(templates_path))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Renderiza a interface do Chat em Tailwind CSS."""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao carregar template HTML: {str(e)}"
        )

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

    # Autenticação para o Azure Foundry Responses API
    headers = {
        "api-key": HOTEL_AGENT_API_KEY,
        "Authorization": f"Bearer {HOTEL_AGENT_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            
            # Formato de payload compatível com Azure Agent Responses Protocol
            payload = {
                "input": mensagem or "Olá",
                "stream": False
            }

            response = await client.post(
                HOTEL_AGENT_ENDPOINT,
                json=payload,
                headers=headers
            )

            # Caso a API de Agentes exija o formato clássico de messages como fallback
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
            
            # Mapeamento do retorno do Azure Responses API
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

