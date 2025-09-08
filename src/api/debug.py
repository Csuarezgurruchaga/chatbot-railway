from fastapi import APIRouter
from fastapi.responses import JSONResponse
from src.services.memory_service import conversation_memory
from src.services.email_service import email_service
from src.services.logging_service import logger
import smtplib
import os
from email.mime.text import MIMEText

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

@router.get("/debug/smtp")
async def debug_smtp():
    """Endpoint para testing conexión SMTP"""
    try:
        smtp_server = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
        smtp_port = int(os.getenv('EMAIL_PORT', '587'))
        email_user = os.getenv('EMAIL_USER')
        email_password = os.getenv('EMAIL_PASS')
        
        # Verificar variables de entorno
        env_status = {
            "EMAIL_HOST": smtp_server,
            "EMAIL_PORT": smtp_port,
            "EMAIL_USER": email_user[:10] + "***" if email_user else None,
            "EMAIL_PASS": "***" if email_password else None,
            "LEAD_RECIPIENT": os.getenv('LEAD_RECIPIENT')
        }
        
        if not email_user or not email_password:
            return JSONResponse({
                "status": "error",
                "message": "EMAIL_USER or EMAIL_PASS not configured",
                "env_variables": env_status
            }, status_code=400)
        
        # Test conexión SMTP
        try:
            logger.info("smtp_connection_test_started", server=smtp_server, port=smtp_port)
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_user, email_password)
                
                # Test email
                test_msg = MIMEText("Test email from Eva chatbot - SMTP working correctly!")
                test_msg['Subject'] = "🔥 SMTP Test - Eva Chatbot"
                test_msg['From'] = email_user
                test_msg['To'] = email_user  # Send to self
                
                server.send_message(test_msg)
                
            logger.info("smtp_test_successful", recipient=email_user)
            
            return JSONResponse({
                "status": "success",
                "message": "SMTP connection and email sending successful",
                "test_email_sent_to": email_user,
                "env_variables": env_status
            })
            
        except smtplib.SMTPAuthenticationError as e:
            logger.log_api_failure("smtp_auth_error", str(e))
            return JSONResponse({
                "status": "error",
                "error_type": "authentication",
                "message": "Gmail authentication failed. Check EMAIL_USER and EMAIL_PASS (App Password)",
                "details": str(e),
                "env_variables": env_status
            }, status_code=401)
            
        except smtplib.SMTPConnectError as e:
            logger.log_api_failure("smtp_connect_error", str(e))
            return JSONResponse({
                "status": "error", 
                "error_type": "connection",
                "message": "Cannot connect to Gmail SMTP server. Railway might be blocking SMTP",
                "details": str(e),
                "suggestion": "Try SendGrid/Mailgun or contact Railway support",
                "env_variables": env_status
            }, status_code=503)
            
        except Exception as e:
            logger.log_api_failure("smtp_general_error", str(e))
            return JSONResponse({
                "status": "error",
                "error_type": "general",
                "message": "SMTP test failed",
                "details": str(e),
                "env_variables": env_status
            }, status_code=500)
            
    except Exception as e:
        logger.log_api_failure("debug_smtp_endpoint", str(e))
        return JSONResponse({
            "status": "error",
            "message": "Debug endpoint error",
            "error": str(e)
        }, status_code=500)

@router.get("/debug/smtp/ports")
async def debug_smtp_ports():
    """Test diferentes puertos SMTP"""
    email_user = os.getenv('EMAIL_USER')
    email_password = os.getenv('EMAIL_PASS')
    
    if not email_user or not email_password:
        return JSONResponse({
            "status": "error",
            "message": "EMAIL_USER or EMAIL_PASS not configured"
        }, status_code=400)
    
    ports_to_test = [
        {"port": 587, "security": "TLS/STARTTLS"},
        {"port": 465, "security": "SSL"},
        {"port": 25, "security": "Plain (usually blocked)"}
    ]
    
    results = []
    
    for port_config in ports_to_test:
        port = port_config["port"]
        try:
            if port == 465:
                # SSL connection
                with smtplib.SMTP_SSL('smtp.gmail.com', port) as server:
                    server.login(email_user, email_password)
                    status = "success"
            else:
                # TLS/Plain connection
                with smtplib.SMTP('smtp.gmail.com', port) as server:
                    if port == 587:
                        server.starttls()
                    server.login(email_user, email_password)
                    status = "success"
                    
            results.append({
                "port": port,
                "security": port_config["security"],
                "status": status,
                "message": "Connection successful"
            })
            
        except Exception as e:
            results.append({
                "port": port,
                "security": port_config["security"], 
                "status": "failed",
                "error": str(e)
            })
    
    return JSONResponse({
        "status": "completed",
        "port_test_results": results,
        "recommendation": "Use the first successful port for EMAIL_PORT"
    })