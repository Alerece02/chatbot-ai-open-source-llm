"""
Modulo per il caching delle risposte frequenti.

Migliora le performance salvando in cache le risposte per domande comuni.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class ResponseCache:
    """
    Cache per le risposte del chatbot.
    """
    
    def __init__(self, max_size: int = 100, ttl_hours: int = 24, cache_file: str = "cache.json"):
        """
        Inizializza la cache.
        
        Args:
            max_size: numero massimo di elementi in cache
            ttl_hours: tempo di vita delle entry in ore
            cache_file: file per persistenza cache
        """
        self.max_size = max_size
        self.ttl_hours = ttl_hours
        self.cache_file = Path(cache_file)
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
        
        # Carica cache esistente se disponibile
        self._load_cache()
    
    def _get_key(self, question: str, intent: str) -> str:
        """
        Genera una chiave univoca per la cache.
        
        Args:
            question: domanda dell'utente
            intent: intent classificato
            
        Returns:
            Hash MD5 come chiave
        """
        combined = f"{question.lower().strip()}_{intent}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get(self, question: str, intent: str) -> Optional[Dict[str, Any]]:
        """
        Recupera una risposta dalla cache.
        
        Args:
            question: domanda dell'utente
            intent: intent classificato
            
        Returns:
            Dizionario con la risposta se in cache e valida, None altrimenti
        """
        key = self._get_key(question, intent)
        
        if key in self.cache:
            entry = self.cache[key]
            
            # Verifica TTL
            timestamp = datetime.fromisoformat(entry['timestamp'])
            if datetime.now() - timestamp < timedelta(hours=self.ttl_hours):
                self.stats['hits'] += 1
                logger.debug(f"Cache HIT per: {question[:30]}...")
                
                # Aggiorna ultimo accesso
                entry['last_access'] = datetime.now().isoformat()
                entry['access_count'] = entry.get('access_count', 0) + 1
                
                return entry['data']
            else:
                # Entry scaduta, rimuovi
                del self.cache[key]
                logger.debug(f"Cache entry scaduta per: {question[:30]}...")
        
        self.stats['misses'] += 1
        return None
    
    def set(self, question: str, intent: str, data: Dict[str, Any]) -> None:
        """
        Salva una risposta in cache.
        
        Args:
            question: domanda dell'utente
            intent: intent classificato
            data: dati da salvare (risposta, struttura, etc.)
        """
        key = self._get_key(question, intent)
        
        # Se la cache è piena, rimuovi l'elemento meno usato
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        self.cache[key] = {
            'question': question,
            'intent': intent,
            'data': data,
            'timestamp': datetime.now().isoformat(),
            'last_access': datetime.now().isoformat(),
            'access_count': 1
        }
        
        logger.debug(f"Cache SET per: {question[:30]}...")
        
        # Salva cache su file periodicamente
        if len(self.cache) % 10 == 0:
            self._save_cache()
    
    def _evict_lru(self) -> None:
        """Rimuove l'elemento meno recentemente usato."""
        if not self.cache:
            return
        
        # Trova l'elemento con last_access più vecchio
        lru_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].get('last_access', self.cache[k]['timestamp'])
        )
        
        del self.cache[lru_key]
        self.stats['evictions'] += 1
        logger.debug(f"Cache LRU eviction, size: {len(self.cache)}")
    
    def clear(self) -> None:
        """Svuota la cache."""
        self.cache.clear()
        self.stats = {'hits': 0, 'misses': 0, 'evictions': 0}
        logger.info("Cache svuotata")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Restituisce statistiche sulla cache.
        
        Returns:
            Dizionario con statistiche
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'evictions': self.stats['evictions'],
            'hit_rate': f"{hit_rate:.1f}%",
            'total_requests': total_requests
        }
    
    def _save_cache(self) -> None:
        """Salva la cache su file."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'cache': self.cache,
                    'stats': self.stats
                }, f, ensure_ascii=False, indent=2)
            logger.debug(f"Cache salvata su {self.cache_file}")
        except Exception as e:
            logger.error(f"Errore nel salvataggio cache: {e}")
    
    def _load_cache(self) -> None:
        """Carica la cache da file se esiste."""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.cache = data.get('cache', {})
                self.stats = data.get('stats', {'hits': 0, 'misses': 0, 'evictions': 0})
            
            # Pulisci entry scadute
            now = datetime.now()
            expired_keys = []
            for key, entry in self.cache.items():
                timestamp = datetime.fromisoformat(entry['timestamp'])
                if now - timestamp >= timedelta(hours=self.ttl_hours):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.info(f"Rimosse {len(expired_keys)} entry scadute dalla cache")
            
            logger.info(f"Cache caricata: {len(self.cache)} entry")
            
        except Exception as e:
            logger.error(f"Errore nel caricamento cache: {e}")
            self.cache = {}

# Cache singleton per uso globale
_cache_instance: Optional[ResponseCache] = None

def get_cache() -> ResponseCache:
    """Restituisce l'istanza singleton della cache."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ResponseCache()
    return _cache_instance