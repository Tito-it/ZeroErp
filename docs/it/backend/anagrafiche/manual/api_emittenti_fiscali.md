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
Le risposte seguono l'envelope standard `{"data": ..., "meta": {...}}` per il
successo e `{"error": {"code": "...", "message": "..."}, "meta": {...}}` per gli errori.

**Accesso riservato agli amministratori**: tutte le view ereditano da `AdminAPIView`
(`apps.core.api.base_views`), che applica `IsAdminZeroERP` (superuser Django o
binding `SUPER_ADMIN`, con bypass del resolver aree). Un utente non admin
riceve `403 E_ACCESSO_RISERVATO_ADMIN`.

## Base URL

```text
/api/v1/anagrafiche/emittenti-fiscali/
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
| 1 | `GET` | `/emittenti-fiscali/` | Lista paginata + filtro `attivo` |
| 2 | `GET` | `/emittenti-fiscali/<id>/` | Dettaglio emittente |
| 3 | `POST` | `/emittenti-fiscali/` | Crea emittente |
| 4 | `PATCH` | `/emittenti-fiscali/<id>/` | Aggiorna emittente |
| 5.1 | `GET` | `/emittenti-fiscali/<id>/billing-account/` | Lista dei clienti (BA) dell'emittente, in consultazione |
| 5.2 | `POST` | `/emittenti-fiscali/<id>/billing-account/` | Rende l'emittente l'azienda predefinita |
| 5.4 | `GET` | `/emittenti-fiscali/<id>/billing-account/summary/` | Summary mapping (has_default + count_specifici) |
| 6.1 | `GET` | `/emittenti-fiscali/<id>/utilities/` | Le utility dell'azienda, gestite o no |
| 6.2 | `POST` | `/emittenti-fiscali/<id>/utilities/` | Attiva un'utility per l'azienda |
| 6.3 | `PATCH` | `/emittenti-fiscali/<id>/utilities/<record_id>/` | I parametri d'importo |
| 6.4 | `DELETE` | `/emittenti-fiscali/<id>/utilities/<record_id>/` | Toglie l'utility all'azienda (se non in uso) |
| 7 | `GET` | `/api/v1/anagrafiche/billing-account/<id>/utilities/` | Utility guidate dall'emittente per un billing account (non admin, vedi §7) |

## Codici errore (envelope `{"error": {"code", "message"}}`)

| Codice | HTTP | Descrizione |
| --- | --- | --- |
| `E_NOT_AUTHENTICATED` | 401 | Token JWT mancante |
| `E_AUTHENTICATION_FAILED` | 401 | Token JWT non valido o scaduto |
| `E_ACCESSO_RISERVATO_ADMIN` | 403 | Utente autenticato ma non admin |
| `E_ANAG_VALIDAZIONE` | 400 | Campi obbligatori mancanti o non validi |
| `E_ANAG_NOT_FOUND` | 404 | Risorsa non trovata o non appartenente al padre |
| `E_ANAG_DUPLICATO` | 409 | Vincolo univocita' violato (codice, soggetto, default) |
| `E_BA_EMITTENTE_CON_STORIA` | 409 | **Sub-resource 5**: si sta spostando un billing account che ha gia' fatture o commesse. Nasce nel database (`20260826-49`) e arriva al client **senza codice Python**: la classe `CONFLITTO_STATO` a catalogo lo mappa a 409 dalla catena centralizzata. ⚠️ Non c'e' la chiave `campo` nel contesto — su un conflitto di stato non esiste un input da accendere |
| `E_EMITTENTE_DEFAULT_SINGLETON` | 409 | **Sub-resource 5**: si sta cancellando il gestore globale, che deve sempre esistere e non e' mai rimovibile |

> Eccezioni inattese vengono normalizzate dal middleware
> [error-handling-api](../../core/manual/error-handling-api.md) in
> envelope `{"error": {"code": "E_INTERNAL", ...}}` con HTTP 500.

## Dipendenze DB

| Oggetto | Tipo | Ruolo |
| --- | --- | --- |
| `anagrafiche.emittenti_fiscali` | Tabella | Master emittente |
| `anagrafiche.emittenti_fiscali_billing_account` | Tabella | Mapping BA -> emittente (sub-resource sezione 5) |
| `anagrafiche.emittenti_fiscali_utilities` | Tabella | Le utility che l'azienda gestisce, coi parametri d'importo facoltativi (sezione 6) |
| `anagrafiche.soggetti_ruoli` | Tabella | Legame ruolo soggetto (codice `EF`) |
| `anagrafiche.soggetti` | Tabella | Display fields (ragione sociale, CF, P.IVA) |
| `config.utilities` | Tabella | Lookup utility (sezione 6) |
| `config.utilities_tipi_ruolo` | Tabella | Matrice utility ammesse per ruolo (fail-closed: senza righe, nessuno) |
| `anagrafiche.fn_utilities_emittente` | Funzione | Le utility di un'azienda: ammesse, gestite, coi parametri effettivi (sezione 6.1) |
| `config.valute` | Tabella | Lookup valuta (display ISO) |
| `script.fn_get_or_create_soggetto_ruolo` | Funzione | Crea ruolo `EF` se non esiste |
| `anagrafiche.trgfn_emittenti_fiscali_default_bootstrap` | Trigger | Inserisce default mapping `is_default=true, billing_account_id=NULL` alla creazione del primo emittente |
| `anagrafiche.trgfn_emittenti_fiscali_normalize` | Trigger | Normalizzazione INSERT/UPDATE |
| `anagrafiche.trgfn_emittenti_fiscali_guard_ruolo_emi_fis` | Trigger | Coerenza ruolo `EF` |
| `dbops.trgfn_prevent_deactivate_if_children` | Trigger (uno per FK figlia) | Blocca la disattivazione se esistono figli. Un trigger **per tabella figlia** generato dall'automazione ATTIVO. Il messaggio **non nomina tabelle**: dal 2026-11-11 (S-BE-1 di brief-db-revisione-dbops) la frase è per l'operatore, e quale tabella figlia blocca sta nel contesto del registro errori (`dbops.error_log`), per chi ripara il dato. Dal changeSet `20260820-08` i codici sono **due**, scelti dal guard secondo la tabella figlia: `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` dove le righe collegate si **disattivano** (la figlia ha la colonna `attivo`) e `E_ATTIVO_BLOCK_CHILDREN_EXIST` dove si **tolgono** (la figlia non ce l'ha). Prima era un codice solo e la parola «attive» era falsa per 181 trigger su 349. Copertura reale (letta dagli argomenti dei trigger, non dai loro nomi troncati): `anagrafiche.emittenti_fiscali_billing_account`, `anagrafiche.emittenti_fiscali_utilities`, `config.parameter_overrides`, `config.user_emittente_attivo`, `config.user_emittenti_fiscali`, `documenti.documenti_generati`, `documenti.template_asset`, `documenti.template_documenti`, `pratiche.pratiche`, `pratiche.workflow_definizioni`, `vendite.contratti`, `vendite.ddt`, `vendite.offerte_commerciali`, `vendite.ordini`, `vendite.preventivi`, `vendite.resi`.<br>⚠️ Sostituisce `anagrafiche.trgfn_emittenti_fiscali_guard_attivo`, **droppato** il 2026-08-20 (changeSet `20260820-02`): era un doppione che copriva **il solo** mapping billing account — non i quattro figli che questa riga gli attribuiva — e non veniva nemmeno più raggiunto, perché i BEFORE ROW scattano in ordine alfabetico e il generico viene prima. Il suo codice `E_EMITTENTE_DISATTIVAZIONE_BLOCCATA` è **ritirato**. |
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
| `search` | string | No | — | Ricerca ILIKE sulle colonne (fra `codice`, `ragione_sociale_completa`, `id_fiscale_univoco_cf_piva`) che il catalogo della lista `anagrafiche.emittenti_fiscali` accende; sotto soglia non filtra (nessun 400) |
| `attivo` | bool | No | — | Filtra per flag attivo (`true`/`false`). Se omesso: nessun filtro |
| `limit` | int | No | 25 | Risultati per pagina (max: 200) |
| `offset` | int | No | 0 | Offset per paginazione |
| `order_by` | string | No | `ragione_sociale_completa` | Campo di ordinamento (vedi sotto); fuori elenco → **400** `E_VALIDATION_INPUT` (dal 2026-10-20) |
| `order_dir` | string | No | `asc` (`desc` per `data_insert`) | Direzione: `asc` / `desc` |

**Colonne ordinabili:** `codice`, `ragione_sociale_completa`, `partita_iva`,
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
    "results": [
      {
        "id": 1,
        "uid": "019bac81-3f96-7ce8-a086-7e0bd0a2fec1",
        "soggetto_ruolo_id": 50,
        "codice": "EF-001",
        "attivo": true,
        "regime_fiscale_rf": "RF01",
        "bollo_auto": true,
        "bollo_soglia": 77.47,
        "rounding_policy": "HALF_UP",
        "valuta_id": 1,
        "valuta_iso": "EUR",
        "soggetto_id": "019bac81-3f96-7ce8-a086-7e0bd0a2fec0",
        "ragione_sociale_completa": "ACME S.p.A.",
        "codice_fiscale": "01234567890",
        "partita_iva": "01234567890",
        "id_fiscale_univoco_cf_piva": "01234567890",
        "data_insert": "2026-04-07T10:00:00Z",
        "data_update": "2026-04-07T10:00:00Z"
      }
    ]
  },
  "meta": {"request_id": "..."}
}
```

---

## 2. Dettaglio emittente fiscale

| | |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/` |

Restituisce lo stesso oggetto della lista (senza `id_fiscale_univoco_cf_piva`), con in piu' `valuta_descrizione`,
`brand_meta` (jsonb opzionale per branding/metadati emittente) e, dal
2026-10-01, `regime_fiscale_descrizione` e, dal 2026-11-22, `regime_fiscale_codice` (il codice a video,
distinto da `codice_interno` = `regime_fiscale_rf`; tutti e due dal catalogo `config.regimi_fiscali`)
con `regime_fiscale_confermato_il` / `regime_fiscale_confermato_da` (entrambi
`null` = regime mai confermato, vedi §4.2).

**Fase 4 — `non_editable_fields` nel detail**: il dict di response include
`non_editable_fields: ["codice", "soggetto_ruolo_id"]`, tutta dal lock vivo di
`dbops.vw_non_editable_fields` (BB `compute_non_editable_fields`, nessun gap):
`codice` lo blocca `E_CODICE_NON_MODIFICABILE`, `soggetto_ruolo_id`
`E_EMITTENTE_SOGGETTO_IMMUTABILE` (dal 2026-11-21: un emittente appartiene per
sempre al suo soggetto). ⚠️ Fino a quel giorno la lista portava il gap Python
`soggetto_id`, un campo del payload: la tabella non ha quella colonna, e il DB
non garantiva la regola. ⚠️ Oggi `EmittenteFiscaleDrawer.vue` non legge la
chiave: il soggetto si sceglie solo in creazione e i campi immutabili li spegne
`isEdit`. Pattern coerente con altre matrici amm-software (categorie clienti
listini, tipi ruolo indirizzi).

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
| `attivo` | bool | No | Default DB `true` |
| `regime_fiscale_rf` | string | No | Codice del catalogo `config.regimi_fiscali` (FK, es. `RF01`, `RF17`). **Presente** = regime dichiarato e **confermato**: la INSERT non conferma mai, quindi il service la fa seguire da un UPDATE del regime nella stessa transazione, e data e autore li deriva il DB. **Omesso** = default DB `RF01`, non confermato: l'emittente entra nel presidio `dbops.vw_emittenti_regime_non_confermato`. Vuoto o `null` → 400 |
| `bollo_auto` | bool | No | Calcolo bollo automatico |
| `bollo_soglia` | numeric | No | Soglia per applicare il bollo |
| `rounding_policy` | enum | No | Uno tra: `UP`, `DOWN`, `HALF_UP`, `HALF_DOWN` (allineato alla matrice utility) |
| `valuta_id` | int | No | FK `config.valute` |

### 3.2 Comportamento

1. Validazione campi obbligatori (`soggetto_id`, `codice`). Il nome dell'emittente
   e' la ragione sociale del soggetto: `descrizione` non esiste piu' (colonna
   eliminata). In creazione una chiave fuori tabella, `descrizione` compresa, è un
   **400** `E_ANAG_VALIDAZIONE` (dal 2026-10-21: prima era ignorata, mentre la
   PATCH la rifiutava già).
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
| `E_ANAG_VALIDAZIONE` | 400 | `soggetto_id` o `codice` mancanti, oppure soggetto senza P.IVA; `regime_fiscale_rf` vuoto/`null` o fuori catalogo (`error.fields` = `regime_fiscale_rf`) |
| `E_ANAG_DUPLICATO` | 409 | Esiste gia' un emittente per questo soggetto o codice |
| `E_ATTIVO_PADRE_NON_ATTIVO` | 409 | `regime_fiscale_rf` di un regime del catalogo **spento** (`attivo = false`): un regime spento non si assegna (D-6 di brief-db-fornitore-doppioni-del-soggetto, require del DB). `error.fields` = `regime_fiscale_rf` |

---

## 4. Aggiorna emittente fiscale

| | |
| --- | --- |
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/` |

### 4.1 Campi editabili

`attivo`, `regime_fiscale_rf`, `bollo_auto`, `bollo_soglia`,
`rounding_policy`, `valuta_id`. Qualsiasi altra chiave (anche `codice`,
`descrizione`, `soggetto_id`) → `400 E_ANAG_VALIDAZIONE`; un corpo senza campi →
`400 E_ANAG_VALIDAZIONE`.

> **Nota:** `codice` e' immutabile (trigger DB `lock_columns`); il service lo
> rifiuta prima, con 400.

### 4.2 Regole

- I campi nullable (es. `rounding_policy`, `bollo_soglia`) accettano stringhe
  vuote che vengono normalizzate a `NULL`.
- **Regime fiscale** (dal 2026-10-01, `brief-db-esigibilita-iva-per-cassa-emittente`):
  `regime_fiscale_rf` e' NOT NULL con FK al catalogo `config.regimi_fiscali`.
  Una PATCH che lo porta — **anche con lo stesso valore** — lo dichiara e lo
  **conferma**: dal 2026-10-02 `regime_fiscale_confermato_il`/`_da` li
  **deriva il database** da ogni UPDATE che nomina il regime (trigger
  `trgfn_emittenti_fiscali_regime_conferma`; l'autore e' l'operatore, GUC
  `app.jwt_user`). Chi non tocca il regime **omette la chiave**, e la conferma
  resta com'e'. Le due colonne di conferma non sono chiavi del contratto, e il
  database rifiuta chi le scrive direttamente
  (`E_EMITTENTE_REGIME_CONFERMA_DERIVATA`). Vuoto, `null` o codice fuori
  catalogo → `E_ANAG_VALIDAZIONE` 400 sul campo.
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
     -d '{ "bollo_auto": true, "bollo_soglia": 77.47 }'
```

### 4.4 Risposta (200)

```json
{ "data": { "updated": true } }
```

### 4.5 Errori specifici

| Codice | HTTP | Descrizione |
| --- | --- | --- |
| `E_ANAG_VALIDAZIONE` | 400 | Chiave fuori elenco (compreso `codice`), corpo vuoto, regime vuoto/`null`/fuori catalogo |
| `E_ATTIVO_PADRE_NON_ATTIVO` | 409 | `regime_fiscale_rf` di un regime del catalogo **spento** (`attivo = false`): un regime spento non si assegna (D-6 di brief-db-fornitore-doppioni-del-soggetto, require del DB). `error.fields` = `regime_fiscale_rf` |
| `E_ANAG_NOT_FOUND` | 404 | Emittente non trovato |

---

## 5. Sub-resource: mapping Billing Account → Emittente

La scheda dei clienti di un emittente (`emittenti_fiscali_billing_account`) e la
riga della **predefinita** (`billing_account_id IS NULL`, `is_default = true`):
l'azienda in cui nascono i billing account creati senza sessione.

⛔ **Dal 2026-11-27 la lista e' in sola consultazione** (giro 6 di
`brief-db-revisione-anagrafiche`, D-T4-3; Tid, §26.2). Ogni billing account nasce
col suo collegamento a un'azienda (`trgfn_billing_account_link_ef`) e non lo perde
mai: un collegamento **non si crea** da qui (urterebbe il vincolo unico) e **non si
toglie** (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`, anche sulla predefinita). Prima
c'erano il `POST` col `billing_account_id` e il `DELETE` del mapping, con
`can_remove` e il motivo del blocco per riga: ritirati lo stesso giorno. L'unico
gesto rimasto e' **«rendi predefinita»** (§5.2), che **sposta** la riga della
predefinita su questo emittente.

### 5.0 Regole DB

- CHECK constraint `chk_emittenti_fiscali_ba_default`:
  `(is_default = true AND billing_account_id IS NULL) OR (is_default = false AND billing_account_id IS NOT NULL)`
- UNIQUE su `billing_account_id`: un BA ha un collegamento solo.
- UNIQUE WHERE `is_default = true`: una sola predefinita in tutto il sistema.
- Nessun collegamento si cancella (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`) e nessuno
  cambia `billing_account_id` (`E_BA_COLLEGAMENTO_NON_SI_SPOSTA`); il cliente cambia
  azienda solo senza documenti (`E_BA_EMITTENTE_CON_STORIA`).
- Le richieste passano da `_resolve_soggetto_ruolo_id` (l'emittente padre deve
  esistere).

### 5.1 Lista mapping

| | |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/billing-account/` |

#### Parametri query

| Parametro | Tipo | Default | Descrizione |
| --- | --- | --- | --- |
| `search` | string | — | Ricerca ILIKE sulle colonne (fra `billing_account_codice`, `billing_account_ragione_sociale`, `id_fiscale_univoco`) accese dal catalogo della lista `anagrafiche.emittente_billing_account`; sotto soglia non filtra |
| `limit` | int | 25 | Righe per pagina (max 200) |
| `offset` | int | 0 | Offset |
| `order_by` | string | `billing_account_codice` | `billing_account_codice`, `billing_account_ragione_sociale`, `id_fiscale_univoco`, `is_default`, `data_insert`; fuori elenco → **400** `E_VALIDATION_INPUT` (dal 2026-10-20) |
| `order_dir` | string | `asc` (`desc` per `data_insert`) | `asc` / `desc` |

#### Esempio cURL

```bash
curl -X GET "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/1/billing-account/" \
     -H "Authorization: Bearer $TOKEN"
```

#### Risposta (200)

Envelope paginato standard:

```json
{
  "data": {
    "count": 2,
    "results": [
      {
        "id": 10,
        "billing_account_id": null,
        "is_default": true,
        "billing_account_codice": null,
        "billing_account_ragione_sociale": null,
        "id_fiscale_univoco": null,
        "data_insert": "2026-04-07T10:00:00Z",
        "data_update": "2026-04-07T10:00:00Z"
      },
      {
        "id": 11,
        "billing_account_id": 5,
        "is_default": false,
        "billing_account_codice": "BA-005",
        "billing_account_ragione_sociale": "Acme Energia Srl",
        "id_fiscale_univoco": "01234567890",
        "data_insert": "2026-04-07T10:05:00Z",
        "data_update": "2026-04-07T10:05:00Z"
      }
    ]
  },
  "meta": {"request_id": "..."}
}
```

Ordinamento: la riga default sempre per prima, poi la colonna scelta (default
codice BA crescente). Con `order_by=is_default` conta solo quella colonna, col
suo verso.

`id_fiscale_univoco` = `soggetti.id_fiscale_univoco_cf_piva` del soggetto del BA.
### 5.2 Rendi predefinita

| | |
| --- | --- |
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/billing-account/` |

Corpo **vuoto**. La riga della predefinita si **sposta** su questo emittente
(`UPDATE` di `emittente_soggetto_ruolo_id`), con lo stesso `id`. La predefinita c'è
sempre, appena esiste un emittente (la porta il bootstrap del primo, e il DB la esige
al COMMIT): il backend non la crea, e se mancasse risponde `E_EMITTENTE_DEFAULT_MISSING`
invece di rifarla. Da quel
momento i billing account creati senza un'azienda in sessione nascono qui; quelli
che esistono non cambiano azienda. Sullo stesso emittente due volte: nessun
cambio.

#### Esempio cURL

```bash
curl -X POST "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/1/billing-account/" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{}'
```

#### Risposta

```json
{
  "data": {
    "id": 10,
    "emittente_id": 1,
    "billing_account_id": null,
    "is_default": true
  }
}
```

#### Errori

| Codice | HTTP | Descrizione |
| --- | --- | --- |
| `E_ANAG_NOT_FOUND` | 404 | Emittente padre non trovato |
| `E_ANAG_VALIDAZIONE` | 400 | Il corpo porta una chiave (per esempio `billing_account_id`): un cliente nasce gia' collegato alla sua azienda. `context.unknown_keys` la nomina |
| `E_ATTIVO_PADRE_NON_ATTIVO` | 409 | L'emittente è spento: la predefinita va su un'azienda attiva (trigger del genitore attivo, dal DB) |
| `E_EMITTENTE_DEFAULT_MISSING` | 500 | Non c'è la riga della predefinita: stato che il modello esclude (vedi sopra), detto e non riparato |

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

## 6. Sub-resource: le utility che l'azienda gestisce

`anagrafiche.emittenti_fiscali_utilities` e' l'**elenco delle utility che l'azienda
gestisce** ([brief-db-utility-gestite-dall-emittente](/dev/work-in-progress/brief-db-utility-gestite-dall-emittente),
2026-11-27): una riga = l'azienda gestisce l'utility, e tratta solo quelle; un'azienda
senza righe non ne gestisce nessuna. Sulla stessa riga stanno i **parametri d'importo**,
tutti facoltativi (soglie del minimo, decimali e metodo di arrotondamento): un campo
`null` vale la policy dell'azienda e il valore di sistema. Lo scrive solo il
SUPER_ADMIN (`AdminAPIView`).

### 6.0 Regole DB

- UNIQUE `(emittente_soggetto_ruolo_id, utility_id)`: una sola riga per coppia; le
  due colonne sono ferme (`E_CODICE_NON_MODIFICABILE`).
- La riga nasce solo sotto un emittente acceso (`child_requires_active_parent`) e su
  un'utility che la matrice `config.utilities_tipi_ruolo` ammette per il ruolo `EF`
  (`script.fn_guard_utility_tipo_ruolo`, **fail-closed**: un'utility senza righe
  nella matrice non e' ammessa per nessuno, `E_UTILITY_RUOLO_NON_AMMESSO`).
- La riga **non ha uno stato suo**: `attivo` e' sempre `true`
  (`chk_emittenti_fiscali_utilities_attivo`). «Gestita» = riga presente ed emittente
  acceso.
- La cancellazione toglie l'utility all'azienda, ed e' rifiutata (`23503`) finche' un
  billing account o un documento usa la coppia: le FK composte e differite
  `fk_<tabella>_utility_gestita` di `emittenti_fiscali_billing_account`,
  `categorie_clienti_listini`, `listini`, `commesse`, `fatture`,
  `registri_fatturazione`, `fatturazione_lotti`.
- Validazione di proprieta' (record figlio appartiene all'emittente padre)
  applicata su PATCH e DELETE tramite `_verify_record_ownership`.

> **Nota lookup utility (UI)**: la combo di scelta utility nel frontend usa il
> componente core riusabile `UtilityPerRuoloSelect`, che chiama
> `GET /api/v1/core/lookup/utilities-per-emittente/?ruolo=<codice>&emittente_fiscale_id=<pk>`:
> le utility che l'azienda **gestisce** (senza `emittente_fiscale_id`, quelle gestite
> da almeno un'azienda del perimetro), dal BB del DB `anagrafiche.fn_utilities_emittente`
> ([api_lookup_dedicati.md §4](../../core/manual/api_lookup_dedicati.md)).

### 6.1 Le utility dell'azienda

| | |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/utilities/` |

Ritorna **tutte** le utility che la matrice ammette oggi per il ruolo `EF`, gestite o
no, lette dal BB del DB `anagrafiche.fn_utilities_emittente` (sede unica della regola:
ammesse, `gestita`, parametri effettivi). Della riga si leggono in piu' i valori
**scritti**, che il form modifica: `null` = non scritto. I valori `effettivo_*` sono
quelli che valgono (riga, poi policy dell'azienda, poi sistema). Ordinate per
descrizione dell'utility (l'ordine lo fissa il repository, non il BB).

#### Risposta — le utility dell'azienda

```json
{
  "data": {
    "results": [
      {
        "utility_id": 1,
        "utility_codice": "EE",
        "utility_descrizione": "Energia Elettrica",
        "gestita": true,
        "record_id": 100,
        "personalizzata": true,
        "minimo_soglia_min": null,
        "minimo_soglia_max": null,
        "arrotondamento_importi_dec": 0,
        "metodo_arrotondamento_importi": null,
        "effettivo_minimo_soglia_min": null,
        "effettivo_minimo_soglia_max": null,
        "effettivo_arrotondamento_importi_dec": 0,
        "effettivo_metodo_arrotondamento_importi": "HALF_UP",
        "can_attivare": false,
        "can_update": true,
        "can_reset": true,
        "can_remove": true
      },
      {
        "utility_id": 2,
        "utility_codice": "GAS",
        "utility_descrizione": "Gas Naturale",
        "gestita": false,
        "record_id": null,
        "personalizzata": false,
        "minimo_soglia_min": null,
        "minimo_soglia_max": null,
        "arrotondamento_importi_dec": null,
        "metodo_arrotondamento_importi": null,
        "effettivo_minimo_soglia_min": null,
        "effettivo_minimo_soglia_max": null,
        "effettivo_arrotondamento_importi_dec": 2,
        "effettivo_metodo_arrotondamento_importi": "HALF_UP",
        "can_attivare": true,
        "can_update": false,
        "can_reset": false,
        "can_remove": false
      }
    ]
  }
}
```

| Campo | Tipo | Significato |
| --- | --- | --- |
| `gestita` | bool | L'azienda ha la riga ed e' accesa |
| `record_id` | int \| null | La riga dell'azienda, `null` se non c'e' |
| `personalizzata` | bool | Almeno un parametro scritto sulla riga |
| `can_attivare` | bool | Nessuna riga ed emittente acceso: si puo' attivare |
| `can_update` | bool | La riga c'e': si scrivono i parametri |
| `can_reset` | bool | La riga ha parametri suoi: si riportano a `null` |
| `can_remove` | bool | La riga c'e': si puo' togliere (il DB rifiuta se e' in uso) |

Le capability sono preview UX, non garanzia: **l'autorita' resta il DB**. `can_remove`
non anticipa il «in uso»: lo decide la FK alla cancellazione.

### 6.2 Attiva un'utility

| | |
| --- | --- |
| **Metodo** | `POST` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/utilities/` |

#### Body — attivazione

| Campo | Tipo | Obbligatorio | Note |
| --- | --- | --- | --- |
| `utility_id` | int | Si | FK `config.utilities` (ammessa per il ruolo `EF`) |
| `arrotondamento_importi_dec` | int \| null | No | Decimali degli importi (0..2, CHECK DB) |
| `metodo_arrotondamento_importi` | string \| null | No | `HALF_UP`, `HALF_DOWN`, `UP`, `DOWN` (CHECK DB) |
| `minimo_soglia_min` | numeric \| null | No | Soglia minima |
| `minimo_soglia_max` | numeric \| null | No | Soglia massima (`>= minimo_soglia_min`) |

⛔ `attivo` non e' nel contratto: una chiave fuori contratto e' un `400
E_ANAG_VALIDAZIONE` che la nomina.

I parametri hanno il tipo verificato prima del DB, in POST come in PATCH: un valore
non numerico nei decimali o nelle soglie e' un `400 E_ANAG_VALIDAZIONE` col campo;
`null` o la stringa vuota = nessun valore (vale la policy dell'azienda o il sistema).

Le due soglie si dichiarano **insieme**: entrambe valorizzate (fondo fattura
attivo sulla banda) o entrambe vuote (non attivo). Una sola →
`400 E_FONDO_SOGLIE_INCOMPLETE` (CHECK `chk_emittenti_fiscali_utilities_soglie_coppia`);
la regola vale anche in PATCH, sull'unione di payload e riga a database.

#### Esempio cURL — POST utility

```bash
curl -X POST "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/1/utilities/" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{ "utility_id": 1 }'
```

#### Risposta — POST record utility

```json
{ "data": { "id": 100 } }
```

#### Errori specifici POST utility

| Codice | HTTP | Descrizione |
| --- | --- | --- |
| `E_ANAG_VALIDAZIONE` | 400 | `utility_id` mancante, chiave fuori contratto, parametro di tipo sbagliato, decimali o metodo fuori dominio, soglia minima > massima |
| `E_FONDO_SOGLIE_INCOMPLETE` | 400 | Una sola delle due soglie valorizzata |
| `E_UTILITY_RUOLO_NON_AMMESSO` | 400 | L'utility non e' ammessa per il ruolo `EF` (matrice fail-closed) |
| `E_ATTIVO_PADRE_NON_ATTIVO` | 409 | L'emittente e' spento |
| `E_ANAG_DUPLICATO` | 409 | L'azienda gestisce gia' l'utility |
| `E_ANAG_NOT_FOUND` | 404 | Emittente padre non trovato |

### 6.3 I parametri

| | |
| --- | --- |
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/utilities/<record_id>/` |

Campi editabili, tutti facoltativi e annullabili: `minimo_soglia_min`,
`minimo_soglia_max`, `arrotondamento_importi_dec`, `metodo_arrotondamento_importi`.
«Togli i parametri» = i quattro a `null`: l'utility resta gestita. `utility_id` e
`attivo` fuori contratto (`400`).

#### Esempio cURL — PATCH utility

```bash
curl -X PATCH "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/1/utilities/100/" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{ "arrotondamento_importi_dec": null, "metodo_arrotondamento_importi": null }'
```

#### Risposta — PATCH utility

```json
{ "data": { "updated": true } }
```

### 6.4 Togli l'utility all'azienda

| | |
| --- | --- |
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/anagrafiche/emittenti-fiscali/<emittente_id>/utilities/<record_id>/` |

Verifica appartenenza al padre prima di cancellare. Correzione di un'attivazione
sbagliata (D-U-9): ammessa solo se nessun billing account e nessun documento usa la
coppia; altrimenti `E_ANAG_FK` col messaggio «L'utility e' usata da billing account
o documenti di questa azienda: non si puo' togliere.» (le FK `*_utility_gestita`,
mappate in `_UTILITY_FK_CONSTRAINTS`). Le FK sono differite: il rifiuto arriva a fine
istruzione perche' il backend gira in autocommit; dentro un `transaction.atomic()`
arriverebbe al COMMIT, fuori dalla traduzione.

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

## 7. Utility di un billing account guidate dall'emittente

| | |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/billing-account/<billing_account_id>/utilities/` |
| **View** | `BillingAccountUtilitiesView` (`views_billing_account.py`), `DomainAPIView` — **non** admin |
| **Permesso** | oggetto `("anagrafiche", "cliente")`, area `anagrafiche`; in piu' scope emittente sul BA (lo saltano solo gli operatori senza emittente di lavoro: il superuser Django non ha bypass, D-J) |

Query: `ruolo` **obbligatorio**, `CL` \| `FO` \| `GE` (ruolo del soggetto del BA,
confrontato esatto: e' il `codice_interno`, non si porta in maiuscolo).

Le utility ammesse per il ruolo del soggetto, intersecate con quelle ammesse per
il ruolo `EF` dell'emittente del BA (mapping specifico, altrimenti gestore
globale), con i parametri di `emittenti_fiscali_utilities` quando esistono
(`anagrafiche.fn_lookup_utilities_per_ba`). Ordine per `descrizione`.

```json
{
  "data": {
    "results": [
      {
        "utility_id": 1,
        "codice": "EE",
        "descrizione": "Energia Elettrica",
        "is_personalizzata_per_ef": true,
        "minimo_soglia_min": 0.50,
        "minimo_soglia_max": 5.00,
        "arrotondamento_importi_dec": 2,
        "metodo_arrotondamento_importi": "HALF_UP"
      }
    ]
  },
  "meta": {"request_id": "..."}
}
```

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_ANAG_VALIDAZIONE` | 400 | `ruolo` assente o diverso da `CL`/`FO`/`GE` |
| `E_PARAMETRO_INVALIDO` | 400 | `ruolo` ammesso ma diverso da quello del billing account (per esempio `FO` su un BA cliente): lo rifiuta `anagrafiche.fn_lookup_utilities_per_ba` |
| `E_BILLING_ACCOUNT_NOT_FOUND` | 404 | Billing account inesistente o fuori dal perimetro di chi chiama (RLS): i due casi sono uno solo. Lo solleva il service prima del controllo di scope, e la funzione SQL per lo stesso caso (dal `20261126-42`; prima `E_ANAG_NOT_FOUND`) |
| `E_PERMESSO_NEGATO` | 403 | Billing account di un emittente diverso da quello dell'operatore |

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
  `IsAdminZeroERP` (binding `SUPER_ADMIN` o superuser Django).
- Helper di service `_verify_record_ownership` (modulo
  `emittenti_fiscali_service`) e' condiviso da `EmittentiFiscaliBillingAccountService`
  e `EmittentiFiscaliUtilitiesService` per evitare duplicazione del pattern
  "resolve padre + verifica appartenenza".
- I test mockano `IsAdminZeroERP.has_permission` per bypassare il check ADMIN
  in CI; sono presenti test 403 specifici sia per l'endpoint principale che
  per i sub-resource BA e Utilities.
