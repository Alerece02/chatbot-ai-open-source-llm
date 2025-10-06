"""
Modulo per generare suggerimenti di domande follow-up.

Aiuta gli utenti suggerendo domande pertinenti basate sul contesto.
"""

import random
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Suggerimenti per intent
SUGGESTIONS_BY_INTENT = {
    'orari': [
        "Quali sono gli orari del pronto soccorso?",
        "È aperto anche la domenica?",
        "A che ora apre il centro prelievi?",
        "Quali sono gli orari per le visite specialistiche?",
        "Fino a che ora posso fare le analisi del sangue?"
    ],
    'servizi': [
        "C'è il servizio di radiologia?",
        "Fanno anche la fisioterapia?",
        "Quali esami posso fare?",
        "C'è un reparto di cardiologia?",
        "Hanno il servizio di day hospital?"
    ],
    'prenotazione': [
        "Qual è il numero del CUP per prenotare?",
        "Posso prenotare online?",
        "Quanto tempo di attesa c'è per una visita?",
        "Cosa devo portare per la visita?",
        "Come posso disdire un appuntamento?"
    ],
    'contatti': [
        "Qual è il numero del centralino?",
        "Come posso contattare il CUP?",
        "C'è un numero per le urgenze?",
        "Hanno un indirizzo email?",
        "Qual è il numero del pronto soccorso?"
    ],
    'posizione': [
        "Come arrivo con i mezzi pubblici?",
        "C'è parcheggio vicino?",
        "Qual è l'indirizzo esatto?",
        "È vicino alla stazione?",
        "Ci sono parcheggi per disabili?"
    ],
    'analisi': [
        "Devo essere a digiuno per le analisi?",
        "Quando posso ritirare i risultati?",
        "Quali documenti servono per il prelievo?",
        "A che ora apre il centro prelievi?",
        "Posso vedere i risultati online?"
    ],
    'documenti': [
        "Serve l'impegnativa del medico?",
        "Devo portare la tessera sanitaria?",
        "Quali documenti servono per la prima visita?",
        "Serve il documento d'identità?",
        "L'impegnativa ha una scadenza?"
    ],
    'costi': [
        "Quanto costa il ticket?",
        "Ci sono esenzioni per reddito?",
        "Come posso pagare il ticket?",
        "Le visite private quanto costano?",
        "Posso avere l'esenzione per patologia?"
    ],
    'accessibilita': [
        "C'è l'ascensore per i disabili?",
        "Ci sono barriere architettoniche?",
        "C'è parcheggio riservato ai disabili?",
        "Posso entrare con la carrozzina?",
        "C'è assistenza per non vedenti?"
    ],
    'emergenza': [
        "Qual è il numero per le emergenze?",
        "Dove si trova il pronto soccorso più vicino?",
        "Quanto tempo di attesa al pronto soccorso?",
        "Cosa sono i codici colore?",
        "Quando devo andare al pronto soccorso?"
    ],
    'generale': [
        "Quali servizi offre questa struttura?",
        "Quali sono gli orari di apertura?",
        "Come posso prenotare una visita?",
        "Dove si trova esattamente?",
        "Qual è il numero di telefono?"
    ]
}

# Suggerimenti contestuali basati su parole chiave
CONTEXTUAL_SUGGESTIONS = {
    'ospedale': [
        "Quali reparti ci sono in questo ospedale?",
        "C'è il pronto soccorso?",
        "Come arrivo all'ospedale?"
    ],
    'prelievi': [
        "A che ora devo venire per i prelievi?",
        "Devo essere a digiuno?",
        "Quanto tempo per i risultati?"
    ],
    'visita': [
        "Come prenoto la visita?",
        "Quanto costa la visita?",
        "Cosa devo portare?"
    ],
    'anziani': [
        "C'è assistenza per anziani?",
        "Ci sono servizi domiciliari?",
        "C'è la geriatria?"
    ],
    'bambini': [
        "C'è la pediatria?",
        "Quali sono gli orari della pediatria?",
        "C'è il pronto soccorso pediatrico?"
    ]
}

def genera_suggerimenti(
    domanda: str,
    risposta: str,
    intent: str,
    max_suggerimenti: int = 3
) -> List[str]:
    """
    Genera suggerimenti di domande follow-up.
    
    Args:
        domanda: domanda originale dell'utente
        risposta: risposta fornita dal chatbot
        intent: intent classificato
        max_suggerimenti: numero massimo di suggerimenti
        
    Returns:
        Lista di domande suggerite
    """
    suggerimenti = []
    
    # 1. Suggerimenti basati sull'intent
    if intent in SUGGESTIONS_BY_INTENT:
        intent_suggestions = SUGGESTIONS_BY_INTENT[intent].copy()
        # Rimuovi domande simili a quella già fatta
        intent_suggestions = [
            s for s in intent_suggestions 
            if not _is_similar_question(s, domanda)
        ]
        suggerimenti.extend(intent_suggestions)
    
    # 2. Suggerimenti contestuali basati sulla risposta
    risposta_lower = risposta.lower()
    domanda_lower = domanda.lower()
    
    for keyword, context_suggestions in CONTEXTUAL_SUGGESTIONS.items():
        if keyword in risposta_lower or keyword in domanda_lower:
            for suggestion in context_suggestions:
                if not _is_similar_question(suggestion, domanda):
                    suggerimenti.append(suggestion)
    
    # 3. Suggerimenti specifici basati su menzioni nella risposta
    if 'pronto soccorso' in risposta_lower and 'orari' not in domanda_lower:
        suggerimenti.append("Quali sono i tempi di attesa medi al pronto soccorso?")
    
    if 'prenotare' in risposta_lower and 'numero' not in domanda_lower:
        suggerimenti.append("Qual è il numero per prenotare?")
    
    if 'ospedale' in risposta_lower and 'parcheggio' not in domanda_lower:
        suggerimenti.append("C'è parcheggio vicino all'ospedale?")
    
    if 'cup' in risposta_lower and 'orari' not in domanda_lower:
        suggerimenti.append("Quali sono gli orari del CUP?")
    
    # 4. Rimuovi duplicati mantenendo l'ordine
    seen = set()
    unique_suggerimenti = []
    for s in suggerimenti:
        if s not in seen:
            seen.add(s)
            unique_suggerimenti.append(s)
    
    # 5. Seleziona i migliori suggerimenti
    if len(unique_suggerimenti) > max_suggerimenti:
        # Prioritizza suggerimenti più pertinenti
        prioritized = _prioritize_suggestions(unique_suggerimenti, domanda, risposta)
        return prioritized[:max_suggerimenti]
    
    return unique_suggerimenti[:max_suggerimenti]

def _is_similar_question(question1: str, question2: str) -> bool:
    """
    Verifica se due domande sono simili.
    
    Args:
        question1: prima domanda
        question2: seconda domanda
        
    Returns:
        True se le domande sono simili
    """
    q1_lower = question1.lower()
    q2_lower = question2.lower()
    
    # Verifica sovrapposizione di parole chiave
    words1 = set(q1_lower.split())
    words2 = set(q2_lower.split())
    
    # Rimuovi parole comuni
    stopwords = {'il', 'la', 'i', 'le', 'un', 'una', 'di', 'da', 'per', 'con', 'su', 'è', 'sono', 'a', 'e'}
    words1 = words1 - stopwords
    words2 = words2 - stopwords
    
    # Calcola sovrapposizione
    if not words1 or not words2:
        return False
    
    overlap = len(words1 & words2) / min(len(words1), len(words2))
    
    return overlap > 0.6

def _prioritize_suggestions(
    suggestions: List[str],
    domanda: str,
    risposta: str
) -> List[str]:
    """
    Prioritizza i suggerimenti basandosi sulla pertinenza.
    
    Args:
        suggestions: lista di suggerimenti
        domanda: domanda originale
        risposta: risposta del chatbot
        
    Returns:
        Lista ordinata per priorità
    """
    scored_suggestions = []
    
    for suggestion in suggestions:
        score = 0
        
        # Aumenta score se il suggerimento è un naturale follow-up
        if 'come' in domanda.lower() and 'dove' in suggestion.lower():
            score += 2
        elif 'dove' in domanda.lower() and 'orari' in suggestion.lower():
            score += 2
        elif 'orari' in domanda.lower() and 'prenotare' in suggestion.lower():
            score += 2
        
        # Aumenta score se il suggerimento approfondisce il tema
        if any(word in risposta.lower() for word in suggestion.lower().split()):
            score += 1
        
        scored_suggestions.append((score, suggestion))
    
    # Ordina per score decrescente
    scored_suggestions.sort(key=lambda x: x[0], reverse=True)
    
    return [s for _, s in scored_suggestions]

def get_emergency_suggestions() -> List[str]:
    """
    Restituisce suggerimenti per situazioni di emergenza.
    
    Returns:
        Lista di suggerimenti per emergenze
    """
    return [
        "Chiama immediatamente il 118 per emergenze mediche",
        "Dove si trova il pronto soccorso più vicino?",
        "Quali documenti servono al pronto soccorso?"
    ]

def get_greeting_suggestions() -> List[str]:
    """
    Restituisce suggerimenti per l'inizio conversazione.
    
    Returns:
        Lista di suggerimenti iniziali
    """
    return [
        "Dove posso fare le analisi del sangue?",
        "Come prenoto una visita specialistica?",
        "Quali sono gli orari del centro prelievi?",
        "Dove si trova l'ospedale più vicino?",
        "Come posso contattare il CUP?"
    ]

def format_suggestions_for_ui(suggestions: List[str]) -> List[dict]:
    """
    Formatta i suggerimenti per l'interfaccia utente.
    
    Args:
        suggestions: lista di suggerimenti
        
    Returns:
        Lista di dizionari con suggerimenti formattati
    """
    formatted = []
    
    # Icone per categorie di domande
    icons = {
        'orari': '🕐',
        'prenot': '📅',
        'dove': '📍',
        'telefono': '📞',
        'document': '📄',
        'analisi': '💉',
        'emergenz': '🚨',
        'servizi': '🏥'
    }
    
    for suggestion in suggestions:
        icon = '❓'  # Default
        suggestion_lower = suggestion.lower()
        
        for keyword, emoji in icons.items():
            if keyword in suggestion_lower:
                icon = emoji
                break
        
        formatted.append({
            'text': suggestion,
            'icon': icon,
            'action': 'ask'
        })
    
    return formatted