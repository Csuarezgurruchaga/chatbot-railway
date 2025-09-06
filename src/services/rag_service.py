from pinecone import Pinecone, ServerlessSpec
import time
from typing import List
from src.config.settings import openai_client, PINECONE_API_KEY, PINECONE_NAMESPACE

class RAGManager:
    def __init__(self):
        """Inicializa el sistema RAG con Pinecone"""
        self.pc = Pinecone(api_key=PINECONE_API_KEY)
        self.index_name = 'argenfuego-chatbot-knowledge-base'
        self.dimension = 1536
        self.namespace = PINECONE_NAMESPACE
        print(f"🎯 Usando namespace: {self.namespace}")
        self.setup_pinecone_index()
    
    def setup_pinecone_index(self):
        """Crea o conecta al índice de Pinecone"""
        spec = ServerlessSpec(cloud="aws", region="us-east-1")
        
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
        
        while not self.pc.describe_index(self.index_name).status.ready:
            print("⏳ Esperando que el índice esté listo...")
            time.sleep(1)
        
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
        chunks = self.chunk_text(text)
        embeddings = self.create_embeddings(chunks)
        
        if not embeddings:
            print(f"❌ No se pudieron crear embeddings para {doc_id}")
            return False
        
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
        
        print(f"💾 Guardando en namespace: '{self.namespace}' - documento: '{doc_id}'")
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch, namespace=self.namespace)
        
        print(f"✅ Documento '{doc_id}' agregado con {len(chunks)} fragmentos")
        return True
    
    def search_relevant_context(self, query: str, top_k: int = 3) -> str:
        """Busca contexto relevante para una consulta"""
        print(f"🔍 Buscando en namespace: '{self.namespace}' para query: '{query[:50]}...'")
        
        query_embeddings = self.create_embeddings([query])
        
        if not query_embeddings:
            return ""
        
        results = self.index.query(
            vector=query_embeddings[0],
            top_k=top_k,
            include_metadata=True,
            namespace=self.namespace
        )
        
        print(f"📊 Encontrados {len(results.matches)} matches en namespace '{self.namespace}'")
        
        relevant_texts = []
        for match in results.matches:
            if match.score > 0.7:
                text_content = match.metadata.get('chunk_text', '') or match.metadata.get('text', '')
                if text_content:
                    relevant_texts.append(text_content)
                    print(f"📄 Match encontrado (score: {match.score:.4f}): {text_content[:100]}...")
        
        return "\n\n".join(relevant_texts)

rag_manager = None

def get_rag_manager():
    """Obtiene la instancia de RAGManager con lazy loading"""
    global rag_manager
    if rag_manager is None:
        print("🔧 Creando nueva instancia de RAGManager...")
        rag_manager = RAGManager()
    else:
        print(f"♻️ Reutilizando instancia existente de RAGManager (namespace: '{rag_manager.namespace}')")
    return rag_manager