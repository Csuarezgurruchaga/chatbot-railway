import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from langchain_core.tools import tool
from src.services.logging_service import logger

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('EMAIL_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASS')
        self.recipient = os.getenv('LEAD_RECIPIENT', 'csuarezgurruchaga@gmail.com')
    
    def send_email(self, subject: str, body: str) -> bool:
        """Envía email usando configuración SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = self.recipient
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            logger.info("email_sent_successfully", recipient=self.recipient, subject=subject)
            return True
            
        except Exception as e:
            logger.log_api_failure("email_send", str(e))
            return False

# Instancia global
email_service = EmailService()

@tool
def send_lead_email(
    intent: str,
    nombre: str = "No proporcionado",
    telefono: str = "",
    email: str = "No proporcionado", 
    producto_info: str = "",
    ubicacion: str = "No especificada",
    observaciones: str = ""
) -> str:
    """
    Envía email con información del lead cuando se han capturado datos suficientes.
    
    Args:
        intent: Intención del cliente (ej: "Necesita extintores para restaurant")
        nombre: Nombre del cliente
        telefono: Teléfono WhatsApp del cliente
        email: Email del cliente para contacto
        producto_info: Información del producto solicitado
        ubicacion: Ubicación o características del espacio
        observaciones: Información adicional relevante
    """
    
    # Crear timestamp
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Template del email
    email_body = f"""🔥 NUEVO LEAD - Eva WhatsApp Bot 🔥

📅 FECHA: {timestamp}

👤 DATOS DEL CLIENTE:
• Nombre: {nombre}
• WhatsApp: {telefono}
• Email: {email}

🎯 CONSULTA:
• Intent: {intent}
• Producto: {producto_info}
• Ubicación: {ubicacion}

📝 OBSERVACIONES:
{observaciones if observaciones else "Ninguna"}

🚀 PRÓXIMOS PASOS:
□ Contactar al cliente por WhatsApp o email
□ Enviar cotización personalizada
□ Agendar visita técnica si es necesario
□ Hacer seguimiento de la propuesta

---
Generado automáticamente por Eva - Asistente Virtual Argenfuego
"""
    
    subject = f"🔥 NUEVO LEAD WhatsApp - {nombre} ({intent[:50]}...)"
    
    try:
        success = email_service.send_email(subject, email_body)
        if success:
            logger.info("lead_email_sent", 
                       nombre=nombre, 
                       telefono=telefono, 
                       intent=intent[:50])
            return f"✅ Perfecto {nombre}! Envié tu consulta al equipo comercial de Argenfuego. Te contactarán pronto por WhatsApp o email 🔥"
        else:
            logger.log_api_failure("lead_email_failed", f"Failed to send email for {nombre}")
            return "✅ Recibí tu consulta. El equipo te contactará pronto por WhatsApp 📱"
            
    except Exception as e:
        logger.log_api_failure("lead_email_tool_error", str(e))
        return "✅ Consulta recibida. Te contactarán por WhatsApp en breve 📱"