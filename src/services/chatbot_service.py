from src.config.settings import openai_client
from src.services.rag_service import get_rag_manager
from src.services.guardrails_service import guardrails_service
from src.templates.prompts import SYSTEM_PROMPT, FALLBACK_PROMPT

class ChatbotService:
    def __init__(self):
        self.model = "gpt-3.5-turbo"
        self.max_tokens = 150
        self.temperature = 0.3
    
    def procesar_mensaje(self, mensaje_usuario: str) -> str:
        """Procesa un mensaje del usuario con RAG y guardrails"""
        try:
            # 1. Validar input con guardrails
            validacion_input = guardrails_service.validar_input(mensaje_usuario)
            if not validacion_input["es_valido"]:
                return validacion_input["respuesta_rechazo"]
            
            # 2. Buscar contexto relevante en RAG
            contexto = get_rag_manager().search_relevant_context(mensaje_usuario)
            
            # 3. Construir prompt con contexto
            if contexto:
                system_prompt = SYSTEM_PROMPT.render(contexto_relevante=contexto)
                print(f"✅ Usando contexto RAG ({len(contexto)} caracteres)")
            else:
                system_prompt = FALLBACK_PROMPT
                print("⚠️ No se encontró contexto relevante, usando prompt genérico")
            
            # 4. Generar respuesta con OpenAI
            response = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": mensaje_usuario}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            respuesta_ia = response.choices[0].message.content
            
            # 5. Validar output con guardrails
            validacion_output = guardrails_service.validar_output(respuesta_ia)
            if not validacion_output["es_valido"]:
                return validacion_output["respuesta_fallback"]
            
            return respuesta_ia
            
        except Exception as e:
            print(f"❌ Error en chatbot: {e}")
            return "Disculpa, tengo problemas técnicos en este momento 🤖"

chatbot_service = ChatbotService()