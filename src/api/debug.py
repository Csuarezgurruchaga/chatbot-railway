from fastapi import APIRouter
from fastapi.responses import JSONResponse
from src.services.memory_service import conversation_memory
from src.services.email_service import email_service
from src.services.logging_service import logger
import sendgrid
import os
from datetime import datetime
from sendgrid.helpers.mail import Mail, Email, To, Content

router = APIRouter()

@router.get("/debug/memory")
async def debug_memory():
    """Endpoint para debugging del sistema de memoria"""
    try:
        sessions = conversation_memory.debug_user_sessions()
        return JSONResponse({
            "status": "success",
            "user_sessions": sessions,
            "total_sessions": len(sessions)
        })
    except Exception as e:
        logger.log_api_failure("debug_memory_endpoint", str(e))
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)

@router.get("/debug/sendgrid")
async def debug_sendgrid():
    """Endpoint para testing conexión SendGrid API"""
    try:
        # Verificar variables de entorno SendGrid
        sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        env_status = {
            "SENDGRID_API_KEY": sendgrid_api_key[:10] + "***" if sendgrid_api_key else None,
            "LEAD_RECIPIENT": os.getenv('LEAD_RECIPIENT'),
            "SENDGRID_FROM_EMAIL": os.getenv('SENDGRID_FROM_EMAIL', 'eva@argenfuego.com'),
            "SENDGRID_FROM_NAME": os.getenv('SENDGRID_FROM_NAME', 'Eva - Argenfuego')
        }
        
        if not sendgrid_api_key:
            return JSONResponse({
                "status": "error",
                "message": "SENDGRID_API_KEY not configured",
                "env_variables": env_status
            }, status_code=400)
        
        # Test conexión SendGrid API
        try:
            logger.info("sendgrid_api_test_started", api_key_prefix=sendgrid_api_key[:10])
            
            sg = sendgrid.SendGridAPIClient(api_key=sendgrid_api_key)
            
            # Crear email de prueba
            from_email = Email(email_service.sender_email, email_service.sender_name)
            to_email = To(email_service.recipient)
            subject = "🔥 SendGrid API Test - Eva Chatbot"
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #ff6b35;">🔥 SendGrid Test Exitoso</h2>
                <p>Este email confirma que SendGrid API está funcionando correctamente.</p>
                <p><strong>Timestamp:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                <p><strong>Servicio:</strong> Eva Chatbot - Argenfuego</p>
                <hr>
                <p style="font-size: 12px; color: #666;">Email enviado automáticamente desde Railway usando SendGrid API</p>
            </body>
            </html>
            """
            
            mail = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            response = sg.send(mail)
            
            logger.info("sendgrid_test_successful", 
                       recipient=email_service.recipient,
                       status_code=response.status_code)
            
            return JSONResponse({
                "status": "success",
                "message": "SendGrid API connection and email sending successful",
                "test_email_sent_to": email_service.recipient,
                "status_code": response.status_code,
                "env_variables": env_status
            })
            
        except sendgrid.exceptions.BadRequestsError as e:
            logger.log_api_failure("sendgrid_bad_request", str(e))
            return JSONResponse({
                "status": "error",
                "error_type": "bad_request",
                "message": "SendGrid API request error. Check API key and email addresses",
                "details": str(e),
                "env_variables": env_status
            }, status_code=400)
            
        except sendgrid.exceptions.UnauthorizedError as e:
            logger.log_api_failure("sendgrid_auth_error", str(e))
            return JSONResponse({
                "status": "error", 
                "error_type": "authentication",
                "message": "SendGrid API authentication failed. Check SENDGRID_API_KEY",
                "details": str(e),
                "suggestion": "Verify API key is correct and has send permissions",
                "env_variables": env_status
            }, status_code=401)
            
        except Exception as e:
            logger.log_api_failure("sendgrid_general_error", str(e))
            return JSONResponse({
                "status": "error",
                "error_type": "general",
                "message": "SendGrid API test failed",
                "details": str(e),
                "env_variables": env_status
            }, status_code=500)
            
    except Exception as e:
        logger.log_api_failure("debug_sendgrid_endpoint", str(e))
        return JSONResponse({
            "status": "error",
            "message": "Debug endpoint error",
            "error": str(e)
        }, status_code=500)

@router.get("/debug/sendgrid/template")
async def debug_sendgrid_template():
    """Test SendGrid con template personalizado de lead"""
    sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
    
    if not sendgrid_api_key:
        return JSONResponse({
            "status": "error",
            "message": "SENDGRID_API_KEY not configured"
        }, status_code=400)
    
    try:
        # Simular datos de lead para testing
        test_lead_data = {
            "intent": "Necesita extintores para restaurant",
            "nombre": "Carlos Test",
            "telefono": "+5491112345678",
            "email": "carlos.test@restaurant.com",
            "producto_info": "Restaurant 150m2 con cocina",
            "ubicacion": "CABA, zona Palermo",
            "observaciones": "Email de prueba generado desde debug endpoint"
        }
        
        # Usar el mismo tool que usa el chatbot
        from src.services.email_service import send_lead_email
        result = send_lead_email.invoke(test_lead_data)
        
        return JSONResponse({
            "status": "success",
            "message": "Template email sent successfully",
            "lead_data_used": test_lead_data,
            "tool_response": result,
            "sent_to": email_service.recipient
        })
        
    except Exception as e:
        logger.log_api_failure("debug_sendgrid_template", str(e))
        return JSONResponse({
            "status": "error",
            "message": "Template test failed",
            "error": str(e)
        }, status_code=500)