# 🏥 Assistente Virtuale Sanitario

## 📋 Descrizione Progetto

Assistente virtuale basato su AI per facilitare l'accesso alle informazioni.

### 🎯 Obiettivi
- **Accessibilità**: Rendere le informazioni sanitarie facilmente accessibili, specialmente per anziani
- **Privacy**: Tutto rimane on-premise, nessun dato esce dall'infrastruttura
- **Costi Zero**: Utilizzo di tecnologie open source (Ollama/Mistral)
- **Scalabilità**: Architettura modulare facilmente estendibile

## 🚀 Quick Start

### Prerequisiti
- Docker e Docker Compose installati
- Ollama installato sulla macchina host
- 8GB RAM minimo consigliato

### Installazione


1. **Installa e avvia Ollama** (sulla macchina host, NON nel container)
```bash
# Su macOS
brew install ollama
ollama serve

# Su Linux
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve
```

2. **Scarica il modello Mistral**
```bash
ollama pull mistral
```

3. **Avvia i container Docker**
```bash
docker-compose up --build
```


## 📁 Struttura Progetto

```
chatbot/
├── backend/
│   ├── main.py                 # Entry point FastAPI
│   ├── routes/
│   │   └── chatbot.py          # Endpoint principale
│   ├── utils/
│   │   ├── db_loader.py        # Caricamento dati
│   │   ├── memory.py           # Gestione memoria conversazione
│   │   ├── prompt_builder.py   # Costruzione prompt
│   │   ├── intent_classifier.py # Classificazione intent
│   │   ├── response_cache.py   # Cache risposte
│   │   ├── analytics.py        # Sistema analytics
│   │   └── suggestions.py      # Generazione suggerimenti
│   ├── dati_sanitari.json      # Database strutture
│   ├── requirements.txt        # Dipendenze Python
│   └── Dockerfile
├── frontend/
│   ├── index.html              # Homepage
│   ├── chatbot.html           # Widget chat
│   ├── app.js                 # Logica frontend
│   ├── style.css              # Stili personalizzati
│   ├── nginx.conf             # Config nginx
│   └── Dockerfile
├── analytics/                  # Directory per log analytics
├── docker-compose.yml         # Orchestrazione container
└── README.md
```

## 🔧 Architettura Tecnica

### Backend (FastAPI + Ollama)
- **FastAPI**: Framework web moderno e veloce
- **Ollama + Mistral**: LLM locale per privacy garantita
- **Intent Classification**: Identifica il tipo di richiesta
- **Context Memory**: Mantiene il contesto della conversazione
- **Response Cache**: Ottimizza performance per domande frequenti
- **Fuzzy Search**: Trova strutture rilevanti

### Frontend (HTML + Tailwind CSS + Vanilla JS)
- **Responsive Design**: Ottimizzato per tutti i dispositivi
- **Accessibility First**: Font grandi, alto contrasto, navigazione tastiera
- **Voice I/O**: Input e output vocale per accessibilità
- **Real-time Feedback**: Indicatori di stato e suggerimenti

## 🌟 Funzionalità Principali

### Per gli Utenti
- ✅ Ricerca informazioni su ospedali e ambulatori
- ✅ Orari di apertura e servizi disponibili
- ✅ Informazioni per prenotazioni
- ✅ Numeri di telefono e contatti
- ✅ Indicazioni stradali e mappe
- ✅ Input/Output vocale
- ✅ Suggerimenti domande follow-up
- ✅ Interfaccia accessibile per anziani

### Per gli Amministratori
- 📊 Analytics delle query
- 🔍 Classificazione intent automatica
- 💾 Cache intelligente
- 📈 Metriche performance
- 🔐 Privacy garantita (tutto on-premise)

## 📊 Analytics e Monitoraggio

Il sistema raccoglie metriche anonime per migliorare il servizio:

- **Query più frequenti**: Identifica le necessità degli utenti
- **Tempi di risposta**: Monitora le performance
- **Intent distribution**: Capisce i tipi di richieste
- **Success rate**: Valuta l'efficacia delle risposte

Accedi alle statistiche: `GET http://localhost:8000/api/stats`

## 🔐 Privacy e Sicurezza

- **Nessuna API esterna**: Tutto gira localmente
- **Dati anonimi**: Nessun dato personale salvato
- **On-premise**: Deployabile su infrastruttura
- **Open Source**: Codice ispezionabile e verificabile


### Tecnologie utilizzate
- [FastAPI](https://fastapi.tiangolo.com/)
- [Ollama](https://ollama.ai/)
- [Mistral AI](https://mistral.ai/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Docker](https://www.docker.com/)
