// Stato globale dell'applicazione
let storicoDomande = [];
let voiceEnabled = false;
let chatFontSize = 14;
let isListening = false;
let sessionId = generateSessionId();

// Genera ID sessione univoco
function generateSessionId() {
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Mostra/Nascondi Chat
function mostraChat() {
  const modal = document.getElementById('chatModal');
  modal.classList.remove('hidden');
  modal.classList.add('chat-animation');
  document.getElementById('domanda').focus();
  
  // Nascondi launcher
  document.getElementById('chatbot-launcher').style.display = 'none';
}

function nascondiChat() {
  document.getElementById('chatModal').classList.add('hidden');
  document.getElementById('chatbot-launcher').style.display = 'block';
}

// Funzione principale per inviare domande
async function chiedi() {
  const domandaInput = document.getElementById("domanda");
  const domanda = domandaInput.value.trim();
  
  if (!domanda) {
    showNotification("Per favore, scrivi una domanda", "warning");
    return;
  }

  const storicoDiv = document.getElementById("storico");
  
  // Nascondi suggerimenti durante la conversazione
  document.getElementById('suggestedQuestions').style.display = 'none';

  // Mostra messaggio utente
  const userMsg = document.createElement("div");
  userMsg.className = "self-end bg-blue-600 text-white px-4 py-2 rounded-xl rounded-tr-none max-w-[85%] break-words message-user";
  userMsg.innerText = domanda;
  storicoDiv.appendChild(userMsg);

  // Mostra typing indicator
  const typingDiv = createTypingIndicator();
  storicoDiv.appendChild(typingDiv);
  storicoDiv.scrollTop = storicoDiv.scrollHeight;

  // Mostra status bar
  showStatus("Sto elaborando la tua richiesta...");

  try {
    const startTime = Date.now();
    
    const response = await fetch("http://localhost:8000/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: domanda,
        history: storicoDomande,
        session_id: sessionId
      })
    });

    if (!response.ok) {
      throw new Error(`Errore server: ${response.status}`);
    }

    const data = await response.json();
    const responseTime = (Date.now() - startTime) / 1000;
    
    // Rimuovi typing indicator
    typingDiv.remove();
    hideStatus();

    // Mostra risposta AI
    const aiMsg = createAIMessage(data);
    storicoDiv.appendChild(aiMsg);
    
    // Mostra suggerimenti se presenti
    if (data.suggerimenti && data.suggerimenti.length > 0) {
      showSuggestions(data.suggerimenti);
    }
    
    // Mostra metriche (solo in dev/demo)
    if (data.tempo_risposta) {
      showMetrics(data);
    }
    
    // Scroll to bottom
    storicoDiv.scrollTop = storicoDiv.scrollHeight;

    // Salva nella storia
    storicoDomande.push({ 
      utente: domanda, 
      ai: data.risposta,
      timestamp: new Date().toISOString()
    });
    
    // Limita storia a 10 elementi
    if (storicoDomande.length > 10) {
      storicoDomande.shift();
    }

    // Leggi risposta se voce attiva
    if (voiceEnabled) {
      leggiVoce(data.risposta);
    }

    // Pulisci input
    domandaInput.value = "";
    
    // Log analytics
    console.log(`Intent: ${data.intent}, Tempo: ${responseTime}s, Cached: ${data.cached}`);

  } catch (err) {
    console.error("Errore:", err);
    typingDiv.remove();
    hideStatus();
    
    const errorMsg = document.createElement("div");
    errorMsg.className = "self-start bg-red-100 text-red-800 px-4 py-2 rounded-xl max-w-[85%]";
    errorMsg.innerHTML = `
      <p class="font-semibold">⚠️ Errore di connessione</p>
      <p class="text-sm mt-1">Non riesco a contattare il server. Riprova tra poco o chiama il centralino: 045 807 1111</p>
    `;
    storicoDiv.appendChild(errorMsg);
    storicoDiv.scrollTop = storicoDiv.scrollHeight;
  }
}

// Crea messaggio AI con formattazione
function createAIMessage(data) {
  const aiMsg = document.createElement("div");
  aiMsg.className = "self-start bg-white text-gray-800 px-4 py-3 rounded-xl rounded-tl-none shadow-sm max-w-[85%] message-ai";
  
  // Formatta la risposta con link e evidenziazioni
  let formattedResponse = formatResponse(data.risposta);
  
  // Aggiungi intent badge se disponibile
  if (data.intent && data.intent !== 'generale') {
    formattedResponse = `<span class="inline-block px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full mb-2">${getIntentLabel(data.intent)}</span><br>` + formattedResponse;
  }
  
  aiMsg.innerHTML = formattedResponse;
  
  // Aggiungi bottoni di feedback
  const feedbackDiv = document.createElement("div");
  feedbackDiv.className = "mt-2 flex gap-2";
  feedbackDiv.innerHTML = `
    <button onclick="sendFeedback(true)" class="text-xs text-gray-500 hover:text-green-600">👍 Utile</button>
    <button onclick="sendFeedback(false)" class="text-xs text-gray-500 hover:text-red-600">👎 Non utile</button>
  `;
  aiMsg.appendChild(feedbackDiv);
  
  return aiMsg;
}

// Formatta la risposta con link e evidenziazioni
function formatResponse(text) {
  // Converti URL in link cliccabili
  text = linkify(text);
  
  // Evidenzia numeri di telefono
  text = text.replace(/(\d{3,4}\s?\d{3,4}\s?\d{3,4})/g, '<span class="font-semibold text-blue-600">$1</span>');
  
  // Evidenzia orari
  text = text.replace(/(\d{1,2}:\d{2})/g, '<span class="font-semibold">$1</span>');
  
  // Aggiungi emoji per parole chiave
  text = text.replace(/pronto soccorso/gi, '🚨 Pronto Soccorso');
  text = text.replace(/CUP/g, '📞 CUP');
  
  return text;
}

// Converte URL in link
function linkify(text) {
  const urlRegex = /(https?:\/\/[^\s<>]+)/g;
  return text.replace(urlRegex, (url) => {
    const cleanUrl = url.replace(/[.,!?)]*$/, '');
    return `<a href="${cleanUrl}" target="_blank" class="text-blue-600 underline hover:text-blue-700">${cleanUrl}</a>`;
  });
}

// Mostra suggerimenti
function showSuggestions(suggerimenti) {
  const container = document.createElement("div");
  container.className = "mt-3 p-3 bg-gray-50 rounded-lg";
  container.innerHTML = '<p class="text-xs text-gray-600 mb-2">Potrebbe interessarti anche:</p>';
  
  const buttonsDiv = document.createElement("div");
  buttonsDiv.className = "flex flex-wrap gap-2";
  
  suggerimenti.forEach(sugg => {
    const btn = document.createElement("button");
    btn.className = "text-xs bg-white px-3 py-1 rounded-full border border-gray-200 hover:bg-blue-50 hover:border-blue-300 transition";
    btn.textContent = sugg;
    btn.onclick = () => quickAsk(sugg);
    buttonsDiv.appendChild(btn);
  });
  
  container.appendChild(buttonsDiv);
  document.getElementById("storico").appendChild(container);
}

// Typing indicator
function createTypingIndicator() {
  const div = document.createElement("div");
  div.className = "self-start flex items-center gap-2 bg-gray-100 px-4 py-3 rounded-xl rounded-tl-none";
  div.innerHTML = `
    <div class="typing-indicator">
      <span></span>
      <span></span>
      <span></span>
    </div>
    <span class="text-sm text-gray-500">Sto pensando...</span>
  `;
  return div;
}

// Quick ask function
function quickAsk(question) {
  document.getElementById("domanda").value = question;
  chiedi();
}

// Voice Recognition
function attivaVoce() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  
  if (!SpeechRecognition) {
    showNotification("Il tuo browser non supporta il riconoscimento vocale", "error");
    return;
  }

  if (isListening) return;

  const recognition = new SpeechRecognition();
  recognition.lang = 'it-IT';
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  const feedbackDiv = document.getElementById('voiceFeedback');
  feedbackDiv.classList.remove('hidden');
  isListening = true;

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    document.getElementById("domanda").value = transcript;
    
    if (event.results[0].isFinal) {
      feedbackDiv.classList.add('hidden');
      isListening = false;
    }
  };

  recognition.onerror = (event) => {
    feedbackDiv.classList.add('hidden');
    isListening = false;
    showNotification("Errore nel riconoscimento vocale: " + event.error, "error");
  };

  recognition.onend = () => {
    feedbackDiv.classList.add('hidden');
    isListening = false;
  };

  recognition.start();
}

// Text to Speech
let vociDisponibili = [];
speechSynthesis.onvoiceschanged = () => {
  vociDisponibili = speechSynthesis.getVoices();
};

function leggiVoce(testo) {
  if (!voiceEnabled) return;
  
  // Cancella eventuali letture in corso
  speechSynthesis.cancel();
  
  const utterance = new SpeechSynthesisUtterance(testo);
  utterance.lang = 'it-IT';
  utterance.rate = 0.9; // Velocità leggermente ridotta per anziani
  utterance.pitch = 1.0;
  utterance.volume = 1.0;

  // Cerca voce italiana
  const voceItaliana = vociDisponibili.find(v => v.lang.startsWith('it'));
  if (voceItaliana) {
    utterance.voice = voceItaliana;
  }

  speechSynthesis.speak(utterance);
}

// Toggle voice output
function toggleVoiceOutput() {
  voiceEnabled = !voiceEnabled;
  const icon = document.getElementById('voiceIcon');
  icon.textContent = voiceEnabled ? '🔊' : '🔇';
  
  if (voiceEnabled) {
    showNotification("Lettura vocale attivata", "success");
  } else {
    speechSynthesis.cancel();
    showNotification("Lettura vocale disattivata", "info");
  }
}

// Font size controls
function aumentaFontChat() {
  if (chatFontSize < 20) {
    chatFontSize += 2;
    document.getElementById('storico').style.fontSize = chatFontSize + 'px';
    document.getElementById('domanda').style.fontSize = chatFontSize + 'px';
  }
}

function diminuisciFontChat() {
  if (chatFontSize > 10) {
    chatFontSize -= 2;
    document.getElementById('storico').style.fontSize = chatFontSize + 'px';
    document.getElementById('domanda').style.fontSize = chatFontSize + 'px';
  }
}

// Feedback system
async function sendFeedback(positive) {
  const emoji = positive ? '👍' : '👎';
  console.log(`Feedback: ${emoji}`);
  
  // Qui potresti inviare il feedback al server
  showNotification(positive ? "Grazie per il feedback positivo!" : "Ci dispiace, miglioreremo!", "info");
}

// Status bar
function showStatus(message) {
  const statusBar = document.getElementById('statusBar');
  const statusText = document.getElementById('statusText');
  statusText.textContent = message;
  statusBar.classList.remove('hidden');
}

function hideStatus() {
  document.getElementById('statusBar').classList.add('hidden');
}

// Notifications
function showNotification(message, type = "info") {
  const colors = {
    success: "bg-green-100 text-green-800",
    error: "bg-red-100 text-red-800",
    warning: "bg-yellow-100 text-yellow-800",
    info: "bg-blue-100 text-blue-800"
  };
  
  const notification = document.createElement("div");
  notification.className = `fixed top-4 right-4 px-4 py-2 rounded-lg shadow-lg ${colors[type]} z-50 notification-fade`;
  notification.textContent = message;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.remove();
  }, 3000);
}

// Metrics display (for demo/debugging)
function showMetrics(data) {
  if (!data.tempo_risposta) return;
  
  const metricsDiv = document.createElement("div");
  metricsDiv.className = "text-xs text-gray-400 mt-2 px-4";
  metricsDiv.innerHTML = `
    <details>
      <summary class="cursor-pointer hover:text-gray-600">📊 Metriche</summary>
      <div class="mt-1 pl-4">
        <p>⏱ Tempo risposta: ${data.tempo_risposta.toFixed(2)}s</p>
        <p>🎯 Intent: ${data.intent}</p>
        <p>💾 Cache: ${data.cached ? 'Sì' : 'No'}</p>
      </div>
    </details>
  `;
  
  document.getElementById("storico").appendChild(metricsDiv);
}

// Get intent label
function getIntentLabel(intent) {
  const labels = {
    'orari': '🕐 Orari',
    'servizi': '🏥 Servizi',
    'prenotazione': '📅 Prenotazione',
    'contatti': '📞 Contatti',
    'posizione': '📍 Posizione',
    'emergenza': '🚨 Emergenza',
    'analisi': '💉 Analisi',
    'documenti': '📄 Documenti',
    'costi': '💰 Costi',
    'accessibilita': '♿ Accessibilità'
  };
  
  return labels[intent] || intent;
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
  // Set initial font size
  document.getElementById('storico').style.fontSize = chatFontSize + 'px';
  
  // Load voices
  if (speechSynthesis.onvoiceschanged !== undefined) {
    speechSynthesis.onvoiceschanged = () => {
      vociDisponibili = speechSynthesis.getVoices();
    };
  }
});

// CSS for animations
const style = document.createElement('style');
style.textContent = `
  .typing-indicator {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  
  .typing-indicator span {
    display: block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #6b7280;
    animation: typing 1.4s infinite;
  }
  
  .typing-indicator span:nth-child(2) {
    animation-delay: 0.2s;
  }
  
  .typing-indicator span:nth-child(3) {
    animation-delay: 0.4s;
  }
  
  @keyframes typing {
    0%, 60%, 100% {
      transform: translateY(0);
      opacity: 0.5;
    }
    30% {
      transform: translateY(-10px);
      opacity: 1;
    }
  }
  
  .notification-fade {
    animation: fadeInOut 3s ease-in-out;
  }
  
  @keyframes fadeInOut {
    0% { opacity: 0; transform: translateY(-20px); }
    20% { opacity: 1; transform: translateY(0); }
    80% { opacity: 1; transform: translateY(0); }
    100% { opacity: 0; transform: translateY(-20px); }
  }
`;
document.head.appendChild(style);