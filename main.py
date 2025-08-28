# ==================== IMPORTS ====================
from fastapi import FastAPI, Form
from twilio.rest import Client
from openai import OpenAI
import os
from dotenv import load_dotenv

# ==================== CONFIGURACIÓN ====================
app = FastAPI()
load_dotenv()

# Clientes
twilio_client = Client(
    os.environ["TWILIO_ACCOUNT_SID"], 
    os.environ["TWILIO_AUTH_TOKEN"]
)

openai_client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

# ==================== CHATBOT CON IA ====================
def chatbot_respuesta(mensaje_usuario):
    """El chatbot usa OpenAI para responder inteligentemente"""
    try:
        # Crear conversación con ChatGPT
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": """Eres un asistente de WhatsApp amigable y útil. 
                    Respondes en español, de forma concisa (máximo 3 líneas).
                    Eres profesional pero cercano. Usas emojis ocasionalmente."""
                },
                {
                    "role": "user", 
                    "content": mensaje_usuario
                }
            ],
            max_tokens=150,
            temperature=0
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"❌ Error con OpenAI: {e}")
        return "Disculpa, tengo problemas técnicos en este momento 🤖"

# ==================== WEBHOOK PRINCIPAL ====================
@app.post("/webhook")
async def recibir_mensaje(Body: str = Form(), From: str = Form()):
    """Cuando llega mensaje, ChatGPT responde"""
    
    numero = From.replace("whatsapp:", "")
    print(f"📨 {numero}: {Body}")
    
    # 🧠 ChatGPT piensa la respuesta
    respuesta_ia = chatbot_respuesta(Body)
    
    # 📱 Enviar respuesta por WhatsApp
    twilio_client.messages.create(
        from_="whatsapp:+14155238886",
        to=From,
        body=respuesta_ia
    )
    
    print(f"🤖 Respondí: {respuesta_ia}")
    return {"status": "ok"}

# ==================== ENDPOINTS EXTRAS ====================
@app.get("/")
async def inicio():
    return {"mensaje": "🤖 ChatGPT Bot funcionando!", "webhook": "/webhook"}

@app.post("/test")
async def probar_chatbot(mensaje: str):
    """Probar el chatbot sin WhatsApp"""
    respuesta = chatbot_respuesta(mensaje)
    return {"mensaje": mensaje, "respuesta": respuesta}

# ==================== EJECUTAR ====================
if __name__ == "__main__":
    print("🚀 ChatGPT WhatsApp Bot iniciando...")
    print("🧠 Usando OpenAI GPT-3.5-turbo")
    print("🌐 Prueba en: http://localhost:8000/docs")
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
