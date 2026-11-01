# API Fornitori (Anagrafiche)

## Scopo

Endpoint REST per la gestione dei fornitori. Il fornitore e' un ruolo specializzato
del soggetto base (pattern `soggetti → soggetti_ruoli → fornitori`, relazione 1:1
via `soggetto_ruolo_id`).

## Contesto

Tutti gli endpoint risiedono sotto `/api/v1/anagrafiche/fornitori/`.
L'autenticazione avviene tramite token JWT (`Authorization: Bearer <token>`).
Le risposte seguono l'envelope standard `{"data": ...}`.
La view usa `DomainAPIView` con `area_funzionale = "anagrafiche"` e permesso
`model_permission = ("anagrafiche", "fornitore")` (tutti gli endpoint, export compreso).

## Base URL

```
/api/v1/anagrafiche/fornitori/
```

## Dipendenze DB

| Oggetto | Tipo | Ruolo |
| --- | --- | --- |
| `anagrafiche.fornitori` | Tabella | Tabella master fornitore |
| `anagrafiche.vw_fornitori_dettaglio` | Vista | Source per lista/search (join soggetto + config) |
| `config.stati_fornitore` | Tabella | Stati operativi (VE, AT, SO, CE, BL) |
| `anagrafiche.fn_crea_fornitore` | Funzione | Creazione in un'istruzione: ruolo FO (get or create), fornitore in stato `VE`, contatto e indirizzi del ruolo |
| `config.sistema_codici` + `script.fn_generate_codice` | Funzione | Auto-generazione codice fornitore |
| `anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required` | Trigger | Verifica indirizzi obbligatori su assegnazione ruolo |

---

## 1. Lista fornitori

Restituisce l'elenco paginato dei fornitori con ricerca full-text e filtri.

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/fornitori/` |
| **Throttling** | `is_search_endpoint = True` |

### Parametri query

| Parametro | Tipo | Obbligatorio | Descrizione |
| --- | --- | --- | --- |
| `search` | string | No | Ricerca full guidata dal catalogo `anagrafiche.fornitori` sui campi `codice`, `ragione_sociale_completa`, `id_fiscale_univoco_cf_piva` |
| `stato_fornitore_id` | int | No | Filtra per stato operativo (FK `config.stati_fornitore`) |
| `attivo` | bool | No | Filtra per flag attivo (`true`/`false`). Se omesso: nessun filtro |
| `limit` | int | No | Risultati per pagina (default: 25, max: 200) |
| `offset` | int | No | Offset per paginazione |
| `order_by` | string | No | Campo di ordinamento (default: `ragione_sociale_completa`) |
| `order_dir` | string | No | Direzione: `asc` o `desc`. Se omessa: `asc`, salvo le colonne data (`data_insert`, `data_update`) che partono `desc` |

**Colonne ordinabili:** `codice`, `ragione_sociale_completa`, `id_fiscale_univoco_cf_piva`,
`stato_descrizione`, `modalita_pagamento_desc`, `data_insert`, `data_update`
(`codice_fiscale`, `partita_iva` e `attivo` non sono ordinabili). Un valore fuori
whitelist ripiega sul default.

### Risposta (200)

> **Naming (2026-06-28)**: `stato_codice_interno` è il codice **immutabile** dello stato
> (per la logica/severity: `AT`/`SO`/`CE`/…); `stato_codice` porta il `codice` **mutabile**
> (display). Per il display preferire `stato_descrizione`. Vedi linee-guida-sql.md §6c.

```json
{
  "data": {
    "count": 42,
    "page": 1,
    "page_size": 25,
    "total_pages": 2,
    "results": [
      {
        "id": 1,
        "soggetto_ruolo_id": 50,
        "codice": "FO-000001",
        "attivo": true,
        "stato_codice_interno": "AT",
        "stato_codice": "AT",
        "stato_descrizione": "Attivo",
        "blocca_ordini": false,
        "soggetto_id": "a1b2c3d4-...",
        "ragione_sociale_completa": "Acme Srl",
        "codice_fiscale": "01234567890",
        "partita_iva": "01234567890",
        "id_fiscale_univoco_cf_piva": "01234567890",
        "valuta_iso": "EUR",
        "modalita_pagamento_codice": "BB",
        "modalita_pagamento_desc": "Bonifico Bancario",
        "termine_pagamento_codice": "30GG",
        "giorni_pagamento": 30,
        "fine_mese": true,
        "split_payment": false,
        "ritenuta_acconto": false,
        "regime_fiscale": "RF01",
        "rating": 80,
        "qualifica_scadenza": null,
        "canale_fe": "0000000",
        "pec_email": "acme@pec.it",
        "data_insert": "2026-01-15T10:30:00+01:00",
        "data_update": "2026-03-20T14:00:00+01:00"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

---

## 2. Crea fornitore

Crea un fornitore con un'unica chiamata a `anagrafiche.fn_crea_fornitore`
(atomica): assegna il ruolo FO al soggetto (get or create), inserisce il record
fornitore con stato iniziale `VE` (In verifica), il contatto del ruolo (se
presente) e gli indirizzi del ruolo.

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/fornitori/` |
| **Body** | JSON |
| **Handler** | `handle_post_json` |

### Prerequisiti

- Il soggetto deve esistere
- Il soggetto deve avere tutti gli indirizzi obbligatori definiti nella matrice
  `config.tipi_ruolo_tipi_indirizzo` per il tipo ruolo FORNITORE (verificato
  dal trigger DB `trgfn_soggetti_ruoli_guard_indirizzi_required`)

### Parametri body

| Campo | Tipo | Obbligatorio | Descrizione |
| --- | --- | --- | --- |
| `soggetto_id` | UUID | **Si** | ID del soggetto base |
| `codice` | string | No | Codice fornitore; se omesso lo genera `config.sistema_codici` |
| `valuta_id` | int | No | FK `config.valute` |
| `modalita_pagamento_id` | int | No | FK `config.modalita_pagamento` |
| `termine_pagamento_id` | int | No | FK `config.termini_pagamento` |
| `giorni_pagamento` | int | No | Giorni pagamento (override manuale) |
| `fine_mese` | bool | No | Scadenza a fine mese |
| `split_payment` | bool | No | Split payment attivo |
| `ritenuta_acconto` | bool | No | Soggetto a ritenuta d'acconto |
| `ritenuta_aliquota` | float | No | Aliquota ritenuta (obbligatoria se `ritenuta_acconto = true`, validato da trigger DB) |
| `regime_fiscale` | string | No | Codice regime fiscale SDI (es. `RF01`) |
| `bollo_esente` | bool | No | Esente da bollo |
| `canale_fe` | string | No | Codice destinatario SDI (7 caratteri, normalizzato uppercase dal trigger) |
| `pec_email` | string | No | PEC per fatturazione elettronica (normalizzata lowercase dal trigger) |
| `rating` | int | No | Rating qualifica 0-100 |
| `qualifica_scadenza` | date | No | Data scadenza qualifica (ISO 8601) |
| `note` | string | No | Note libere |
| `contatto` | object | No | Contatto del ruolo (`nominativo`, `tipo_contatto_id`, `email`, `telefono`, `cellulare`, `pec`, `unita_organizzativa_id`, `note`); vedi regola sotto |
| `indirizzi` | array | No | Indirizzi del ruolo (stessa grammatica degli indirizzi ruolo: `tipo_indirizzo_codice_interno` + indirizzo libero, `indirizzo_dettaglio_id` o via da risolvere). Non lista → 400 `E_ANAG_VALIDAZIONE` |

I booleani vanno inviati come booleani JSON (`true`/`false`); stringhe o numeri → 400 `E_VALIDATION_INPUT`.
Le stringhe vuote e i `null` valgono come campo assente (default DB).

### Risposta (200)

```json
{
  "data": {
    "id": 1,
    "soggetto_ruolo_id": 50
  },
  "meta": { "request_id": "..." }
}
```

### Errori

| Codice | HTTP | Causa |
| --- | --- | --- |
| `E_ANAG_VALIDAZIONE` | 400 | `soggetto_id` mancante o non valido; `indirizzi` non lista; elemento indirizzo non oggetto |
| `E_ANAG_DUPLICATO` | 409 | Il soggetto ha gia' il ruolo FORNITORE |
| `E_INDIRIZZO_OBBLIGATORIO_MANCANTE` | 400 | Indirizzi obbligatori mancanti per il ruolo FO (trigger DB) |
| `E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA` | 400 | `ritenuta_acconto = true` senza `ritenuta_aliquota > 0` (trigger DB `trgfn_fornitori_guard_normalize`) |
| `E_CONTATTO_INCOMPLETO` | 400 | Payload `contatto` parziale: almeno un campo valorizzato MA mancano `nominativo` o `tipo_contatto_id`. Il `context.missing` lista i campi mancanti |

#### Regola contatto inline (refactor 28-04-2026)

Il contatto e' opzionale per il fornitore. Stati possibili applicati da
`classify_contatto_payload`:

- `EMPTY` (nessun campo valorizzato) → contatto NON creato, fornitore
  creato senza contatto inline
- `PARTIAL` (campi valorizzati MA mancano `nominativo`/`tipo_contatto_id`)
  → solleva `E_CONTATTO_INCOMPLETO` (sostituisce il vecchio silent
  skip che faceva perdere dati)
- `VALID` (`nominativo` + `tipo_contatto_id` presenti) → procede

#### Normalizzazione fiscale automatica (trigger DB)

Il trigger `trgfn_fornitori_guard_normalize` applica:

- `canale_fe` → uppercase senza spazi
- `pec_email` → lowercase trimmed
- se `ritenuta_acconto = false` → `ritenuta_aliquota` forzato a `NULL`
- se `ritenuta_acconto = true` con aliquota non valida → solleva
  `E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA`

---

## 3. Dettaglio fornitore

Restituisce il dettaglio completo di un fornitore con dati soggetto e decodifiche FK.

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/fornitori/{fornitore_id}/` |

### Risposta (200)

```json
{
  "data": {
    "id": 1,
    "uid": "019bac81-0000-...",
    "codice": "FO-000001",
    "attivo": true,
    "soggetto_ruolo_id": 50,
    "stato_fornitore_id": 2,
    "soggetto_id": "a1b2c3d4-...",
    "ragione_sociale_completa": "Acme Srl",
    "codice_fiscale": "01234567890",
    "partita_iva": "01234567890",
    "valuta_id": 1,
    "valuta_iso": "EUR",
    "modalita_pagamento_id": 3,
    "modalita_pagamento_descrizione": "Bonifico Bancario",
    "termine_pagamento_id": null,
    "termine_pagamento_descrizione": null,
    "giorni_pagamento": 30,
    "fine_mese": true,
    "split_payment": false,
    "ritenuta_acconto": false,
    "ritenuta_aliquota": null,
    "regime_fiscale": "RF01",
    "bollo_esente": false,
    "canale_fe": "0000000",
    "pec_email": "acme@pec.it",
    "rating": 80,
    "qualifica_scadenza": null,
    "stato_codice_interno": "AT",
    "stato_codice": "AT",
    "stato_descrizione": "Attivo",
    "blocca_ordini": false,
    "note": null,
    "data_insert": "2026-01-15T10:30:00+01:00",
    "data_update": "2026-03-20T14:00:00+01:00"
  },
  "meta": { "request_id": "..." }
}
```

### Errori

| Codice | HTTP | Causa |
| --- | --- | --- |
| `E_ANAG_NOT_FOUND` | 404 | Fornitore con id indicato non trovato |

---

## 4. Aggiorna fornitore

Aggiornamento parziale (delta) dei campi editabili del fornitore.
Solo i campi inclusi nel payload vengono modificati. Il corpo deve essere un
oggetto JSON con sole chiavi della tabella sotto: una chiave fuori contratto → 400.

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/anagrafiche/fornitori/{fornitore_id}/` |
| **Body** | JSON oggetto |

### Campi editabili

| Campo | Tipo | Note |
| --- | --- | --- |
| `stato_fornitore_id` | int | FK `config.stati_fornitore` (trigger require_attivo) |
| `attivo` | bool | Flag attivazione |
| `valuta_id` | int | Nullable |
| `modalita_pagamento_id` | int | Nullable |
| `termine_pagamento_id` | int | Nullable (trigger require_attivo) |
| `giorni_pagamento` | int | Nullable |
| `fine_mese` | bool | |
| `split_payment` | bool | |
| `ritenuta_acconto` | bool | |
| `ritenuta_aliquota` | float | Nullable (obbligatoria se ritenuta_acconto, trigger DB) |
| `regime_fiscale` | string | Nullable |
| `bollo_esente` | bool | |
| `canale_fe` | string | Nullable, 7 char, uppercase (trigger normalize) |
| `pec_email` | string | Nullable, lowercase (trigger normalize) |
| `rating` | int | Nullable, 0-100 (check DB) |
| `qualifica_scadenza` | date | Nullable |
| `note` | string | Nullable |

**Normalizzazione:** le stringhe vuote nei campi nullable vengono convertite a `NULL`.

### Risposta (200)

```json
{
  "data": { "updated": true },
  "meta": { "request_id": "..." }
}
```

### Errori

| Codice | HTTP | Causa |
| --- | --- | --- |
| `E_ANAG_VALIDAZIONE` | 400 | Chiave fuori contratto; corpo vuoto (dal 2026-10-14: prima 404) |
| `E_VALIDATION_INPUT` | 400 | Corpo non JSON o non oggetto |
| `E_ANAG_NOT_FOUND` | 404 | Fornitore non trovato |

---

## Regole di business (DB-first)

Le seguenti regole sono gestite dal database tramite trigger e vincoli, non dal
backend Python:

| Regola | Oggetto DB |
| --- | --- |
| Validazione ruolo FO | `trgfn_fornitori_guard_ruolo_fornitore` |
| Normalizzazione canale_fe (uppercase) e pec_email (lowercase) | `trgfn_fornitori_guard_normalize` |
| Coerenza ritenuta (aliquota obbligatoria se ritenuta_acconto = true) | `trgfn_fornitori_guard_normalize` |
| Blocco modifica codice | `script.trgfn_lock_columns('codice')` |
| Blocco delete senza GUC | `script.trgfn_delete_block_by_guc('zeroerp.maintenance_ruoli_delete')` |
| Require attivo su stato_fornitore_id | `dbops.trgfn_child_requires_active_parent` |
| Require attivo su termine_pagamento_id | `dbops.trgfn_child_requires_active_parent` |
| Indirizzi obbligatori per ruolo FO | `trgfn_soggetti_ruoli_guard_indirizzi_required` |
| Rating range 0-100 | `chk_fornitori_rating` |
| Ritenuta aliquota range | `chk_fornitori_ritenuta_aliquota` |
| Canale FE lunghezza 7 | `chk_fornitori_canale_fe_len` |
| Auto-generazione codice | `config.sistema_codici` + `script.fn_generate_codice` |
| Storicizzazione | `script.trgfn_storico_generic('fornitori_id')` |
| Audit timestamp/user | `script.trgfn_audit_data_user_generic` |

## Note di migrazione

Nessuna — gli endpoint sono nuovi, non sostituiscono API esistenti.
