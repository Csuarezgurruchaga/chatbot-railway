import os
from datetime import datetime
from langchain_core.tools import tool
from src.services.logging_service import logger
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

class EmailService:
    def __init__(self):
        self.api_key = os.getenv('SENDGRID_API_KEY')
        self.recipient = os.getenv('LEAD_RECIPIENT', 'csuarezgurruchaga@gmail.com')
        self.sender_email = os.getenv('SENDGRID_FROM_EMAIL', 'eva@argenfuego.com')
        self.sender_name = os.getenv('SENDGRID_FROM_NAME', 'Eva - Argenfuego')
        
        if not self.api_key:
            logger.log_api_failure("sendgrid_init", "SENDGRID_API_KEY not configured")
    
    def send_email(self, subject: str, html_content: str, text_content: str = None) -> bool:
        """Envía email usando SendGrid API"""
        try:
            if not self.api_key:
                logger.log_api_failure("sendgrid_no_api_key", "SendGrid API key not configured")
                return False
            
            sg = sendgrid.SendGridAPIClient(api_key=self.api_key)
            
            # Crear email
            from_email = Email(self.sender_email, self.sender_name)
            to_email = To(self.recipient)
            
            # Si no se proporciona texto plano, extraer del HTML
            if not text_content:
                text_content = self._html_to_text(html_content)
            
            mail = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content,
                plain_text_content=text_content
            )
            
            # Enviar
            response = sg.send(mail)
            
            if response.status_code in [200, 201, 202]:
                logger.info("sendgrid_email_sent", 
                           recipient=self.recipient,
                           subject=subject,
                           status_code=response.status_code)
                return True
            else:
                logger.log_api_failure("sendgrid_bad_status", 
                                     f"Status: {response.status_code}, Body: {response.body}")
                return False
                
        except Exception as e:
            logger.log_api_failure("sendgrid_send_error", str(e))
            return False
    
    def _html_to_text(self, html_content: str) -> str:
        """Convierte HTML básico a texto plano"""
        # Reemplazos básicos para mantener formato legible
        text = html_content.replace('<br>', '\n')
        text = text.replace('<br/>', '\n')
        text = text.replace('<br />', '\n')
        text = text.replace('<p>', '\n')
        text = text.replace('</p>', '\n')
        text = text.replace('<h1>', '\n=== ')
        text = text.replace('</h1>', ' ===\n')
        text = text.replace('<h2>', '\n--- ')
        text = text.replace('</h2>', ' ---\n')
        text = text.replace('<h3>', '\n• ')
        text = text.replace('</h3>', '\n')
        text = text.replace('<li>', '• ')
        text = text.replace('</li>', '\n')
        text = text.replace('<strong>', '**')
        text = text.replace('</strong>', '**')
        text = text.replace('<b>', '**')
        text = text.replace('</b>', '**')
        
        # Remover otros tags HTML
        import re
        text = re.sub(r'<[^>]+>', '', text)
        
        # Limpiar espacios extras
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        
        return text

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
    
    # Template HTML del email
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #ff6b35, #f7931e); color: white; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px; }}
            .content {{ background: #f9f9f9; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .client-info {{ background: white; padding: 15px; border-radius: 6px; margin: 10px 0; }}
            .field {{ margin: 8px 0; }}
            .label {{ font-weight: bold; color: #333; }}
            .value {{ color: #666; }}
            .footer {{ text-align: center; font-size: 12px; color: #888; margin-top: 30px; }}
            .priority {{ background: #ff6b35; color: white; padding: 5px 10px; border-radius: 4px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔥 NUEVO LEAD - Eva WhatsApp Bot</h1>
            <p>Lead capturado automáticamente</p>
        </div>
        
        <div class="content">
            <div class="field">
                <span class="label">📅 Fecha:</span> 
                <span class="value">{timestamp}</span>
                <span class="priority">NUEVO</span>
            </div>
        </div>
        
        <div class="client-info">
            <h3>👤 Información del Cliente</h3>
            <div class="field"><span class="label">Nombre:</span> <span class="value">{nombre}</span></div>
            <div class="field"><span class="label">WhatsApp:</span> <span class="value">{telefono}</span></div>
            <div class="field"><span class="label">Email:</span> <span class="value">{email}</span></div>
        </div>
        
        <div class="client-info">
            <h3>🎯 Consulta del Cliente</h3>
            <div class="field"><span class="label">Intención:</span> <span class="value">{intent}</span></div>
            <div class="field"><span class="label">Producto/Servicio:</span> <span class="value">{producto_info}</span></div>
            <div class="field"><span class="label">Ubicación/Detalles:</span> <span class="value">{ubicacion}</span></div>
        </div>
        
        {f'<div class="client-info"><h3>📝 Observaciones</h3><p>{observaciones}</p></div>' if observaciones else ''}
        
        <div class="client-info">
            <h3>🚀 Próximos Pasos</h3>
            <ul>
                <li>✅ Contactar al cliente por WhatsApp: <strong>{telefono}</strong></li>
                {f'<li>✅ Enviar cotización por email: <strong>{email}</strong></li>' if email != "No proporcionado" else ''}
                <li>📋 Agendar visita técnica si es necesario</li>
                <li>📊 Hacer seguimiento de la propuesta</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>Generado automáticamente por <strong>Eva</strong> - Asistente Virtual Argenfuego</p>
            <p>Para configurar este sistema, contacta al equipo técnico</p>
        </div>
    </body>
    </html>
    """
    
    # Subject dinámico
    cliente_info = nombre if nombre != "No proporcionado" else telefono[-4:]
    subject = f"🔥 NUEVO LEAD WhatsApp - {cliente_info} ({intent[:40]}{'...' if len(intent) > 40 else ''})"
    
    try:
        success = email_service.send_email(subject, html_content)
        if success:
            logger.info("lead_email_sent_successfully", 
                       nombre=nombre, 
                       telefono=telefono, 
                       intent=intent[:50],
                       email_cliente=email)
            return f"✅ Perfecto {nombre}! Envié tu consulta al equipo comercial de Argenfuego. Te contactarán pronto por WhatsApp o email 🔥"
        else:
            logger.log_api_failure("lead_email_failed", f"Failed to send email for {nombre}")
            return "✅ Recibí tu consulta. El equipo te contactará pronto por WhatsApp 📱"
            
    except Exception as e:
        logger.log_api_failure("lead_email_tool_error", str(e))
        return "✅ Consulta recibida. Te contactarán por WhatsApp en breve 📱"