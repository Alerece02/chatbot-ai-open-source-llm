"""
Modulo per la gestione della memoria conversazionale.

Mantiene il contesto della conversazione, risolve riferimenti ambigui
e gestisce lo stato della sessione utente.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class ConversationMemory:
    """
    Gestisce la memoria della conversazione per mantenere il contesto.
    """
    
    def __init__(self, max_turns: int = 5):
        """
        Inizializza la memoria conversazionale.
        
        Args:
            max_turns: numero massimo di turni da mantenere in memoria
        """
        self.max_turns = max_turns
        self.history: List[Dict[str, str]] = []
        self.current_context = {
            'struttura': None,
            'servizio': None,
            'citta': None,
            'ultimo_aggiornamento': None
        }
        self.pronomi_ambigui = [
            "suo", "sua", "suoi", "sue",
            "lì", "là", "li",
            "questa", "questo", "questi", "queste",
            "quella", "quello", "quelli", "quelle",
            "stesso", "stessa", "stessi", "stesse"
        ]
        
    def extract_structure(self, text: str) -> Optional[str]:
        """
        Estrae il nome di una struttura dal testo.
        
        Args:
            text: testo da analizzare
            
        Returns:
            Nome della struttura se trovata, None altrimenti
        """
        # Pattern per identificare strutture sanitarie
        patterns = [
            r"(?:Ospedale|Centro|Ambulatorio|Poliambulatorio)\s+(?:di\s+)?[\w\s\-']+",
            r"(?:Ospedale|Centro)\s+[\w\s\-']+\s+(?:di|a)\s+[\w\s\-']+",
            r"[\w\s\-']+\s+(?:di|a)\s+(?:Malcesine|Marzana|Bussolengo|Bovolone|Villafranca|San Bonifacio)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                struttura = match.group(0).strip()
                # Normalizza il nome
                struttura = re.sub(r'\s+', ' ', struttura)
                logger.debug(f"Struttura estratta: {struttura}")
                return struttura
        
        return None
    
    def extract_service(self, text: str) -> Optional[str]:
        """
        Estrae il servizio menzionato dal testo.
        
        Args:
            text: testo da analizzare
            
        Returns:
            Servizio se trovato, None altrimenti
        """
        servizi_comuni = [
            "pronto soccorso", "radiologia", "laboratorio analisi",
            "centro prelievi", "fisioterapia", "riabilitazione",
            "cardiologia", "ortopedia", "pediatria", "geriatria",
            "breast unit", "farmacia", "cup", "prenotazioni"
        ]
        
        text_lower = text.lower()
        for servizio in servizi_comuni:
            if servizio in text_lower:
                logger.debug(f"Servizio estratto: {servizio}")
                return servizio
        
        return None
    
    def extract_city(self, text: str) -> Optional[str]:
        """
        Estrae la città menzionata dal testo.
        
        Args:
            text: testo da analizzare
            
        Returns:
            Città se trovata, None altrimenti
        """
        citta_ulss9 = [
            "Verona", "Malcesine", "Marzana", "Bussolengo",
            "San Bonifacio", "Villafranca", "Bovolone",
            "Villafranca di Verona"
        ]
        
        text_lower = text.lower()
        for citta in citta_ulss9:
            if citta.lower() in text_lower:
                logger.debug(f"Città estratta: {citta}")
                return citta
        
        return None
    
    def update_from_history(self, history: List[Dict]) -> None:
        """
        Aggiorna la memoria dalla storia della conversazione.
        
        Args:
            history: lista di dizionari con chiavi 'utente' e 'ai'
        """
        self.history = []
        
        for entry in history[-self.max_turns:]:
            user_msg = entry.get('utente', '')
            ai_msg = entry.get('ai', '')
            
            self.history.append({
                'user': user_msg,
                'ai': ai_msg,
                'timestamp': entry.get('timestamp', datetime.now().isoformat())
            })
            
            # Estrai entità dall'ultima risposta AI
            struttura = self.extract_structure(ai_msg)
            if struttura:
                self.current_context['struttura'] = struttura
            
            servizio = self.extract_service(ai_msg)
            if servizio:
                self.current_context['servizio'] = servizio
            
            citta = self.extract_city(ai_msg)
            if citta:
                self.current_context['citta'] = citta
        
        self.current_context['ultimo_aggiornamento'] = datetime.now().isoformat()
    
    def add_turn(self, user_msg: str, ai_msg: str) -> None:
        """
        Aggiunge un nuovo turno alla memoria.
        
        Args:
            user_msg: messaggio dell'utente
            ai_msg: risposta dell'AI
        """
        turn = {
            'user': user_msg,
            'ai': ai_msg,
            'timestamp': datetime.now().isoformat()
        }
        
        self.history.append(turn)
        
        # Mantieni solo gli ultimi N turni
        if len(self.history) > self.max_turns:
            self.history.pop(0)
        
        # Aggiorna contesto
        struttura = self.extract_structure(ai_msg)
        if struttura:
            self.current_context['struttura'] = struttura
        
        servizio = self.extract_service(ai_msg)
        if servizio:
            self.current_context['servizio'] = servizio
        
        citta = self.extract_city(ai_msg)
        if citta:
            self.current_context['citta'] = citta
        
        self.current_context['ultimo_aggiornamento'] = datetime.now().isoformat()
    
    def resolve_references(self, domanda: str) -> str:
        """
        Risolve riferimenti ambigui nella domanda.
        
        Args:
            domanda: domanda con possibili riferimenti ambigui
            
        Returns:
            Domanda con riferimenti risolti
        """
        domanda_lower = domanda.lower()
        
        # Controlla se ci sono pronomi ambigui
        has_ambiguous = any(pronome in domanda_lower for pronome in self.pronomi_ambigui)
        
        if not has_ambiguous:
            return domanda
        
        # Risolvi riferimenti basandoti sul contesto
        domanda_risolta = domanda
        
        if self.current_context['struttura']:
            # Sostituisci pronomi con la struttura
            patterns = [
                (r'\b(li|lì|là)\b', f"presso {self.current_context['struttura']}"),
                (r'\b(questo|questa)\b', self.current_context['struttura']),
                (r'\b(quello|quella)\b', self.current_context['struttura'])
            ]
            
            for pattern, replacement in patterns:
                if re.search(pattern, domanda_lower):
                    domanda_risolta = f"{domanda} (riferito a {self.current_context['struttura']})"
                    break
        
        logger.debug(f"Domanda risolta: {domanda} -> {domanda_risolta}")
        return domanda_risolta
    
    def get_dialog_context(self) -> str:
        """
        Genera il contesto del dialogo per il prompt.
        
        Returns:
            Stringa formattata con la storia della conversazione
        """
        if not self.history:
            return ""
        
        dialogo = []
        for turn in self.history[-3:]:  # Ultimi 3 turni
            dialogo.append(f"Utente: {turn['user']}")
            dialogo.append(f"Assistente: {turn['ai']}")
        
        return "\n".join(dialogo)
    
    def get_current_structure(self) -> Optional[str]:
        """
        Restituisce la struttura corrente nel contesto.
        
        Returns:
            Nome della struttura o None
        """
        return self.current_context.get('struttura')
    
    def get_context_summary(self) -> Dict:
        """
        Restituisce un riassunto del contesto corrente.
        
        Returns:
            Dizionario con il contesto attuale
        """
        return {
            'struttura_discussa': self.current_context.get('struttura'),
            'servizio_richiesto': self.current_context.get('servizio'),
            'citta_interesse': self.current_context.get('citta'),
            'turni_conversazione': len(self.history),
            'ultimo_aggiornamento': self.current_context.get('ultimo_aggiornamento')
        }
    
    def is_follow_up_question(self, domanda: str) -> bool:
        """
        Determina se la domanda è un follow-up.
        
        Args:
            domanda: domanda da analizzare
            
        Returns:
            True se è un follow-up, False altrimenti
        """
        domanda_lower = domanda.lower()
        
        # Indicatori di follow-up
        follow_up_indicators = [
            "e per", "invece", "e se", "ma",
            "altro", "ancora", "anche",
            "stesso", "stessa", "sempre"
        ]
        
        # Controlla pronomi ambigui
        if any(pronome in domanda_lower for pronome in self.pronomi_ambigui):
            return True
        
        # Controlla indicatori di follow-up
        if any(indicator in domanda_lower for indicator in follow_up_indicators):
            return True
        
        # Se la domanda è molto corta potrebbe essere un follow-up
        if len(domanda.split()) <= 3 and self.history:
            return True
        
        return False
    
    def clear(self) -> None:
        """Pulisce la memoria della conversazione."""
        self.history = []
        self.current_context = {
            'struttura': None,
            'servizio': None,
            'citta': None,
            'ultimo_aggiornamento': None
        }
        logger.info("Memoria conversazione pulita")