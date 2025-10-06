"""
Sistema RAG semplificato senza dipendenze complesse.
Usa TF-IDF invece di embeddings neurali - più veloce e stabile.
"""

import json
import hashlib
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Rappresenta un chunk di documento indicizzato"""
    id: str
    text: str
    metadata: Dict[str, Any]
    score: float = 0.0

class SimpleChunker:
    """Divide i dati in chunk ottimali"""
    
    def chunk_struttura(self, struttura: Dict) -> List[DocumentChunk]:
        chunks = []
        base_id = hashlib.md5(struttura['nome'].encode()).hexdigest()[:8]
        
        # Chunk principale con tutte le info
        main_text = f"{struttura['nome']} a {struttura['città']}. "
        main_text += f"Orari: {struttura['orari']}. "
        main_text += f"Telefono: {struttura['telefono']}. "
        main_text += f"Indirizzo: {struttura['indirizzo']}. "
        
        if struttura.get('servizi'):
            main_text += f"Servizi: {', '.join(struttura['servizi'])}. "
        
        chunk_main = DocumentChunk(
            id=f"{base_id}_main",
            text=main_text,
            metadata={'tipo': 'completo', 'struttura': struttura['nome']}
        )
        chunks.append(chunk_main)
        
        # Chunk specifici per orari dettagliati
        if struttura.get('orari_dettaglio'):
            for servizio, orario in struttura['orari_dettaglio'].items():
                chunk_detail = DocumentChunk(
                    id=f"{base_id}_{servizio}",
                    text=f"{struttura['nome']}: {servizio.replace('_', ' ')} - {orario}",
                    metadata={'tipo': 'orario_dettaglio', 'struttura': struttura['nome']}
                )
                chunks.append(chunk_detail)
        
        return chunks

class SimpleTfidfIndex:
    """Indice basato su TF-IDF - più semplice e stabile"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            stop_words=None,  # Manteniamo tutto per l'italiano
            use_idf=True
        )
        self.vectors = None
        self.chunks: List[DocumentChunk] = []
        
    def build_index(self, chunks: List[DocumentChunk]):
        """Costruisce l'indice TF-IDF"""
        if not chunks:
            logger.warning("Nessun chunk da indicizzare")
            return
            
        logger.info(f"Costruzione indice TF-IDF per {len(chunks)} chunks...")
        
        # Estrai testi
        texts = [chunk.text for chunk in chunks]
        
        # Crea vettori TF-IDF
        self.vectors = self.vectorizer.fit_transform(texts)
        self.chunks = chunks
        
        logger.info(f"Indice costruito! Features: {self.vectors.shape}")
    
    def search(self, query: str, k: int = 3, filter_tipo: str = None) -> List[DocumentChunk]:
        """Ricerca con TF-IDF e cosine similarity"""
        if self.vectors is None:
            logger.warning("Indice non inizializzato")
            return []
        
        # Vettorizza la query
        query_vector = self.vectorizer.transform([query])
        
        # Calcola similarità
        similarities = cosine_similarity(query_vector, self.vectors)[0]
        
        # Ordina per similarità
        indices = np.argsort(similarities)[::-1]
        
        results = []
        for idx in indices:
            chunk = self.chunks[idx]
            
            # Applica filtro se specificato
            if filter_tipo and chunk.metadata.get('tipo') != filter_tipo:
                continue
            
            chunk.score = float(similarities[idx])
            
            # Ignora risultati con score troppo basso
            if chunk.score < 0.1:
                continue
                
            results.append(chunk)
            
            if len(results) >= k:
                break
        
        return results

class OptimizedRAG:
    """Sistema RAG semplificato con TF-IDF"""
    
    def __init__(self, data_path: str = "dati_sanitari.json"):
        self.data_path = data_path
        self.chunker = SimpleChunker()
        self.index = SimpleTfidfIndex()
        self.cache = {}
        
        # Inizializza
        self._initialize()
    
    def _initialize(self):
        """Inizializza il sistema"""
        try:
            # Carica dati
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Gestisci diversi formati
            if isinstance(data, list):
                strutture = data
            else:
                strutture = data.get('strutture', [])
            
            # Crea chunks
            all_chunks = []
            for struttura in strutture:
                chunks = self.chunker.chunk_struttura(struttura)
                all_chunks.extend(chunks)
            
            # Aggiungi FAQ se presenti
            if isinstance(data, dict) and 'faq' in data:
                for faq in data['faq']:
                    chunk = DocumentChunk(
                        id=hashlib.md5(faq['domanda'].encode()).hexdigest()[:8],
                        text=f"FAQ: {faq['domanda']} Risposta: {faq['risposta']}",
                        metadata={'tipo': 'faq'}
                    )
                    all_chunks.append(chunk)
            
            # Costruisci indice
            self.index.build_index(all_chunks)
            logger.info(f"Sistema RAG (TF-IDF) pronto con {len(all_chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Errore inizializzazione: {e}")
            raise
    
    def get_relevant_context(self, query: str, intent: str = None) -> str:
        """Ottiene contesto rilevante per la query"""
        # Check cache
        cache_key = f"{intent}:{query[:50]}"
        if cache_key in self.cache:
            logger.info("Cache HIT!")
            return self.cache[cache_key]
        
        # Determina numero di risultati
        k_results = 2 if intent in ['orari', 'telefono'] else 3
        
        # Ricerca
        chunks = self.index.search(query, k=k_results)
        
        if not chunks:
            return "Non ho trovato informazioni pertinenti."
        
        # Costruisci contesto
        context_parts = []
        for chunk in chunks:
            if chunk.score > 0.2:  # Solo risultati rilevanti
                context_parts.append(chunk.text)
                logger.debug(f"Chunk usato (score: {chunk.score:.3f})")
        
        context = " ".join(context_parts[:2])  # Max 2 chunks
        
        # Cache
        self.cache[cache_key] = context
        
        # Limita cache
        if len(self.cache) > 100:
            keys_to_remove = list(self.cache.keys())[:50]
            for key in keys_to_remove:
                del self.cache[key]
        
        return context

# Funzioni helper
_rag_instance = None

def get_rag_instance(data_path: str = "dati_sanitari.json") -> OptimizedRAG:
    """Singleton pattern"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = OptimizedRAG(data_path)
    return _rag_instance

def get_optimized_context(query: str, intent: str = None) -> str:
    """Funzione semplificata per ottenere contesto"""
    rag = get_rag_instance()
    return rag.get_relevant_context(query, intent)