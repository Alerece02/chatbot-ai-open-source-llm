"""
Modulo per analytics e monitoraggio del chatbot.

Raccoglie metriche sulle performance e l'utilizzo per ottimizzazioni future.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

class Analytics:
    """
    Sistema di analytics per il chatbot.
    """
    
    def __init__(self, analytics_file: str = "analytics/usage.json"):
        """
        Inizializza il sistema di analytics.
        
        Args:
            analytics_file: percorso del file per salvare le analytics
        """
        self.analytics_file = Path(analytics_file)
        self.analytics_file.parent.mkdir(exist_ok=True)
        
        self.current_session = {
            'queries': [],
            'start_time': datetime.now().isoformat(),
            'intent_counts': Counter(),
            'response_times': [],
            'error_count': 0
        }
        
        self.historical_data = self._load_historical()
    
    def log_query(
        self,
        question: str,
        intent: str,
        response_time: float,
        success: bool = True,
        session_id: str = "default"
    ) -> None:
        """
        Registra una query e le sue metriche.
        
        Args:
            question: domanda dell'utente
            intent: intent classificato
            response_time: tempo di risposta in secondi
            success: se la risposta è stata generata con successo
            session_id: ID della sessione utente
        """
        query_data = {
            'timestamp': datetime.now().isoformat(),
            'question': question[:100],  # Limita lunghezza per privacy
            'intent': intent,
            'response_time': response_time,
            'success': success,
            'session_id': session_id
        }
        
        self.current_session['queries'].append(query_data)
        self.current_session['intent_counts'][intent] += 1
        self.current_session['response_times'].append(response_time)
        
        if not success:
            self.current_session['error_count'] += 1
        
        # Salva periodicamente
        if len(self.current_session['queries']) % 10 == 0:
            self._save_current_session()
        
        logger.debug(f"Query logged - Intent: {intent}, Time: {response_time:.2f}s, Success: {success}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Calcola e restituisce le statistiche.
        
        Returns:
            Dizionario con statistiche aggregate
        """
        # Stats della sessione corrente
        current_queries = len(self.current_session['queries'])
        avg_response_time = (
            sum(self.current_session['response_times']) / current_queries
            if current_queries > 0 else 0
        )
        
        # Stats storiche
        total_historical = sum(
            len(session.get('queries', [])) 
            for session in self.historical_data.get('sessions', [])
        )
        
        # Top intents
        intent_counts = self.current_session['intent_counts']
        top_intents = intent_counts.most_common(5)
        
        # Calcola trend orari
        hourly_distribution = self._calculate_hourly_distribution()
        
        # Calcola success rate
        success_count = sum(
            1 for q in self.current_session['queries'] 
            if q.get('success', True)
        )
        success_rate = (success_count / current_queries * 100) if current_queries > 0 else 100
        
        return {
            'current_session': {
                'total_queries': current_queries,
                'avg_response_time': f"{avg_response_time:.2f}s",
                'success_rate': f"{success_rate:.1f}%",
                'error_count': self.current_session['error_count'],
                'session_duration': self._get_session_duration(),
                'top_intents': [
                    {'intent': intent, 'count': count} 
                    for intent, count in top_intents
                ]
            },
            'historical': {
                'total_queries_all_time': total_historical + current_queries,
                'total_sessions': len(self.historical_data.get('sessions', [])) + 1
            },
            'insights': {
                'peak_hours': self._get_peak_hours(hourly_distribution),
                'common_questions': self._get_common_questions(),
                'performance_trends': self._get_performance_trends()
            }
        }
    
    def _calculate_hourly_distribution(self) -> Dict[int, int]:
        """Calcola la distribuzione oraria delle query."""
        hourly_counts = defaultdict(int)
        
        for query in self.current_session['queries']:
            timestamp = datetime.fromisoformat(query['timestamp'])
            hourly_counts[timestamp.hour] += 1
        
        return dict(hourly_counts)
    
    def _get_peak_hours(self, hourly_dist: Dict[int, int]) -> List[str]:
        """Identifica le ore di punta."""
        if not hourly_dist:
            return []
        
        sorted_hours = sorted(hourly_dist.items(), key=lambda x: x[1], reverse=True)
        peak_hours = sorted_hours[:3]
        
        return [f"{hour:02d}:00-{hour+1:02d}:00" for hour, _ in peak_hours]
    
    def _get_common_questions(self) -> List[str]:
        """Identifica le domande più comuni."""
        question_patterns = Counter()
        
        for query in self.current_session['queries']:
            # Semplifica la domanda per trovare pattern
            question = query['question'].lower()
            # Rimuovi dettagli specifici per trovare pattern
            simplified = self._simplify_question(question)
            question_patterns[simplified] += 1
        
        return [pattern for pattern, _ in question_patterns.most_common(5)]
    
    def _simplify_question(self, question: str) -> str:
        """Semplifica una domanda per trovare pattern comuni."""
        # Rimuovi nomi di città e strutture specifiche
        cities = ['verona', 'malcesine', 'bussolengo', 'villafranca', 'bovolone', 'marzana', 'san bonifacio']
        for city in cities:
            question = question.replace(city, '[CITTÀ]')
        
        # Rimuovi orari specifici
        import re
        question = re.sub(r'\d{1,2}:\d{2}', '[ORA]', question)
        question = re.sub(r'\d{1,2}-\d{1,2}', '[ORARIO]', question)
        
        return question.strip()
    
    def _get_performance_trends(self) -> Dict[str, str]:
        """Analizza i trend delle performance."""
        if not self.current_session['response_times']:
            return {'status': 'Dati insufficienti'}
        
        times = self.current_session['response_times']
        recent_avg = sum(times[-10:]) / len(times[-10:]) if len(times) >= 10 else sum(times) / len(times)
        overall_avg = sum(times) / len(times)
        
        trend = 'stabile'
        if recent_avg < overall_avg * 0.8:
            trend = 'miglioramento'
        elif recent_avg > overall_avg * 1.2:
            trend = 'peggioramento'
        
        return {
            'trend': trend,
            'recent_avg': f"{recent_avg:.2f}s",
            'overall_avg': f"{overall_avg:.2f}s"
        }
    
    def _get_session_duration(self) -> str:
        """Calcola la durata della sessione corrente."""
        start = datetime.fromisoformat(self.current_session['start_time'])
        duration = datetime.now() - start
        
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def _save_current_session(self) -> None:
        """Salva la sessione corrente su file."""
        try:
            data = {
                'sessions': self.historical_data.get('sessions', []),
                'current_session': self.current_session,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.analytics_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Analytics salvate: {len(self.current_session['queries'])} queries")
            
        except Exception as e:
            logger.error(f"Errore nel salvataggio analytics: {e}")
    
    def _load_historical(self) -> Dict[str, Any]:
        """Carica dati storici se disponibili."""
        if not self.analytics_file.exists():
            return {'sessions': []}
        
        try:
            with open(self.analytics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.error(f"Errore nel caricamento analytics: {e}")
            return {'sessions': []}
    
    def close_session(self) -> None:
        """Chiude la sessione corrente e la salva come storica."""
        if self.current_session['queries']:
            self._save_current_session()
            
            # Sposta sessione corrente nello storico
            self.historical_data['sessions'].append(self.current_session)
            
            # Mantieni solo ultime 100 sessioni
            if len(self.historical_data['sessions']) > 100:
                self.historical_data['sessions'] = self.historical_data['sessions'][-100:]
            
            # Reset sessione corrente
            self.current_session = {
                'queries': [],
                'start_time': datetime.now().isoformat(),
                'intent_counts': Counter(),
                'response_times': [],
                'error_count': 0
            }
            
            logger.info("Sessione analytics chiusa e salvata")