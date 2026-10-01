# Area 'ai-assistant' (Backend)

## API
- [api_ai_query](manual/api_ai_query.md) — Esporre via HTTP l'endpoint principale dell'assistente AI. Riceve un messaggio in linguaggio naturale, lo invia al provider LLM con il catalogo strumenti, esegue le tool_call in loop e restituisce la risposta contestual…
- [api_ai_status](manual/api_ai_status.md) — Esporre via HTTP un health check per verificare se l'assistente AI e' attivo, se **l'utente che chiede** lo puo' usare, e quanti strumenti sono registrati. Usato dal frontend per decidere se mostrare il bottone AI nella…

## Altri contenuti
- [ai_tool_registry](manual/ai_tool_registry.md) — Gestire il catalogo centralizzato degli strumenti AI disponibili per il function calling, con filtro per permessi utente e blacklist per installazione.
