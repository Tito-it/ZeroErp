# API Categorie Clienti (Anagrafiche)

## Scopo

Endpoint REST per la gestione delle **categorie cliente** (STANDARD, BASE, SILVER,
GOLD, PLATINUM). Le categorie sono contenitori commerciali trasversali che
segmentano i `billing_account` per politica di pricing.

La categoria determina (via la matrice `anagrafiche.categorie_clienti_listini`)
a quale listino e con quale variazione di prezzo un BA senza contratto individuale
viene mappato. E` la dimensione principale dello **STADIO 2** del resolver
prezzi v5. Il flag `partecipa_promo` abilita/disabilita l'applicazione della
promo overlay (STADIO 0).

Vedi anche:
* [sviluppo-listini-v5.md §4.1](/dev/work-done/sviluppo-listini-v5) — specifica funzionale
* [anagrafiche.categorie_clienti](/dbzero/anagrafiche/tabelle/categorie_clienti) — schema DB

## Contesto

Tutti gli endpoint risiedono sotto `/api/v1/anagrafiche/categorie-clienti/` e
sono implementati in:

- `apps/anagrafiche/api/views_categorie_clienti.py`
- `apps/anagrafiche/services/categorie_clienti_service.py`
- `apps/anagrafiche/db/categorie_clienti_repository.py`

L'autenticazione avviene tramite token JWT (`Authorization: Bearer <token>`).
Le risposte seguono l'envelope standard `{"data": ..., "meta": {...}}` per il
successo e `{"error": {"code": "...", "message": "..."}, "meta": {...}}` per gli
errori.

**Accesso riservato agli amministratori**: tutte le view ereditano da
`AdminAPIView` (`apps.core.api.base_views`), che applica `IsAdminZeroERP`
(superuser Django o binding `SUPER_ADMIN`). Un utente non admin riceve
`403 E_ACCESSO_RISERVATO_ADMIN`.

## Lookup generico — preferire dove possibile

Per dropdown / selezioni "scegli categoria" nelle UI NON creare endpoint dedicati:
la tabella `anagrafiche.categorie_clienti` e` nella lista del lookup generico
(`config.tabelle_gestibili`, colonna `lookup`) e accessibile via:

```text
GET /api/v1/core/lookup/codici/?rel=anagrafiche.categorie_clienti
```

Gli endpoint qui documentati sono **CRUD admin** — non vanno usati per popolare
dropdown nei form cliente/BA.

## Base URL

```text
/api/v1/anagrafiche/categorie-clienti/
```

## Headers comuni

| Header | Valore | Note |
| --- | --- | --- |
| `Authorization` | `Bearer <jwt>` | Token di accesso valido (superuser o utente `SUPER_ADMIN`) |
| `Content-Type` | `application/json` | Richiesto per POST/PATCH |
| `Accept` | `application/json` | Opzionale, default JSON |

## Sommario endpoint

| # | Metodo | URL | Descrizione |
| --- | --- | --- | --- |
| 1 | `GET`   | `/categorie-clienti/` | Lista paginata + filtri + ordinamento |
| 2 | `POST`  | `/categorie-clienti/` | Crea categoria |
| 3 | `GET`   | `/categorie-clienti/<id>/` | Dettaglio |
| 4 | `PATCH` | `/categorie-clienti/<id>/` | Aggiorna categoria (codice immutabile) |

## Codici errore (envelope `{"error": {"code", "message"}}`)

| Codice | HTTP | Descrizione |
| --- | --- | --- |
| `E_NOT_AUTHENTICATED` | 401 | Token JWT mancante |
| `E_AUTHENTICATION_FAILED` | 401 | Token JWT non valido o scaduto |
| `E_ACCESSO_RISERVATO_ADMIN` | 403 | Utente autenticato ma non admin |
| `E_ANAG_VALIDAZIONE` | 400 | Payload non valido (campi obbligatori mancanti, tipi errati, boundary violati) |
| `E_ANAG_NOT_FOUND` | 404 | Categoria inesistente |
| `E_ANAG_DUPLICATO` | 409 | Vincolo univocita` violato (`codice` duplicato) |

Eccezioni inattese vengono normalizzate dal middleware in envelope
`{"error": {"code": "E_INTERNAL", ...}}` con HTTP 500.

Validazione payload e traduzione vincoli DB delegate al building block
`apps.core.services.payload_helpers` (`PayloadValidator`,
`map_integrity_error`). Vedi
[catalogo-building-block-backend.md](/dev/backend/catalogo-building-block-backend).

## Dipendenze DB

| Oggetto | Tipo | Ruolo |
| --- | --- | --- |
| `anagrafiche.categorie_clienti` | Tabella | Master categorie |
| `uq_categorie_clienti_codice` | UNIQUE | Garanzia univocita` codice (mappata su `E_ANAG_DUPLICATO`) |
| `codice_interno` + `uq_categorie_clienti_codice_interno` | Colonna + UNIQUE | Chiave logica **immutabile** (NOT NULL, lockata). Valorizzata dal BE `= codice` alla create (qui `codice` è già immutabile, quindi i due coincidono). Non esposta dal CRUD; serve la logica di sistema che deve poggiare su una chiave stabile (convenzione `codice_interno`/`codice`, vedi `analisi-hardcoded-codice.md`). |
| `anagrafiche.billing_account.categoria_cliente_id` | FK | Ogni BA ha una categoria (v5) |
| `anagrafiche.categorie_clienti_listini.categoria_cliente_id` | FK | Matrice categoria → listino (v5) |

---

## 1. Lista categorie

| | |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/categorie-clienti/` |

### Query param

| Parametro | Tipo | Obbligatorio | Descrizione |
| --- | --- | --- | --- |
| `search` | string | No | Ricerca ILIKE sulle colonne (fra `codice` e `descrizione`) che il catalogo della lista `anagrafiche.categorie_clienti` accende; sotto la soglia del catalogo non filtra (nessun 400) |
| `attivo` | bool | No | Filtro flag attivo. `true`/`false`/`1`/`0`/`yes`/`no`. Stringa vuota (`attivo=`) equivale a chiave assente (nessun filtro); altro valore -> 400 |
| `partecipa_promo` | bool | No | Filtro flag partecipazione promo (stesso contratto di `attivo`) |
| `limit` | int | No | Righe per pagina, default `25`, max `200` |
| `offset` | int | No | Righe da saltare, default `0` (la risposta riporta `page`/`page_size` calcolati da `limit`/`offset`) |
| `order_by` | string | No | `codice` \| `descrizione` \| `ordinamento` \| `partecipa_promo` \| `attivo` \| `data_insert` \| `data_update`. Default: `ordinamento` |
| `order_dir` | string | No | `asc` oppure `desc`. Assente: `asc`, salvo le colonne data (`data_insert`, `data_update`) che partono `desc` |

### Risposta (200)

```json
{
  "data": {
    "count": 5,
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
    "results": [
      {
        "id": 1,
        "codice": "STANDARD",
        "descrizione": "Cliente standard",
        "partecipa_promo": false,
        "ordinamento": 10,
        "meta": {},
        "attivo": true,
        "data_insert": "2026-04-14T00:00:00+02:00",
        "user_insert": "titodb",
        "data_update": "2026-04-14T00:00:00+02:00",
        "user_update": "titodb"
      }
    ]
  },
  "meta": {"request_id": "..."}
}
```

### Note implementative

- Paginazione deterministica: `ORDER BY <campo> <dir>, cc.id ASC` (tiebreaker su `id`).
- Validazione `order_by` contro whitelist lato service: `E_ANAG_VALIDAZIONE` se valore non ammesso.

---

## 2. Crea categoria

| | |
| --- | --- |
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/categorie-clienti/` |

### Body JSON

| Campo | Tipo | Obbligatorio | Default DB | Descrizione |
| --- | --- | --- | --- | --- |
| `codice` | string | Si | — | Codice univoco (max 32 char). Convertito con trim. **Immutabile** dopo create |
| `descrizione` | string | Si | — | Descrizione UI (max 255 char). Trim |
| `partecipa_promo` | bool | No | `true` | Abilita promo overlay (STADIO 0 resolver) |
| `ordinamento` | int | No | `100` | Ordine display UI, range `[0, 32767]` |
| `meta` | object | No | `{}` | Metadati liberi. `null` esplicito -> reset a `{}`. Stringa JSON valida ammessa (parse server-side). Non-dict e JSON invalido rifiutati |
| `attivo` | bool | No | `true` | Flag abilitazione |

### Esempio request

```json
{
  "codice": "VIP",
  "descrizione": "Cliente VIP",
  "partecipa_promo": true,
  "ordinamento": 60
}
```

### Risposta (200)

Restituisce il dettaglio completo della categoria creata (stesso formato di `GET detail`).

### Errori tipici

- `400` `E_ANAG_VALIDAZIONE`:
  - `codice` o `descrizione` mancanti / stringa vuota
  - `codice` > 32 char o `descrizione` > 255 char
  - `partecipa_promo` / `attivo` non booleani stretti (rifiuta `"true"`, `1`, `0`)
  - `ordinamento` fuori range `[0, 32767]` o non numerico
  - `meta` non oggetto JSON / JSON invalido / lista
  - Campi sconosciuti nel payload
- `409` `E_ANAG_DUPLICATO`: `codice` gia` esistente

---

## 3. Dettaglio categoria

| | |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/categorie-clienti/<id>/` |

### Risposta (200)

```json
{
  "data": {
    "id": 3,
    "codice": "SILVER",
    "descrizione": "Cliente silver",
    "partecipa_promo": true,
    "ordinamento": 30,
    "meta": {},
    "attivo": true,
    "data_insert": "2026-04-14T00:00:00+02:00",
    "user_insert": "titodb",
    "data_update": "2026-04-14T00:00:00+02:00",
    "user_update": "titodb"
  }
}
```

### Errori tipici

- `404` `E_ANAG_NOT_FOUND`: id inesistente

---

## 4. Aggiorna categoria

| | |
| --- | --- |
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/anagrafiche/categorie-clienti/<id>/` |

### Body JSON

Campi ammessi (tutti opzionali; almeno uno deve essere presente):

| Campo | Tipo | Nullable | Descrizione |
| --- | --- | --- | --- |
| `descrizione` | string | No | Nuova descrizione (trim + max 255) |
| `partecipa_promo` | bool | No | Se presente, non puo` essere `null` |
| `ordinamento` | int | No | Se presente, non puo` essere `null`. Range `[0, 32767]` |
| `meta` | object | Si | `null` esplicito -> reset a `{}` |
| `attivo` | bool | No | Se presente, non puo` essere `null` |

### Regole specifiche

- `codice` e` immutabile a livello API: inviarlo nel payload provoca `400 E_ANAG_VALIDAZIONE`
  con messaggio esplicito "Il codice della categoria e' immutabile." Per rinominare
  una categoria, disattivare la vecchia e crearne una nuova.
- Payload vuoto (`{}`) -> `400 E_ANAG_VALIDAZIONE`.

### Errori tipici

- `400` `E_ANAG_VALIDAZIONE`:
  - `codice` nel payload
  - Payload vuoto
  - `partecipa_promo`/`ordinamento`/`attivo` = `null`
  - Valori fuori tipo / fuori range
- `404` `E_ANAG_NOT_FOUND`: id inesistente
- `409` `E_ANAG_DUPLICATO`: vincolo univocita` violato (non dovrebbe capitare in update — `codice` immutabile — mappato per robustezza)

---

## Regole trasversali

- Tutti gli endpoint richiedono JWT.
- Tutti gli endpoint sono admin-only: utente non admin -> `403 E_ACCESSO_RISERVATO_ADMIN`.
- Le view write (`POST`, `PATCH`) usano il pattern core `handle_post_json(...)` per POST e delegate diretta al service per PATCH.
- Error envelope uniforme dal middleware `api_exception_middleware`.
- Paginazione deterministica con tiebreaker `id ASC` lato repository.

## Note di migrazione

- **Sprint v5 Fase 2 BE (F2-BE-01, 14-04-2026)**: creazione CRUD admin end-to-end.
  Tabella introdotta dalla migrazione DB `20260414-01-create-categorie-clienti`
  con seed CSV in `db/changelog/migrations_v2/80_data/sql/anagrafiche/categorie_clienti.csv`
  (5 categorie: STANDARD, BASE, SILVER, GOLD, PLATINUM). Collegamento a
  `billing_account.categoria_cliente_id` con backfill a `STANDARD` e `SET NOT NULL`
  (migrazioni `20260414-02/-03`). Whitelist lookup aggiunta in `dbops_repository`
  (step F1-DB-03 v5, completato nel service).
