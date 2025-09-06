from fastapi import APIRouter, Form
from src.services.chatbot_service import chatbot_service
from src.services.rag_service import get_rag_manager

router = APIRouter()

@router.post("/test")
async def probar_chatbot(mensaje: str = Form()):
    """Probar el chatbot con RAG y guardrails sin WhatsApp"""
    respuesta = chatbot_service.procesar_mensaje(mensaje)
    return {"mensaje": mensaje, "respuesta": respuesta}

@router.get("/test-simple")
async def probar_chatbot_simple(mensaje: str):
    """Probar el chatbot usando query parameter"""
    respuesta = chatbot_service.procesar_mensaje(mensaje)
    return {"mensaje": mensaje, "respuesta": respuesta}

@router.get("/status")
async def estado_rag():
    """Verifica el estado de la base de conocimiento"""
    try:
        stats = get_rag_manager().index.describe_index_stats()
        return {
            "indice_activo": True,
            "vectores_almacenados": stats.total_vector_count,
            "dimensiones": get_rag_manager().dimension,
            "namespace": get_rag_manager().namespace
        }
    except Exception as e:
        return {"error": f"Error verificando estado: {str(e)}"}

@router.get("/")
async def inicio():
    return {
        "mensaje": "🤖 ChatGPT Bot con RAG y Guardrails funcionando!",
        "endpoints": {
            "webhook": "/webhook",
            "probar": "/test",
            "probar_simple": "/test-simple",
            "estado": "/status"
        }
    }