from langgraph.checkpoint.memory import MemorySaver
from datetime import datetime, timedelta
import threading
import time
from src.services.logging_service import logger

class ConversationMemoryService:
    def __init__(self, cleanup_hours: int = 2):
        self.memory = MemorySaver()
        self.cleanup_hours = cleanup_hours
        self.user_sessions = {}  # Track first interactions
        self._start_cleanup_timer()
    
    def is_first_interaction(self, user_id: str) -> bool:
        """Determina si es la primera interacción real del usuario"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'first_interaction': True,
                'timestamp': datetime.now()
            }
            logger.debug("first_interaction_detected", user_id=user_id)
            return True
        return False
    
    def mark_interaction_complete(self, user_id: str):
        """Marca que el usuario ya tuvo su primera interacción"""
        if user_id in self.user_sessions:
            self.user_sessions[user_id]['first_interaction'] = False
    
    def get_conversation_state(self, user_id: str) -> dict:
        """Obtiene el estado de conversación del usuario"""
        thread_id = f"user_{user_id}"
        try:
            # Crear thread config para LangGraph
            config = {"configurable": {"thread_id": thread_id}}
            state = self.memory.get(config)
            return state if state else {}
        except Exception as e:
            logger.debug("memory_get_error", user_id=user_id, error=str(e))
            return {}
    
    def save_conversation_state(self, user_id: str, state: dict):
        """Guarda el estado de conversación del usuario"""
        thread_id = f"user_{user_id}"
        try:
            config = {"configurable": {"thread_id": thread_id}}
            checkpoint = {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "state": state
            }
            self.memory.put(config, checkpoint, {"step": 1})
            logger.debug("memory_save_success", user_id=user_id)
        except Exception as e:
            logger.debug("memory_save_error", user_id=user_id, error=str(e))
    
    def _cleanup_expired_sessions(self):
        """Limpia sesiones expiradas de memoria"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.cleanup_hours)
            expired_users = []
            
            for user_id, session_data in list(self.user_sessions.items()):
                if session_data['timestamp'] < cutoff_time:
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del self.user_sessions[user_id]
                # También limpiar de LangGraph memory
                thread_id = f"user_{user_id}"
                config = {"configurable": {"thread_id": thread_id}}
                try:
                    self.memory.delete(config)
                except:
                    pass  # Si no existe, no importa
            
            if expired_users:
                logger.info("memory_cleanup_completed", 
                           expired_sessions=len(expired_users),
                           cleanup_hours=self.cleanup_hours)
        except Exception as e:
            logger.log_api_failure("memory_cleanup", str(e))
    
    def _start_cleanup_timer(self):
        """Inicia el timer de limpieza automática"""
        def cleanup_loop():
            while True:
                time.sleep(30 * 60)  # Cada 30 minutos
                self._cleanup_expired_sessions()
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
        logger.info("memory_cleanup_timer_started", interval_minutes=30)

# Instancia global
conversation_memory = ConversationMemoryService()