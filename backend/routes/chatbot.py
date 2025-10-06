"""
Route FastAPI per il chatbot sanitario ULSS9.

Questo modulo gestisce l'endpoint principale per le domande degli utenti,
utilizzando un sistema di intent classification e memoria contestuale
per fornire risposte pertinenti e accessibili.
"""

from __future__ import annotations

import time
import logging
from typing import List, Dict, Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import httpx

from utils.db_loader import carica_strutture, trova_rilevanti
from utils.memory import ConversationMemory
from utils.prompt_builder import costruisci_prompt
from utils.intent_classifier import classify_intent
from utils.response_cache import ResponseCache
from utils.analytics import Analytics
from utils.suggestions import genera_suggerimenti

# Configurazione
logger = logging.getLogger(__name__)
router = APIRouter()

# Inizializza componenti
memory = ConversationMemory()
cache = ResponseCache()
analytics = Analytics()

# Modelli Pydantic per request/response
class ChatRequest(BaseModel):
    question: str
    history: List[Dict] = []
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    risposta: str
    struttura: Optional[str] = None
    suggerimenti: List[str] = []
    intent: str = "generale"
    tempo_risposta: float = 0.0
    cached: bool = False

@router.post("/ask", response_model=ChatResponse)
async def ask_question(req: ChatRequest):
    """
    Endpoint principale per rispondere alle domande degli utenti.
    
    Gestisce:
    - Intent classification per capire il tipo di domanda
    - Memoria contestuale per domande di follow-up
    - Cache per risposte frequenti
    - Analytics per monitoraggio performance
    - Suggerimenti per domande successive
    """
    start_time = time.time()
    
    domanda = req.question.strip()
    storia = req.history
    session_id = req.session_id or "default"
    
    if not domanda:
        raise HTTPException(status_code=400, detail="La domanda non può essere vuota")
    
    logger.info(f"Nuova domanda: {domanda[:50]}... (session: {session_id})")
    
    try:
        # 1. Carica i dati delle strutture
        dati = carica_strutture("dati_sanitari.json")
        strutture = dati.get("strutture", [])
        faq = dati.get("faq", [])
        numeri_utili = dati.get("numeri_utili", {})
        
    except Exception as e:
        logger.error(f"Errore caricamento dati: {e}")
        return ChatResponse(
            risposta="Mi dispiace, c'è un problema temporaneo nel caricamento dei dati. Riprova tra qualche istante.",
            tempo_risposta=time.time() - start_time
        )
    
    # 2. Classifica l'intent della domanda
    intent = classify_intent(domanda)
    logger.info(f"Intent rilevato: {intent}")
    
    # 3. Aggiorna memoria conversazione
    memory.update_from_history(storia)
    dialogo = memory.get_dialog_context()
    ultima_struttura = memory.get_current_structure()
    
    # 4. Gestisci riferimenti ambigui (questo, quello, lì, etc.)
    domanda_contestualizzata = memory.resolve_references(domanda)
    
    # 5. Controlla cache per risposte frequenti
    cached_response = cache.get(domanda_contestualizzata, intent)
    if cached_response:
        logger.info("Risposta dalla cache")
        return ChatResponse(
            risposta=cached_response['risposta'],
            struttura=cached_response.get('struttura'),
            suggerimenti=genera_suggerimenti(domanda, cached_response['risposta'], intent),
            intent=intent,
            tempo_risposta=time.time() - start_time,
            cached=True
        )
    
    # 6. Cerca FAQ pertinenti
    faq_response = cerca_in_faq(domanda_contestualizzata, faq)
    if faq_response:
        logger.info("Risposta trovata nelle FAQ")
        cache.set(domanda_contestualizzata, intent, {'risposta': faq_response})
        return ChatResponse(
            risposta=faq_response,
            suggerimenti=genera_suggerimenti(domanda, faq_response, intent),
            intent=intent,
            tempo_risposta=time.time() - start_time
        )
    
    # 7. Trova strutture rilevanti
    contesto_strutture = trova_rilevanti(domanda_contestualizzata, strutture, max_strutture=3)
    
    # 8. Aggiungi informazioni specifiche per intent
    contesto_extra = ""
    if intent == "prenotazione":
        contesto_extra = f"\nPer prenotazioni: CUP {numeri_utili.get('cup_prenotazioni', 'N/D')}"
    elif intent == "emergenza":
        contesto_extra = f"\nPer emergenze: chiamare il 118"
    
    # 9. Costruisci il prompt
    contesto_completo = "\n".join(contesto_strutture) + contesto_extra
    prompt = costruisci_prompt(
        contesto=contesto_completo,
        dialogo=dialogo,
        domanda=domanda_contestualizzata,
        intent=intent
    )
    
    # 10. Chiama Ollama per generare la risposta
    try:
        response = await chiamata_ollama(prompt)
        risposta = response.strip()
        
        # Estrai eventuale struttura menzionata
        struttura_menzionata = memory.extract_structure(risposta)
        
        # Salva in cache
        cache.set(domanda_contestualizzata, intent, {
            'risposta': risposta,
            'struttura': struttura_menzionata
        })
        
        # Aggiorna memoria
        memory.add_turn(domanda, risposta)
        
        # Log analytics
        tempo_risposta = time.time() - start_time
        analytics.log_query(
            question=domanda,
            intent=intent,
            response_time=tempo_risposta,
            success=True,
            session_id=session_id
        )
        
        # Genera suggerimenti
        suggerimenti = genera_suggerimenti(domanda, risposta, intent)
        
        return ChatResponse(
            risposta=risposta,
            struttura=struttura_menzionata or ultima_struttura,
            suggerimenti=suggerimenti,
            intent=intent,
            tempo_risposta=tempo_risposta
        )
        
    except Exception as e:
        logger.error(f"Errore nella generazione risposta: {e}")
        tempo_risposta = time.time() - start_time
        analytics.log_query(
            question=domanda,
            intent=intent,
            response_time=tempo_risposta,
            success=False,
            session_id=session_id
        )
        
        return ChatResponse(
            risposta="Mi dispiace, ho avuto un problema nel generare la risposta. Puoi riprovare o chiamare il centralino ULSS9 al 045 807 1111.",
            intent=intent,
            tempo_risposta=tempo_risposta
        )

async def chiamata_ollama(prompt: str, model: str = "mistral") -> str:
    """
    Effettua la chiamata al modello Ollama.
    
    Args:
        prompt: Il prompt completo da inviare
        model: Il modello da utilizzare (default: mistral)
    
    Returns:
        La risposta del modello
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "http://host.docker.internal:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 500
                }
            }
        )
        response.raise_for_status()
        return response.json().get("response", "")

def cerca_in_faq(domanda: str, faq_list: List[Dict]) -> Optional[str]:
    """
    Cerca una risposta nelle FAQ.
    
    Args:
        domanda: La domanda dell'utente
        faq_list: Lista delle FAQ
    
    Returns:
        La risposta se trovata, None altrimenti
    """
    domanda_lower = domanda.lower()
    
    for faq in faq_list:
        # Controlla se la domanda matcha con le FAQ
        if any(tag in domanda_lower for tag in faq.get('tags', [])):
            return faq['risposta']
        
        # Controlla similarità con la domanda FAQ
        import difflib
        similarity = difflib.SequenceMatcher(None, domanda_lower, faq['domanda'].lower()).ratio()
        if similarity > 0.7:
            return faq['risposta']
    
    return None

@router.get("/stats")
async def get_statistics():
    """Endpoint per ottenere statistiche di utilizzo"""
    return analytics.get_stats()

@router.get("/suggestions")
async def get_suggestions(intent: str = "generale"):
    """Endpoint per ottenere suggerimenti basati sull'intent"""
    suggestions_map = {
        "orari": ["A che ora apre il pronto soccorso?", "Orari del centro prelievi?", "È aperto la domenica?"],
        "servizi": ["Quali servizi offre?", "C'è la radiologia?", "Fanno fisioterapia?"],
        "prenotazione": ["Come prenoto una visita?", "Numero del CUP?", "Posso prenotare online?"],
        "posizione": ["Dove si trova?", "Come ci arrivo?", "C'è parcheggio?"],
        "generale": ["Orari di apertura?", "Come prenoto?", "Quali servizi ci sono?"]
    }
    return {"suggestions": suggestions_map.get(intent, suggestions_map["generale"])}