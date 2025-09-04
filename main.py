# ==================== IMPORTS ====================
from prompt import SYSTEM_PROMPT
from fastapi import FastAPI, Form, UploadFile, File
from twilio.rest import Client
from openai import OpenAI
import os
from dotenv import load_dotenv
from fastapi.responses import PlainTextResponse
from pinecone import Pinecone, ServerlessSpec
import time
import PyPDF2
import io
from typing import List
import numpy as np
import json

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

# ==================== CONFIGURACIÓN PINECONE ====================
class RAGManager:
    def __init__(self):
        """Inicializa el sistema RAG con Pinecone"""
        self.pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        self.index_name = 'argenfuego-chatbot-knowledge-base'
        self.dimension = 1536  # Dimensión estándar para OpenAI embeddings
        self.setup_pinecone_index()
    
    def setup_pinecone_index(self):
        """Crea o conecta al índice de Pinecone"""
        spec = ServerlessSpec(cloud="aws", region="us-east-1")
        
        # Crear índice si no existe
        if self.index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=self.index_name, 
                dimension=self.dimension, 
                metric='cosine', 
                spec=spec
            )
            print(f"✅ Índice creado: {self.index_name}")
        else:
            print(f"✅ Conectado al índice existente: {self.index_name}")
        
        # Esperar hasta que esté listo
        while not self.pc.describe_index(self.index_name).status.ready:
            print("⏳ Esperando que el índice esté listo...")
            time.sleep(1)
        
        # Conectar al índice
        self.index = self.pc.Index(self.index_name)
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Convierte textos en vectores usando OpenAI embeddings"""
        try:
            response = openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=texts
            )
            return [embedding.embedding for embedding in response.data]
        except Exception as e:
            print(f"❌ Error creando embeddings: {e}")
            return []
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Divide el texto en fragmentos manejables para el RAG"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if len(chunk.strip()) > 0:
                chunks.append(chunk)
        
        return chunks
    
    def add_document(self, text: str, doc_id: str, metadata: dict = None):
        """Agrega un documento completo al índice vectorial"""
        # Dividir el texto en fragmentos
        chunks = self.chunk_text(text)
        
        # Crear embeddings para cada fragmento
        embeddings = self.create_embeddings(chunks)
        
        if not embeddings:
            print(f"❌ No se pudieron crear embeddings para {doc_id}")
            return False
        
        # Preparar datos para insertar
        vectors = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_id = f"{doc_id}_chunk_{i}"
            vector_metadata = {
                "text": chunk,
                "doc_id": doc_id,
                "chunk_index": i,
                **(metadata or {})
            }
            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": vector_metadata
            })
        
        # Insertar en Pinecone (en lotes para eficiencia)
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch)
        
        print(f"✅ Documento '{doc_id}' agregado con {len(chunks)} fragmentos")
        return True
    
    def search_relevant_context(self, query: str, top_k: int = 3) -> str:
        """Busca contexto relevante para una consulta"""
        # Crear embedding de la consulta
        query_embeddings = self.create_embeddings([query])
        
        if not query_embeddings:
            return ""
        
        # Buscar vectores similares
        results = self.index.query(
            vector=query_embeddings[0],
            top_k=top_k,
            include_metadata=True
        )
        
        # Extraer y combinar el contexto relevante
        relevant_texts = []
        for match in results.matches:
            if match.score > 0.7:  # Solo usar matches con alta similitud
                relevant_texts.append(match.metadata.get('text', ''))
        
        return "\n\n".join(relevant_texts)

# Instancia global del RAG Manager
rag_manager = RAGManager()

# ==================== UTILIDADES PARA ARCHIVOS ====================
def extract_text_from_pdf(file_content: bytes) -> str:
    """Extrae texto de un archivo PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"❌ Error extrayendo PDF: {e}")
        return ""

def extract_text_from_txt(file_content: bytes) -> str:
    """Extrae texto de un archivo TXT"""
    try:
        return file_content.decode('utf-8')
    except Exception as e:
        print(f"❌ Error extrayendo TXT: {e}")
        return ""

# ==================== CHATBOT CON RAG ====================
def chatbot_con_rag(mensaje_usuario):
    """Chatbot que usa RAG para respuestas más informadas"""
    try:
        # 1. Buscar contexto relevante en nuestra base de conocimiento
        contexto = rag_manager.search_relevant_context(mensaje_usuario)
        # 2. Construir el prompt con contexto
        if contexto:
            system_prompt = SYSTEM_PROMPT
        else:
            system_prompt = """Eres un asistente de WhatsApp amigable y útil.
            Respondes en español, de forma concisa (máximo 3 líneas).
            Eres profesional pero cercano. Usas emojis ocasionalmente."""
        
        # 3. Generar respuesta con OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": mensaje_usuario}
            ],
            max_tokens=150,
            temperature=0.3
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"❌ Error en chatbot con RAG: {e}")
        return "Disculpa, tengo problemas técnicos en este momento 🤖"

# ==================== WEBHOOKS Y ENDPOINTS ====================
@app.post("/webhook")
async def recibir_mensaje(Body: str = Form(), From: str = Form()):
    """Webhook principal - ahora con RAG"""
    numero = From.replace("whatsapp:", "")
    print(f"📨 {numero}: {Body}")
    
    # 🧠 ChatGPT + RAG piensa la respuesta
    respuesta_ia = chatbot_con_rag(Body)
    
    # 📱 Enviar respuesta por WhatsApp
    twilio_client.messages.create(
        from_="whatsapp:+5491147361881",
        to=From,
        body=respuesta_ia
    )
    
    print(f"🤖 Respondí con RAG: {respuesta_ia}")
    return PlainTextResponse("", status_code=200)

@app.post("/upload-document")
async def subir_documento(file: UploadFile = File(...), doc_id: str = Form(...)):
    """Endpoint para subir documentos a la base de conocimiento"""
    try:
        # Leer contenido del archivo
        file_content = await file.read()
        
        # Extraer texto según el tipo de archivo
        if file.filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf(file_content)
        elif file.filename.lower().endswith('.txt'):
            text = extract_text_from_txt(file_content)
        else:
            return {"error": "Tipo de archivo no soportado. Usa PDF o TXT"}
        
        if not text.strip():
            return {"error": "No se pudo extraer texto del archivo"}
        
        # Agregar a la base de conocimiento
        metadata = {
            "filename": file.filename,
            "file_type": file.content_type
        }
        
        success = rag_manager.add_document(text, doc_id, metadata)
        
        if success:
            return {
                "mensaje": f"✅ Documento '{file.filename}' agregado exitosamente",
                "doc_id": doc_id,
                "caracteres_procesados": len(text)
            }
        else:
            return {"error": "Error procesando el documento"}
            
    except Exception as e:
        print(f"❌ Error subiendo documento: {e}")
        return {"error": f"Error interno: {str(e)}"}

@app.post("/add-text")
async def agregar_texto(texto: str = Form(...), doc_id: str = Form(...)):
    """Endpoint para agregar texto directamente"""
    try:
        success = rag_manager.add_document(texto, doc_id)
        
        if success:
            return {
                "mensaje": f"✅ Texto agregado exitosamente como '{doc_id}'",
                "caracteres_procesados": len(texto)
            }
        else:
            return {"error": "Error procesando el texto"}
    except Exception as e:
        return {"error": f"Error interno: {str(e)}"}

@app.get("/search")
async def buscar_contexto(query: str):
    """Endpoint para probar búsquedas en la base de conocimiento"""
    try:
        contexto = rag_manager.search_relevant_context(query, top_k=5)
        return {
            "query": query,
            "contexto_encontrado": contexto,
            "tiene_contexto": bool(contexto.strip())
        }
    except Exception as e:
        return {"error": f"Error en búsqueda: {str(e)}"}

@app.post("/test")
async def probar_chatbot(mensaje: str = Form()):
    """Probar el chatbot con RAG sin WhatsApp"""
    respuesta = chatbot_con_rag(mensaje)
    return {"mensaje": mensaje, "respuesta": respuesta}

@app.get("/test-simple")
async def probar_chatbot_simple(mensaje: str):
    """Probar el chatbot con RAG usando query parameter (más fácil para testing)"""
    respuesta = chatbot_con_rag(mensaje)
    return {"mensaje": mensaje, "respuesta": respuesta}

@app.get("/")
async def inicio():
    return {
        "mensaje": "🤖 ChatGPT Bot con RAG funcionando!",
        "endpoints": {
            "webhook": "/webhook",
            "subir_documento": "/upload-document",
            "agregar_texto": "/add-text",
            "buscar": "/search",
            "probar": "/test"
        }
    }

@app.get("/status")
async def estado_rag():
    """Verifica el estado de la base de conocimiento"""
    try:
        stats = rag_manager.index.describe_index_stats()
        return {
            "indice_activo": True,
            "vectores_almacenados": stats.total_vector_count,
            "dimensiones": rag_manager.dimension
        }
    except Exception as e:
        return {"error": f"Error verificando estado: {str(e)}"}

# ==================== EJECUTAR ====================
if __name__ == "__main__":
    print("🚀 ChatGPT WhatsApp Bot con RAG iniciando...")
    print("🧠 Usando OpenAI GPT-3.5-turbo + RAG")
    print("📚 Base de conocimiento: Pinecone")
    print("🌐 Prueba en: http://localhost:8000/docs")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)