"""
Modulo per la costruzione di prompt ottimizzati per il modello.

Genera prompt specifici in base all'intent e al contesto della conversazione,
ottimizzando per chiarezza e accessibilità delle risposte.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

def costruisci_prompt(
    contesto: str,
    dialogo: str,
    domanda: str,
    intent: str = "generale"
) -> str:
    """
    Costruisce un prompt ottimizzato per il modello linguistico.
    
    Args:
        contesto: informazioni sulle strutture rilevanti
        dialogo: storia della conversazione
        domanda: domanda corrente dell'utente
        intent: tipo di richiesta (orari, servizi, prenotazione, etc.)
        
    Returns:
        Prompt completo per il modello
    """
    
    # Istruzioni base
    base_instructions = """Sei un assistente virtuale dell'ULSS 9 Scaligera, gentile e paziente.
Il tuo compito è aiutare gli utenti, specialmente anziani, a trovare informazioni sui servizi sanitari.

REGOLE IMPORTANTI:
1. Usa un linguaggio SEMPLICE e CHIARO, evita termini medici complessi
2. Fornisci risposte BREVI ma COMPLETE (massimo 3-4 frasi)
3. Usa SOLO le informazioni fornite nelle strutture elencate
4. Se non hai l'informazione richiesta, suggerisci di chiamare il centralino ULSS9: 045 807 1111
5. Sii particolarmente paziente e gentile con gli anziani
6. Quando menzioni orari, sii molto preciso e chiaro
7. Per i numeri di telefono, ripetili in modo chiaro"""
    
    # Personalizzazione per intent
    intent_instructions = {
        "orari": """
FOCUS: L'utente chiede informazioni sugli ORARI.
- Specifica SEMPRE gli orari completi (giorni e ore)
- Se ci sono orari diversi per servizi specifici, menzionali
- Ricorda di specificare se alcuni servizi hanno orari particolari
- Usa formato chiaro: "Dal lunedì al venerdì dalle 8:00 alle 16:00"
""",
        "servizi": """
FOCUS: L'utente chiede quali SERVIZI sono disponibili.
- Elenca i servizi principali disponibili
- Se chiede un servizio specifico, conferma se è disponibile o no
- Menziona brevemente come accedere ai servizi
""",
        "prenotazione": """
FOCUS: L'utente vuole PRENOTARE una visita o esame.
- Spiega CHIARAMENTE come prenotare
- Fornisci il numero del CUP: 800 123 456
- Menziona gli orari del servizio prenotazioni
- Ricorda i documenti necessari (tessera sanitaria, impegnativa)
""",
        "posizione": """
FOCUS: L'utente chiede DOVE si trova la struttura.
- Fornisci l'indirizzo completo
- Se disponibile, menziona il link alla mappa
- Dai indicazioni su parcheggio se rilevante
""",
        "emergenza": """
FOCUS: Possibile situazione di EMERGENZA.
- Se è un'emergenza, ricorda SUBITO di chiamare il 118
- Fornisci info sul pronto soccorso più vicino
- Spiega brevemente i codici colore del pronto soccorso
""",
        "contatti": """
FOCUS: L'utente cerca CONTATTI telefonici.
- Fornisci i numeri di telefono in modo chiaro
- Ripeti i numeri importanti
- Specifica gli orari in cui risponde il centralino
"""
    }
    
    # Esempi di risposte per intent
    response_examples = {
        "orari": """
Esempio di risposta per orari:
"L'Ospedale di Bussolengo è aperto dal lunedì al sabato dalle 7:00 alle 19:00, e la domenica dalle 7:00 alle 12:30. Il pronto soccorso invece è sempre aperto, 24 ore su 24. Posso aiutarla con altro?"
""",
        "servizi": """
Esempio di risposta per servizi:
"L'Ospedale di Bussolengo offre molti servizi tra cui: Pronto Soccorso, Cardiologia, Laboratorio Analisi, Radiologia e Geriatria. Per prenotare una visita può chiamare il CUP al numero 800 123 456."
""",
        "prenotazione": """
Esempio di risposta per prenotazioni:
"Per prenotare una visita può chiamare il CUP al numero verde 800 123 456, attivo dal lunedì al venerdì dalle 8:00 alle 18:00. Tenga pronta la tessera sanitaria e l'impegnativa del medico."
"""
    }
    
    # Costruisci il prompt completo
    prompt_parts = [
        base_instructions,
        intent_instructions.get(intent, ""),
        response_examples.get(intent, ""),
        f"\nINFORMAZIONI STRUTTURE DISPONIBILI:\n{contesto}\n"
    ]
    
    # Aggiungi dialogo se presente
    if dialogo:
        prompt_parts.append(f"CONVERSAZIONE PRECEDENTE:\n{dialogo}\n")
    
    # Aggiungi la domanda corrente
    prompt_parts.append(f"DOMANDA UTENTE: {domanda}")
    
    # Aggiungi reminder finale
    prompt_parts.append("""
RICORDA: Rispondi in modo semplice, chiaro e gentile. Massimo 3-4 frasi.
Se non hai l'informazione, suggerisci di chiamare il centralino: 045 807 1111.

LA TUA RISPOSTA:""")
    
    prompt = "\n".join(prompt_parts)
    
    logger.debug(f"Prompt costruito per intent '{intent}', lunghezza: {len(prompt)} caratteri")
    
    return prompt

def costruisci_prompt_faq(domanda: str, faq_risposta: str) -> str:
    """
    Costruisce un prompt per riformulare una risposta FAQ.
    
    Args:
        domanda: domanda dell'utente
        faq_risposta: risposta trovata nelle FAQ
        
    Returns:
        Prompt per riformulare la risposta
    """
    return f"""Riformula questa risposta in modo più conversazionale e amichevole, 
mantenendo tutte le informazioni importanti ma usando un tono gentile e paziente:

Domanda utente: {domanda}
Risposta da riformulare: {faq_risposta}

Risposta riformulata (massimo 3 frasi, tono gentile):"""

def costruisci_prompt_chiarimento(contesto_precedente: str) -> str:
    """
    Costruisce un prompt per chiedere chiarimenti.
    
    Args:
        contesto_precedente: contesto della conversazione
        
    Returns:
        Prompt per generare una richiesta di chiarimento
    """
    return f"""Basandoti sul contesto, genera una domanda di chiarimento gentile e specifica.

Contesto: {contesto_precedente}

Genera una domanda di chiarimento breve e cortese (massimo 1-2 frasi):"""