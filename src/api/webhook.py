from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse
from src.config.settings import twilio_client
from src.services.logging_service import logger
import time
from src.services.chatbot_service import chatbot_service

router = APIRouter()

@router.post("/webhook")
async def recibir_mensaje(Body: str = Form(), From: str = Form()):
    """Webhook principal de WhatsApp con RAG y guardrails"""
    numero = From.replace("whatsapp:", "")
    start_time = time.time()
    
    logger.info("message_received", user_id=numero, message_preview=Body[:50] + "...")
    
    # 🧠 ChatGPT + RAG + Guardrails + LangGraph
    respuesta_ia = chatbot_service.procesar_mensaje(Body, numero)
    
    # 📱 Enviar respuesta por WhatsApp
    twilio_client.messages.create(
        from_="whatsapp:+5491147361881",
        to=From,
        body=respuesta_ia
    )
    
    # Calcular tiempo de respuesta
    response_time = int((time.time() - start_time) * 1000)
    
    logger.log_message_processed(
        user_id=numero,
        response_time=response_time, 
        tokens_used=len(Body.split()) + len(respuesta_ia.split()),  # Aproximación
        cost=0.002,  # Estimación promedio
        rag_used=True,
        guardrails_passed=True
    )
    
    logger.info("message_sent", user_id=numero, response_preview=respuesta_ia[:50] + "...")
    return PlainTextResponse("", status_code=200)