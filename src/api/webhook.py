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
    
    # Final safety check: ensure response is never None or empty
    if respuesta_ia is None or respuesta_ia.strip() == "":
        logger.log_api_failure("webhook_null_response", f"Chatbot returned None/empty for user {numero}")
        respuesta_ia = "Disculpa, tuve un problema técnico. ¿Puedo ayudarte con algo sobre seguridad contra incendios? 🔥"
    
    # 📱 Enviar respuesta por WhatsApp
    twilio_client.messages.create(
        from_="whatsapp:+5491147361881",
        to=From,
        body=respuesta_ia
    )
    
    # Calcular tiempo de respuesta
    response_time = int((time.time() - start_time) * 1000)
    
    # Safe token calculation
    try:
        tokens_used = len(Body.split()) + len(respuesta_ia.split()) if respuesta_ia else len(Body.split())
    except:
        tokens_used = len(Body.split())  # Fallback
        
    logger.log_message_processed(
        user_id=numero,
        response_time=response_time, 
        tokens_used=tokens_used,
        cost=0.002,  # Estimación promedio
        rag_used=True,
        guardrails_passed=True
    )
    
    # Safe preview generation
    response_preview = respuesta_ia[:50] + "..." if respuesta_ia and len(respuesta_ia) > 50 else (respuesta_ia or "")
    logger.info("message_sent", user_id=numero, response_preview=response_preview)
    return PlainTextResponse("", status_code=200)