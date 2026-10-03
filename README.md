# LuxeStay

# 🏨 Agent AI LuxeStay - Atendimento ao Cliente

Este é o agente de Inteligência Artificial para atendimento ao cliente da rede de hotéis **LuxeStay**. A solução oferece suporte multimodal e em tempo real para hóspedes e visitantes através da plataforma web.

---

## 🚀 Funcionalidades

- **Atendimento Multimodal:** Processamento e interpretação de **texto**, **áudio** (mensagens de voz) e **imagens** (comprovantes, fotos do quarto, documentos).
- **Suporte 24/7:** Respostas instantâneas sobre reservas, serviços do hotel, horários, check-in/check-out e recomendações locais.
- **Integração Web:** Backend construído para se comunicar de forma assíncrona com o frontend do site do hotel.
- **Segurança de Dados:** Gerenciamento seguro de credenciais via variáveis de ambiente.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.10+
- **Framework Web:** FastAPI
- **Servidor ASGI:** Uvicorn
- **Cliente HTTP Assíncrono:** HTTPX
- **Validação de Dados:** Pydantic
- **Gerenciamento de Ambiente:** python-dotenv

---

## 📦 Estrutura do Projeto

```text
├── .env.example        # Modelo para configuração de variáveis de ambiente
├── .gitignore          # Arquivos e pastas ignorados pelo Git
├── main.py             # Aplicação FastAPI e integração com o Agente
└── requirements.txt    # Dependências do projeto
