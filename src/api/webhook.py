from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse
from src.config.settings import twilio_client
from src.services.chatbot_service import chatbot_service

router = APIRouter()

@router.post("/webhook")
async def recibir_mensaje(Body: str = Form(), From: str = Form()):
    """Webhook principal de WhatsApp con RAG y guardrails"""
    numero = From.replace("whatsapp:", "")
    print(f"📨 {numero}: {Body}")
    
    # 🧠 ChatGPT + RAG + Guardrails
    respuesta_ia = chatbot_service.procesar_mensaje(Body)
    
    # 📱 Enviar respuesta por WhatsApp
    twilio_client.messages.create(
        from_="whatsapp:+5491147361881",
        to=From,
        body=respuesta_ia
    )
    
    print(f"🤖 Respondí: {respuesta_ia}")
    return PlainTextResponse("", status_code=200)