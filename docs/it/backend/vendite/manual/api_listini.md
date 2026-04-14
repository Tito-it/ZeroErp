# API Listini (Vendite)

## Scopo

Esporre via HTTP la gestione completa dei listini vendite: anagrafica listino,
versioni temporali, righe prezzo, associazioni di contesto e test del resolver prezzo.

## Contesto

Tutti gli endpoint risiedono sotto `/api/v1/vendite/listini/` e sono implementati in:
- `apps/vendite/api/views_listini.py`
- `apps/vendite/services/listini_service.py`
- `apps/vendite/db/listini_repository.py`

Il backend segue il modello DB-first del progetto:
- PostgreSQL resta source of truth per vincoli, overlap temporali, unicita` e resolver prezzo;
- Django orchestra parsing HTTP, validazione applicativa minima, envelope risposta e traduzione errori.

Le API richiedono JWT (`Authorization: Bearer <token>`) e usano l'envelope standard:

```json
{
  "data": {},
  "meta": {
    "request_id": "..."
  }
}
```

## Base URL

```text
/api/v1/vendite/listini/
```

---

## 1. Lista e creazione listini

### 1.1 Lista listini

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/vendite/listini/` |

#### Query param

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `search` | string | No | Ricerca su `codice` e `descrizione` |
| `utility_id` | int | No | Filtro per utility (FK `config.utilities`) |
| `tipologia_id` | int | No | Filtro per tipologia listino (FK `config.listini_tipologie`) |
| `attivo` | bool | No | Filtro attivo/disattivo; parsing rigoroso |
| `page` | int | No | Numero pagina, default `1` |
| `page_size` | int | No | Righe per pagina, default `25`, max `200` |
| `order_by` | string | No | `codice`, `descrizione`, `utility_descrizione`, `tipologia_descrizione`, `data_insert`, `data_update` |
| `order_dir` | string | No | `asc` oppure `desc` |

I query param `utility_id` e `tipologia_id` sono normalizzati via `qp_str`:
stringa vuota equivale a parametro assente (nessun filtro).

#### Risposta (200)

```json
{
  "data": {
    "count": 1,
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
    "results": [
      {
        "id": 10,
        "codice": "LIST-GAS-2026",
        "descrizione": "Tariffe consumo gas 2026",
        "utility_id": 1,
        "utility_codice": "GAS",
        "utility_descrizione": "Gas",
        "tipologia_id": 1,
        "tipologia_codice": "CONSUMO",
        "tipologia_descrizione": "Consumi",
        "attivo": true,
        "versioni_count": 2,
        "associazioni_count": 1
      }
    ]
  }
}
```

### 1.2 Crea listino

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/` |

#### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `codice` | string | Si | Codice univoco listino (immutabile dopo create) |
| `descrizione` | string | Si | Descrizione listino |
| `utility_id` | int | Si | FK `config.utilities` — intero positivo (per il commercio usare la utility `Base`, id=5 nel seed standard) |
| `tipologia_id` | int | Si | FK `config.listini_tipologie` — intero positivo; la coppia `(utility_id, tipologia_id)` deve esistere attiva in `config.listini_tipologie_utilities` (guard DB) |
| `meta` | object | No | Metadati liberi |
| `attivo` | bool | No | Default DB `true` |

#### Risposta (200)

Restituisce il dettaglio completo del listino creato, con array `versioni` e `associazioni`.

#### Errori tipici

- `400` `E_VENDITE_VALIDATION`:
  - `utility_id` o `tipologia_id` mancanti, nulli, non numerici, non positivi
  - `utility_id` / `tipologia_id` non esistenti (FK violation)
  - Combinazione `(utility_id, tipologia_id)` non ammessa dalla matrice `config.listini_tipologie_utilities`
  - codice duplicato (`uq_listini_codice`)
  - payload JSON non coerente

---

## 2. Dettaglio e update listino

### 2.1 Dettaglio listino

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/` |

#### Risposta (200)

```json
{
  "data": {
    "id": 10,
    "codice": "LIST-GAS-2026",
    "descrizione": "Tariffe consumo gas 2026",
    "utility_id": 1,
    "utility_codice": "GAS",
    "utility_descrizione": "Gas",
    "tipologia_id": 1,
    "tipologia_codice": "CONSUMO",
    "tipologia_descrizione": "Consumi",
    "attivo": true,
    "versioni_count": 2,
    "associazioni_count": 1,
    "versioni": [],
    "associazioni": []
  }
}
```

### 2.2 Aggiorna listino

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/` |

#### Body JSON

Campi ammessi (tutti opzionali; almeno uno deve essere presente):

| Campo | Tipo | Nullable | Descrizione |
| --- | --- | --- | --- |
| `descrizione` | string | No | Nuova descrizione |
| `utility_id` | int | No | Nuova utility (se inviato, NOT NULL; guard matrice DB) |
| `tipologia_id` | int | No | Nuova tipologia (se inviato, NOT NULL; guard matrice DB) |
| `meta` | object | Si | Metadati liberi |
| `attivo` | bool | No | Attivazione / disattivazione |

#### Regole specifiche

- `codice` è immutabile a livello API (trigger DB `trg_listini_a10_protect_codice_upd` lo conferma).
- `utility_id` e `tipologia_id` non possono essere inviati a `null`: se presenti nel payload devono essere interi positivi. Il cambio coppia è validato dal trigger DB `trg_listini_a10_guard_tipologia_utility_ins_upd` contro la matrice `config.listini_tipologie_utilities`.
- La `PATCH` usa il pattern standard `handle_post_json(...)`.
- Se nessun campo supportato è presente nel payload, restituisce `400` `E_VENDITE_VALIDATION`.

#### Errori tipici

- `404` `E_VENDITE_LISTINO_NOT_FOUND`
- `400` `E_VENDITE_VALIDATION`:
  - `tipologia_id` inviato come `null`
  - Combinazione `(utility_id, tipologia_id)` non ammessa dalla matrice
  - Payload vuoto

### 1.5 Elimina listino mai usato

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/` |

Elimina un listino **solo se non ha figli**: `versioni_count == 0` AND
`associazioni_count == 0`. Caso d'uso tipico: listini di test creati per
errore. Per disattivare un listino con figli, usare `PATCH attivo=false`.

Risposta (200):

```json
{ "data": { "deleted": true, "id": 10 } }
```

Errori tipici:

- `400` `E_VENDITE_VALIDATION` se il listino ha versioni o associazioni
- `404` `E_VENDITE_LISTINO_NOT_FOUND`

---

## 2bis. Tipologie ammesse per utility

Endpoint di supporto per il frontend: dato un `utility_id`, restituisce le
tipologie di listino ammesse dalla matrice
`config.listini_tipologie_utilities` (solo righe attive). Usato dal
`ListinoDrawer` per popolare il Select tipologia al cambio utility.

### 2bis.1 Lista tipologie per utility

| | |
| --- | --- |
| **Metodo** | `GET` |
| **URL** | `/api/v1/vendite/listini/tipologie-per-utility/` |

#### Query param

| Parametro | Tipo | Obbligatorio | Descrizione |
| --- | --- | --- | --- |
| `utility_id` | int | Si | FK `config.utilities`, intero positivo |

Se `utility_id` manca o è stringa vuota, la risposta è `400`
`E_VENDITE_VALIDATION` con detail che riporta esplicitamente
"utility_id è obbligatorio".

#### Risposta (200)

Envelope standard con chiave `results` (pattern lookup dedicati):

```json
{
  "data": {
    "results": [
      {
        "id": 1,
        "codice": "CONSUMO",
        "descrizione": "Consumi",
        "e_consumo": true,
        "e_quota_fissa": false,
        "e_imposta": false,
        "e_onere": false,
        "e_prodotto": false,
        "e_servizio": false,
        "ordinamento": 10
      },
      {
        "id": 2,
        "codice": "QUOTA_FISSA",
        "descrizione": "Quote fisse",
        "e_consumo": false,
        "e_quota_fissa": true,
        "e_imposta": false,
        "e_onere": false,
        "e_prodotto": false,
        "e_servizio": false,
        "ordinamento": 20
      }
    ]
  }
}
```

L'ordinamento segue `ordinamento ASC, descrizione ASC`. Sono restituite
solo le tipologie attive (`listini_tipologie.attivo = true`) e solo le
righe della matrice attive (`listini_tipologie_utilities.attivo = true`).

#### Errori tipici

- `400` `E_VENDITE_VALIDATION`: `utility_id` mancante, vuoto o non positivo.

#### Note

- L'utility deve esistere per ottenere righe. Per `utility_id` inesistente
  la risposta è `200` con `results: []` (no 404) — accettabile per un
  endpoint lookup.
- Non applica scope per emittente: `config.listini_tipologie` è tabella
  globale.

---

## 3. Versioni listino

### 3.1 Lista versioni

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/` |

Restituisce:
- dati principali versione
- `righe_count` per ogni versione

### 3.2 Crea versione

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/` |

#### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `codice_versione` | string | Si | Codice univoco per listino |
| `valido_dal` | date | Si | Data inizio validita` |
| `valido_al` | date | No | Data fine validita` |
| `meta` | object | No | Metadati liberi |
| `attivo` | bool | No | Default DB `true` |

### 3.3 Dettaglio versione

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/` |

### 3.4 Aggiorna versione

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/` |

#### Campi ammessi per stato (whitelist)

I campi modificabili dipendono dallo **stato corrente** della versione. Il backend
applica una whitelist fail-fast: qualsiasi campo non ammesso nel payload provoca
un errore `400 E_VENDITE_VALIDATION` senza eseguire l'UPDATE.

| Stato versione | Campi modificabili |
|---|---|
| `BOZZA` | `codice_versione`, `valido_dal`, `valido_al`, `meta`, `attivo` |
| `ATTIVA` | solo `valido_al` (programmazione chiusura) |
| `CHIUSA` | nessun campo (stato terminale) |

**Razionale**: una versione `ATTIVA` ha gia` propagato i prezzi negli snapshot di
`commesse_attivita`/`attivita_fatturabili`. Modificare `codice_versione`, `valido_dal`
o `meta` su una versione operativa creerebbe drift tra documenti emessi e stato
listino. Solo `valido_al` (programmazione chiusura) resta modificabile. Per
cambiare prezzi su un periodo gia` attivo, si crea una nuova versione (clone +
edit + activate).

#### Errori tipici

- `400` `E_VENDITE_VALIDATION` con `detail` che elenca i campi non ammessi e quelli consentiti
- `404` `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND`

### 3.5 Clona versione

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{src_ver_id}/clona/` |

Crea una **nuova versione BOZZA** dello stesso listino copiando tutte le righe
attive della versione sorgente. Workflow operativo "cambio prezzi": clona V001
in V002 BOZZA, modifica i prezzi che cambiano, attiva V002. La sorgente non
viene toccata.

#### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `codice_versione` | string | Si | Codice univoco per il listino |
| `valido_dal` | date | Si | Data inizio validita` (vedi vincolo D2 sotto) |
| `valido_al` | date | No | Data fine validita`, NULL = aperta |

`meta` e `attivo` non sono ammessi nel payload del clone: la nuova versione
nasce in stato BOZZA con `attivo=true` e `meta` vuoto. Le righe vengono copiate
con `attivo=true` (le righe non attive della sorgente sono escluse).

#### Vincolo D2 — `valido_dal` e retroattivita`

`nuova.valido_dal` puo` essere retroattivo (precedente alla data odierna), ma
**non puo` essere inferiore a `sorgente.valido_dal`**. Cio` protegge da cloni
"prima dell'inizio" della versione che si vuole sostituire.

Il clone retroattivo non modifica le fatturazioni gia` emesse nel periodo:
queste continuano a basarsi sullo snapshot in `commesse_attivita` /
`attivita_fatturabili`. Per correggerle e` necessaria una rettifica DB-L4
(dominio separato, vedi `dev/work-in-progress/sviluppo-rettifiche.md`).

#### Errori tipici

- `400` `E_VENDITE_VALIDATION` se `nuova.valido_dal < sorgente.valido_dal` o se
  manca un campo obbligatorio
- `400` `E_VENDITE_VALIDATION` se `codice_versione` duplicato per il listino
- `404` `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND` se la sorgente non esiste

### 3.6 Elimina versione

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/` |

Elimina una versione **solo se in stato `BOZZA`**, con tutte le sue righe in
cascata. Versioni `ATTIVA` o `CHIUSA` sono storiche e non eliminabili.

Risposta (200):

```json
{ "data": { "deleted": true, "id": 101 } }
```

Errori tipici:

- `400` `E_VENDITE_VALIDATION` se la versione non e` BOZZA
- `404` `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND`

### 3.7 Cambia stato versione

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/stato/` |

#### Body JSON

```json
{
  "stato": "ATTIVA",
  "dry_run": false
}
```

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `stato` | string | Si | `ATTIVA` o `CHIUSA` (transizione di stato) |
| `dry_run` | bool | No | Se `true`, esegue tutte le validazioni e calcola l'auto-close ma non scrive nulla. Restituisce un envelope di preview. Default `false`. |

#### Regole specifiche

- Stati ammessi:
  - `BOZZA`
  - `ATTIVA`
  - `CHIUSA`
- Transizioni ammesse:
  - `BOZZA -> ATTIVA`
  - `ATTIVA -> CHIUSA`
- Per `BOZZA -> ATTIVA` deve esistere almeno una riga **attiva** nella versione.
- Overlap temporali e unicita` restano governati dai vincoli DB su `vendite.listini_versioni`.

#### Auto-close della versione precedente (decisione D3)

Quando si esegue `BOZZA -> ATTIVA`, il backend cerca le altre versioni dello
stesso listino in stato `ATTIVA + attivo` con `valido_dal < nuova.valido_dal`
e che si **sovrappongono** al nuovo intervallo (`valido_al IS NULL` oppure
`valido_al >= nuova.valido_dal`). Per ognuna, nella **stessa transazione DB**:

1. Imposta `precedente.valido_al = nuova.valido_dal - 1`
2. Attiva la nuova versione

L'ordine e` necessario per non urtare il vincolo `ex_listini_versioni_no_overlap`
(GIST exclusion). Senza l'auto-close, l'attivazione fallirebbe per overlap.

#### Modalita` `dry_run` (preview UI)

Con `dry_run: true`, la chiamata non scrive nel DB e restituisce:

```json
{
  "data": {
    "dry_run": true,
    "versione_id": 202,
    "nuovo_stato": "ATTIVA",
    "auto_close": [
      {
        "id": 101,
        "codice_versione": "V001",
        "valido_dal": "2026-01-01",
        "valido_al_prima": null,
        "valido_al_dopo": "2026-03-31"
      }
    ]
  }
}
```

Il frontend usa questa preview per il dialog di conferma attivazione, mostrando
all'operatore l'elenco delle versioni che verranno auto-chiuse e la nuova
`valido_al` calcolata.

#### Errori tipici

- `404` `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND`
- `400` `E_VENDITE_VALIDATION` per transizione non ammessa o versione senza righe attive

---

## 4. Righe prezzo versione

### 4.1 Lista righe

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/righe/` |

Le righe sono arricchite con campi display:
- `articolo_codice`, `articolo_descrizione`
- `uom_codice`, `uom_descrizione`
- descrizioni del contesto BA / utility / emittente se presenti

### 4.2 Crea riga

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/righe/` |

#### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `articolo_id` | uuid | Si | Articolo prezzo |
| `uom_id` | int | Si | UoM prezzo |
| `prezzo` | decimal | Si | Prezzo unitario, `>= 0` |
| `billing_account_id` | int | No | Perimetro BA |
| `utility_id` | int | No | Perimetro utility |
| `emittente_soggetto_ruolo_id` | int | No | Perimetro emittente fiscale |
| `meta` | object | No | Metadati liberi |
| `attivo` | bool | No | Default DB `true` |

### 4.3 Aggiorna riga

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/righe/{riga_id}/` |

Campi ammessi:
- `prezzo`
- `billing_account_id`
- `utility_id`
- `emittente_soggetto_ruolo_id`
- `meta`
- `attivo`

### 4.4 Elimina riga

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/righe/{riga_id}/` |

#### Regole specifiche

- **Immutabilita` per stato versione (guard fail-fast)**: `POST`, `PATCH` e `DELETE`
  riga sono ammessi **solo** se la versione padre e` in stato `BOZZA`. Su versioni
  `ATTIVA` o `CHIUSA` il backend rifiuta con `400 E_VENDITE_VALIDATION` prima di
  toccare il DB. Razionale: i prezzi delle versioni operative sono gia` snapshot
  in `commesse_attivita`/`attivita_fatturabili` e ogni modifica creerebbe drift
  con i documenti gia` emessi. Per cambiare prezzi su un periodo gia` attivo, si
  crea una nuova versione (clone + edit + activate).
- Il backend valida pre-flight:
  - articolo attivo
  - UoM attiva
  - compatibilita` articolo/UoM: UoM base articolo oppure UoM operativa attiva
- L'unicita` della combinazione attiva (`versione + articolo + uom + contesto`) e` demandata al DB.

---

## 5. Associazioni listino

### 5.1 Lista associazioni

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/associazioni/` |

### 5.2 Crea associazione

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/associazioni/` |

#### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `valido_dal` | date | Si | Data inizio validita` associazione |
| `valido_al` | date | No | Data fine validita` |
| `billing_account_id` | int | No | Contesto BA |
| `utility_id` | int | No | Contesto utility |
| `emittente_soggetto_ruolo_id` | int | No | Contesto emittente fiscale |
| `meta` | object | No | Metadati liberi |
| `attivo` | bool | No | Default DB `true` |

### 5.3 Aggiorna associazione

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/associazioni/{assoc_id}/` |

### 5.4 Elimina associazione

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/associazioni/{assoc_id}/` |

#### Regole specifiche

- `valido_al`, se presente, deve essere maggiore di `valido_dal`
- L'unicita` della combinazione attiva (`listino + contesto + valido_dal`) e` demandata al DB

---

## 6. Test resolver prezzo

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/test-prezzo/` |

### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `articolo_id` | uuid | Si | Articolo da risolvere |
| `uom_id` | int | Si | UoM da risolvere |
| `data_riferimento` | date | Si | Data di riferimento |
| `billing_account_id` | int | No | BA di contesto |
| `utility_id` | int | No | Utility di contesto |
| `emittente_soggetto_ruolo_id` | int | No | Emittente fiscale di contesto |

### Risposta (200)

```json
{
  "data": {
    "listino_id": 10,
    "listino_codice": "LIST-UTILITY",
    "listino_descrizione": "Listino Utility Base",
    "listino_versione_id": 101,
    "codice_versione": "2026-Q2",
    "versione_stato": "ATTIVA",
    "listino_riga_id": 1001,
    "listino_associazione_id": 3001,
    "prezzo": "12.5000000000",
    "match_level": 6
  }
}
```

### Regole specifiche

- Wrapper HTTP del resolver DB `vendite.fn_resolve_prezzo_listino(...)`
- Richiede `data_riferimento`
- In caso di nessun match o pareggio totale, gli errori restano quelli del DB:
  - `E_PREZZO_LISTINO_NON_TROVATO`
  - `E_PREZZO_LISTINO_AMBIGUO`

---

## 7. Alert scadenze versioni (N2)

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/vendite/listini/alert-scadenze/` |

Restituisce le versioni ATTIVE in scadenza entro N giorni che non hanno una versione
successiva (ATTIVA o BOZZA) con `valido_dal > valido_al`. Serve per monitorare
listini a rischio "buco di copertura" in produzione.

### Query param

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `giorni` | int | No | Anticipo in giorni, default `15`, range 1-365 |

### Risposta (200)

```json
{
  "data": {
    "results": [
      {
        "listino_id": 10,
        "listino_codice": "LIST-UTILITY",
        "listino_descrizione": "Listino Utility Base",
        "dominio": "UTILITY",
        "versione_id": 101,
        "codice_versione": "V001",
        "valido_dal": "2026-01-01",
        "valido_al": "2026-04-30",
        "giorni_rimanenti": 8
      }
    ],
    "count": 1,
    "giorni": 15
  }
}
```

### Regole specifiche

- Filtro temporale isolato nel repository (`_filter_versioni_in_scadenza`) per facilitare
  futura migrazione a `daterange` nativo PostgreSQL (N1).
- `giorni_rimanenti` puo` essere negativo se la versione e` gia` scaduta.
- Frontend: widget `AlertScadenzeWidget.vue` con badge nella toolbar listini.

---

## 8. Variazione percentuale massa (N8a)

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/applica-variazione/` |

Applica una variazione percentuale ai prezzi di tutte le righe attive di una versione
BOZZA. Supporta `dry_run` per preview e filtro opzionale per articoli.

### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `variazione_percentuale` | decimal | Si | Positivo = aumento, negativo = riduzione. Range: -99 a +1000 |
| `arrotondamento_decimali` | int | No | Decimali da mantenere. Default `4`, range 0-10 |
| `filtro_articoli` | array uuid | No | Se valorizzato, applica solo a questi articoli |
| `dry_run` | bool | No | Se `true`, calcola preview senza modificare. Default `false` |

### Risposta dry_run (200)

```json
{
  "data": {
    "dry_run": true,
    "righe_coinvolte": 500,
    "preview": [
      {
        "riga_id": 1001,
        "articolo_codice": "ART001",
        "articolo_descrizione": "Articolo esempio",
        "prezzo_attuale": "12.5000",
        "prezzo_calcolato": "12.8750"
      }
    ],
    "variazione_percentuale": "3.0",
    "arrotondamento_decimali": 4
  }
}
```

### Risposta applicazione (200)

```json
{
  "data": {
    "righe_aggiornate": 500,
    "variazione_percentuale": "3.0",
    "arrotondamento_decimali": 4
  }
}
```

### Regole specifiche

- Guard BOZZA: rifiuta con 400 su versioni ATTIVA o CHIUSA.
- Guard range: `-99 <= variazione <= 1000`. Fuori range → 400.
- **Arrotondamento composto**: ogni applicazione e` atomica con arrotondamento immediato.
  Due variazioni successive (+3% poi +2%) producono risultati diversi da una singola +5.06%.
- **Audit**: la variazione viene registrata in `versione.meta.variazioni_percentuali[]`
  con data, percentuale, arrotondamento, righe aggiornate e filtro.
- Frontend: `ApplicaVariazioneDialog.vue` (2 step: input → preview dry_run → conferma).

### Errori tipici

- `400` `E_VENDITE_VALIDATION`: versione non BOZZA, percentuale fuori range, arrotondamento fuori range

---

## 9. Rettifica controllata riga ATTIVA (N6)

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/vendite/listini/{listino_id}/versioni/{ver_id}/righe/{riga_id}/rettifica-controllata/` |

Consente la modifica del prezzo di una riga in versione **ATTIVA** solo se la riga
**non e` mai stata propagata** in `commesse_attivita` o `attivita_fatturabili`.
Caso d'uso: errore di battitura su riga non ancora usata da nessuna commessa.

### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `prezzo` | decimal | Si | Nuovo prezzo, `> 0` |
| `motivo` | string | Si | Motivazione obbligatoria, max 500 caratteri |

### Risposta (200)

```json
{
  "data": {
    "riga_id": 1001,
    "prezzo_precedente": "12.5000000000",
    "prezzo_nuovo": "12.2500000000",
    "motivo": "errore di battitura al caricamento"
  }
}
```

### Regole specifiche

- **Endpoint dedicato** separato dal PATCH ordinario della riga. L'operazione
  eccezionale deve essere esplicita, non mascherata dal PATCH standard.
- **Guard triplo livello**:
  1. Service Python: lock `FOR UPDATE` sulla riga + check non-propagazione nella stessa transazione
  2. Trigger DB `trgfn_listini_righe_guard_stato` (defense-in-depth, da implementare su `dev/db-tid`)
  3. Audit obbligatorio in `riga.meta.rettifiche_controllate[]`
- **Tabelle controllate per propagazione** (espansione concentrica):
  - `vendite.commesse_attivita` (`listino_riga_id`)
  - `vendite.attivita_fatturabili` (`listino_riga_id`)
- Se la riga e` stata propagata → errore `409 E_VENDITE_RIGA_GIA_PROPAGATA`.
  Soluzione: clonare la versione (O1).

### Errori tipici

- `400` `E_VENDITE_VALIDATION`: versione non ATTIVA, prezzo non valido, motivo mancante o troppo lungo
- `409` `E_VENDITE_RIGA_GIA_PROPAGATA`: riga usata in almeno una commessa/fatturabile

---

## Regole trasversali

- Tutti gli endpoint richiedono JWT.
- Le view write (`POST`, `PATCH`) usano il pattern core `handle_post_json(...)`.
- Gli endpoint `PATCH` accettano solo payload JSON.
- Non e` richiesto `Idempotency-Key`: il sottodominio listini non e` ancora agganciato a write idempotenti dedicate.
- I codici errore applicativi sono centralizzati in `error_policies.py`:
  - `E_VENDITE_LISTINO_NOT_FOUND` (404)
  - `E_VENDITE_LISTINO_VERSIONE_NOT_FOUND` (404)
  - `E_VENDITE_LISTINO_RIGA_NOT_FOUND` (404)
  - `E_VENDITE_LISTINO_ASSOCIAZIONE_NOT_FOUND` (404)
  - `E_VENDITE_RIGA_GIA_PROPAGATA` (409) — rettifica controllata N6
  - `E_VENDITE_VALIDATION` (400) — validazione generica

## Dipendenze DB

- Tabelle:
  - `vendite.listini`
  - `vendite.listini_versioni`
  - `vendite.listini_righe`
  - `vendite.listini_associazioni`
- Lookup/decodifiche:
  - `catalogo.vw_articoli_dettaglio`
  - `catalogo.unita_misura`
  - `catalogo.articoli`
  - `catalogo.articoli_uom_operativa`
  - `config.utilities`
  - `config.listini_tipologie`
  - `config.listini_tipologie_utilities` (matrice ammissibilita` utility x tipologia)
  - `anagrafiche.billing_account`
  - `anagrafiche.vw_soggetti_ruoli_dettaglio`
- Funzioni SQL:
  - `vendite.fn_resolve_prezzo_listino(...)`
- Trigger DB di guard rilevanti per le API:
  - `trg_listini_a10_guard_tipologia_utility_ins_upd` → `vendite.trgfn_listini_guard_tipologia_utility()`
    valida la coppia `(utility_id, tipologia_id)` contro `config.listini_tipologie_utilities`

## Note di migrazione

- Il backend non replica la logica pricing del DB: la consuma.
- Overlap temporali, univocita` e buona parte delle guard di integrita` restano nel database.
- **Post-refactor 2026-04-09**: il campo `priorita` e` stato droppato da `listini_versioni` e
  `listini_associazioni` (migration `20260409-04/-05`). Nessun endpoint lo accetta piu`.
- **Sprint B-v3 (2026-04-12)**: aggiunti endpoint alert scadenze (N2), variazione % massa (N8a),
  rettifica controllata (N6). La rettifica N6 attende trigger DB defense-in-depth (`dev/db-tid`).
- **Sprint v4 (2026-04-13/14)**: rimosso il campo legacy `dominio` (enum UTILITY/COMMERCIO).
  Ogni listino ha ora due colonne NOT NULL: `utility_id` (FK `config.utilities`; id=5
  utility Base per il commercio) e `tipologia_id` (FK `config.listini_tipologie`).
  Gli endpoint create/update richiedono entrambi i campi; la matrice di ammissibilita` e`
  verificata da trigger DB. Nuovo endpoint di supporto per il drawer frontend:
  GET /api/v1/vendite/listini/tipologie-per-utility/. Nuovo filtro `tipologia_id` sulla lista
  listini e nuovi campi di ordinamento `utility_descrizione` e `tipologia_descrizione`.
