from fastapi import FastAPI
from src.api import webhook, testing

app = FastAPI()

app.include_router(webhook.router)
app.include_router(testing.router)

if __name__ == "__main__":
    print("🚀 ChatGPT WhatsApp Bot con RAG y Guardrails iniciando...")
    print("🧠 Usando OpenAI GPT-3.5-turbo + RAG + Guardrails")
    print("📚 Base de conocimiento: Pinecone")
    print("🛡️ Filtros: Tema (seguridad contra incendios) + Lenguaje apropiado")
    print("🌐 Prueba en: http://localhost:8000/docs")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)