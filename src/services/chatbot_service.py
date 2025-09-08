from src.config.settings import openai_client
from src.services.logging_service import logger
from src.services.rag_service import get_rag_manager
from src.services.guardrails_service import guardrails_service
from src.services.memory_service import conversation_memory
from src.services.email_service import send_lead_email
from src.templates.prompts import SYSTEM_PROMPT, FALLBACK_PROMPT
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import Annotated, TypedDict

class ChatbotState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: str
    lead_data: dict

class ChatbotService:
    def __init__(self):
        self.model = "gpt-3.5-turbo"
        self.max_tokens = 150
        self.temperature = 0.3
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Construye el grafo LangGraph para manejo de conversaciones"""
        graph = StateGraph(ChatbotState)
        
        # Definir nodos
        graph.add_node("process_message", self._process_message_node)
        graph.add_node("send_lead", self._send_lead_node)
        
        # Definir flujo
        graph.add_edge(START, "process_message")
        graph.add_conditional_edges(
            "process_message",
            self._should_send_lead,
            {
                "send_lead": "send_lead",
                "end": END
            }
        )
        graph.add_edge("send_lead", END)
        
        return graph.compile(checkpointer=conversation_memory.memory)
    
    def _process_message_node(self, state: ChatbotState) -> dict:
        """Procesa el mensaje del usuario con RAG y guardrails"""
        try:
            user_message = state["messages"][-1].content
            user_id = state["user_id"]
            
            # 1. Validar input con guardrails
            validacion_input = guardrails_service.validar_input(user_message)
            if not validacion_input["es_valido"]:
                response = validacion_input["respuesta_rechazo"]
                return {
                    "messages": [AIMessage(content=response)]
                }
            
            # 2. Buscar contexto relevante en RAG
            contexto = get_rag_manager().search_relevant_context(user_message)
            
            # 3. Verificar si es primera interacción
            is_first = conversation_memory.is_first_interaction(user_id)
            
            # 4. Construir prompt con contexto
            if contexto:
                system_prompt = SYSTEM_PROMPT.render(
                    contexto_relevante=contexto,
                    es_primera_interaccion=is_first
                )
                logger.debug("rag_context_used", context_length=len(contexto))
            else:
                system_prompt = FALLBACK_PROMPT
                logger.debug("rag_context_empty", fallback="generic_prompt")
            
            # 5. Generar respuesta con OpenAI
            response = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            respuesta_ia = response.choices[0].message.content
            
            # 6. Validar output con guardrails
            validacion_output = guardrails_service.validar_output(respuesta_ia)
            if not validacion_output["es_valido"]:
                respuesta_ia = validacion_output["respuesta_fallback"]
            
            # 7. Marcar que ya no es primera interacción
            if is_first:
                conversation_memory.mark_interaction_complete(user_id)
            
            # 8. Extraer posible información de lead
            lead_data = self._extract_lead_info(user_message, respuesta_ia, state.get("lead_data", {}))
            
            return {
                "messages": [AIMessage(content=respuesta_ia)],
                "lead_data": lead_data
            }
            
        except Exception as e:
            logger.log_api_failure("chatbot_processing", str(e))
            error_response = "Disculpa, tengo problemas técnicos en este momento 🤖"
            return {
                "messages": [AIMessage(content=error_response)]
            }
    
    def _extract_lead_info(self, user_message: str, bot_response: str, current_lead: dict) -> dict:
        """Extrae información de lead de la conversación"""
        lead_data = current_lead.copy()
        
        # Detectar intent comercial
        commercial_keywords = [
            'necesito', 'quiero', 'busco', 'precio', 'cotización', 'extintores', 
            'matafuegos', 'empresa', 'oficina', 'local', 'restaurant', 'fábrica'
        ]
        
        user_lower = user_message.lower()
        if any(keyword in user_lower for keyword in commercial_keywords):
            if not lead_data.get('intent'):
                lead_data['intent'] = user_message[:100]  # Primeros 100 caracteres
        
        # Extraer email (regex simple)
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, user_message)
        if emails:
            lead_data['email'] = emails[0]
        
        # Extraer nombre (después de "soy" o "me llamo")
        name_patterns = [r'soy ([A-Za-z\s]+)', r'me llamo ([A-Za-z\s]+)', r'mi nombre es ([A-Za-z\s]+)']
        for pattern in name_patterns:
            match = re.search(pattern, user_lower)
            if match:
                lead_data['nombre'] = match.group(1).strip().title()
                break
        
        # Extraer información de ubicación/tamaño
        if any(word in user_lower for word in ['m2', 'metros', 'oficina', 'local', 'restaurant']):
            lead_data['ubicacion'] = user_message[:200]
        
        return lead_data
    
    def _should_send_lead(self, state: ChatbotState) -> str:
        """Decide si enviar lead basado en información capturada"""
        lead_data = state.get("lead_data", {})
        
        # Verificar si tenemos información suficiente para enviar lead
        has_intent = bool(lead_data.get('intent'))
        has_contact = bool(lead_data.get('nombre') or lead_data.get('email'))
        
        if has_intent and has_contact:
            logger.debug("lead_ready_to_send", lead_data=lead_data)
            return "send_lead"
        
        return "end"
    
    def _send_lead_node(self, state: ChatbotState) -> dict:
        """Envía el lead por email"""
        lead_data = state.get("lead_data", {})
        user_id = state["user_id"]
        
        # Preparar datos para el tool
        telefono = user_id.replace("whatsapp:", "")
        
        result = send_lead_email(
            intent=lead_data.get('intent', 'Consulta general'),
            nombre=lead_data.get('nombre', 'No proporcionado'),
            telefono=telefono,
            email=lead_data.get('email', 'No proporcionado'),
            producto_info=lead_data.get('ubicacion', 'No especificado'),
            ubicacion=lead_data.get('ubicacion', 'No especificada'),
            observaciones=f"Lead capturado automáticamente por Eva"
        )
        
        return {
            "messages": [AIMessage(content=result)]
        }
    
    def procesar_mensaje(self, mensaje_usuario: str, user_id: str) -> str:
        """Procesa un mensaje del usuario usando LangGraph"""
        try:
            # Configurar estado inicial
            config = {"configurable": {"thread_id": f"user_{user_id}"}}
            
            initial_state = {
                "messages": [HumanMessage(content=mensaje_usuario)],
                "user_id": user_id,
                "lead_data": {}
            }
            
            # Ejecutar el grafo
            result = self.graph.invoke(initial_state, config)
            
            # Obtener la última respuesta
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                return last_message.content
            else:
                return str(last_message)
                
        except Exception as e:
            logger.log_api_failure("langgraph_processing", str(e))
            return "Disculpa, tengo problemas técnicos en este momento 🤖"

chatbot_service = ChatbotService()