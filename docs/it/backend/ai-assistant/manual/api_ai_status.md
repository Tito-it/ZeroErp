# API ai_status (Django)

## Scopo

Esporre via HTTP un health check per verificare se l'assistente AI e' attivo e quanti strumenti sono disponibili. Usato dal frontend per decidere se mostrare il bottone AI nella topbar.

## Contesto

GET restituisce lo stato di configurazione AI senza query DB. Il conteggio tool usa il registro in-memory (popolato all'avvio dell'app). L'endpoint usa autenticazione JWT semplice senza check `area_funzionale`: tutti gli utenti autenticati possono verificare la disponibilita' AI.

## Input

### GET — Status AI

- Metodo: `GET`
- Path canonico: `/api/v1/ai-assistant/status/`
- Header sicurezza: `Authorization: Bearer <access_token>`

## Output

### GET 200:

```json
{
  "data": {
    "enabled": true,
    "provider": "anthropic",
    "tools_available": 6
  },
  "meta": {
    "request_id": "req-uuid"
  }
}
```

| Campo | Tipo | Descrizione |
|---|---|---|
| `enabled` | boolean | `true` se `AI_ENABLED=True` in settings |
| `provider` | string | Provider configurato: `anthropic`, `mistral`, `mock` |
| `tools_available` | integer | Numero totale di tool registrati (senza filtro permessi) |

### Errori:

- `401` — JWT mancante o non valido

## Regole

- Nessuna query DB: il conteggio tool usa il registro in-memory (`get_all_tools()`).
- Il campo `tools_available` indica il totale registrato, non quelli accessibili all'utente specifico (il filtro permessi avviene solo su `/query/`).
- L'endpoint non richiede `area_funzionale` — usa `IsAuthenticated` direttamente. Questo perche' tutti gli utenti devono poter verificare la disponibilita' AI per la UI.
- Se `AI_ENABLED=False`, le rotte `/api/v1/ai-assistant/` non sono registrate nel urlconf e restituiscono `404`.

## Dipendenze DB

Nessuna.

## Note di migrazione

- L'endpoint e' disponibile solo se `AI_ENABLED=True` (l'app e le rotte non vengono caricate altrimenti).
- Il conteggio tool puo' essere `0` se nessun tool e' stato registrato (app caricata ma `populate_registry` non eseguito).
