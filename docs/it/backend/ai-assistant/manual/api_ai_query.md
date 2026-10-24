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

#### Protocollo di conferma delle scritture

Quando l'LLM chiede un tool che scrive, il service esegue solo l'anteprima e restituisce in `actions` una voce `{"type": "confirm", "label", "confirmation_id"}`. Il client risponde con una seconda POST sulla stessa rotta:

- `{"message": "__confirm__", "conversation_id": "<id>"}` — esegue l'operazione in attesa per quella conversazione;
- `{"message": "__cancel__", "conversation_id": "<id>"}` — la annulla.

I due messaggi riservati valgono solo insieme a `conversation_id` e saltano la validazione del messaggio. L'esito è sempre un `200` con il testo in `response` (es. «Operazione annullata.», «Nessuna operazione in attesa di conferma.», «Operazione non piu' consentita: permessi non sufficienti.», o il messaggio d'errore dell'esecuzione); `actions` è vuoto.

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
| `actions` | Action[] | Azioni suggerite: navigazione verso entita' trovate, o conferma di una scrittura |
| `actions[].type` | string | `navigate` oppure `confirm` |
| `actions[].label` | string | Testo del link o riepilogo dell'operazione da confermare, gia' localizzato |
| `actions[].route` | object | Solo per `navigate`: oggetto compatibile con Vue Router `router.push()` |
| `actions[].confirmation_id` | string | Solo per `confirm` (senza `route`): id della conferma pendente; si conferma con `__confirm__` (vedi §Protocollo di conferma) |
| `has_more` | boolean | `true` se il loop tool si e' fermato per limite di iterazioni o di tempo (risposta parziale) |

### Errori:

- `400` — `E_AI_QUERY_EMPTY`: messaggio vuoto
- `400` — `E_AI_QUERY_TOO_LONG`: messaggio oltre 2000 caratteri
- `401` — JWT mancante o non valido
- `403` — livello `BLOCCATO` sull'area `ai_assistant`
- `404` — AI non attiva (`AI_ENABLED` spento): la rotta non è montata

Un errore del provider AI non è un errore HTTP: la risposta è `200` con un testo di scuse in `response`; il codice (`E_AI_PROVIDER_ERROR`, o quello dell'eccezione) resta solo in `dbops.ai_query_log`.

## Regole

- Il messaggio non puo' essere vuoto ne' superare 2000 caratteri.
- Il catalogo strumenti e' filtrato per permessi dell'utente autenticato, con la regola dell'endpoint gemello di ogni tool **e** il livello sull'area `ai_assistant` (vedi [ai_tool_registry](ai_tool_registry.md)): se l'operatore non ha accesso all'area `pratiche`, il tool `cerca_pratiche` non e' disponibile; con `LETTURA` sull'assistente i tool di scrittura non sono offerti.
- **Permessi ri-verificati a execution-time** (difesa in profondità, non solo all'offer-time): quando l'LLM invoca un tool, il service ri-controlla che l'utente possa usarlo (predicato unico `is_tool_allowed_for_user`) **prima** di preview/execute, e di nuovo alla conferma `__confirm__`. Chiude il TOCTOU (permesso revocato tra preview e conferma) e un tool_call per un tool fuori scope (injection/errore modello). I service chiamati dai tool non rifanno il check area-level (vive nel layer view, non attraversato dall'AI): il backstop è qui.
- **Granularità come la UI**: il permesso di un tool e' quello del suo endpoint gemello (`valuta_accesso_endpoint`), azione di processo compresa. Es.: `cambia_stato_pratica` ha per gemello `ApiPraticaStato` POST, quindi richiede l'azione `cambia_stato_pratica` come la UI.
- **Le letture non scrivono, e lo garantisce il DB**: ogni tool di lettura e l'anteprima di ogni tool di scrittura girano in `transazione_sola_lettura`; una scrittura tentata li' dentro fallisce con `25006`. Fuori restano l'esecuzione confermata e l'INSERT in `dbops.ai_query_log`.
- Il loop tool_call ha un limite di 8 iterazioni (`MAX_TOOL_ITERATIONS`) e un tempo massimo complessivo di 30 secondi (`MAX_TOOL_LOOP_TIMEOUT`). Al superamento di uno dei due restituisce risposta parziale con `has_more: true`.
- La conversazione in-memory ha un TTL di 15 minuti (configurabile via `AI_CONVERSATION_TTL`). Dopo la scadenza, il `conversation_id` non e' piu' valido e viene creata una nuova conversazione.
- **Conferme di scrittura durabili in cache** (`django.core.cache` → Redis in prod): le conferme pendenti sopravvivono tra i worker gunicorn, con TTL nativo di 5 minuti. Chiave per scope `(conversazione, owner_user_id, owner_identita_id)`: una conferma per conversazione (un nuovo preview sovrascrive) e isolamento sicurezza nella chiave (un altro owner non vede/annulla la conferma altrui).
- Il system prompt non contiene mai dati dal database — solo vocabolario e regole operative; i dati arrivano come `tool_result`. ⚠️ Questo è **igiene** (riduce injection diretta e invenzioni), **non** una protezione contro la prompt injection: per il modello `tool_result` e system prompt sono lo stesso flusso. La difesa vera è il *blast radius* — permessi + RLS + conferma sulle scritture (vedi [guida AI §4](../../../guide/integrazione-ai.md)).
- Ogni interazione viene loggata in `dbops.ai_query_log` con `request_id`, strumenti chiamati, token consumati e durata. Il logging delle **letture** è best-effort (un errore non blocca la risposta); per le **scritture confermate** è **affidabile** (`reliable=True`): se l'audit fallisce viene emesso un **alert ERROR** (l'audit è anche il sistema di rilevamento anomalie). Retention via framework `dbops` cleanup (`cleanup_at`, regola `*all` 30gg default).
- L'endpoint richiede `area_funzionale = ai_assistant` nel sistema permessi (`ZeroERPPermission`), in **lettura**: `post_accesso = "view"`, perche' una domanda e' una lettura anche se viaggia in una POST. Basta `LETTURA` per entrare; `BLOCCATO` risponde 403.
- Con `AI_ENABLED` spento l'app e le rotte `/api/v1/ai-assistant/` non sono caricate: la chiamata riceve `404`.

## Dipendenze DB

- `dbops.ai_query_log` (tabella logging interazioni AI)
- `script.fn_resolve_livello_area` / `fn_resolve_livello_oggetto` / `fn_check_azione_processo` via `PermissionResolver` (filtro tool per permessi utente)
- `script.fn_get_parameter_full('AI_DISABLED_TOOLS')` (blacklist tool per installazione)

## Note di migrazione

- L'endpoint e' disponibile solo se `AI_ENABLED=True` in settings (l'app `ai_assistant` non viene caricata altrimenti).
- Il provider AI e' configurabile via `AI_PROVIDER` (anthropic, mistral, mock).
- Le **conferme pendenti** sono in **cache** (`django.core.cache` → Redis in prod, LocMemCache in CI/test): durano tra i worker gunicorn, TTL 5 minuti.
- Le **conversazioni** sono ancora **in-memory per processo** (non condivise tra worker gunicorn): un follow-up che colpisce un altro worker non ne ricostruisce il contesto. Migrazione alla cache (stesso meccanismo delle conferme) consigliata come follow-up — vedi [analisi-sicurezza-aggiornata.md](../../../dev/work-done/analisi-sicurezza-aggiornata.md).
