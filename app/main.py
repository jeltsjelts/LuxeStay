import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import httpx
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# CREDENCIAIS DO AGENTE LUXESTAY
# ==========================================
HOTEL_AGENT_ENDPOINT = os.getenv("HOTEL_AGENT_ENDPOINT", "https://api.exemplo-ai.com/v1/chat")
HOTEL_AGENT_API_KEY = os.getenv("HOTEL_AGENT_API_KEY", "SUA_CHAVE_API_AQUI")
HOTEL_AGENT_ID = os.getenv("HOTEL_AGENT_ID") # Opcional: ID do agente no Azure Foundry

app = FastAPI(title="LuxeStay AI Agent Portal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Caminho absoluto para a pasta templates (evita erro 500 no Render)
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Renderiza a interface do Chat em Tailwind CSS."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/v1/chat")
async def conversar_com_agente(
    mensagem: Optional[str] = Form(None),
    arquivo: Optional[UploadFile] = File(None)
):
    """
    Recebe textos, imagens ou áudios e encaminha para o agente LuxeStay.
    """
    if not mensagem and not arquivo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie uma mensagem de texto ou um arquivo de mídia (imagem/áudio)."
        )

    # Cabeçalho padrão do Azure AI / Foundry
    headers = {
        "api-key": HOTEL_AGENT_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            
            # Encaminhamento Multimodal (Texto + Arquivo se houver)
            if arquivo:
                file_bytes = await arquivo.read()
                files = {"file": (arquivo.filename, file_bytes, arquivo.content_type)}
                data = {"message": mensagem or ""}
                response = await client.post(
                    HOTEL_AGENT_ENDPOINT,
                    data=data,
                    files=files,
                    headers={"api-key": HOTEL_AGENT_API_KEY}
                )
            else:
                # ==========================================
                # PAYLOAD CONFIGURADO PARA AZURE OPENAI / FOUNDRY
                # ==========================================
                payload = {
                    "messages": [
                        {"role": "user", "content": mensagem or "Olá"}
                    ]
                }
                
                # Se você configurou um HOTEL_AGENT_ID no .env, adiciona ao payload
                if HOTEL_AGENT_ID:
                    payload["assistant_id"] = HOTEL_AGENT_ID

                response = await client.post(
                    HOTEL_AGENT_ENDPOINT,
                    json=payload,
                    headers=headers
                )

            if response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erro de autenticação com a API do agente LuxeStay (Chave inválida)."
                )
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Falha na comunicação com o agente (Status {response.status_code}): {response.text}"
                )

            res_json = response.json()
            
            # Extração da resposta considerando estrutura do Azure OpenAI e respostas padrão
            try:
                resposta_texto = res_json["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                resposta_texto = res_json.get("reply") or res_json.get("response") or res_json.get("message")

            return {"resposta": resposta_texto or "Mensagem processada com sucesso."}

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Tempo limite excedido ao comunicar com o agente de IA."
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Erro de conexão: {str(exc)}"
        )