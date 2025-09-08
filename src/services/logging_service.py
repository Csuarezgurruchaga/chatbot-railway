import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from src.config.settings import *

class LoggingService:
    def __init__(self):
        self.log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        self.log_format = os.environ.get("LOG_FORMAT", "JSON").upper()
        self.pii_masking = os.environ.get("LOG_PII_MASKING", "true").lower() == "true"
        
        # Niveles de logging (menor número = mayor prioridad)
        self.levels = {
            "CRITICAL": 50,
            "WARN": 40, 
            "INFO": 30,
            "DEBUG": 10
        }
        self.current_level = self.levels.get(self.log_level, 30)
        
        # Métricas agregadas
        self.metrics = {
            "messages_processed": 0,
            "total_response_time": 0,
            "api_costs": 0.0,
            "guardrail_blocks": {
                "profanity": 0,
                "topic-drift": 0, 
                "rate_limit": 0,
                "system_error": 0
            }
        }
    
    def hash_user_id(self, user_id: str) -> str:
        """Hash irreversible de user ID para compliance PDPA"""
        if not self.pii_masking:
            return user_id
        
        if user_id is None:
            return "hash_anonymous"
            
        return "hash_" + hashlib.sha256(user_id.encode()).hexdigest()[:8]
    
    def should_log(self, level: str) -> bool:
        """Verifica si el nivel debe ser loggeado"""
        return self.levels.get(level, 0) >= self.current_level
    
    def format_log(self, level: str, event: str, data: Dict[str, Any]) -> str:
        """Formatea el log según configuración"""
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "event": event,
            **data
        }
        
        if self.log_format == "JSON":
            return json.dumps(log_entry)
        else:
            # Formato simple para desarrollo
            return f"[{timestamp}] {level}: {event} - {data}"
    
    def log(self, level: str, event: str, **kwargs):
        """Log principal con filtrado por nivel"""
        if not self.should_log(level):
            return
            
        # Maskear PII si está habilitado
        if "user_id" in kwargs and self.pii_masking:
            kwargs["user_id"] = self.hash_user_id(kwargs["user_id"])
            
        log_message = self.format_log(level, event, kwargs)
        print(log_message)
    
    def critical(self, event: str, **kwargs):
        """Log crítico - acción inmediata requerida"""
        self.log("CRITICAL", event, **kwargs)
    
    def warn(self, event: str, **kwargs):  
        """Log warning - monitorear tendencias"""
        self.log("WARN", event, **kwargs)
    
    def info(self, event: str, **kwargs):
        """Log info - business intelligence"""
        self.log("INFO", event, **kwargs)
    
    def debug(self, event: str, **kwargs):
        """Log debug - solo desarrollo"""
        self.log("DEBUG", event, **kwargs)
    
    def log_message_processed(self, user_id: str, response_time: int, tokens_used: int, cost: float, **kwargs):
        """Log específico para mensajes procesados"""
        self.metrics["messages_processed"] += 1
        self.metrics["total_response_time"] += response_time
        self.metrics["api_costs"] += cost
        
        self.info("message_processed", 
                 user_id=user_id,
                 response_time_ms=response_time,
                 tokens_used=tokens_used, 
                 cost_usd=cost,
                 **kwargs)
    
    def log_guardrail_block(self, user_id: str, block_type: str, reason: str):
        """Log bloqueos de guardrails"""
        if block_type in self.metrics["guardrail_blocks"]:
            self.metrics["guardrail_blocks"][block_type] += 1
            
        self.warn("content_blocked",
                 user_id=user_id,
                 block_type=block_type,
                 reason=reason)
    
    def log_lead_generated(self, user_id: str, intent: str, contact_requested: bool = False):
        """Log generación de leads"""
        self.info("lead_generated",
                 user_id=user_id, 
                 intent=intent,
                 contact_requested=contact_requested,
                 business_hours=datetime.now().hour >= 9 and datetime.now().hour <= 18)
    
    def log_api_failure(self, service: str, error: str, user_id: Optional[str] = None):
        """Log fallos críticos de API"""
        self.critical("api_failure",
                     service=service,
                     error=error,
                     user_id=user_id,
                     business_impact="user_blocked")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas agregadas"""
        avg_response_time = (self.metrics["total_response_time"] / self.metrics["messages_processed"] 
                           if self.metrics["messages_processed"] > 0 else 0)
        
        return {
            "total_messages": self.metrics["messages_processed"],
            "avg_response_time_ms": round(avg_response_time, 2),
            "total_api_cost_usd": round(self.metrics["api_costs"], 4),
            "guardrail_blocks": self.metrics["guardrail_blocks"]
        }

# Instancia global
logger = LoggingService()