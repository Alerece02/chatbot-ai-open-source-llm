"""
Modulo per la classificazione dell'intent delle domande degli utenti.

Identifica il tipo di richiesta per ottimizzare la ricerca e la risposta.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Definizione degli intent e relative parole chiave
INTENT_KEYWORDS: Dict[str, List[str]] = {
    'orari': [
        'orari', 'orario', 'aperto', 'apre', 'chiude', 'chiuso',
        'apertura', 'chiusura', 'quando', 'che ora', 'a che ora',
        'domenica', 'sabato', 'festivi', 'weekend'
    ],
    'servizi': [
        'servizi', 'servizio', 'cosa offre', 'disponibile', 'fanno',
        'reparto', 'reparti', 'specialità', 'ambulatorio',
        'esami', 'visite', 'prestazioni', 'cosa posso fare'
    ],
    'prenotazione': [
        'prenot', 'prenotazione', 'prenotare', 'appuntamento',
        'cup', 'come prenoto', 'voglio prenotare', 'devo prenotare',
        'fissare', 'riservare', 'numero verde'
    ],
    'contatti': [
        'telefono', 'numero', 'chiamare', 'contatto', 'contatti',
        'tel', 'cell', 'email', 'mail', 'pec', 'centralino'
    ],
    'posizione': [
        'dove', 'indirizzo', 'via', 'posizione', 'ubicazione',
        'come arrivo', 'come arrivare', 'strada', 'indicazioni',
        'mappa', 'maps', 'parcheggio', 'autobus', 'mezzi'
    ],
    'emergenza': [
        'emergenza', 'urgenza', 'urgente', 'pronto soccorso',
        'male', 'dolore', 'subito', 'grave', 'incidente',
        'codice rosso', 'codice giallo', '118'
    ],
    'documenti': [
        'documenti', 'documento', 'tessera', 'carta identità',
        'impegnativa', 'ricetta', 'cosa porto', 'cosa serve',
        'necessario', 'bisogno', 'requisiti'
    ],
    'costi': [
        'costo', 'costi', 'prezzo', 'quanto costa', 'pagare',
        'ticket', 'gratuito', 'gratis', 'esenzione', 'esente',
        'tariffa', 'pagamento'
    ],
    'analisi': [
        'analisi', 'sangue', 'urine', 'prelievi', 'prelievo',
        'laboratorio', 'esami del sangue', 'ematici', 'glicemia',
        'colesterolo', 'referti', 'risultati'
    ],
    'accessibilita': [
        'disabili', 'disabilità', 'carrozzina', 'sedia a rotelle',
        'ascensore', 'barriere', 'accessibile', 'accompagnatore',
        'parcheggio disabili', 'rampa'
    ]
}

# Pesi per ciascun intent (alcuni sono più importanti)
INTENT_WEIGHTS: Dict[str, float] = {
    'emergenza': 2.0,      # Priorità alta per emergenze
    'prenotazione': 1.5,   # Importante per l'utenza
    'orari': 1.3,          # Richiesta frequente
    'servizi': 1.2,        # Informazione base
    'analisi': 1.2,        # Servizio comune
    'contatti': 1.0,       # Standard
    'posizione': 1.0,      # Standard
    'documenti': 1.0,      # Standard
    'costi': 1.0,          # Standard
    'accessibilita': 1.1   # Importante per inclusività
}

def classify_intent(domanda: str, threshold: float = 0.3) -> str:
    """
    Classifica l'intent di una domanda.
    
    Args:
        domanda: domanda dell'utente
        threshold: soglia minima per considerare un intent
        
    Returns:
        Intent identificato o 'generale' se non specifico
    """
    if not domanda:
        return 'generale'
    
    domanda_lower = domanda.lower()
    scores = {}
    
    # Calcola score per ogni intent
    for intent, keywords in INTENT_KEYWORDS.items():
        score = 0.0
        matched_keywords = []
        
        for keyword in keywords:
            if keyword in domanda_lower:
                score += 1.0
                matched_keywords.append(keyword)
        
        # Normalizza per il numero di parole chiave
        if keywords:
            score = score / len(keywords)
        
        # Applica peso
        score *= INTENT_WEIGHTS.get(intent, 1.0)
        
        # Bonus per match multipli
        if len(matched_keywords) > 1:
            score *= 1.2
        
        scores[intent] = score
        
        if matched_keywords:
            logger.debug(f"Intent '{intent}' score: {score:.2f}, matched: {matched_keywords}")
    
    # Trova l'intent con score più alto
    if scores:
        best_intent = max(scores.items(), key=lambda x: x[1])
        if best_intent[1] >= threshold:
            logger.info(f"Intent classificato: '{best_intent[0]}' (score: {best_intent[1]:.2f})")
            return best_intent[0]
    
    # Se nessun intent supera la soglia, classifica come generale
    logger.info("Intent classificato come 'generale' (nessun match significativo)")
    return 'generale'

def get_intent_description(intent: str) -> str:
    """
    Restituisce una descrizione dell'intent.
    
    Args:
        intent: nome dell'intent
        
    Returns:
        Descrizione testuale dell'intent
    """
    descriptions = {
        'orari': 'Richiesta informazioni su orari di apertura',
        'servizi': 'Richiesta informazioni sui servizi disponibili',
        'prenotazione': 'Richiesta per prenotare visite o esami',
        'contatti': 'Richiesta numeri di telefono o contatti',
        'posizione': 'Richiesta indicazioni o posizione struttura',
        'emergenza': 'Possibile situazione di emergenza medica',
        'documenti': 'Richiesta informazioni sui documenti necessari',
        'costi': 'Richiesta informazioni su costi e ticket',
        'analisi': 'Richiesta informazioni su analisi e prelievi',
        'accessibilita': 'Richiesta informazioni su accessibilità per disabili',
        'generale': 'Richiesta generica di informazioni'
    }
    return descriptions.get(intent, 'Richiesta non classificata')

def is_emergency(domanda: str) -> bool:
    """
    Verifica se la domanda indica un'emergenza.
    
    Args:
        domanda: domanda dell'utente
        
    Returns:
        True se potrebbe essere un'emergenza
    """
    emergency_keywords = [
        'emergenza', 'urgente', 'urgenza', 'subito',
        'male forte', 'dolore forte', 'grave', 'sangue',
        'non respiro', 'infarto', 'ictus', 'incidente'
    ]
    
    domanda_lower = domanda.lower()
    for keyword in emergency_keywords:
        if keyword in domanda_lower:
            logger.warning(f"Possibile emergenza rilevata: '{keyword}' in domanda")
            return True
    
    return False

def extract_service_from_intent(domanda: str) -> Optional[str]:
    """
    Estrae il servizio specifico richiesto dalla domanda.
    
    Args:
        domanda: domanda dell'utente
        
    Returns:
        Nome del servizio se identificato
    """
    service_map = {
        'pronto soccorso': ['pronto soccorso', 'ps', 'emergenza'],
        'radiologia': ['radiologia', 'radiografia', 'rx', 'raggi', 'tac', 'risonanza'],
        'laboratorio': ['laboratorio', 'analisi', 'sangue', 'urine', 'prelievi'],
        'cardiologia': ['cardiologo', 'cardiologia', 'cuore', 'elettrocardiogramma', 'ecg'],
        'ortopedia': ['ortopedico', 'ortopedia', 'ossa', 'frattura', 'articolazioni'],
        'fisioterapia': ['fisioterapia', 'riabilitazione', 'recupero', 'fisioterapista'],
        'farmacia': ['farmacia', 'farmaci', 'medicine', 'ricetta'],
        'cup': ['cup', 'prenotazioni', 'prenotare']
    }
    
    domanda_lower = domanda.lower()
    
    for service, keywords in service_map.items():
        for keyword in keywords:
            if keyword in domanda_lower:
                logger.debug(f"Servizio estratto: {service}")
                return service
    
    return None