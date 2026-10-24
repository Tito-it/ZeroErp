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
| 5.1 | `GET` | `/emittenti-fiscali/<id>/billing-account/` | Lista mapping BA |
| 5.2 | `POST` | `/emittenti-fiscali/<id>/billing-account/` | Crea mapping BA o default globale |
| 5.3 | `DELETE` | `/emittenti-fiscali/<id>/billing-account/<mapping_id>/` | Elimina mapping BA |
| 5.4 | `GET` | `/emittenti-fiscali/<id>/billing-account/summary/` | Summary mapping (has_default + count_specifici) |
| 6.1 | `GET` | `/emittenti-fiscali/<id>/utilities/` | Lista record utility per emittente |
| 6.2 | `POST` | `/emittenti-fiscali/<id>/utilities/` | Crea record utility |
| 6.3 | `PATCH` | `/emittenti-fiscali/<id>/utilities/<record_id>/` | Aggiorna record utility |
| 6.4 | `DELETE` | `/emittenti-fiscali/<id>/utilities/<record_id>/` | Elimina record utility |
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
| `dbops.trgfn_prevent_deactivate_if_children` | Trigger (×16) | Blocca la disattivazione se esistono figli. Un trigger **per tabella figlia** generato dall'automazione ATTIVO, e il messaggio **nomina la tabella** che sta bloccando. Dal changeSet `20260820-08` i codici sono **due**, scelti dal guard secondo la tabella figlia: `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` dove le righe collegate si **disattivano** (la figlia ha la colonna `attivo`) e `E_ATTIVO_BLOCK_CHILDREN_EXIST` dove si **tolgono** (la figlia non ce l'ha). Prima era un codice solo e la parola «attive» era falsa per 181 trigger su 349. Copertura reale (letta dagli argomenti dei trigger, non dai loro nomi troncati): `anagrafiche.emittenti_fiscali_billing_account`, `anagrafiche.emittenti_fiscali_utilities`, `config.parameter_overrides`, `config.user_emittente_attivo`, `config.user_emittenti_fiscali`, `documenti.documenti_generati`, `documenti.template_asset`, `documenti.template_documenti`, `pratiche.pratiche`, `pratiche.workflow_definizioni`, `vendite.contratti`, `vendite.ddt`, `vendite.offerte_commerciali`, `vendite.ordini`, `vendite.preventivi`, `vendite.resi`.<br>⚠️ Sostituisce `anagrafiche.trgfn_emittenti_fiscali_guard_attivo`, **droppato** il 2026-08-20 (changeSet `20260820-02`): era un doppione che copriva **il solo** mapping billing account — non i quattro figli che questa riga gli attribuiva — e non veniva nemmeno più raggiunto, perché i BEFORE ROW scattano in ordine alfabetico e il generico viene prima. Il suo codice `E_EMITTENTE_DISATTIVAZIONE_BLOCCATA` è **ritirato**. |
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
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
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
2026-10-01, `regime_fiscale_descrizione` (dal catalogo `config.regimi_fiscali`)
con `regime_fiscale_confermato_il` / `regime_fiscale_confermato_da` (entrambi
`null` = regime mai confermato, vedi §4.2).

**Fase 4 — `non_editable_fields` nel detail**: il dict di response include
`non_editable_fields: ["codice", "soggetto_id"]`. Il FE consuma il campo
nel drawer di edit per gating dei Select dimensionali. Pattern coerente con
altre matrici amm-software (categorie clienti listini, tipi ruolo indirizzi).

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
| `E_ANAG_NOT_FOUND` | 404 | Emittente non trovato |

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
- ⭐ Trigger `trg_emittenti_fiscali_ba_a10_guard_storia_emittente_ins_upd_dlt`
  (dal `20260826-49`): un billing account che ha gia' **fatture o commesse** non
  cambia piu' emittente. ⛔ E il movimento da presidiare non e' solo l'`INSERT`:
  il backend non espone nessun `UPDATE` sul mapping, quindi «spostare un cliente
  da un emittente all'altro» si fa con `DELETE` + `INSERT` — ed e' la
  **cancellazione** a fare il danno.
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
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
    "results": [
      {
        "id": 10,
        "billing_account_id": null,
        "is_default": true,
        "billing_account_codice": null,
        "billing_account_ragione_sociale": null,
        "id_fiscale_univoco": null,
        "data_insert": "2026-04-07T10:00:00Z",
        "data_update": "2026-04-07T10:00:00Z",
        "can_remove": false,
        "rimozione_blocco_reason": "DEFAULT_SINGLETON",
        "rimozione_blocco_reason_key": "amministrazione.emittenti_fiscali.ba_blocco.default_singleton",
        "rimozione_blocco_storia": null
      },
      {
        "id": 11,
        "billing_account_id": 5,
        "is_default": false,
        "billing_account_codice": "BA-005",
        "billing_account_ragione_sociale": "Acme Energia Srl",
        "id_fiscale_univoco": "01234567890",
        "data_insert": "2026-04-07T10:05:00Z",
        "data_update": "2026-04-07T10:05:00Z",
        "can_remove": true,
        "rimozione_blocco_reason": null,
        "rimozione_blocco_reason_key": null,
        "rimozione_blocco_storia": null
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
`rimozione_blocco_storia` = l'elenco per famiglia dei documenti che bloccano la
rimozione (dal `dettaglio` di `fn_check_ba_cambio_emittente`), solo col motivo
`BA_CON_STORIA`; `null` altrimenti. Il testo lo compone il client.

#### Capability di riga — `can_remove` e il motivo del blocco

Ogni riga porta **quattro** campi che riguardano la sola azione «rimuovi»:

| Campo | Tipo | Significato |
| --- | --- | --- |
| `can_remove` | bool | `false` quando la riga **non** si puo' togliere |
| `rimozione_blocco_reason` | string \| null | codice macchina del **primo** motivo. `null` = ammesso |
| `rimozione_blocco_reason_key` | string \| null | chiave i18n del tooltip. Il testo **non** viaggia mai nel payload |
| `rimozione_blocco_storia` | json \| null | conteggi per famiglia documentale (solo `BA_CON_STORIA`) |

⚠️ **`can_remove` NON e' piu' `true` per costruzione**, ed e' il cambiamento del
2026-08-27: prima era scritto a mano nel service, e da quando un billing account
con storia non cambia piu' emittente era diventato una **promessa falsa** —
l'operatore scopriva il divieto premendo, dopo aver confermato un dialog. Chi
consuma questa lista non deve piu' presumerlo.

⭐ **I campi del motivo vengono dalla stessa funzione che il database usa per
rifiutare** — `script.fn_check_ba_cambio_emittente`, chiamata in `LATERAL` sulla
riga e chiamata dalla madre `fn_guard_ba_cambio_emittente` per sollevare
l'errore. ⇒ Tooltip e rifiuto non «coincidono oggi»: **non possono divergere**,
perche' la regola sta scritta in un posto solo (`linee-guida-sql` §12.5.2).

**I due motivi oggi a contratto** — l'elenco lo decide il database, non questa
pagina, e puo' crescere senza che il backend cambi:

| `reason` | `codice` sollevato | Quando |
| --- | --- | --- |
| `BA_CON_STORIA` | `E_BA_EMITTENTE_CON_STORIA` | il cliente ha fatture o commesse **e** l'emittente cambierebbe davvero |
| `DEFAULT_SINGLETON` | `E_EMITTENTE_DEFAULT_SINGLETON` | riga del **gestore globale**: deve sempre esistercene una, quindi non si toglie **mai** |

⛔ **Il predicato di un mapping specifico e' una COPPIA**, e la meta' che si
dimentica e' la prima: togliere l'aggancio fa ricadere il billing account sul
gestore globale, quindi il cambio di emittente esiste **solo se** l'emittente
della riga e' **diverso** da quello del default. Se coincidono non si sposta
nessun documento e la rimozione resta ammessa — e' manutenzione ordinaria.
⚠️ Su un'installazione con un solo emittente questo e' il caso **normale**: chi
consumasse un `can_remove` derivato dalla sola presenza di storia spegnerebbe il
gesto su quasi tutte le righe, tutte a torto.

⛔ **Il client non ricalcola il motivo e non compone il testo**: rende
`reason_key` (con ripiego su `reason` se la chiave manca) e disabilita l'azione.
Il BA mapping non ha `PATCH`, quindi `can_update`/`can_configure` non sono
applicabili.

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
| `E_BA_EMITTENTE_CON_STORIA` | 409 | Il billing account ha gia' fatture o commesse presso un **altro** emittente: agganciarlo qui lo sposterebbe |

⚠️ **Su questo verbo non c'e' capability che lo anticipi**, ed e' deliberato: il
billing account si sceglie da un lookup, quindi finche' non e' scelto non c'e'
niente da spegnere. Il 409 resta il canale, e qui **non fa perdere lavoro** —
davanti non c'e' nessun form da compilare, solo un click. La questione e'
tracciata come **Q-2** nel brief `brief-db-motivo-rimozione-mapping-ba`, aperta
d'accordo col team DB.

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
| `E_BA_EMITTENTE_CON_STORIA` | 409 | Il cliente ha gia' fatture o commesse e la rimozione lo sposterebbe su un altro emittente |
| `E_EMITTENTE_DEFAULT_SINGLETON` | 409 | Si sta cancellando il gestore globale |

⭐ **Questi due 409 sono gli stessi che `can_remove` anticipa** (§5.1): l'errore
resta la rete, non il canale — un client che legge la capability non ci arriva.
⚠️ Nessuno dei due e' sollevato da codice Python: nascono nel database e
attraversano il backend senza essere catturati (`create_with_dedup` intercetta
il solo `IntegrityError`, e un `RAISE` PL/pgSQL e' `P0001`).

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
> `GET /api/v1/core/lookup/utilities-per-emittente/?ruolo=<codice>`: le utility
> ammesse per il ruolo `EF` nella matrice `config.utilities_tipi_ruolo`,
> intersecate con quelle del ruolo indicato in `ruolo` (se presente). Coerente
> con il trigger DB `script.fn_guard_utility_tipo_ruolo`, evitando errori
> `E_UTILITY_RUOLO_NON_AMMESSO` lato UI.

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
        "utility_attiva": true,
        "record_id": 100,
        "minimo_soglia_min": 0.50,
        "minimo_soglia_max": null,
        "arrotondamento_importi_dec": 2,
        "metodo_arrotondamento_importi": "HALF_UP",
        "record_attivo": true,
        "record_data_insert": "2026-04-07T10:00:00Z",
        "record_data_update": "2026-04-07T10:00:00Z",
        "can_configure": false,
        "can_update": true,
        "can_remove": true
      },
      {
        "utility_id": 2,
        "utility_codice": "GAS",
        "utility_descrizione": "Gas Naturale",
        "utility_attiva": true,
        "record_id": null,
        "minimo_soglia_min": null,
        "minimo_soglia_max": null,
        "arrotondamento_importi_dec": null,
        "metodo_arrotondamento_importi": null,
        "record_attivo": null,
        "record_data_insert": null,
        "record_data_update": null,
        "can_configure": true,
        "can_update": false,
        "can_remove": false
      }
    ]
  }
}
```

> **Stato della riga**: `record_id != null` -> riga configurata (esiste override);
> `record_id == null` -> riga ammessa ma non personalizzata (l'emittente usa i default
> di sistema).

**Fase 4 — capability di riga data-driven**:

| Campo | Tipo | Quando `true` |
| --- | --- | --- |
| `can_configure` | bool | Slot vuoto (`record_id == null`) + `emittente.attivo == true` + `utility_attiva == true`. L'admin puo' creare la configurazione |
| `can_update` | bool | Record configurato (`record_id != null`). L'admin puo' modificare i parametri |
| `can_remove` | bool | Record configurato (`record_id != null`). L'admin puo' rimuovere |

Il FE consuma le capability per gating UI (mostra/nasconde "Configura"/"Modifica"/"Rimuovi"
nel `RowActionsMenu`) invece di derivare da `record_id`. **L'autorita' resta il
trigger DB** (`child_requires_active_parent`, `guard_utility_tipo_ruolo`): le
capability sono preview UX, non garanzia (race tra sessioni).

Il campo `utility_attiva` e' oggi la costante `TRUE`: `config.utilities` non ha
una colonna `attivo`. Resta nel contratto per il calcolo di `can_configure`.

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
| `minimo_soglia_max` | numeric | No | Soglia massima (`>= minimo_soglia_min`) |
| `attivo` | bool | No | Default `true` |

Le due soglie si dichiarano **insieme**: entrambe valorizzate (fondo fattura
attivo sulla banda) o entrambe vuote (non attivo). Una sola →
`400 E_FONDO_SOGLIE_INCOMPLETE` (CHECK `chk_emittenti_fiscali_utilities_soglie_coppia`);
la regola vale anche in PATCH, sull'unione di payload e riga a database.

#### Esempio cURL — POST utility

```bash
curl -X POST "https://api.example.com/api/v1/anagrafiche/emittenti-fiscali/1/utilities/" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "utility_id": 1,
       "arrotondamento_importi_dec": 2,
       "metodo_arrotondamento_importi": "HALF_UP",
       "minimo_soglia_min": 0.50,
       "minimo_soglia_max": 5.00
     }'
```

#### Risposta — POST record utility

```json
{ "data": { "id": 100 } }
```

#### Errori specifici POST utility

| Codice | HTTP | Descrizione |
| --- | --- | --- |
| `E_ANAG_VALIDAZIONE` | 400 | `utility_id`, `arrotondamento_importi_dec` o `metodo_arrotondamento_importi` mancanti; soglia minima > massima |
| `E_FONDO_SOGLIE_INCOMPLETE` | 400 | Una sola delle due soglie valorizzata |
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

## 7. Utility di un billing account guidate dall'emittente

| | |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/anagrafiche/billing-account/<billing_account_id>/utilities/` |
| **View** | `BillingAccountUtilitiesView` (`views_billing_account.py`), `DomainAPIView` — **non** admin |
| **Permesso** | oggetto `("anagrafiche", "cliente")`, area `anagrafiche`; in piu' scope emittente sul BA (superuser e operatori senza emittente di lavoro lo saltano) |

Query: `ruolo` **obbligatorio**, `CL` \| `FO` \| `GE` (ruolo del soggetto del BA;
case-insensitive).

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
| `E_ANAG_NOT_FOUND` | 404 | Billing account inesistente |
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
