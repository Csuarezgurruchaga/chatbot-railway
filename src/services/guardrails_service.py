from src.config.settings import (
    openai_client, 
    ENABLE_INPUT_MODERATION, 
    ENABLE_TOPIC_VALIDATION, 
    ENABLE_OUTPUT_MODERATION
)
import asyncio

class GuardrailsService:
    def __init__(self):
        self.respuestas_rechazo = {
            "tema_fuera_alcance": (
                "Perdon, no puedo ayudarte con eso, me especializo unicamente "
                "en temas de seguridad contra incendios"
            ),
            "lenguaje_inapropiado": (
                "Por favor, mantengamos una conversación respetuosa. "
                "Estoy aquí para ayudarte con consultas sobre seguridad contra incendios. 🙏"
            ),
            "tema_y_lenguaje": (
                "Por favor, mantengamos una conversación respetuosa sobre temas relacionados "
                "con seguridad contra incendios. ¿En qué puedo ayudarte? 😊"
            )
        }
    
    def validar_contenido_inapropiado(self, texto: str) -> dict:
        """Usa OpenAI Moderation API para detectar contenido inapropiado"""
        try:
            response = openai_client.moderations.create(input=texto)
            result = response.results[0]
            
            if result.flagged:
                print(f"🚫 Contenido inapropiado detectado: {result.categories}")
                return {
                    "es_valido": False,
                    "respuesta_rechazo": self.respuestas_rechazo["lenguaje_inapropiado"],
                    "razon": "contenido_inapropiado",
                    "categorias": [cat for cat, flagged in result.categories if flagged]
                }
            
            print("✅ Contenido apropiado según OpenAI Moderation")
            return {"es_valido": True}
            
        except Exception as e:
            print(f"⚠️ Error en OpenAI Moderation: {e}")
            # Fallback: continuar sin bloquear
            return {"es_valido": True}
    
    def validar_tema_con_llm(self, mensaje: str) -> dict:
        """Valida si el mensaje está relacionado con seguridad contra incendios usando LLM"""
        try:
            prompt = f"""Eres un validador para Argenfuego, empresa especializada en seguridad contra incendios.

SERVICIOS DE ARGENFUEGO:
- Venta de matafuegos/extintores y elementos de protección personal
- Mantenimiento y recarga de extintores
- Control anual e inspecciones de sistemas contra incendios
- Instalación de redes de incendio y sistemas fijos
- Habilitaciones y certificaciones de seguridad
- Asesoramiento y capacitación en prevención de incendios

Responde SOLO 'SÍ' si el mensaje está relacionado con:
- Cualquier consulta sobre nuestros servicios/productos
- Preguntas técnicas sobre seguridad contra incendios
- Consultas de ventas, precios, mantenimiento
- Saludos y conversación básica de atención al cliente
- Solicitudes de información o asesoramiento

Responde 'NO' solo para temas COMPLETAMENTE ajenos (deportes, política, cocina, etc.)

Mensaje del cliente: "{mensaje}"

Respuesta:"""
            
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5,
                temperature=0.2
            )
            
            respuesta = response.choices[0].message.content.lower().strip()
            es_tema_valido = "sí" in respuesta or "si" in respuesta
            
            if not es_tema_valido:
                print(f"🚫 Tema fuera de alcance: {mensaje[:50]}...")
                return {
                    "es_valido": False,
                    "respuesta_rechazo": self.respuestas_rechazo["tema_fuera_alcance"],
                    "razon": "tema_fuera_alcance"
                }
            
            print("✅ Tema válido según LLM")
            return {"es_valido": True}
            
        except Exception as e:
            print(f"⚠️ Error en validación de tema: {e}")
            # Fallback: permitir el mensaje
            return {"es_valido": True}
    
    def validar_input(self, mensaje: str) -> dict:
        """Valida el input del usuario con configuración dinámica de guardrails"""
        print(f"🔧 Guardrails config: INPUT_MOD={ENABLE_INPUT_MODERATION}, TOPIC={ENABLE_TOPIC_VALIDATION}")
        
        # Nivel 1: Contenido inapropiado (condicional)
        if ENABLE_INPUT_MODERATION:
            validacion_contenido = self.validar_contenido_inapropiado(mensaje)
            if not validacion_contenido["es_valido"]:
                return validacion_contenido
        else:
            print("⏭️ Saltando OpenAI Moderation (deshabilitado)")
        
        # Nivel 2: Validación de tema (condicional)
        if ENABLE_TOPIC_VALIDATION:
            validacion_tema = self.validar_tema_con_llm(mensaje)
            if not validacion_tema["es_valido"]:
                return validacion_tema
        else:
            print("⏭️ Saltando validación de tema (deshabilitado)")
        
        print("✅ Mensaje aprobado por guardrails configurables")
        return {"es_valido": True}
    
    def validar_output(self, respuesta: str) -> dict:
        """Valida la respuesta del chatbot con configuración dinámica"""
        if not ENABLE_OUTPUT_MODERATION:
            print("⏭️ Saltando validación de output (deshabilitado)")
            return {"es_valido": True, "respuesta": respuesta}
            
        print("🔍 Validando output del chatbot...")
        validacion = self.validar_contenido_inapropiado(respuesta)
        
        if not validacion["es_valido"]:
            print("🚫 Respuesta del chatbot rechazada por contenido inapropiado")
            return {
                "es_valido": False,
                "respuesta_fallback": (
                    "Disculpa, hubo un problema procesando tu consulta. "
                    "¿Podrías reformular tu pregunta sobre seguridad contra incendios? 🔥"
                )
            }
        
        print("✅ Respuesta del chatbot aprobada")
        return {"es_valido": True, "respuesta": respuesta}

    async def log_conversation_async(self, user_id: str, mensaje: str, respuesta: str, metadata: dict = None):
        """Log conversaciones de manera async sin impactar latencia"""
        try:
            # TODO: Implementar logging real (archivo, base de datos, etc.)
            log_data = {
                "timestamp": asyncio.get_event_loop().time(),
                "user_id": user_id,
                "input": mensaje,
                "output": respuesta,
                "metadata": metadata or {}
            }
            print(f"📈 [ASYNC LOG] {user_id}: {mensaje[:30]}... -> {respuesta[:30]}...")
        except Exception as e:
            print(f"⚠️ Error en logging async: {e}")

guardrails_service = GuardrailsService()