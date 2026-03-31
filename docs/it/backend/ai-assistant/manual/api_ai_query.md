# API ai_query (Django)

## Scopo

Esporre via HTTP l'endpoint principale dell'assistente AI. Riceve un messaggio in linguaggio naturale, lo invia al provider LLM con il catalogo strumenti, esegue le tool_call in loop e restituisce la risposta contestuale.

## Contesto

POST delega a `ai_assistant_service.query()` che orchestra il flusso completo: validazione input, costruzione system prompt, comunicazione con il provider AI, esecuzione tool_call (loop fino a risposta testuale o limite iterazioni), estrazione azioni di navigazione e logging in `dbops.ai_query_log`. L'endpoint usa `handle_post_json` come tutti gli endpoint POST di ZeroERP.

## Input

### POST — Query AI

- Metodo: `POST`
- Path canonico: `/api/v1/ai-assistant/query/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Header: `Content-Type: application/json`
- Body:
  - `message` (string, obbligatorio) — messaggio in linguaggio naturale, max 2000 caratteri
  - `conversation_id` (string UUID, opzionale) — ID conversazione esistente per mantenere il contesto intra-sessione; se omesso, viene creata una nuova conversazione

## Output

### POST 200:

```json
{
  "data": {
    "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "response": "Ho trovato 4 pratiche aperte di Acea. La piu' urgente e' la pratica PRA-2026-0042.",
    "tools_used": ["cerca_pratiche"],
    "actions": [
      {
        "type": "navigate",
        "label": "Apri PRA-2026-0042",
        "route": { "name": "pratiche-dettaglio", "params": { "id": 2341 } }
      }
    ],
    "has_more": false
  },
  "meta": {
    "request_id": "req-uuid"
  }
}
```

| Campo | Tipo | Descrizione |
|---|---|---|
| `conversation_id` | UUID | ID conversazione (nuovo o riusato) |
| `response` | string | Risposta testuale dell'LLM in linguaggio naturale |
| `tools_used` | string[] | Nomi degli strumenti invocati durante la query |
| `actions` | Action[] | Azioni suggerite (navigazione verso entita' trovate) |
| `actions[].type` | string | Tipo azione: `navigate` |
| `actions[].label` | string | Testo del link, gia' localizzato |
| `actions[].route` | object | Oggetto compatibile con Vue Router `router.push()` |
| `has_more` | boolean | `true` se il limite iterazioni tool e' stato raggiunto (risposta parziale) |

### Errori:

- `400` — `E_AI_QUERY_EMPTY`: messaggio vuoto
- `400` — `E_AI_QUERY_TOO_LONG`: messaggio oltre 2000 caratteri
- `401` — JWT mancante o non valido
- `501` — `E_AI_DISABLED`: funzionalita' AI non attiva (`AI_ENABLED=false`)
- `502` — `E_AI_PROVIDER_ERROR`: errore comunicazione con il provider AI esterno

## Regole

- Il messaggio non puo' essere vuoto ne' superare 2000 caratteri.
- Il catalogo strumenti e' filtrato per permessi dell'utente autenticato: se l'operatore non ha accesso all'area `pratiche`, il tool `cerca_pratiche` non e' disponibile.
- Il loop tool_call ha un limite di 5 iterazioni. Al superamento restituisce risposta parziale con `has_more: true`.
- La conversazione in-memory ha un TTL di 15 minuti (configurabile via `AI_CONVERSATION_TTL`). Dopo la scadenza, il `conversation_id` non e' piu' valido e viene creata una nuova conversazione.
- Il system prompt non contiene mai dati dal database — solo vocabolario e regole operative. I dati arrivano come `tool_result` e sono trattati dall'LLM come dati, non istruzioni (protezione prompt injection).
- Ogni interazione viene loggata in `dbops.ai_query_log` con `request_id`, strumenti chiamati, token consumati e durata. Il logging e' best-effort: un errore di log non blocca la risposta.
- L'endpoint richiede `area_funzionale = ai_assistant` nel sistema permessi (`ZeroERPPermission`).
- Guard `AI_ENABLED`: se `false`, l'endpoint restituisce `501` senza tentare alcuna operazione.

## Dipendenze DB

- `dbops.ai_query_log` (tabella logging interazioni AI)
- `script.fn_get_user_permissions_map` (filtro tool per permessi utente)
- `script.fn_get_parameter_full('AI_DISABLED_TOOLS')` (blacklist tool per installazione)

## Note di migrazione

- L'endpoint e' disponibile solo se `AI_ENABLED=True` in settings (l'app `ai_assistant` non viene caricata altrimenti).
- Il provider AI e' configurabile via `AI_PROVIDER` (anthropic, mistral, mock).
- Le conversazioni sono in-memory (non persistite in DB). In futuro, se necessario, migrazione a Redis.
