from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.chatbot import router as chatbot_router
import logging

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="ULSS9 Chatbot Sanitario",
    description="Assistente virtuale per informazioni sanitarie ULSS9 Scaligera",
    version="1.0.0"
)

# Middleware CORS per permettere richieste dal frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione, specificare domini esatti
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include le route del chatbot
app.include_router(chatbot_router, prefix="/api", tags=["chatbot"])

# Health check endpoint
@app.get("/health")
async def health_check():
    """Endpoint per verificare che il servizio sia attivo"""
    return {
        "status": "healthy",
        "service": "ULSS9 Chatbot Backend",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """Endpoint root con informazioni base"""
    return {
        "message": "Benvenuto nel backend del Chatbot ULSS9",
        "endpoints": {
            "chatbot": "/api/ask",
            "health": "/health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)