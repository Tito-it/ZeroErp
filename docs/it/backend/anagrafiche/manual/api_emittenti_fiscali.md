# API Emittenti Fiscali (Anagrafiche)

## Scopo

Endpoint REST per la gestione degli **emittenti fiscali**. L'emittente fiscale e' un
ruolo specializzato del soggetto base (pattern `soggetti -> soggetti_ruoli -> emittenti_fiscali`,
relazione 1:1 via `soggetto_ruolo_id`, codice ruolo `EF`).

Rappresenta l'identita' fiscale che compare nei documenti emessi dal sistema e
consente la gestione **multi-emittente** (piu' soggetti emittenti nella stessa istanza).

## Contesto

Tutti gli endpoint risiedono sotto `/api/v1/anagrafiche/emittenti-fiscali/`.

L'autenticazione avviene tramite token JWT (`Authorization: Bearer <token>`).
Le risposte seguono l'envelope standard `{"data": ...}` per il successo
e `{"error": {"code": "...", "message": "..."}}` per gli errori.

**Accesso riservato agli amministratori**: tutte le view ereditano da `AdminAPIView`
(`apps.core.api.base_views`), che applica `IsAdminZeroERP` (controllo diretto su
`ruolo_sistema = "ADMIN"` con bypass del resolver aree). Un utente non admin
riceve `403 Forbidden`.

## Base URL

```text
/api/v1/anagrafiche/emittenti-fiscali/
```

## Headers comuni

| Header | Valore | Note |
| --- | --- | --- |
| `Authorization` | `Bearer <jwt>` | Token di accesso valido (utente con `ruolo_sistema = ADMIN`) |
| `Content-Type` | `application/json` | Richiesto per POST/PATCH |
| `Accept` | `application/json` | Opzionale, default JSON |

## Sommario endpoint

| # | Metodo | URL | Descrizione |
| --- | --- | --- | --- |
| 1 | `GET` | `/emittenti-fiscali/` | Lista paginata + filtro `attivo` |
| 2 | `GET` | `/emittenti-fiscali/<id>/` | Dettaglio emittente |
| 3 | `POST` | `/emittenti-fiscali/` | Crea emittente |
| 4 | `PATCH` | `/emittenti-fiscali/<id>/` | Aggiorna emittente |
| 5.1 | `GET` | `/emittenti-fiscali/<id>/billing-account/` | Lista mapping BA |
| 5.2 | `POST` | `/emittenti-fiscali/<id>/billing-account/` | Crea mapping BA o default globale |
| 5.3 | `DELETE` | `/emittenti-fiscali/<id>/billing-account/<mapping_id>/` | Elimina mapping BA |
| 5.4 | `GET` | `/emittenti-fiscali/<id>/billing-account/summary/` | Summary mapping (has_default + count_specifici) |
| 6.1 | `GET` | `/emittenti-fiscali/<id>/utilities/` | Lista record utility per emittente |
| 6.2 | `POST` | `/emittenti-fiscali/<id>/utilities/` | Crea record utility |
| 6.3 | `PATCH` | `/emittenti-fiscali/<id>/utilities/<record_id>/` | Aggiorna record utility |
| 6.4 | `DELETE` | `/emittenti-fiscali/<id>/utilities/<record_id>/` | Elimina record utility |

## Codici errore (envelope `{"error": {"code", "message"}}`)

| Codice | HTTP | Descrizione |
| --- | --- | --- |
| `E_AUTH_REQUIRED` | 401 | Token JWT mancante o non valido |
| `E_FORBIDDEN_ROLE` | 403 | Utente autenticato ma non admin |
| `E_ANAG_VALIDAZIONE` | 400 | Campi obbligatori mancanti o non validi |
| `E_ANAG_NOT_FOUND` | 404 | Risorsa non trovata o non appartenente al padre |
| `E_ANAG_DUPLICATO` | 409 | Vincolo univocita' violato (codice, soggetto, default) |

> Eccezioni inattese vengono normalizzate dal middleware
> [api_exception_middleware](../../core/manual/api_exception_middleware.md) in
> envelope `{"error": {"code": "E_INTERNAL", ...}}` con HTTP 500.

## Dipendenze DB

| Oggetto | Tipo | Ruolo |
| --- | --- | --- |
| `anagrafiche.emittenti_fiscali` | Tabella | Master emittente |
| `anagrafiche.emittenti_fiscali_billing_account` | Tabella | Mapping BA -> emittente (sub-resource sezione 5) |
| `anagrafiche.emittenti_fiscali_utilities` | Tabella | Parametri fatturazione per coppia emittente x utility (sezione 6) |
| `anagrafiche.soggetti_ruoli` | Tabella | Legame ruolo soggetto (codice `EF`) |
| `anagrafiche.soggetti` | Tabella | Display fields (ragione sociale, CF, P.IVA) |
| `config.utilities` | Tabella | Lookup utility (sezione 6) |
| `config.utilities_tipi_ruolo` | Tabella | Matrice utility ammesse per ruolo (fail-open) |
| `config.valute` | Tabella | Lookup valuta (display ISO) |
| `script.fn_get_or_create_soggetto_ruolo` | Funzione | Crea ruolo `EF` se non esiste |
| `anagrafiche.trgfn_emittenti_fiscali_default_bootstrap` | Trigger | Inserisce default mapping `is_default=true, billing_account_id=NULL` alla creazione del primo emittente |
| `anagrafiche.trgfn_emittenti_fiscali_normalize` | Trigger | Normalizzazione INSERT/UPDATE |
| `anagrafiche.trgfn_emittenti_fiscali_guard_ruolo_emi_fis` | Trigger | Coerenza ruolo `EF` |
| `anagrafiche.trgfn_emittenti_fiscali_guard_attivo` | Trigger | Blocca disattivazione se esistono figli (BA mapping, utilities, parameter_overrides, user_emittenti_fiscali) |
| `anagrafiche.trgfn_emittenti_fiscali_default_guard` | Trigger | Garantisce un solo default globale in `emittenti_fiscali_billing_account` |
| `dbops.trgfn_child_requires_active_parent` | Trigger | Per `emittenti_fiscali_utilities` impedisce inserire/aggiornare un record figlio se il padre `emittenti_fiscali` non e' attivo |
| `script.trgfn_lock_columns` | Trigger | Rende immutabile `codice` in UPDATE |
| `script.trgfn_audit_data_user_generic` | Trigger | Popola `data_insert/update`, `user_insert/update` |

---

## 1. Lista emittenti fiscali

Restituisce l'elenco paginato degli emittenti fiscali con ricerca full-text e
filtro opzionale per stato attivo.

| | |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/` |
| **Throttling** | `is_search_endpoint = True` (DRF rate limit per ricerca) |

### 1.1 Parametri query

| Parametro | Tipo | Obbligatorio | Default | Descrizione |
| --- | --- | --- | --- | --- |
| `search` | string | No | — | Ricerca ILIKE su `codice`, `descrizione`, `ragione_sociale_completa`, `P.IVA`, `CF` |
| `attivo` | bool | No | — | Filtra per flag attivo (`true`/`false`). Se omesso: nessun filtro |
| `limit` | int | No | 25 | Risultati per pagina (max: 200) |
| `offset` | int | No | 0 | Offset per paginazione |
| `order_by` | string | No | `descrizione` | Campo di ordinamento (vedi sotto) |
| `order_dir` | string | No | `asc` | Direzione: `asc` / `desc` |

**Colonne ordinabili:** `codice`, `descrizione`, `ragione_sociale_completa`,
`attivo`, `data_insert`.

### 1.2 Esempio cURL

```bash
curl -X GET "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/?search=ACME&attivo=true&limit=10" \
     -H "Authorization: Bearer $TOKEN"
```

### 1.3 Risposta (200)

```json
{
  "data": {
    "count": 1,
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
    "results": [
      {
        "id": 1,
        "uid": "019bac81-3f96-7ce8-a086-7e0bd0a2fec1",
        "soggetto_ruolo_id": 50,
        "codice": "EF-001",
        "descrizione": "Sede principale",
        "attivo": true,
        "regime_fiscale_rf": "RF01",
        "esigibilita_iva_default": "I",
        "split_payment_default": false,
        "bollo_auto": true,
        "bollo_soglia": 77.47,
        "rounding_policy": "HALF_UP",
        "valuta_id": 1,
        "valuta_iso": "EUR",
        "soggetto_id": "019bac81-3f96-7ce8-a086-7e0bd0a2fec0",
        "ragione_sociale_completa": "ACME S.p.A.",
        "codice_fiscale": "01234567890",
        "partita_iva": "01234567890",
        "data_insert": "2026-04-07T10:00:00Z",
        "data_update": "2026-04-07T10:00:00Z"
      }
    ]
  }
}
```

---

## 2. Dettaglio emittente fiscale

| | |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/` |

Restituisce lo stesso oggetto della lista, con in piu' `valuta_descrizione` e
`brand_meta` (jsonb opzionale per branding/metadati emittente).

### 2.1 Esempio cURL

```bash
curl -X GET "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/1/" \
     -H "Authorization: Bearer $TOKEN"
```

### 2.2 Errori specifici

| Codice | HTTP | Descrizione |
| --- | --- | --- |
| `E_ANAG_NOT_FOUND` | 404 | Emittente fiscale non trovato |

---

## 3. Crea emittente fiscale

| | |
| --- | --- |
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/` |

### 3.1 Body richiesta

| Campo | Tipo | Obbligatorio | Note |
| --- | --- | --- | --- |
| `soggetto_id` | uuid | Si | UUID di un `anagrafiche.soggetti` esistente con **P.IVA valorizzata** |
| `codice` | string | Si | Univoco; **immutabile** dopo la creazione (lock_columns trigger) |
| `descrizione` | string | Si | Etichetta visibile |
| `attivo` | bool | No | Default DB `true` |
| `regime_fiscale_rf` | string | No | Codice regime fiscale RF del tracciato FE/SdI (es. `RF01`) |
| `bollo_auto` | bool | No | Calcolo bollo automatico |
| `bollo_soglia` | numeric | No | Soglia per applicare il bollo |
| `rounding_policy` | enum | No | Uno tra: `UP`, `DOWN`, `HALF_UP`, `HALF_DOWN` (allineato alla matrice utility) |
| `valuta_id` | int | No | FK `config.valute` |

### 3.2 Comportamento

1. Validazione campi obbligatori (`soggetto_id`, `codice`, `descrizione`).
2. Validazione **P.IVA del soggetto**: query su `anagrafiche.soggetti.partita_iva`;
   se NULL/empty -> `E_ANAG_VALIDAZIONE 400`. Requisito legale per emissione fattura SDI.
3. Apertura transazione atomica.
4. Se il soggetto non ha ancora un ruolo `EF`, viene creato tramite
   `script.fn_get_or_create_soggetto_ruolo`.
5. Insert nella tabella `anagrafiche.emittenti_fiscali`. I trigger DB gestiscono
   `audit`, `tx_id`, `normalize`, `storicizzazione`.
6. Alla creazione del **primo** emittente, il trigger `default_bootstrap`
   inserisce automaticamente il record di default in
   `emittenti_fiscali_billing_account` con `billing_account_id = NULL` e
   `is_default = true`.

### 3.3 Esempio cURL

```bash
curl -X POST "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "soggetto_id": "019bac81-3f96-7ce8-a086-7e0bd0a2fec0",
       "codice": "EF-001",
       "descrizione": "Sede principale",
       "regime_fiscale_rf": "RF01",
       "bollo_auto": true,
       "bollo_soglia": 77.47
     }'
```

### 3.4 Risposta (200)

```json
{
  "data": {
    "id": 1,
    "soggetto_ruolo_id": 50
  }
}
```

### 3.5 Errori specifici

| Codice | HTTP | Descrizione |
| --- | --- | --- |
| `E_ANAG_VALIDAZIONE` | 400 | `soggetto_id`, `codice` o `descrizione` mancanti, oppure soggetto senza P.IVA |
| `E_ANAG_DUPLICATO` | 409 | Esiste gia' un emittente per questo soggetto o codice |

---

## 4. Aggiorna emittente fiscale

| | |
| --- | --- |
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/` |

### 4.1 Campi editabili

`descrizione`, `attivo`, `regime_fiscale_rf`, `bollo_auto`, `bollo_soglia`,
`rounding_policy`, `valuta_id`.

> **Nota:** il campo `codice` e' bloccato dal trigger DB `lock_columns` (errore
> `CODICE_NON_MODIFICABILE`). Il backend lo ignora se incluso nel payload
> tramite whitelist `_UPDATE_ALLOWED`.

### 4.2 Regole

- I campi nullable (es. `regime_fiscale_rf`, `bollo_soglia`) accettano stringhe
  vuote che vengono normalizzate a `NULL`.
- `rounding_policy` accetta solo i valori enum `UP`, `DOWN`, `HALF_UP`, `HALF_DOWN`
  (allineato ai metodi della matrice utility).
- **Disattivazione (`attivo = false`)**: rifiutata dal trigger DB se l'emittente ha
  record collegati in `emittenti_fiscali_billing_account`,
  `emittenti_fiscali_utilities`, `parameter_overrides` o `user_emittenti_fiscali`.

### 4.3 Esempio cURL

```bash
curl -X PATCH "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/1/" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{ "descrizione": "Sede principale 2026", "split_payment_default": true }'
```

### 4.4 Risposta (200)

```json
{ "data": { "updated": true } }
```

### 4.5 Errori specifici

| Codice | HTTP | Descrizione |
| --- | --- | --- |
| `E_ANAG_NOT_FOUND` | 404 | Emittente non trovato o nessun campo modificato |

---

## 5. Sub-resource: mapping Billing Account → Emittente

Gestione del mapping `emittenti_fiscali_billing_account` per associare uno o piu'
billing account a un emittente fiscale, oppure definire il **default globale**
(record con `billing_account_id IS NULL` e `is_default = true`).

### 5.0 Regole DB

- CHECK constraint `chk_emittenti_fiscali_ba_default`:
  `(is_default = true AND billing_account_id IS NULL) OR (is_default = false AND billing_account_id IS NOT NULL)`
- UNIQUE su `billing_account_id`: un BA puo' essere mappato a un solo emittente.
- UNIQUE WHERE `is_default = true`: un solo default globale in tutto il sistema.
- Trigger `default_guard` su INSERT/UPDATE/DELETE per rispetto invarianti.
- Tutte le richieste sono validate dal service tramite `_resolve_soggetto_ruolo_id`
  (l'emittente padre deve esistere) e, su DELETE, da `belongs_to_emittente`
  (il mapping deve appartenere all'emittente atteso, fail safe).

Il backend non espone `is_default` come campo modificabile: viene **derivato**
automaticamente da `billing_account_id` (NULL → default globale, valorizzato →
mapping specifico).

### 5.1 Lista mapping

| | |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/billing-account/` |

#### Esempio cURL

```bash
curl -X GET "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/1/billing-account/" \
     -H "Authorization: Bearer $TOKEN"
```

#### Risposta (200)

```json
{
  "data": {
    "results": [
      {
        "id": 10,
        "billing_account_id": null,
        "is_default": true,
        "billing_account_codice": null,
        "billing_account_ragione_sociale": null,
        "data_insert": "2026-04-07T10:00:00Z",
        "data_update": "2026-04-07T10:00:00Z"
      },
      {
        "id": 11,
        "billing_account_id": 5,
        "is_default": false,
        "billing_account_codice": "BA-005",
        "billing_account_ragione_sociale": "Acme Energia Srl",
        "data_insert": "2026-04-07T10:05:00Z",
        "data_update": "2026-04-07T10:05:00Z"
      }
    ]
  }
}
```

Ordinamento: default per primo, poi per codice BA crescente.

### 5.2 Crea mapping

| | |
| --- | --- |
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/billing-account/` |

#### Body — Crea mapping BA

| Campo | Tipo | Obbligatorio | Note |
| --- | --- | --- | --- |
| `billing_account_id` | int | No | Se omesso/null crea il **default globale** (uno solo nel sistema) |

#### Esempio cURL — mapping specifico

```bash
curl -X POST "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/1/billing-account/" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{ "billing_account_id": 5 }'
```

#### Esempio cURL — default globale

```bash
curl -X POST "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/1/billing-account/" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{}'
```

#### Risposta — POST mapping BA

```json
{
  "data": {
    "id": 11,
    "emittente_id": 1,
    "billing_account_id": 5,
    "is_default": false
  }
}
```

#### Errori specifici BA

| Codice | HTTP | Descrizione |
| --- | --- | --- |
| `E_ANAG_NOT_FOUND` | 404 | Emittente padre non trovato |
| `E_ANAG_DUPLICATO` | 409 | Il BA e' gia' associato a un emittente o il default globale esiste gia' |

### 5.3 Elimina mapping

| | |
| --- | --- |
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/billing-account/<mapping_id>/` |

Verifica che il mapping appartenga all'emittente padre prima di eliminare.

#### Esempio cURL — DELETE mapping

```bash
curl -X DELETE "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/1/billing-account/11/" \
     -H "Authorization: Bearer $TOKEN"
```

#### Risposta — DELETE mapping BA

```json
{ "data": { "deleted": true } }
```

#### Errori specifici DELETE BA

| Codice | HTTP | Descrizione |
| --- | --- | --- |
| `E_ANAG_NOT_FOUND` | 404 | Mapping non esiste o non appartiene all'emittente indicato |

### 5.4 Summary mapping BA

| | |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/billing-account/summary/` |

Riepilogo dei mapping BA per l'emittente, **indipendente dalla pagina/search**
della lista paginata. Risolve il bug A8/C3 dell'analisi frontend amm-software:
il pulsante "default" lato FE non puo' affidarsi a `store.items.some(is_default)`
perche' il record default puo' trovarsi fuori dalla pagina corrente.

#### Esempio cURL — GET summary

```bash
curl -X GET "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/1/billing-account/summary/" \
     -H "Authorization: Bearer $TOKEN"
```

#### Risposta — summary

```json
{
  "data": {
    "has_default": true,
    "count_specifici": 7
  }
}
```

| Campo | Tipo | Descrizione |
| --- | --- | --- |
| `has_default` | bool | True se esiste il mapping default globale per l'emittente |
| `count_specifici` | int | Numero mapping specifici (con `billing_account_id` valorizzato) |

---

## 6. Sub-resource: utilities per emittente fiscale

Gestione della matrice `emittenti_fiscali_utilities` (parametri di fatturazione
per ogni coppia emittente x utility: soglie minime, decimali e metodo di
arrotondamento).

### 6.0 Regole DB

- UNIQUE `(emittente_soggetto_ruolo_id, utility_id)`: una sola riga per coppia.
- Trigger `child_requires_active_parent`: l'emittente padre deve essere attivo.
- Trigger `guard_utility_tipo_ruolo`: la utility deve essere ammessa per il
  ruolo `EF` (matrice `config.utilities_tipi_ruolo`, fail-open se la utility
  non ha alcuna configurazione di matrice).
- Validazione di proprieta' (record figlio appartiene all'emittente padre)
  applicata su PATCH e DELETE tramite `_verify_record_ownership`.

> **Nota lookup utility (UI)**: la combo di scelta utility nel frontend usa il
> componente core riusabile `UtilityPerRuoloSelect`, che chiama l'endpoint
> `GET /api/v1/core/lookup/tipi-ruolo/EF/utilities/`. L'endpoint applica
> filtro **strict** sulla matrice `config.utilities_tipi_ruolo`: ritorna solo
> utility con riga ATTIVA per il `tipo_ruolo_codice` indicato e nel periodo
> di validita' corrente. Coerente con il trigger DB `script.fn_guard_utility_tipo_ruolo`,
> evitando errori `E_UTILITY_RUOLO_NON_AMMESSO` lato UI.

### 6.1 Lista matrice utility per emittente

| | |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/utilities/` |

Pattern **slot/override**: ritorna SEMPRE tutte le utility ammesse per il ruolo `EF`
(da `config.utilities_tipi_ruolo`), con sovrapposti i parametri specifici dell'emittente
(da `anagrafiche.emittenti_fiscali_utilities`) **solo dove esistono**. Per le righe non
configurate, i campi override sono `null` e `record_id` e' `null`. Implementato con
LEFT JOIN dal building block `LookupRepository.list_entity_utility_matrix`.

#### Risposta — matrice utility

```json
{
  "data": {
    "results": [
      {
        "utility_id": 1,
        "utility_codice": "EE",
        "utility_descrizione": "Energia Elettrica",
        "record_id": 100,
        "minimo_soglia_min": 0.50,
        "minimo_soglia_max": null,
        "arrotondamento_importi_dec": 2,
        "metodo_arrotondamento_importi": "HALF_UP",
        "record_attivo": true,
        "record_data_insert": "2026-04-07T10:00:00Z",
        "record_data_update": "2026-04-07T10:00:00Z"
      },
      {
        "utility_id": 2,
        "utility_codice": "GAS",
        "utility_descrizione": "Gas Naturale",
        "record_id": null,
        "minimo_soglia_min": null,
        "minimo_soglia_max": null,
        "arrotondamento_importi_dec": null,
        "metodo_arrotondamento_importi": null,
        "record_attivo": null,
        "record_data_insert": null,
        "record_data_update": null
      }
    ]
  }
}
```

> **Stato della riga**: `record_id != null` -> riga configurata (esiste override);
> `record_id == null` -> riga ammessa ma non personalizzata (l'emittente usa i default
> di sistema).

### 6.2 Crea record

| | |
| --- | --- |
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/utilities/` |

#### Body — Crea record utility

| Campo | Tipo | Obbligatorio | Note |
| --- | --- | --- | --- |
| `utility_id` | int | Si | FK `config.utilities` (deve essere ammessa per ruolo `EF`) |
| `arrotondamento_importi_dec` | int | Si | Decimali per arrotondamento (0..6, vincolo CHECK DB) |
| `metodo_arrotondamento_importi` | string | Si | Uno tra: `HALF_UP`, `HALF_DOWN`, `UP`, `DOWN` (CHECK constraint DB) |
| `minimo_soglia_min` | numeric | No | Soglia minima |
| `minimo_soglia_max` | numeric | No | Soglia massima (se valorizzata: `>= minimo_soglia_min`) |
| `attivo` | bool | No | Default `true` |

#### Esempio cURL — POST utility

```bash
curl -X POST "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/1/utilities/" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "utility_id": 1,
       "arrotondamento_importi_dec": 2,
       "metodo_arrotondamento_importi": "HALF_UP",
       "minimo_soglia_min": 0.50
     }'
```

#### Risposta — POST record utility

```json
{ "data": { "id": 100 } }
```

#### Errori specifici POST utility

| Codice | HTTP | Descrizione |
| --- | --- | --- |
| `E_ANAG_VALIDAZIONE` | 400 | `utility_id`, `arrotondamento_importi_dec` o `metodo_arrotondamento_importi` mancanti |
| `E_ANAG_DUPLICATO` | 409 | Coppia (emittente, utility) gia' presente |
| `E_ANAG_NOT_FOUND` | 404 | Emittente padre non trovato |

### 6.3 Aggiorna record

| | |
| --- | --- |
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/utilities/<record_id>/` |

`utility_id` non e' modificabile (esce dal whitelist `_UTILITIES_UPDATE_ALLOWED`).
Campi editabili: `minimo_soglia_min`, `minimo_soglia_max`,
`arrotondamento_importi_dec`, `metodo_arrotondamento_importi`, `attivo`.

#### Esempio cURL — PATCH utility

```bash
curl -X PATCH "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/1/utilities/100/" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{ "attivo": false }'
```

#### Risposta — PATCH utility

```json
{ "data": { "updated": true } }
```

### 6.4 Elimina record

| | |
| --- | --- |
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/utilities/<record_id>/` |

Verifica appartenenza al padre prima di eliminare.

#### Esempio cURL — DELETE utility

```bash
curl -X DELETE "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/1/utilities/100/" \
     -H "Authorization: Bearer $TOKEN"
```

#### Risposta — DELETE utility

```json
{ "data": { "deleted": true } }
```

---

## File del modulo

| Layer | File |
| --- | --- |
| URL routing | [apps/anagrafiche/api/urls.py](../../../../backend/apps/anagrafiche/api/urls.py) |
| API view | [apps/anagrafiche/api/views_emittenti_fiscali.py](../../../../backend/apps/anagrafiche/api/views_emittenti_fiscali.py) |
| Service | [apps/anagrafiche/services/emittenti_fiscali_service.py](../../../../backend/apps/anagrafiche/services/emittenti_fiscali_service.py) |
| Repository | [apps/anagrafiche/db/emittenti_fiscali_repository.py](../../../../backend/apps/anagrafiche/db/emittenti_fiscali_repository.py) |
| Test API | [apps/anagrafiche/tests/api/test_emittenti_fiscali_api.py](../../../../backend/apps/anagrafiche/tests/api/test_emittenti_fiscali_api.py) |

## Note di migrazione

- Le rotte sono registrate in `apps/anagrafiche/api/urls.py`.
- Le view ereditano da `AdminAPIView`: `skip_area_check = True`, nessun
  `area_funzionale` necessario; il check di autorizzazione si limita a
  `IsAdminZeroERP` (ruolo sistema `ADMIN` o superuser Django).
- Il sub-resource `utilities/lookup/` deve restare registrato **prima**
  delle rotte `<int:emittente_id>/utilities/` in `urls.py`, altrimenti
  Django risolverebbe `lookup` come `emittente_id` letterale.
- Helper di service `_verify_record_ownership` (modulo
  `emittenti_fiscali_service`) e' condiviso da `EmittentiFiscaliBillingAccountService`
  e `EmittentiFiscaliUtilitiesService` per evitare duplicazione del pattern
  "resolve padre + verifica appartenenza".
- I test mockano `IsAdminZeroERP.has_permission` per bypassare il check ADMIN
  in CI; sono presenti test 403 specifici sia per l'endpoint principale che
  per i sub-resource BA e Utilities.
