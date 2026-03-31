# Piano di Sviluppo — Integrazione AI in ZeroERP

**Stato:** COMPLETATO
**Data:** 2026-03-31
**Completamento:** 2026-03-31
**Autore:** Michele Carlo / Claude Code
**Riferimenti:** [integrazione-ai.md](integrazione-ai.md) (visione), [sviluppo-concentrico.md](../../sviluppo-concentrico.md), [api.md](../api.md), [frontend-standards.md](../frontend/frontend-standards.md)

---

## Posizionamento nella Mappa Concentrica

L'integrazione AI non e' un processo di business (Anello 3) ne' un'infrastruttura di orchestrazione (Anello 2). E' uno **strato di interazione** che si appoggia su tutti gli anelli esistenti senza che nessuno di essi dipenda da lui.

```
┌───────────────────────────────────────────────────────┐
│              ANELLO 4 — INTERAZIONE AI                │
│                                                       │
│   Consuma API di tutti gli anelli interni.             │
│   Nessun anello interno lo conosce.                   │
│   Disattivabile senza effetti sul sistema.            │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │           ANELLO 3 — PROCESSI                   │  │
│  │  vendite  acquisti  magazzino  pagamenti  ...   │  │
│  │  ┌───────────────────────────────────────────┐  │  │
│  │  │        ANELLO 2 — ORCHESTRAZIONE          │  │  │
│  │  │              pratiche                     │  │  │
│  │  │  ┌─────────────────────────────────────┐  │  │  │
│  │  │  │      ANELLO 1 — DATI BASE           │  │  │  │
│  │  │  │  config  anagrafiche  catalogo      │  │  │  │
│  │  │  │  ┌───────────────────────────────┐  │  │  │  │
│  │  │  │  │    ANELLO 0 — NUCLEO          │  │  │  │  │
│  │  │  │  │  core  dbops  script          │  │  │  │  │
│  │  │  │  └───────────────────────────────┘  │  │  │  │
│  │  │  └─────────────────────────────────────┘  │  │  │
│  │  └───────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────┘
```

### Regole di posizionamento

1. **Dipendenza solo verso l'interno** — l'AI chiama API esposte dagli anelli 0-3. Nessun anello interno importa, referenzia o dipende dall'app `ai_assistant`.
2. **Disattivazione trasparente** — con `AI_ENABLED=false` l'ERP funziona identicamente. Nessun middleware, nessun template, nessuna migrazione condizionale.
3. **Stesse API del frontend** — l'AI usa gli stessi endpoint REST che usa Vue. Nessun percorso privilegiato, nessuna query SQL diretta.
4. **Stessi permessi dell'utente** — il catalogo strumenti e' filtrato per `area_funzionale` e livello accesso dell'operatore autenticato.

---

## Principi architetturali

### Cosa l'AI fa

- Interpreta il linguaggio naturale e lo traduce in chiamate API strutturate
- Seleziona lo strumento corretto dal catalogo disponibile per quell'utente
- Formula risposte contestuali basate sui risultati delle API
- Suggerisce navigazione verso entita' trovate (link diretti alle rotte Vue)
- Guida operazioni multi-step con conferma esplicita per le scritture

### Cosa l'AI non fa mai

- Non scrive direttamente nel database
- Non bypassa trigger, funzioni o validazioni PostgreSQL
- Non bypassa il sistema permessi (JWT + `ZeroERPPermission`)
- Non esegue operazioni irreversibili senza conferma utente
- Non ha memoria tra sessioni (il contesto viene dalle API, non dall'LLM)
- Non e' fonte di verita' — in caso di discrepanza, i dati a schermo vincono

### Coerenza con lo sviluppo concentrico

| Principio concentrico | Applicazione all'AI |
|---|---|
| Il nucleo si cambia solo quando serve davvero | L'AI non modifica Anello 0. Usa `error_manager`, `handle_post_json`, middleware esistenti |
| Strati esterni dipendono dagli interni | L'AI dipende da tutti gli anelli ma nessuno dipende dall'AI |
| Se un anello esterno rivela debolezza interna, si corregge alla fonte | Se l'AI ha bisogno di dati che le API non espongono, si arricchisce l'API del dominio, non si crea un percorso alternativo |
| Integrazione minima, vocabolario condiviso massimo | L'AI usa lo stesso vocabolario di dominio (stati, codici errore, nomi entita') |
| Crescita incrementale con coerenza verificabile | Ogni fase aggiunge strumenti su API gia' stabili — non su endpoint futuri |

---

## Struttura dell'app Django

```
backend/apps/ai_assistant/
├── api/
│   ├── views.py                 # AIQueryView (endpoint principale)
│   └── urls.py                  # /api/v1/ai-assistant/
├── services/
│   ├── ai_assistant_service.py  # Orchestrazione: prompt → provider → tool exec → risposta
│   ├── tool_registry.py         # Registro strumenti con filtro permessi
│   └── prompt_builder.py        # Costruzione system prompt contestuale
├── providers/
│   ├── base.py                  # Interfaccia astratta provider AI
│   ├── anthropic_provider.py    # Implementazione Anthropic
│   ├── mistral_provider.py      # Implementazione Mistral (EU)
│   └── mock_provider.py         # Provider mock per test CI
├── tools/
│   ├── base.py                  # Classe base AITool
│   ├── pratiche_tools.py        # Strumenti dominio pratiche
│   ├── anagrafiche_tools.py     # Strumenti dominio anagrafiche
│   ├── config_tools.py          # Strumenti dominio config
│   ├── doc_tools.py             # Tool cerca_documentazione (RAG, Fase 2.5b)
│   └── ...                      # Un file per dominio, aggiunto incrementalmente
├── indexing/
│   ├── chunker.py               # Splitting markdown in chunk semantici (Fase 2.5b)
│   ├── embedder.py              # Generazione embedding via provider (Fase 2.5b)
│   └── doc_repository.py        # Accesso tabella doc_embeddings (Fase 2.5b)
├── management/
│   └── commands/
│       └── index_docs.py        # Command: manage.py index_docs (Fase 2.5b)
├── tests/
│   ├── api/
│   │   └── test_ai_query_api.py
│   ├── services/
│   │   ├── test_ai_assistant_service.py
│   │   ├── test_tool_registry.py
│   │   └── test_prompt_builder.py
│   └── indexing/
│       ├── test_chunker.py
│       └── test_index_docs.py
└── __init__.py
```

### Coerenza con il pattern three-layer (da api.md)

```
AIQueryView (api/views.py)
  │  parsing JSON, autenticazione JWT, envelope risposta
  │  usa handle_post_json come tutti gli endpoint POST
  ▼
AIAssistantService (services/ai_assistant_service.py)
  │  orchestrazione: costruisce prompt, chiama provider,
  │  esegue tool_call, gestisce loop multi-tool
  ▼
Provider (providers/*.py)          Tool handler (tools/*.py)
  │  comunicazione con LLM           │  wrappa chiamata API interna
  │  astrazione multi-vendor          │  ogni tool chiama un endpoint
  ▼                                   │  esistente via service/repository
Anthropic/Mistral/Ollama API         ▼
                                   API interne (stessi endpoint di Vue)
```

---

## Fasi di sviluppo

---

### Fase 0 — Fondamenta infrastrutturali

> Obiettivo: predisporre l'infrastruttura minima senza ancora nessuna funzionalita' AI visibile. Al termine di questa fase il sistema ha la struttura, il logging, l'astrazione provider e il feature flag — ma nessun endpoint attivo.

#### DB

**Tabella `dbops.ai_query_log`**

Logging di ogni interazione AI. Nello schema `dbops` perche' e' un log operativo append-only, coerente con gli altri log gia' presenti (`audit_log`, `error_log`, `request_log`). Lo schema `storico` e' riservato alla storicizzazione SCD Type 2 di entita' business.

| Colonna | Tipo | Descrizione |
|---|---|---|
| `id` | `BIGINT GENERATED ALWAYS AS IDENTITY` | PK tecnica |
| `request_id` | `UUID NOT NULL` | Correlazione con `dbops.request_log` (stesso `request_id` del middleware) |
| `user_id` | `INTEGER NOT NULL` | FK → `auth_user.id` — operatore che ha fatto la richiesta |
| `input_text` | `TEXT NOT NULL` | Testo in linguaggio naturale inviato dall'utente |
| `tools_called` | `JSONB` | Array strumenti invocati: `[{"name": "...", "input": {...}, "duration_ms": N}]` |
| `response_text` | `TEXT` | Risposta finale formulata dall'LLM |
| `provider` | `VARCHAR(50) NOT NULL` | Provider usato: `anthropic`, `mistral`, `local` |
| `model` | `VARCHAR(100) NOT NULL` | Modello specifico: `claude-sonnet-4-20250514`, ecc. |
| `tokens_input` | `INTEGER` | Token di input consumati |
| `tokens_output` | `INTEGER` | Token di output consumati |
| `duration_ms` | `INTEGER` | Durata totale della richiesta in millisecondi |
| `error_code` | `VARCHAR(100)` | Codice errore se fallita (`NULL` se successo) |
| `cleanup_at` | `TIMESTAMPTZ` | Data di pulizia programmata (coerente con pattern dbops) |
| `date_insert` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | Timestamp inserimento |

Indici: `ix_ai_query_log_user_id`, `ix_ai_query_log_date_insert`, `ix_ai_query_log_request_id`.

Nessun trigger — tabella append-only con retention gestita dal meccanismo `cleanup_at` gia' in uso per gli altri log `dbops`.

**~~Tabella `config.ai_tools_config`~~** — scartata.

I tool sono oggetti Python con handler: una tabella DB puo' solo disabilitare, non abilitare tool che non esistono nel codice. La disabilitazione per installazione usa `config.parameters` con chiave `ai_assistant.disabled_tools` (lista separata da virgola). Il `tool_registry` legge questa blacklist e la applica insieme al filtro permessi utente. Nessuna tabella aggiuntiva, stesso pattern usato per i default soggetti e altre configurazioni operative.

#### Backend

**Setting e configurazione**

| Setting | Tipo | Default | Descrizione |
|---|---|---|---|
| `AI_ENABLED` | `bool` | `False` | Feature flag globale. Se `False`, l'endpoint restituisce `501 Not Implemented` |
| `AI_PROVIDER` | `str` | `"anthropic"` | Provider attivo: `anthropic`, `mistral`, `local` |
| `AI_API_KEY` | `str` | `""` | Chiave API del provider. Solo via env var, mai in settings.py |
| `AI_MODEL` | `str` | `"claude-sonnet-4-20250514"` | Modello da usare |
| `AI_MAX_TOKENS` | `int` | `4096` | Limite token risposta LLM |
| `AI_CONVERSATION_TTL` | `int` | `900` | TTL conversazione in secondi (15 min) |
| `AI_EMBEDDING_PROVIDER` | `str` | `"same"` | Provider per embedding: `same` (usa AI_PROVIDER), `local` (sentence-transformers), o provider dedicato. Rilevante da Fase 2.5b |
| `AI_EMBEDDING_MODEL` | `str` | `""` | Modello embedding specifico (es. `voyage-3`, `mistral-embed`). Se vuoto, usa il default del provider |
| `AI_DOCS_PATH` | `str` | `"docs/it/"` | Cartella documentazione da indicizzare (Fase 2.5b) |
| `AI_CONTEXT_FILE` | `str` | `"docs/it/ai/ai-context.md"` | File contesto statico per system prompt (Fase 2.5a) |

Tutti caricati da variabili d'ambiente con `env()`.

**Dipendenza Python**

- `anthropic` — SDK ufficiale Anthropic (da aggiungere a `requirements.in` con conferma utente)
- Nessuna altra dipendenza esterna in Fase 0

**App Django `ai_assistant`**

- Registrata in `INSTALLED_APPS` solo se `AI_ENABLED=True` (conditional app loading)
- Struttura cartelle come da schema sopra, file iniziali vuoti con header standard
- `urls.py` incluso nel root urlconf sotto `/api/v1/ai-assistant/`

**Astrazione provider (`providers/`)**

- `base.py`: classe astratta `AIProvider` con metodo `send_message(messages, tools, model) -> ProviderResponse`
  - **Input**: lista messaggi (ruolo + contenuto), catalogo strumenti (schema JSON), nome modello
  - **Output**: `ProviderResponse` — TypedDict con `content` (testo), `tool_calls` (lista), `usage` (token input/output), `stop_reason`
- `anthropic_provider.py`: implementazione con SDK `anthropic`. Gestisce `tool_use` content block
- `mock_provider.py`: per test CI — restituisce risposte predefinite basate su pattern di input. Nessuna chiamata di rete
- `mistral_provider.py`: stub iniziale, implementazione in fase successiva

**Factory provider**

```
get_ai_provider() -> AIProvider
```
- Legge `AI_PROVIDER` da settings
- Restituisce l'istanza corretta
- Raise `ServiceError("E_AI_PROVIDER_UNKNOWN")` se il provider non e' supportato

**Codici errore**

Da registrare in `error_policies.py`:

| Codice | HTTP | Descrizione |
|---|---|---|
| `E_AI_DISABLED` | 501 | Funzionalita' AI non attiva |
| `E_AI_PROVIDER_UNKNOWN` | 500 | Provider configurato non riconosciuto |
| `E_AI_PROVIDER_ERROR` | 502 | Errore nella comunicazione con il provider esterno |
| `E_AI_QUERY_EMPTY` | 400 | Input utente vuoto |
| `E_AI_QUERY_TOO_LONG` | 400 | Input utente oltre il limite consentito |
| `E_AI_TOOL_NOT_FOUND` | 500 | Strumento richiesto dall'LLM non presente nel registro |
| `E_AI_TOOL_DENIED` | 403 | Strumento non accessibile per i permessi dell'utente |
| `E_AI_CONFIRMATION_REQUIRED` | 428 | Operazione in scrittura richiede conferma esplicita |

#### Frontend

Nessuna modifica frontend in Fase 0.

#### Test

- Unit test provider mock: verifica che `send_message` restituisca la struttura attesa
- Unit test factory: verifica scelta provider per ciascun valore di `AI_PROVIDER`
- Unit test codici errore: verifica registrazione in `error_policies`
- Tutti con `unittest.TestCase` + mock, compatibili CI senza DB

#### Checklist Fase 0

**DB:**

- [x] Migrazione Liquibase: tabella `dbops.ai_query_log` con colonne, indici, `cleanup_at`
- [x] ~~(Opzionale) Tabella `config.ai_tools_config`~~ — **Decisione: non serve.** I tool sono oggetti Python con handler; una tabella DB puo' solo disabilitare, non abilitare tool che non esistono nel codice. La disabilitazione per installazione usa `config.parameters` (chiave `ai_assistant.disabled_tools`), pattern gia' consolidato in ZeroERP. La configurazione multi-provider resta nei settings/env var (`AI_PROVIDER` + `AI_EMBEDDING_PROVIDER`)

**Backend:**

- [x] Creare app `backend/apps/ai_assistant/` con struttura cartelle completa e header standard
- [x] Setting in `settings.py`: `AI_ENABLED`, `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`, `AI_MAX_TOKENS`, `AI_CONVERSATION_TTL`, `AI_EMBEDDING_*`, `AI_DOCS_PATH`, `AI_CONTEXT_FILE`
- [x] Aggiungere dipendenza `anthropic` a `requirements.in` (con conferma utente)
- [x] `providers/base.py`: classe astratta `AIProvider` con `send_message()` → `ProviderResponse`
- [x] `providers/anthropic_provider.py`: implementazione con SDK Anthropic
- [x] `providers/mock_provider.py`: provider mock per test CI
- [x] `providers/mistral_provider.py`: stub iniziale
- [x] Factory `get_ai_provider()` con switch su `AI_PROVIDER`
- [x] Registrazione codici errore `E_AI_*` in `error_policies.py`
- [x] Registrazione condizionale in `INSTALLED_APPS` (solo se `AI_ENABLED=True`)
- [x] Inclusione `urls.py` nel root urlconf sotto `/api/v1/ai-assistant/`

**Test:**

- [x] Unit test provider mock: struttura `ProviderResponse` (8 test)
- [x] Unit test factory: scelta provider per ogni valore `AI_PROVIDER` (5 test)
- [x] Unit test codici errore: registrazione in `error_policies` (9 test)

#### Output atteso Fase 0

- App Django strutturata, non ancora funzionante
- Provider astratto con implementazione Anthropic e mock
- Tabella logging pronta in DB
- Feature flag funzionante (501 se disattivo)
- Zero impatto sugli anelli interni

---

### Fase 1 — Nucleo: endpoint, registro strumenti, primo tool

> Obiettivo: un endpoint funzionante che accetta linguaggio naturale, chiama un LLM, esegue un tool, e restituisce una risposta strutturata. Testabile via curl. Al termine di questa fase il backend AI e' operativo end-to-end con un singolo strumento.

#### DB

Nessuna modifica DB in Fase 1. La tabella `dbops.ai_query_log` e' gia' pronta dalla Fase 0.

#### Backend

**Endpoint `POST /api/v1/ai-assistant/query/`**

Vista: `AIQueryView` estende `DomainAPIView`.

- `area_funzionale = 'ai_assistant'`
- Usa `handle_post_json` come tutti gli endpoint POST
- Supporta `Idempotency-Key` header

**Input atteso (body JSON):**

```
{
  "message": "mostrami le pratiche aperte di Acea",
  "conversation_id": "uuid-opzionale"        // null per nuova conversazione
}
```

| Campo | Tipo | Obbligatorio | Validazione |
|---|---|---|---|
| `message` | `string` | Si | Non vuoto, max 2000 caratteri |
| `conversation_id` | `string (UUID)` | No | Se presente, deve corrispondere a una conversazione attiva nel TTL |

**Output atteso (envelope standard):**

```
{
  "data": {
    "conversation_id": "uuid",
    "response": "Ho trovato 4 pratiche aperte di Acea...",
    "tools_used": ["cerca_pratiche"],
    "actions": [
      {
        "type": "navigate",
        "label": "Apri pratica #2341",
        "route": { "name": "pratiche-dettaglio", "params": { "id": 2341 } }
      }
    ],
    "has_more": false
  },
  "meta": {
    "request_id": "uuid"
  }
}
```

| Campo output | Tipo | Descrizione |
|---|---|---|
| `conversation_id` | `UUID` | ID conversazione (nuovo o esistente) |
| `response` | `string` | Risposta testuale dell'LLM in linguaggio naturale |
| `tools_used` | `string[]` | Nomi degli strumenti invocati |
| `actions` | `Action[]` | Azioni suggerite (navigazione, apertura drawer, ecc.) |
| `actions[].type` | `string` | `navigate` (link a rotta Vue), `confirm` (richiede conferma per scrittura) |
| `actions[].label` | `string` | Testo del link/bottone, gia' localizzato |
| `actions[].route` | `object` | Oggetto compatibile con `router.push()` di Vue Router |
| `has_more` | `bool` | Se l'LLM ha indicato che servono ulteriori informazioni dall'utente |

**Service `ai_assistant_service.py`**

Metodo principale:

```
query(user, message, conversation_id=None) -> AIQueryResult
```

Flusso interno:

1. Validazione input (`_require_str`, lunghezza)
2. Recupero o creazione conversazione (in-memory, dict con TTL)
3. Recupero catalogo strumenti filtrato per permessi utente (chiama `tool_registry`)
4. Costruzione system prompt (chiama `prompt_builder`)
5. Invio al provider con messaggi + catalogo strumenti
6. Se il provider risponde con `tool_call`:
   a. Identifica il tool nel registro
   b. Verifica permesso utente per quel tool
   c. Esegue il tool handler (che chiama l'API interna)
   d. Restituisce il risultato al provider come `tool_result`
   e. Torna al punto 5 (loop fino a risposta testuale o limite iterazioni)
7. Salvataggio in `dbops.ai_query_log`
8. Restituzione `AIQueryResult`

**Limite loop tool**: massimo 5 iterazioni di tool_call per singola richiesta. Al superamento, il service interrompe e restituisce la risposta parziale con messaggio di fallback.

**Gestione conversazione in-memory**

- Dizionario `{conversation_id: {"messages": [...], "last_activity": datetime}}`
- Pulizia lazy: ogni nuova richiesta rimuove conversazioni scadute (oltre `AI_CONVERSATION_TTL`)
- In futuro (se necessario): Redis. Per ora in-memory e' sufficiente per un singolo processo Django
- La conversazione contiene solo i messaggi scambiati (ruoli: user, assistant, tool_result). Nessun dato sensibile persistito oltre il TTL

**Registro strumenti (`tool_registry.py`)**

```
get_tools_for_user(user) -> list[AITool]
```

- Ogni tool e' una istanza di `AITool` con:
  - `name`: identificativo univoco (es. `cerca_pratiche`)
  - `description`: descrizione in italiano per l'LLM
  - `input_schema`: JSON Schema dei parametri
  - `required_area`: `area_funzionale` richiesta (es. `pratiche`)
  - `required_level`: livello minimo accesso (`LETTURA` per read, `TUTTO` per write)
  - `handler(params, request) -> dict`: esecuzione effettiva
- Il metodo `get_tools_for_user` filtra gli strumenti confrontando `required_area` con i permessi dell'utente (da `fn_get_user_permissions_map`, gia' disponibile in Anello 0)
- Il registro e' un dizionario Python, popolato all'avvio dell'app via `AppConfig.ready()` attraverso una funzione `register_tools()` in ogni modulo `tools/*.py`

**System prompt (`prompt_builder.py`)**

```
build_system_prompt(user, tools) -> str
```

Il system prompt contiene:

- Ruolo: "Sei l'assistente AI di ZeroERP. Aiuti gli operatori a trovare informazioni e guidare operazioni."
- Vincoli: non inventare dati, non rispondere a domande fuori dominio, non eseguire scritture senza conferma
- Data corrente (per risolvere "questa settimana", "mese scorso")
- Nome e ruolo dell'operatore (per contestualizzare le risposte)
- Istruzioni specifiche per ogni strumento disponibile
- Formato risposta: italiano, conciso, con suggerimenti di navigazione quando pertinenti

**Importante**: il system prompt non contiene mai dati provenienti dal database (nomi clienti, note, ecc.). Solo metadati strutturali. I dati arrivano come `tool_result` e sono trattati dall'LLM come dati, non istruzioni.

**Primo strumento: `cerca_pratiche`**

| Proprieta' | Valore |
|---|---|
| `name` | `cerca_pratiche` |
| `required_area` | `pratiche` |
| `required_level` | `LETTURA` |
| `description` | "Cerca pratiche nel sistema per cliente, stato, priorita', scadenza o operatore" |

**Input schema:**

| Parametro | Tipo | Descrizione |
|---|---|---|
| `search` | `string` | Ricerca libera su codice, descrizione, nominativo soggetto |
| `stato` | `string` | Enum: `BOZZA`, `APERTA`, `SOSPESA`, `CHIUSA`, `ANNULLATA` |
| `priorita` | `string` | Codice priorita' |
| `data_da` | `string (date)` | Data inserimento da (YYYY-MM-DD) |
| `data_a` | `string (date)` | Data inserimento a (YYYY-MM-DD) |
| `page` | `integer` | Pagina risultati (default 1) |
| `page_size` | `integer` | Risultati per pagina (default 10, max 50 per AI) |

Tutti opzionali. Almeno uno deve essere fornito dall'LLM.

**Handler**: chiama internamente lo stesso service/repository usato da `GET /api/v1/pratiche/pratiche/`, non l'endpoint HTTP. Questo evita overhead HTTP loopback ma usa la stessa logica di query. Il handler riceve il `request` originale per ereditare il contesto di autenticazione.

**Output handler (restituito come tool_result all'LLM):**

```
{
  "count": 4,
  "results": [
    {
      "id": 2341,
      "codice": "PRA-2026-0042",
      "descrizione": "Allaccio gas — Via Roma 12",
      "stato": "APERTA",
      "priorita": "ALTA",
      "nominativo_soggetto": "Acea Energia Spa",
      "operatore_assegnato": "M. Rossi",
      "data_insert": "2026-03-15"
    }
  ]
}
```

I campi sono gli stessi display fields gia' risolti via JOIN nel repository pratiche (7 JOIN gia' operativi).

**Estrazione azioni di navigazione**

Dopo la risposta finale dell'LLM, il service analizza i `tool_result` per estrarre azioni di navigazione. Se il tool ha restituito entita' con `id`, il service genera automaticamente le `actions` con rotta Vue corrispondente. Il mapping rotta e' definito nel tool stesso (`route_template`):

```
route_template = { "name": "pratiche-dettaglio", "params": { "id": "{id}" } }
```

#### Frontend

Nessuna modifica frontend in Fase 1. L'endpoint e' testabile via curl o client HTTP.

#### Test

- **Unit test `ai_assistant_service`**: con provider mock, verifica il flusso completo (input → tool_call → tool_result → risposta)
- **Unit test `tool_registry`**: verifica filtro per permessi (utente con/senza area pratiche)
- **Unit test `prompt_builder`**: verifica struttura prompt, assenza dati DB nel system prompt
- **Unit test handler `cerca_pratiche`**: con repository mockato, verifica mapping parametri e formato output
- **Test API `AIQueryView`**: con provider mock, verifica envelope risposta, codici errore, idempotency
- **Smoke test curl**: script bash per test end-to-end con JWT reale e provider mock
- Tutti i test unitari con `unittest.TestCase` + mock, compatibili CI

#### Checklist Fase 1

**Backend:**

- [x] `api/views.py`: `AIQueryView` estende `DomainAPIView`, `area_funzionale='ai_assistant'`
- [x] `api/views.py`: usa `handle_post_json`, supporto `Idempotency-Key`
- [x] `api/urls_v1.py`: rotta `POST /api/v1/ai-assistant/query/`
- [x] `services/ai_assistant_service.py`: metodo `query(user, message, conversation_id)` con flusso completo
- [x] `services/ai_assistant_service.py`: gestione conversazione in-memory con TTL e pulizia lazy
- [x] `services/ai_assistant_service.py`: loop tool_call con limite 5 iterazioni
- [x] `services/ai_assistant_service.py`: salvataggio in `dbops.ai_query_log` dopo ogni query
- [x] `services/tool_registry.py`: `get_tools_for_user(user)` con filtro `area_funzionale` + `livello_accesso` + blacklist `config.parameters`
- [x] `services/tool_registry.py`: registrazione tool via `AppConfig.ready()`
- [x] `services/prompt_builder.py`: `build_system_prompt(user, tools)` con ruolo, vincoli, data corrente, operatore + predisposizione contesto statico (Fase 2.5a)
- [x] `tools/base.py`: classe base `AITool` con `name`, `description`, `input_schema`, `required_area`, `required_level`, `execute()`, `route_template`, `extract_actions()`
- [x] `tools/pratiche_tools.py`: tool `cerca_pratiche` — handler wrappa `pratiche_service.cerca_pratiche()`
- [x] `db/ai_query_log_repository.py`: salvataggio log best-effort in `dbops.ai_query_log`
- [x] Estrazione automatica azioni navigazione dai `tool_result` con `route_template`

**Test:**

- [x] Unit test `ai_assistant_service`: flusso completo con provider mock (6 test)
- [x] Unit test `tool_registry`: filtro permessi, blacklist, area, livello (9 test)
- [x] Unit test `prompt_builder`: struttura prompt, data, operatore, tool (7 test)
- [x] Test API `AIQueryView`: guard AI_ENABLED, envelope risposta (2 test)
- [x] Smoke test curl: `scripts/tests/smoke-test-ai-assistant.sh` (5 test)

#### Output atteso Fase 1

- Endpoint funzionante: `POST /api/v1/ai-assistant/query/` con JWT
- Un tool operativo (`cerca_pratiche`) che wrappa l'API esistente
- Logging in `dbops.ai_query_log`
- Testabile via curl con risposte reali del provider AI
- Pattern replicabile per aggiungere nuovi strumenti

---

### Fase 2 — Frontend: drawer AI

> Obiettivo: interfaccia utente per interagire con l'AI. Drawer dedicato integrato nel layout esistente, coerente con i pattern di frontend-standards.md. Al termine di questa fase l'utente puo' usare l'AI dall'interfaccia.

#### DB

Nessuna modifica DB.

#### Backend

**Endpoint aggiuntivo: `GET /api/v1/ai-assistant/status/`**

Verifica rapida se l'AI e' attiva e funzionante (health check).

**Input:** nessuno (solo JWT).

**Output:**

```
{
  "data": {
    "enabled": true,
    "provider": "anthropic",
    "tools_available": 1
  },
  "meta": { "request_id": "uuid" }
}
```

Serve al frontend per decidere se mostrare il bottone AI o nasconderlo.

#### Frontend

**Composable `useAiAssistant()`** — in `src/core/composables/`

Stato reattivo e metodi per la comunicazione con l'endpoint AI.

| Proprieta'/Metodo | Tipo | Descrizione |
|---|---|---|
| `isAvailable` | `ref<bool>` | `true` se l'AI e' attiva (da `/status/`) |
| `isLoading` | `ref<bool>` | `true` durante la chiamata API |
| `conversationId` | `ref<string>` | UUID conversazione corrente |
| `messages` | `ref<Message[]>` | Lista messaggi della conversazione |
| `sendMessage(text)` | `async function` | Invia messaggio, aggiorna `messages` con risposta |
| `clearConversation()` | `function` | Reset conversazione |
| `executeAction(action)` | `function` | Esegue azione suggerita (navigazione via `router.push`) |

Il composable:
- Usa `useApiHandler()` per gestione loading/errori/toast
- Formatta la risposta AI come messaggio nella lista
- Gestisce le `actions` restituendo oggetti route pronti per `router.push()`
- Non persiste nulla in localStorage — la conversazione vive solo nella sessione

**Pinia store `aiAssistantStore`** — in `src/stores/`

Store globale (non per dominio) perche' l'AI e' trasversale.

| Proprieta' | Tipo | Descrizione |
|---|---|---|
| `drawerVisible` | `bool` | Stato apertura/chiusura drawer |
| `isAvailable` | `bool` | Cache dello stato AI (da `/status/`, aggiornato al login) |
| `toggleDrawer()` | `action` | Apre/chiude il drawer |
| `checkAvailability()` | `action` | Chiama `/status/` e aggiorna `isAvailable` |

**Componente `AiAssistantDrawer.vue`** — in `src/core/components/`

Drawer laterale destro, width `WIDE` (960px da `constants.js`).

Struttura interna:

```
┌──────────────────────────────────────┐
│  Header: "Assistente AI"      [X]   │
├──────────────────────────────────────┤
│                                      │
│  Area messaggi (scrollabile)         │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ [U] mostrami le pratiche...   │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │ [AI] Ho trovato 4 pratiche... │  │
│  │                                │  │
│  │ > Apri pratica #2341          │  │
│  │ > Apri pratica #2342          │  │
│  └────────────────────────────────┘  │
│                                      │
├──────────────────────────────────────┤
│  [input text...]        [Invia ➤]   │
└──────────────────────────────────────┘
```

| Elemento | Comportamento |
|---|---|
| Header | Titolo `$t('ai.title')`, bottone chiudi (ESC) |
| Area messaggi | Scroll automatico verso il basso, distinzione visiva user/AI |
| Messaggi AI | Rendering markdown (testo LLM), link azioni cliccabili |
| Azioni | Bottoni/link con `@click="executeAction(action)"` → `router.push(route)` |
| Input | `<InputText>` con submit su Enter, disabilitato durante loading |
| Loading | Indicatore visivo (skeleton o spinner) durante attesa risposta |

**Regole di coerenza con frontend-standards:**

- CSS: usa classi globali (`app-drawer-content`), non scoped CSS per layout
- Drawer: apre da destra con animazione slide, si chiude con ESC
- Responsive: nascosto sotto 768px (mobile non supporta il drawer AI in Fase 2)
- i18n: tutte le stringhe sotto namespace `ai.*`
- Nessuna logica business — solo presentazione e chiamata API

**Chiavi i18n da aggiungere (namespace `ai.*`):**

| Chiave | it | en |
|---|---|---|
| `ai.title` | Assistente AI | AI Assistant |
| `ai.placeholder` | Scrivi una domanda... | Ask a question... |
| `ai.send` | Invia | Send |
| `ai.clear` | Nuova conversazione | New conversation |
| `ai.loading` | Sto elaborando... | Processing... |
| `ai.error` | Errore nella comunicazione con l'assistente | Error communicating with the assistant |
| `ai.disabled` | Assistente AI non disponibile | AI Assistant not available |
| `ai.navigate` | Apri | Open |

**Integrazione nel layout**

Due opzioni (da valutare in fase di implementazione):

**Opzione A — Bottone nella Topbar**: icona AI nella topbar (accanto al profilo utente), visibile solo se `isAvailable`. Click → `toggleDrawer()`. Shortcut: `Ctrl+Shift+A` (non confligge con Ctrl+K della search).

**Opzione B — Tab nel SearchDrawer**: il drawer di ricerca universale (Ctrl+K) aggiunge una tab/sezione "Chiedi all'AI" sotto i risultati classici. Stesso drawer, doppia modalita'.

L'opzione A e' piu' pulita architetturalmente (separazione di responsabilita'), l'opzione B e' piu' naturale per l'utente. Decisione da prendere con test di usabilita'.

**API client `ai_assistant_api.js`** — in `src/core/api/`

| Funzione | Metodo | Endpoint | Input | Output |
|---|---|---|---|---|
| `queryAI(message, conversationId)` | POST | `/api/v1/ai-assistant/query/` | `{ message, conversation_id }` | Envelope con `data.response`, `data.actions`, ecc. |
| `getAIStatus()` | GET | `/api/v1/ai-assistant/status/` | — | `{ data: { enabled, provider, tools_available } }` |

#### Test

- Test manuale su browser: flusso completo domanda → risposta → navigazione
- Verifica responsive: drawer nascosto su mobile
- Verifica i18n: tutte le stringhe localizzate
- Verifica permessi: bottone AI non visibile se `isAvailable = false`

#### Checklist Fase 2

**Backend:**

- [x] `api/views.py`: `AIStatusView` con `GET /api/v1/ai-assistant/status/`
- [x] `api/urls_v1.py`: rotta `GET /api/v1/ai-assistant/status/`

**Frontend:**

- [x] `src/core/api/ai-api.js`: funzioni `queryAI()` e `getAIStatus()`
- [x] `src/core/composables/useAiAssistant.js`: stato reattivo, `sendMessage()`, `clearConversation()`, `executeAction()`
- [x] `src/stores/ui.js`: esteso con `aiDrawerVisible`, `aiAvailable`, `openAiDrawer()`, `toggleAiDrawer()`
- [x] `src/core/components/AiAssistantDrawer.vue`: drawer COMPLEX (800px) con header, area messaggi, input, loading
- [x] Rendering risposte AI: testo plain con pre-wrap + `cleanResponse()` per rimuovere residui tecnici (tag XML, blocchi codice)
- [x] Azioni navigazione cliccabili (`router.push()`) — rotte corrette con query search
- [x] Scroll automatico area messaggi (watch su messages.length + nextTick)
- [x] Integrazione layout: widget flottante in basso a destra (non modale), bottone nella Topbar
- [x] Shortcut tastiera `Ctrl+Shift+A` — implementato in AppLayout via useKeyboardShortcuts + constants.js
- [x] Chiavi i18n namespace `ai.*` in `it.json` e `en.json` (13 chiavi)
- [x] Responsive: widget full-width su mobile (< 768px)
- [x] Bottone AI visibile solo se `aiAvailable = true` (check via `/status/` al mount)
- [x] Check disponibilita' AI al mount di AppTopbar via `getAIStatus()` (best-effort, guard auth)
- [x] Timeout axios 60s per query AI (tool_call richiede piu' chiamate LLM)
- [x] Widget minimizzabile (header click), animazione slide up/down
- [x] Tema scuro coerente con drawer (`--p-surface-900`, bordi `--p-surface-700`)

**Test:**

- [x] Test manuale browser: flusso domanda → risposta con dati reali da DB
- [x] Test manuale tablet: widget funzionante
- [x] Verifica i18n: tutte le stringhe localizzate
- [x] Verifica permessi: bottone nascosto se AI disattiva — garantito per design (app non caricata, rotte non registrate, `/status/` restituisce 404)

#### Output atteso Fase 2

- Drawer AI funzionante nell'interfaccia
- Conversazione multi-messaggio con contesto intra-sessione
- Link navigazione cliccabili verso entita' trovate
- Nessun impatto sugli schermi esistenti (il drawer e' indipendente)

---

### Fase 2.5 — Knowledge base documentale

> Obiettivo: dare all'AI accesso alla documentazione operativa di ZeroERP, in modo che le risposte siano basate sulle procedure e regole reali del sistema, non sulle conoscenze generiche dell'LLM. Due sotto-fasi: contesto statico (immediato, zero infrastruttura) e RAG con pgvector (ricerca semantica nella documentazione completa).

#### Fase 2.5a — Contesto statico

##### DB

Nessuna modifica DB.

##### Backend

**File `docs/it/ai/ai-context.md`**

Documento scritto **per l'LLM**, non per l'operatore umano. Contiene il vocabolario di dominio e le regole operative essenziali di ZeroERP condensate in ~2000-3000 token.

**Contenuto previsto:**

| Sezione | Descrizione | Esempi |
|---|---|---|
| Vocabolario | Definizioni precise dei termini ZeroERP | Pratica, flusso, soggetto, istanza, ruolo anagrafico, BA, emittente fiscale |
| Stati e transizioni | Macchine a stati di tutte le entita' con ciclo di vita | Pratica: BOZZA→APERTA→SOSPESA→CHIUSA/ANNULLATA. Flusso: CREATO→ATTIVO→COMPLETATO |
| Regole operative | Invarianti del sistema che l'AI deve conoscere | Chiusura lotto config-driven, BA attivo prerequisito per pratiche, clone indirizzi lato backend |
| Struttura anagrafica | Gerarchia soggetto→ruolo→istanza | PF/PG/ENTE, ruoli (cliente/fornitore/risorsa umana), catena precontrattuale→BA |
| Convenzioni codici | Pattern codici generati dal sistema | PRA-YYYY-NNNN (pratiche), formato CF con omocodia |

**Iniezione nel prompt**: il `prompt_builder.py` (Fase 1) legge questo file e lo appende al system prompt, dopo le istruzioni operative e prima del catalogo strumenti. Il contenuto e' statico — caricato una volta all'avvio dell'app, non ad ogni richiesta.

**Manutenzione**: aggiornamento manuale quando cambiano regole o vocabolario. Costo basso perche' le regole di base cambiano raramente. Il file e' versionato in git come tutta la documentazione.

**Limite**: funziona per domande sul vocabolario e le regole fondamentali ("cos'e' una pratica?", "quali stati puo' avere?"), ma non per domande su procedure specifiche ("qual e' la procedura completa per un allaccio gas?"). Per quelle serve la Fase 2.5b.

##### Frontend

Nessuna modifica frontend.

##### Test

- Unit test `prompt_builder`: verifica che il contesto statico sia incluso nel system prompt
- Unit test: verifica che il contenuto non superi il budget token previsto
- Test manuale: domande sul vocabolario ZeroERP producono risposte corrette e specifiche

##### Checklist Fase 2.5a

**Backend:**

- [x] Creare `docs/it/ai/ai-context.md` con vocabolario, stati/transizioni, regole operative, struttura anagrafica, convenzioni codici
- [x] `prompt_builder.py`: caricamento `ai-context.md` all'avvio app (cache statica) — gia' implementato in Fase 1
- [x] `prompt_builder.py`: iniezione contesto nel system prompt (dopo istruzioni, prima catalogo tool) — gia' implementato in Fase 1
- [x] Verifica budget token contesto statico: ~1800 token (verificato con provider reale, 3800 token input totali)

**Test:**

- [x] Unit test `prompt_builder`: struttura prompt verificata (7 test)
- [x] Verifica token: prompt completo con 6 tool = ~3800 token input, entro budget
- [x] Test manuale con provider reale: risposte usano vocabolario ZeroERP, ruoli soggetto corretti

##### Output atteso Fase 2.5a

- L'AI conosce il vocabolario e le regole fondamentali di ZeroERP
- Le risposte usano la terminologia corretta del sistema
- Zero infrastruttura aggiuntiva, solo un file markdown curato

---

#### Fase 2.5b — RAG con pgvector

##### DB

**Estensione pgvector**

Abilitazione dell'estensione `vector` su PostgreSQL 18. Una singola migrazione Liquibase. pgvector e' gia' pacchettizzato per PostgreSQL 18.

**Schema**: i vettori sono infrastruttura tecnica dell'AI, non dati di business. La tabella va nello schema appropriato per l'app `ai_assistant`. Dato che `ai_assistant` e' un'app Django con il proprio dominio, lo schema segue la convenzione: se l'app ha bisogno di tabelle proprie, usa uno schema dedicato `ai_assistant` oppure la tabella va in `dbops` (infrastruttura tecnica). Decisione da prendere in fase di implementazione.

**Tabella `doc_embeddings`**

| Colonna | Tipo | Descrizione |
|---|---|---|
| `id` | `BIGINT GENERATED ALWAYS` | PK tecnica |
| `source_file` | `VARCHAR(500) NOT NULL` | Percorso relativo del file sorgente (es. `docs/it/guide/fatturazione.md`) |
| `section_heading` | `VARCHAR(500)` | Heading della sezione (es. `## Lotti massivi`) |
| `chunk_index` | `INTEGER NOT NULL` | Posizione del chunk nel file (per ordinamento e ricostruzione) |
| `content` | `TEXT NOT NULL` | Testo del chunk (~500-800 token) |
| `embedding` | `vector(1024) NOT NULL` | Vettore embedding del contenuto |
| `content_hash` | `VARCHAR(64) NOT NULL` | SHA-256 del contenuto — per sapere se il chunk e' cambiato e evitare re-embedding inutili |
| `date_insert` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | Timestamp indicizzazione |

**Indici:**

| Nome | Tipo | Colonne | Scopo |
|---|---|---|---|
| `ix_doc_embeddings_vector` | `ivfflat` | `embedding vector_cosine_ops` | Ricerca per similarita' coseno |
| `uq_doc_embeddings_file_chunk` | `UNIQUE` | `(source_file, chunk_index)` | Un solo embedding per chunk per file |

Nessun trigger — tabella gestita interamente dal management command di indicizzazione.

##### Backend

**Dipendenza aggiuntiva**

- `pgvector` — binding Python per pgvector (da aggiungere a `requirements.in` con conferma utente)

**Management command `index_docs`**

Comando Django `manage.py index_docs` per indicizzare la documentazione markdown.

**Flusso del command:**

1. Scansiona la cartella target ricorsivamente per file `.md`
2. Per ogni file, splitta in chunk semantici:
   - Divisione primaria per heading (`##`, `###`) — la struttura a heading dei docs ZeroERP rende il chunking naturale
   - Se una sezione supera ~800 token, divisione secondaria per paragrafi
   - Ogni chunk mantiene il proprio heading come contesto
3. Calcola SHA-256 di ogni chunk
4. Confronta con `content_hash` in tabella:
   - Hash identico → skip (nessuna chiamata API embedding)
   - Hash diverso o chunk nuovo → genera embedding via provider AI
   - Chunk presente in tabella ma assente nel file → elimina (file rimosso o sezione cancellata)
5. Upsert in tabella `doc_embeddings`
6. Report finale: chunk processati, skippati, aggiornati, rimossi

**Input del command:**

| Parametro | Default | Descrizione |
|---|---|---|
| `--path` | `docs/it/` | Cartella da indicizzare |
| `--exclude` | `dev/work-in-progress/` | Pattern da escludere (i WIP non sono documentazione stabile) |
| `--rebuild` | `False` | Se `True`, rigenera tutti gli embedding ignorando l'hash |
| `--dry-run` | `False` | Mostra cosa farebbe senza eseguire |

**Output del command (stdout):**

```
Indicizzazione docs/it/
  File trovati: 47
  Chunk totali: 234
  - Nuovi: 12
  - Aggiornati: 3
  - Invariati (skip): 219
  - Rimossi: 0
  Chiamate embedding: 15
  Completato in 4.2s
```

**Quando eseguirlo:**

- Manualmente dopo aggiornamenti significativi della documentazione
- Opzionalmente in CI dopo merge su `main` (job aggiuntivo, non bloccante)
- Non serve real-time — la documentazione cambia raramente

**Costo embedding**: con ~200 file markdown, ~5 chunk per file = ~1000 chunk. Un singolo run completo costa pochi centesimi in API embedding. I run successivi processano solo i chunk modificati grazie al confronto hash.

**Embedding provider**: usa la stessa astrazione provider della Fase 0. Il metodo `generate_embedding(text) -> list[float]` viene aggiunto all'interfaccia `AIProvider`:

- **Anthropic**: non ha API embedding native, si usa un modello embedding esterno (es. Voyage AI, oppure si aggiunge un secondo provider solo per embedding)
- **Mistral**: ha API embedding native
- **Local (Ollama)**: supporta modelli embedding locali

Alternativa pragmatica: usare un provider embedding dedicato (es. `sentence-transformers` locale) indipendente dal provider LLM. Questo evita di complicare l'astrazione provider per un'operazione che ha caratteristiche diverse (batch offline vs. conversazionale real-time). Decisione da prendere in fase di implementazione.

**Tool `cerca_documentazione`**

| Proprieta' | Valore |
|---|---|
| `name` | `cerca_documentazione` |
| `required_area` | nessuna — tutti gli operatori possono consultare la documentazione |
| `required_level` | `LETTURA` |
| `description` | "Cerca nella documentazione operativa di ZeroERP. Usare quando l'utente chiede come funziona un processo, una procedura, una regola o un termine del sistema" |

**Input schema:**

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `query` | `string` | Si | Domanda o termine da cercare nella documentazione |
| `max_results` | `integer` | No | Numero massimo di frammenti da restituire (default 5, max 10) |

**Flusso handler:**

1. Genera embedding della query utente (singola chiamata API embedding)
2. Query pgvector con ordinamento per distanza coseno
3. Filtra risultati con soglia di similarita' minima (es. similarity < 0.3 → troppo distante, scarta)
4. Restituisce i frammenti pertinenti all'LLM come `tool_result`

**Query SQL del handler:**

```sql
SELECT source_file, section_heading, content,
       1 - (embedding <=> %s) AS similarity
FROM doc_embeddings
ORDER BY embedding <=> %s
LIMIT %s;
```

Eseguita via repository con `cursor.execute()`, coerente con il pattern three-layer.

**Output handler (restituito come tool_result all'LLM):**

```json
{
  "count": 3,
  "results": [
    {
      "source": "guide/fatturazione.md",
      "section": "Lotti massivi",
      "content": "Il lotto massivo raccoglie tutte le fatture del periodo...",
      "relevance": 0.87
    },
    {
      "source": "guide/fatturazione.md",
      "section": "Pipeline di fatturazione",
      "content": "La pipeline e' composta da step configurabili...",
      "relevance": 0.79
    }
  ]
}
```

L'LLM legge i frammenti e formula la risposta basata sulla documentazione reale di ZeroERP, citando la fonte. La risposta non e' generica — e' specifica del sistema.

**Esempio flusso completo:**

```
Utente: "come funziona la sospensione di una pratica?"

LLM → tool_call: cerca_documentazione({ query: "sospensione pratica" })

Handler:
  1. Embedding di "sospensione pratica"
  2. Query pgvector → 3 chunk pertinenti
  3. Restituisce frammenti da guide/pratiche, gestione-pratiche-v2.md

LLM → risposta:
  "In ZeroERP la sospensione congela la pratica e tutti i suoi flussi
   attivi. La propagazione e' automatica: sospendendo la pratica, i
   flussi ATTIVI passano a SOSPESO. La riattivazione puo' essere
   manuale o automatica via job pgAgent alla data prevista. I giorni
   di sospensione vengono esclusi dal calcolo tempi netti.
   
   Fonte: Guida gestione pratiche, sezione Sospensioni"
```

##### Frontend

Nessuna modifica frontend specifica. Le risposte basate sulla documentazione vengono visualizzate nel drawer AI come qualsiasi altra risposta testuale. L'LLM include la citazione della fonte nel testo.

##### Test

- Unit test `index_docs` command: con filesystem mock, verifica chunking, hashing, skip invariati
- Unit test handler `cerca_documentazione`: con repository mockato, verifica formato output e filtro soglia
- Unit test embedding: con provider mock, verifica che genera vettore della dimensione attesa
- Test integrazione (locale, non CI): indicizzazione reale + query reale su docs di test
- Tutti i test CI con mock, nessuna chiamata rete

##### Checklist Fase 2.5b

**DB:**

- [ ] Migrazione Liquibase: abilitazione estensione `pgvector`
- [ ] Migrazione Liquibase: tabella `doc_embeddings` con colonne, indice ivfflat, unique constraint
- [ ] Decisione schema: `ai_assistant` dedicato oppure `dbops`

**Backend:**

- [ ] Aggiungere dipendenza `pgvector` a `requirements.in` (con conferma utente)
- [ ] Decisione provider embedding: stesso AI provider, Voyage AI, o sentence-transformers locale
- [ ] `providers/base.py`: aggiungere metodo `generate_embedding(text) -> list[float]` all'interfaccia
- [ ] Implementazione `generate_embedding` nel provider scelto
- [ ] `indexing/chunker.py`: splitting markdown per heading + fallback per paragrafi
- [ ] `indexing/embedder.py`: generazione embedding via provider con gestione batch
- [ ] `indexing/doc_repository.py`: accesso tabella `doc_embeddings` (upsert, delete, query coseno)
- [ ] `management/commands/index_docs.py`: command con `--path`, `--exclude`, `--rebuild`, `--dry-run`
- [ ] `management/commands/index_docs.py`: logica hash SHA-256 per skip chunk invariati
- [ ] `management/commands/index_docs.py`: pulizia chunk orfani (file rimossi)
- [ ] `management/commands/index_docs.py`: report stdout (nuovi, aggiornati, invariati, rimossi)
- [ ] `tools/doc_tools.py`: tool `cerca_documentazione` con handler query pgvector + filtro soglia
- [ ] Registrazione tool in `register_tools()` (disponibile a tutti, nessun filtro area)

**Test:**

- [ ] Unit test `chunker`: splitting per heading, fallback paragrafi, limiti token
- [ ] Unit test `index_docs`: chunking, hashing, skip invariati (filesystem mock)
- [ ] Unit test handler `cerca_documentazione`: formato output, filtro soglia (repository mock)
- [ ] Unit test embedding: vettore dimensione attesa (provider mock)
- [ ] Test integrazione locale: indicizzazione reale + query reale su docs di test

##### Output atteso Fase 2.5b

- La documentazione di ZeroERP e' indicizzata e ricercabile semanticamente
- L'AI risponde a domande sulle procedure con la documentazione reale del progetto
- L'indicizzazione e' incrementale (solo chunk modificati), costo marginale
- Il tool `cerca_documentazione` e' disponibile a tutti gli operatori senza restrizioni di area

---

### Fase 3 — Ampliamento strumenti read-only

> Obiettivo: arricchire il catalogo strumenti con tutti i domini che hanno API stabili. Solo operazioni di lettura. Al termine di questa fase l'AI puo' cercare e mostrare dati da tutti i domini operativi.

#### DB

Nessuna modifica DB. Il logging assorbe automaticamente i nuovi strumenti.

#### Backend

Ogni strumento segue lo stesso pattern di `cerca_pratiche` (Fase 1). Un file per dominio in `tools/`.

**Strumenti previsti — da implementare solo quando l'API del dominio e' stabile:**

**Dominio `anagrafiche`** (file `anagrafiche_tools.py`)

| Tool | required_area | Descrizione | API wrappata | Parametri principali |
|---|---|---|---|---|
| `cerca_soggetti` | `anagrafiche` | Cerca soggetti (PF/PG/ENTE) per nominativo, CF, P.IVA, natura | `GET /api/v1/anagrafiche/soggetti/` | `search`, `natura` (PF/PG/ENTE), `codice_fiscale`, `partita_iva` |
| `dettaglio_soggetto` | `anagrafiche` | Recupera dati completi di un soggetto | `GET /api/v1/anagrafiche/soggetti/{id}/` | `id` |
| `cerca_indirizzi_soggetto` | `anagrafiche` | Indirizzi associati a un soggetto | `GET /api/v1/anagrafiche/soggetti/{id}/indirizzi/` | `soggetto_id` |
| `cerca_contatti_soggetto` | `anagrafiche` | Contatti di un soggetto | `GET /api/v1/anagrafiche/soggetti/{id}/contatti/` | `soggetto_id` |

**Dominio `pratiche`** (file `pratiche_tools.py`, estensione)

| Tool | required_area | Descrizione | API wrappata | Parametri principali |
|---|---|---|---|---|
| `dettaglio_pratica` | `pratiche` | Dati completi di una pratica | `GET /api/v1/pratiche/pratiche/{id}/` | `id` |
| `cerca_flussi_pratica` | `pratiche` | Flussi operativi di una pratica | `GET /api/v1/pratiche/pratiche/{id}/flussi/` | `pratica_id` |
| `cerca_note_pratica` | `pratiche` | Note di una pratica | `GET /api/v1/pratiche/pratiche/{id}/note/` | `pratica_id` |

**Dominio `config`** (file `config_tools.py`)

| Tool | required_area | Descrizione | API wrappata | Parametri principali |
|---|---|---|---|---|
| `cerca_operatori` | `amm_software` | Cerca operatori per nome, reparto, ruolo | `GET /api/v1/amm-software/operatori/` | `search`, `reparto`, `ruolo_sistema` |

**Dominio `vendite`** (file `vendite_tools.py`) — solo quando le API vendite saranno complete

| Tool | required_area | Descrizione | API wrappata | Parametri principali |
|---|---|---|---|---|
| `cerca_fatture` | `vendite` | Cerca fatture per controparte, stato, importo, periodo | Endpoint da sviluppare | `controparte`, `stato_sdi`, `importo_min`, `importo_max`, `data_da`, `data_a` |
| `cerca_lotti` | `vendite` | Cerca lotti fatturazione per stato e periodo | Endpoint da sviluppare | `stato`, `data_da`, `data_a` |

**Regola per aggiungere nuovi strumenti:**

1. Verificare che l'API di dominio sia stabile e in produzione
2. Creare handler che chiama il service/repository esistente (mai SQL diretto)
3. Definire `required_area` e `required_level` coerenti con `ZeroERPPermission`
4. Aggiungere test unitario con handler mockato
5. Registrare nella funzione `register_tools()` del modulo

**Navigazione contestuale arricchita**

In Fase 3 ogni tool handler dichiara il proprio `route_template` per generare link di navigazione. Il service arricchisce la risposta con azioni specifiche:

| Tool | route_template | Esempio azione |
|---|---|---|
| `cerca_soggetti` | `{ name: "soggetti-dettaglio", params: { id } }` | "Apri scheda Acea Energia" |
| `cerca_pratiche` | `{ name: "pratiche-dettaglio", params: { id } }` | "Apri pratica #2341" |
| `dettaglio_pratica` | — (gia' nel dettaglio) | Link ai flussi/note |

#### Frontend

**Rendering arricchito risposte**

- Risultati lista: rendering come mini-tabella nel messaggio AI (righe cliccabili)
- Dettaglio singolo: card informativa con campi principali
- Link navigazione: bottoni con icona `pi pi-external-link` che fanno `router.push()`

Se un tool restituisce piu' di 5 risultati, il messaggio AI mostra i primi 5 con indicazione "e altri N risultati". Link per aprire la lista completa nella view di dominio con i filtri pre-impostati.

#### Test

- Unit test per ogni nuovo tool handler
- Test integrazione: verifica che il filtro permessi escluda tool dei domini non accessibili
- Smoke test: query che esercitano ciascun tool

#### Checklist Fase 3

**Backend:**

- [x] `tools/anagrafiche_tools.py`: tool `cerca_soggetti` — handler wrappa `SoggettiService.list_soggetti()`
- [x] `tools/anagrafiche_tools.py`: tool `dettaglio_soggetto` — handler wrappa `SoggettiService.get_soggetto()`
- [ ] `tools/anagrafiche_tools.py`: tool `cerca_indirizzi_soggetto` — handler wrappa GET indirizzi (Fase 3 estensione)
- [ ] `tools/anagrafiche_tools.py`: tool `cerca_contatti_soggetto` — handler wrappa GET contatti (Fase 3 estensione)
- [x] `tools/pratiche_tools.py`: tool `dettaglio_pratica` — handler wrappa `PraticheRepository.get_pratica()`
- [x] `tools/pratiche_tools.py`: tool `cerca_flussi_pratica` — handler wrappa `PraticheRepository.list_flussi()`
- [ ] `tools/pratiche_tools.py`: tool `cerca_note_pratica` — handler wrappa GET note (Fase 3 estensione)
- [x] `tools/config_tools.py`: tool `cerca_operatori` — handler wrappa `AmmSoftwareService.list_operatori()`
- [x] `route_template` definito su `cerca_soggetti` e `cerca_pratiche` per navigazione contestuale
- [ ] (Quando API pronte) `tools/vendite_tools.py`: tool `cerca_fatture`, `cerca_lotti`

**Frontend:**

- [ ] Rendering risultati lista come mini-tabella nel widget (righe cliccabili) — da valutare con provider reale
- [ ] Rendering dettaglio singolo come card informativa — da valutare con provider reale
- [ ] Troncamento risultati > 5 con link "e altri N risultati" → lista dominio con filtri

**Test:**

- [x] Unit test registrazione e schema per tutti i 6 tool (9 test)
- [x] Test conteggio totale tool registrati
- [x] Regressione suite completa: 945/945 OK
- [ ] Smoke test: query che esercitano ciascun tool (richiede provider reale)

#### Output atteso Fase 3

- Catalogo strumenti completo per tutti i domini con API stabile
- L'AI naviga trasversalmente tra domini in una singola conversazione
- Ogni risultato ha link di navigazione contestuale

---

### Fase 4 — Operazioni in scrittura con conferma

> Obiettivo: permettere all'AI di eseguire operazioni che modificano dati, sempre con conferma esplicita dell'utente. Al termine di questa fase l'AI puo' creare pratiche, cambiare stati, inserire note — ma solo dopo conferma.

#### DB

Nessuna modifica DB strutturale. La colonna `tools_called` in `ai_query_log` gia' supporta il logging di operazioni in scrittura.

Valutare se aggiungere un campo `ai_initiated BOOLEAN DEFAULT FALSE` nelle tabelle di audit (`storico.*`) per marcare le operazioni originate dall'AI. Decisione da prendere in fase di implementazione in base all'utilita' effettiva.

#### Backend

**Pattern conferma a due step**

Le operazioni in scrittura seguono un protocollo rigido:

**Step 1 — Preview (senza conferma)**

L'LLM chiama il tool con i parametri. Il tool handler:
1. Valida i parametri
2. Verifica prerequisiti (es. stato soggetto per una pratica)
3. Restituisce un **sommario dell'operazione** senza eseguirla
4. Il flag `requires_confirmation: true` segnala al frontend di mostrare il dialog di conferma

**Output del tool (preview):**

```
{
  "requires_confirmation": true,
  "confirmation_id": "uuid-temporaneo",
  "summary": "Creare pratica Allaccio Gas per Acea Energia Spa, priorita' ALTA, operatore M. Rossi",
  "details": {
    "tipo_prestazione": "ALLACCIO_GAS",
    "soggetto": "Acea Energia Spa",
    "priorita": "ALTA"
  }
}
```

**Step 2 — Conferma ed esecuzione**

L'utente conferma nel drawer. Il frontend invia un secondo messaggio con `confirmation_id`:

```
{
  "message": "__confirm__",
  "conversation_id": "uuid",
  "confirmation_id": "uuid-temporaneo"
}
```

Il service:
1. Recupera i parametri originali dalla conversazione in corso
2. Esegue l'operazione reale (chiama il service di dominio)
3. Logga con `tools_called` che include il flag `confirmed: true`

**Strumenti in scrittura previsti:**

| Tool | required_level | Descrizione | API wrappata |
|---|---|---|---|
| `crea_pratica` | `TUTTO` | Crea nuova pratica con dati base | `POST /api/v1/pratiche/pratiche/` |
| `cambia_stato_pratica` | `TUTTO` | Attiva, sospendi, chiudi pratica | `POST /api/v1/pratiche/pratiche/{id}/stato/` |
| `aggiungi_nota_pratica` | `TUTTO` | Aggiunge nota a pratica esistente | `POST /api/v1/pratiche/pratiche/{id}/note/` |
| `crea_flusso_pratica` | `TUTTO` | Aggiunge flusso operativo | `POST /api/v1/pratiche/pratiche/{id}/flussi/` |

Ogni tool in scrittura ha `required_level = TUTTO` — nessuna eccezione.

**Idempotenza**

Le operazioni in scrittura via AI usano `Idempotency-Key` generata dal service. Il `confirmation_id` diventa la chiave di idempotenza — un doppio click sulla conferma non produce duplicati.

#### Frontend

**Dialog di conferma**

Quando la risposta contiene `requires_confirmation: true`, il composable `useAiAssistant()` mostra un dialog tramite `useConfirmAction()` (gia' esistente):

- Titolo: `$t('ai.confirm_title')` — "Conferma operazione"
- Corpo: il `summary` restituito dal tool
- Bottoni: Annulla (secondary) + Conferma (primary)
- Se l'utente conferma: invio automatico del messaggio `__confirm__`
- Se annulla: messaggio nel drawer "Operazione annullata"

**Nuove chiavi i18n:**

| Chiave | it | en |
|---|---|---|
| `ai.confirm_title` | Conferma operazione | Confirm operation |
| `ai.confirm_cancel` | Operazione annullata | Operation cancelled |
| `ai.confirm_success` | Operazione completata | Operation completed |

#### Test

- Unit test pattern conferma: verifica che senza conferma il tool non esegue
- Unit test idempotenza: doppia conferma non produce duplicati
- Unit test permessi: utente LETTURA non vede tool in scrittura nel catalogo
- Smoke test: flusso completo preview → conferma → esecuzione

#### Checklist Fase 4

**DB:**

- [ ] (Valutare) Campo `ai_initiated BOOLEAN DEFAULT FALSE` nelle tabelle audit `storico.*`

**Backend:**

- [x] Pattern conferma a due step nel service: `preview()` → `requires_confirmation` + `confirmation_id` → `__confirm__` → `execute()`
- [x] Gestione `confirmation_id` nel contesto conversazione in-memory (`_pending_confirmations` dict)
- [x] `_execute_confirmation()`: recupera parametri salvati, esegue tool, logga con `confirmed: true`
- [x] `tools/pratiche_tools.py`: tool `crea_pratica` (required_level=TUTTO, requires_confirmation=True)
- [x] `tools/pratiche_tools.py`: tool `cambia_stato_pratica` (required_level=TUTTO, requires_confirmation=True)
- [x] `tools/pratiche_tools.py`: tool `aggiungi_nota_pratica` (required_level=TUTTO, requires_confirmation=True)
- [ ] `tools/pratiche_tools.py`: tool `crea_flusso_pratica` — da aggiungere (estensione)
- [x] Logging con flag `confirmed: true` per operazioni confermate
- [x] `base.py`: attributo `requires_confirmation` + metodo `preview()` nella classe base AITool

**Frontend:**

- [x] Bottoni Conferma/Annulla nel widget quando `pendingConfirmation` presente
- [x] `useAiAssistant.js`: `confirmOperation()` invia `__confirm__`, `cancelOperation()` annulla
- [x] Messaggio "Operazione annullata" nel widget se utente annulla
- [x] Chiavi i18n `ai.confirm_cancel`, `ai.confirm_success` gia' presenti da Fase 2

**Test:**

- [x] Unit test: tool in scrittura registrati con `requires_confirmation=True` e `required_level=TUTTO` (4 test)
- [x] Unit test: `preview()` restituisce summary e details (1 test)
- [x] Unit test: flusso completo conferma preview → `__confirm__` → execute (1 test)
- [x] Regressione suite completa: 951/951 OK
- [ ] Smoke test: flusso completo preview → conferma → esecuzione (richiede provider reale)

#### Output atteso Fase 4

- L'AI puo' eseguire operazioni controllate con conferma esplicita
- Nessuna operazione irreversibile senza secondo step
- Logging completo di ogni operazione AI-initiated
- Pattern replicabile per nuovi tool in scrittura

---

### Fase 5 — Multi-tool, analisi e assistente guidato

> Obiettivo: l'AI puo' orchestrare piu' strumenti in sequenza per rispondere a domande complesse, analizzare dati e guidare l'utente in operazioni multi-step. Al termine di questa fase l'AI diventa un assistente operativo completo.

#### DB

Nessuna modifica DB strutturale.

#### Backend

**Multi-tool gia' supportato**

Il loop tool_call del service (Fase 1) gia' supporta chiamate multiple. In Fase 5 si arricchisce:

- **Tool chaining intelligente**: il system prompt istruisce l'LLM su come combinare strumenti. Es. "per verificare la compliance di un fornitore, prima cerca il soggetto, poi i suoi documenti"
- **Limite iterazioni**: alzato a 8 per consentire catene piu' lunghe
- **Timeout complessivo**: 30 secondi massimi per l'intera catena. Se superato, risposta parziale con i risultati gia' ottenuti

**Assistente guidato (wizard conversazionale)**

Per operazioni complesse (es. "apri una pratica di allaccio per un nuovo cliente"), l'LLM guida l'utente step-by-step:

1. L'LLM chiede i dati mancanti in linguaggio naturale
2. L'utente risponde in linguaggio libero
3. L'LLM estrae i campi strutturati e chiede conferma
4. Dopo conferma, esegue le operazioni necessarie (crea soggetto → assegna ruolo → crea pratica)

Questo non richiede codice aggiuntivo nel backend — il loop conversazionale gia' previsto (messaggi + tool_call + risposta) supporta questo pattern naturalmente. E' una questione di system prompt e catalogo strumenti.

**Tool di analisi (opzionale, valutare utilita' reale)**

| Tool | Descrizione | Note |
|---|---|---|
| `statistiche_pratiche` | Conteggi per stato, priorita', periodo | Query aggregata sulla view pratiche |
| `pratiche_in_scadenza` | Pratiche con scadenza nei prossimi N giorni | Filtro data su endpoint esistente |

Questi tool espongono dati gia' accessibili dalla lista pratiche, ma in forma aggregata. L'analisi vera (pattern, anomalie, confronti) la fa l'LLM sui risultati — non serve codice custom per "rilevamento anomalie".

#### Frontend

**Indicatore progresso multi-step**

Quando la risposta AI indica `has_more: true`, il drawer mostra un indicatore che l'AI sta ancora elaborando (icona animata o testo "Sto analizzando i risultati...").

**Pre-compilazione form**

L'azione `prefill` permette all'AI di aprire un drawer di creazione con campi pre-compilati:

```
{
  "type": "prefill",
  "route": { "name": "pratiche-crea" },
  "data": {
    "soggetto_id": 42,
    "tipo_prestazione": "ALLACCIO_GAS",
    "priorita": "ALTA"
  }
}
```

Il composable `useAiAssistant()` fa `router.push(route)` e pubblica i dati pre-fill tramite il Pinia store. Il componente di destinazione legge lo store e popola i campi.

Questo e' un pattern nuovo che richiede coordinamento tra `aiAssistantStore` e i drawer di dominio. Da valutare se il beneficio giustifica la complessita'.

#### Test

- Test multi-tool: query che richiede 2-3 tool in sequenza
- Test timeout: verifica che il limite 30s produce risposta parziale
- Test wizard: conversazione multi-turno con estrazione parametri

#### Checklist Fase 5

**Backend:**

- [x] Alzare limite iterazioni tool_call a 8
- [x] Timeout complessivo 30s per catena multi-tool con risposta parziale
- [x] Arricchimento system prompt con istruzioni tool chaining (esempi combinazione strumenti)
- [ ] (Opzionale) Tool `statistiche_pratiche`: query aggregata per stato/priorita'/periodo
- [ ] (Opzionale) Tool `pratiche_in_scadenza`: filtro scadenza prossimi N giorni

**Frontend:**

- [x] Shortcut tastiera `Ctrl+Shift+A` per toggle widget AI (in AppLayout via useKeyboardShortcuts)
- [x] Tooltip bottone AI con shortcut visibile
- [ ] (Valutare) Azione `prefill`: pre-compilazione form via `aiAssistantStore` + `router.push()`

**Test:**

- [ ] Test multi-tool: query che richiede 2-3 tool in sequenza (richiede provider reale)
- [x] Test timeout: check nel loop implementato
- [ ] Test wizard: conversazione multi-turno con estrazione parametri (richiede provider reale)

#### Output atteso Fase 5

- L'AI gestisce query complesse che attraversano piu' domini
- Assistente guidato per operazioni multi-step
- Analisi dati su richiesta (aggregazioni, anomalie)
- Pre-compilazione form (se implementato)

---

## Matrice dipendenze aggiornata

```
                 core   config   anagr.   catal.   pratiche   vendite   ai_assistant
core              -       -        -        -        -          -          -
config           usa      -        -        -        -          -          -
anagrafiche      usa      -        -        -        -          -          -
catalogo         usa      -        -        -        -          -          -
pratiche         usa     usa      usa       -        -          -          -
vendite          usa     usa      usa      usa    (futuro)      -          -
ai_assistant     usa     usa      usa       -       usa       (futuro)     -
```

`ai_assistant` dipende dagli anelli interni. Nessun anello interno dipende da `ai_assistant`.

---

## Vincoli trasversali (tutte le fasi)

| Vincolo | Dettaglio |
|---|---|
| Feature flag | `AI_ENABLED=False` disattiva tutto. L'ERP funziona identicamente |
| Nessuna dipendenza inversa | Gli anelli interni non importano mai `ai_assistant` |
| Stesse API | L'AI chiama service/repository esistenti, non SQL diretto |
| Stessi permessi | Filtro tool per `area_funzionale` + `livello_accesso` dell'utente |
| Stessi codici errore | Pattern `E_AI_*` registrati in `error_policies.py` |
| Test CI-compatible | Provider mock, `unittest.TestCase`, nessuna chiamata rete |
| Prompt injection | Dati DB mai nel system prompt, solo come tool_result. Il contesto statico (ai-context.md) contiene solo vocabolario e regole, mai dati reali |
| GDPR | Astrazione provider, il cliente sceglie dove girano i dati. Per embedding: possibilita' di usare modello locale |
| i18n | Tutte le stringhe UI sotto namespace `ai.*`, it + en |
| Knowledge base | Il contesto statico (2.5a) non richiede infrastruttura. Il RAG (2.5b) richiede pgvector e un provider embedding |
| Indicizzazione docs | Incrementale (hash-based), eseguita manualmente o in CI, mai real-time |

---

## Quando iniziare

L'integrazione AI non ha dipendenze bloccanti. Puo' iniziare in qualsiasi momento perche':

1. Non modifica anelli interni
2. Usa API gia' stabili (pratiche, soggetti, config)
3. E' disattivabile con un flag
4. I test usano provider mock

L'unico prerequisito pratico e' che almeno un dominio abbia API di lettura stabili su cui costruire il primo tool — e le **pratiche** sono gia' in quello stato (26 endpoint, 115 test).

La crescita del catalogo strumenti segue naturalmente la crescita delle API di dominio: ogni nuovo endpoint REST di Anello 1-3 e' un potenziale nuovo tool per l'AI. Analogamente, ogni nuova pagina di documentazione viene automaticamente indicizzata e resa disponibile al tool `cerca_documentazione` al prossimo run di `index_docs`.

---

*Documento WIP — piano soggetto a revisione durante l'implementazione.*
