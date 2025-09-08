from src.config.settings import openai_client
from src.services.logging_service import logger
from src.services.rag_service import get_rag_manager
from src.services.guardrails_service import guardrails_service
from src.services.memory_service import conversation_memory
from src.services.email_service import send_lead_email
from src.templates.prompts import SYSTEM_PROMPT, FALLBACK_PROMPT
import re
from typing import Dict, Optional

class ChatbotService:
    def __init__(self):
        self.model = "gpt-3.5-turbo"
        self.max_tokens = 150
        self.temperature = 0.3
    
    def procesar_mensaje(self, mensaje_usuario: str, user_id: str) -> str:
        """Procesa mensaje con memoria, RAG, guardrails y captura de leads"""
        try:
            # 1. Validar input con guardrails
            validacion_input = guardrails_service.validar_input(mensaje_usuario)
            if not validacion_input["es_valido"]:
                # Defensive programming: ensure response is never None
                respuesta_rechazo = validacion_input.get("respuesta_rechazo")
                if respuesta_rechazo is None or respuesta_rechazo.strip() == "":
                    logger.log_api_failure("guardrails_null_response", "Guardrails returned None/empty response")
                    respuesta_rechazo = "Perdón, no puedo ayudarte con eso. ¿Hay algo sobre seguridad contra incendios en lo que pueda asistirte? 🔥"
                return respuesta_rechazo
            
            # 2. Verificar si es primera interacción → Respuesta fija determinista
            is_first = conversation_memory.is_first_interaction(user_id)
            if is_first:
                conversation_memory.mark_interaction_complete(user_id)
                logger.info("first_interaction_welcome_sent", user_id=user_id)
                return "Hola, soy Eva, la asistente virtual de Argenfuego 🔥 ¿En qué te puedo ayudar?"
            
            # 3. Obtener conversación existente (solo para interacciones posteriores)
            conversation_state = conversation_memory.get_conversation_state(user_id)
            lead_data = conversation_state.get("lead_data", {})
            
            # 4. Buscar contexto relevante en RAG
            contexto = get_rag_manager().search_relevant_context(mensaje_usuario)
            
            # 5. Construir prompt con contexto (sin lógica de presentación)
            if contexto:
                system_prompt = SYSTEM_PROMPT.render(contexto_relevante=contexto)
                logger.debug("rag_context_used", context_length=len(contexto))
            else:
                system_prompt = FALLBACK_PROMPT
                logger.debug("rag_context_empty", fallback="generic_prompt")
            
            # 6. Generar respuesta con OpenAI
            response = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": mensaje_usuario}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Defensive programming: handle None response from OpenAI
            respuesta_ia = response.choices[0].message.content
            if respuesta_ia is None or respuesta_ia.strip() == "":
                logger.log_api_failure("openai_null_response", "OpenAI returned None/empty content")
                respuesta_ia = "Disculpa, tuve un problema procesando tu consulta. ¿Podrías reformular tu pregunta sobre seguridad contra incendios? 🔥"
            
            # 7. Validar output con guardrails
            validacion_output = guardrails_service.validar_output(respuesta_ia)
            if not validacion_output["es_valido"]:
                fallback_response = validacion_output.get("respuesta_fallback")
                if fallback_response is None or fallback_response.strip() == "":
                    respuesta_ia = "Disculpa, hubo un problema. ¿Puedo ayudarte con algo sobre seguridad contra incendios? 🔥"
                else:
                    respuesta_ia = fallback_response
            
            # 8. Actualizar información de lead
            updated_lead_data = self._update_lead_data(
                mensaje_usuario, respuesta_ia, lead_data, user_id
            )
            
            # 9. Guardar estado actualizado
            new_state = {
                "lead_data": updated_lead_data,
                "last_message": mensaje_usuario,
                "last_response": respuesta_ia
            }
            conversation_memory.save_conversation_state(user_id, new_state)
            
            # 10. Verificar si enviar lead
            lead_result = self._try_send_lead(updated_lead_data, user_id)
            if lead_result and lead_result.strip() != "":
                return lead_result
            
            # Final defensive check: ensure we never return None or empty
            if respuesta_ia is None or respuesta_ia.strip() == "":
                logger.log_api_failure("final_null_response_check", "Response is None/empty at final check")
                respuesta_ia = "Hola! ¿En qué puedo ayudarte con temas de seguridad contra incendios? 🔥"
            
            return respuesta_ia
            
        except Exception as e:
            logger.log_api_failure("chatbot_processing", str(e))
            # Ensure exception handler never returns None
            return "Disculpa, tengo problemas técnicos en este momento. ¿Puedo ayudarte con algo sobre seguridad contra incendios? 🤖"
    
    def _update_lead_data(self, user_message: str, bot_response: str, 
                         current_lead: dict, user_id: str) -> dict:
        """Actualiza información de lead de manera incremental"""
        lead_data = current_lead.copy()
        user_lower = user_message.lower()
        
        # Detectar intent comercial
        commercial_keywords = [
            'necesito', 'quiero', 'busco', 'precio', 'cotización', 'extintores', 
            'matafuegos', 'empresa', 'oficina', 'local', 'restaurant', 'fábrica',
            'comprar', 'adquirir', 'contratar', 'servicio'
        ]
        
        if any(keyword in user_lower for keyword in commercial_keywords):
            if not lead_data.get('intent'):
                lead_data['intent'] = user_message[:150]
                logger.debug("commercial_intent_detected", user_id=user_id, intent=lead_data['intent'][:50])
        
        # Extraer email (regex mejorado)
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, user_message)
        if emails and not lead_data.get('email'):
            lead_data['email'] = emails[0]
            logger.debug("email_captured", user_id=user_id, email=emails[0])
        
        # Extraer nombre (patrones mejorados)
        name_patterns = [
            r'soy ([A-Za-zÁ-ÿ\s]{2,30})',
            r'me llamo ([A-Za-zÁ-ÿ\s]{2,30})',
            r'mi nombre es ([A-Za-zÁ-ÿ\s]{2,30})',
            r'mi nombre: ([A-Za-zÁ-ÿ\s]{2,30})'
        ]
        
        if not lead_data.get('nombre'):
            for pattern in name_patterns:
                match = re.search(pattern, user_lower, re.IGNORECASE)
                if match:
                    nombre_candidato = match.group(1).strip().title()
                    # Filtrar nombres muy cortos o que parecen comunes
                    if len(nombre_candidato) > 2 and not any(word in nombre_candidato.lower() 
                                                           for word in ['eva', 'asistente', 'bot', 'hola']):
                        lead_data['nombre'] = nombre_candidato
                        logger.debug("name_captured", user_id=user_id, nombre=nombre_candidato)
                        break
        
        # Extraer información de ubicación/negocio
        business_indicators = ['m2', 'metros', 'oficina', 'local', 'restaurant', 
                             'empresa', 'negocio', 'comercio', 'fábrica']
        
        if any(word in user_lower for word in business_indicators):
            if not lead_data.get('ubicacion'):
                lead_data['ubicacion'] = user_message[:250]
            else:
                # Append additional context
                lead_data['ubicacion'] += f" | {user_message[:100]}"
        
        # Detectar confirmación de datos
        confirmation_patterns = [
            r'sí.*mismo whatsapp', r'sí.*este.*número', r'mismo.*número',
            r'correcto', r'exacto', r'perfecto.*datos'
        ]
        
        if any(re.search(pattern, user_lower) for pattern in confirmation_patterns):
            lead_data['datos_confirmados'] = True
        
        return lead_data
    
    def _try_send_lead(self, lead_data: dict, user_id: str) -> Optional[str]:
        """Intenta enviar lead si tiene información suficiente"""
        try:
            # Verificar si tenemos información mínima
            has_intent = bool(lead_data.get('intent'))
            has_name = bool(lead_data.get('nombre'))
            has_email = bool(lead_data.get('email'))
            
            # Criterios para enviar lead
            sufficient_data = has_intent and (has_name or has_email)
            
            if not sufficient_data:
                logger.debug("lead_insufficient_data", 
                           user_id=user_id, 
                           has_intent=has_intent, 
                           has_name=has_name, 
                           has_email=has_email)
                return None
            
            # Evitar envíos duplicados
            if lead_data.get('email_sent'):
                return None
            
            # Preparar datos para el tool
            telefono = user_id.replace("whatsapp:", "")
            
            # Usar el método invoke (fix deprecation)
            tool_input = {
                "intent": lead_data.get('intent', 'Consulta general'),
                "nombre": lead_data.get('nombre', 'No proporcionado'),
                "telefono": telefono,
                "email": lead_data.get('email', 'No proporcionado'),
                "producto_info": lead_data.get('ubicacion', 'No especificado'),
                "ubicacion": lead_data.get('ubicacion', 'No especificada'),
                "observaciones": f"Lead capturado automáticamente por Eva"
            }
            
            result = send_lead_email.invoke(tool_input)
            
            # Marcar como enviado para evitar duplicados
            lead_data['email_sent'] = True
            updated_state = {"lead_data": lead_data}
            conversation_memory.save_conversation_state(user_id, updated_state)
            
            logger.info("lead_sent_successfully", 
                       user_id=user_id, 
                       nombre=lead_data.get('nombre'),
                       email=lead_data.get('email'))
            
            return result
            
        except Exception as e:
            logger.log_api_failure("send_lead_error", str(e))
            # En caso de error en el envío, no fallar la respuesta principal
            return None
    
    def get_lead_status(self, user_id: str) -> dict:
        """Obtiene el estado actual del lead para debugging"""
        conversation_state = conversation_memory.get_conversation_state(user_id)
        return conversation_state.get("lead_data", {})

chatbot_service = ChatbotService()