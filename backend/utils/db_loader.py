"""
Modulo per il caricamento e la ricerca di strutture sanitarie.

Gestisce il caricamento dei dati dal file JSON e implementa un sistema
di ricerca fuzzy migliorato per trovare le strutture più rilevanti.
"""

from __future__ import annotations

import json
import difflib
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache per i dati caricati
_cached_data: Optional[Dict] = None

def carica_strutture(percorso: str = "dati_sanitari.json") -> Dict[str, Any]:
    """
    Carica i dati sanitari da un file JSON con caching.
    
    Args:
        percorso: percorso al file JSON
        
    Returns:
        Dizionario con strutture, FAQ, numeri utili, etc.
        
    Raises:
        FileNotFoundError: se il file non esiste
        json.JSONDecodeError: se il JSON non è valido
    """
    global _cached_data
    
    # Usa cache se disponibile
    if _cached_data is not None:
        return _cached_data
    
    file_path = Path(percorso)
    if not file_path.exists():
        logger.error(f"File non trovato: {percorso}")
        raise FileNotFoundError(f"Il file {percorso} non esiste")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            _cached_data = json.load(f)
            logger.info(f"Caricati dati da {percorso}")
            
            # Valida la struttura dei dati
            if "strutture" not in _cached_data:
                # Se il file contiene solo l'array di strutture (vecchio formato)
                _cached_data = {"strutture": _cached_data}
            
            return _cached_data
            
    except json.JSONDecodeError as e:
        logger.error(f"Errore nel parsing JSON: {e}")
        raise
    except Exception as e:
        logger.error(f"Errore nel caricamento dati: {e}")
        raise

def costruisci_stringa(item: Dict[str, Any], intent: str = None) -> str:
    """
    Costruisce una rappresentazione testuale ottimizzata di una struttura.
    
    Args:
        item: dizionario con le informazioni della struttura
        intent: tipo di informazione richiesta (orari, servizi, etc.)
        
    Returns:
        Stringa formattata per il prompt
    """
    parti = [f"📍 {item['nome']} a {item['città']} ({item['indirizzo']})"]
    
    # Aggiungi info base
    parti.append(f"📞 Tel: {item['telefono']}")
    
    # Personalizza in base all'intent
    if intent == "orari" and "orari_dettaglio" in item:
        parti.append(f"🕐 Orari generali: {item.get('orari', 'N/D')}")
        for servizio, orario in item.get('orari_dettaglio', {}).items():
            parti.append(f"   • {servizio.replace('_', ' ').title()}: {orario}")
    else:
        parti.append(f"🕐 Orari: {item.get('orari', 'N/D')}")
    
    if intent == "servizi" or intent is None:
        servizi = item.get('servizi', [])
        if servizi:
            parti.append(f"🏥 Servizi: {', '.join(servizi[:5])}")
            if len(servizi) > 5:
                parti.append(f"   ...e altri {len(servizi)-5} servizi")
    
    # Aggiungi info accessibilità se presente
    if "accessibilita" in item:
        acc = item["accessibilita"]
        acc_info = []
        if acc.get("parcheggio_disabili"):
            acc_info.append("♿ Parcheggio disabili")
        if acc.get("ascensore"):
            acc_info.append("🛗 Ascensore")
        if acc.get("percorso_tattile"):
            acc_info.append("🦯 Percorso tattile")
        if acc_info:
            parti.append(f"Accessibilità: {', '.join(acc_info)}")
    
    # Link utili
    if item.get("link_mappa"):
        parti.append(f"🗺️ Mappa: {item['link_mappa']}")
    if item.get("pagina_web"):
        parti.append(f"🌐 Info: {item['pagina_web']}")
    
    return "\n".join(parti)

def trova_rilevanti(
    domanda: str,
    dati: List[Dict[str, Any]],
    max_strutture: int = 3,
    intent: str = None
) -> List[str]:
    """
    Trova le strutture più rilevanti con algoritmo di scoring migliorato.
    
    Args:
        domanda: domanda dell'utente
        dati: lista delle strutture
        max_strutture: numero massimo di risultati
        intent: tipo di richiesta per ottimizzare la ricerca
        
    Returns:
        Lista di stringhe formattate delle strutture più pertinenti
    """
    if not dati:
        return ["Nessuna struttura disponibile nel database."]
    
    punteggi: List[tuple[float, Dict[str, Any]]] = []
    q_lower = domanda.lower()
    
    # Parole chiave per boost del punteggio
    boost_keywords = {
        'pronto soccorso': ['pronto soccorso', 'emergenza', 'urgenza'],
        'prelievi': ['prelievi', 'analisi', 'sangue', 'laboratorio'],
        'radiologia': ['radiologia', 'radiografia', 'rx', 'tac'],
        'fisioterapia': ['fisioterapia', 'riabilitazione', 'recupero'],
        'prenotazione': ['prenot', 'cup', 'appuntamento']
    }
    
    for item in dati:
        score = 0.0
        
        # 1. Matching nome struttura
        nome_score = difflib.SequenceMatcher(None, q_lower, item['nome'].lower()).ratio()
        score += nome_score * 2  # Peso doppio per il nome
        
        # 2. Matching città
        citta_score = difflib.SequenceMatcher(None, q_lower, item['città'].lower()).ratio()
        score += citta_score * 1.5
        
        # 3. Matching servizi
        servizi_text = ' '.join(item.get('servizi', [])).lower()
        servizi_score = difflib.SequenceMatcher(None, q_lower, servizi_text).ratio()
        score += servizi_score
        
        # 4. Boost per parole chiave specifiche
        for categoria, keywords in boost_keywords.items():
            if any(kw in q_lower for kw in keywords):
                if any(kw in servizi_text for kw in keywords):
                    score += 0.5  # Boost se il servizio richiesto è presente
        
        # 5. Boost per intent specifici
        if intent == "orari" and "orari_dettaglio" in item:
            score += 0.2
        elif intent == "emergenza" and "pronto soccorso" in servizi_text:
            score += 0.8
        elif intent == "prenotazione" and any(s in servizi_text for s in ['cup', 'prenotazioni']):
            score += 0.3
        
        # 6. Penalità per strutture senza il servizio richiesto
        servizi_richiesti = ['pronto soccorso', 'prelievi', 'radiologia', 'fisioterapia']
        for servizio in servizi_richiesti:
            if servizio in q_lower and servizio not in servizi_text:
                score *= 0.5  # Dimezza il punteggio se manca il servizio richiesto
        
        punteggi.append((score, item))
    
    # Ordina per punteggio
    punteggi.sort(key=lambda x: x[0], reverse=True)
    
    # Se il primo risultato ha un punteggio molto alto, restituisci solo quello
    if punteggi and punteggi[0][0] > 0.8:
        max_strutture = min(2, max_strutture)
    
    # Costruisci le stringhe per le strutture selezionate
    risultati = []
    for score, item in punteggi[:max_strutture]:
        if score > 0.1:  # Soglia minima di rilevanza
            risultati.append(costruisci_stringa(item, intent))
            logger.debug(f"Struttura selezionata: {item['nome']} (score: {score:.2f})")
    
    if not risultati:
        return ["Non ho trovato strutture pertinenti alla tua richiesta. Prova a riformulare la domanda."]
    
    return risultati

def trova_struttura_per_nome(nome: str, dati: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Trova una struttura specifica per nome.
    
    Args:
        nome: nome della struttura
        dati: lista delle strutture
        
    Returns:
        Dizionario della struttura se trovata, None altrimenti
    """
    nome_lower = nome.lower()
    
    for struttura in dati:
        if nome_lower in struttura['nome'].lower():
            return struttura
    
    # Prova con fuzzy matching se non trova corrispondenza esatta
    best_match = None
    best_score = 0
    
    for struttura in dati:
        score = difflib.SequenceMatcher(None, nome_lower, struttura['nome'].lower()).ratio()
        if score > best_score and score > 0.6:  # Soglia minima 60%
            best_score = score
            best_match = struttura
    
    return best_match

def get_servizi_disponibili(dati: List[Dict[str, Any]]) -> List[str]:
    """
    Ottiene lista unica di tutti i servizi disponibili.
    
    Args:
        dati: lista delle strutture
        
    Returns:
        Lista di servizi unici
    """
    servizi_set = set()
    
    for struttura in dati:
        servizi_set.update(struttura.get('servizi', []))
    
    return sorted(list(servizi_set))

def get_citta_disponibili(dati: List[Dict[str, Any]]) -> List[str]:
    """
    Ottiene lista delle città con strutture sanitarie.
    
    Args:
        dati: lista delle strutture
        
    Returns:
        Lista di città uniche
    """
    citta = list(set(struttura['città'] for struttura in dati))
    return sorted(citta)