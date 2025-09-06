from src.config.settings import openai_client

class GuardrailsService:
    def __init__(self):
        self.respuestas_rechazo = {
            "tema_fuera_alcance": (
                "🔥 Soy Eva, la asistente de Argenfuego, y me especializo en temas de seguridad "
                "contra incendios, matafuegos, instalaciones y habilitaciones. "
                "¿En qué puedo ayudarte relacionado con estos temas? 😊"
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
            prompt = f"""Responde SOLO 'SÍ' o 'NO':
¿Este mensaje está relacionado con seguridad contra incendios, matafuegos, extintores, instalaciones de seguridad, habilitaciones, emergencias, o consultas generales de atención al cliente?

Mensaje: "{mensaje}"""
            
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5,
                temperature=0
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
        """Valida el input del usuario con OpenAI Moderation + LLM para tema"""
        # Nivel 1: Contenido inapropiado
        validacion_contenido = self.validar_contenido_inapropiado(mensaje)
        if not validacion_contenido["es_valido"]:
            return validacion_contenido
        
        # Nivel 2: Validación de tema
        validacion_tema = self.validar_tema_con_llm(mensaje)
        if not validacion_tema["es_valido"]:
            return validacion_tema
        
        print("✅ Mensaje aprobado por guardrails híbridos")
        return {"es_valido": True}
    
    def validar_output(self, respuesta: str) -> dict:
        """Valida la respuesta del chatbot con OpenAI Moderation"""
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

guardrails_service = GuardrailsService()