# Area 'ai-assistant' (Backend)

## API
- [api_ai_query](manual/api_ai_query.md) — Endpoint principale per query AI in linguaggio naturale con function calling. POST riceve messaggio, chiama provider LLM, esegue tool, restituisce risposta contestuale.
- [api_ai_status](manual/api_ai_status.md) — Health check per verificare disponibilita' AI e numero strumenti registrati. GET senza query DB.

## Architettura
- [ai_tool_registry](manual/ai_tool_registry.md) — Registro centralizzato strumenti AI con filtro permessi utente e blacklist installazione. Catalogo dei 6 tool disponibili (Fase 1 + Fase 3).

## Note

- L'intera app e' condizionale: caricata solo se `AI_ENABLED=True` in settings.
- Nessun anello interno (core, config, anagrafiche, pratiche) dipende da `ai_assistant`.
- Gli strumenti AI wrappano service/repository esistenti — nessun SQL diretto.
- Provider AI configurabile: Anthropic, Mistral, mock (test).
