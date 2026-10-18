# API Catalogo (Fasi 1..8)

## Scopo

Esporre via HTTP il backend `catalogo` per il perimetro delle Fasi 1..8:

- anagrafica articoli
- lookup articoli, UoM, modi di arrotondamento
- UoM operative articolo
- componenti BoM con capability di chiusura riga + duplica atomica
- conversioni UoM
- note articolo
- metadata immutabilita' campi (`non_editable_fields`) sui detail
- capability di riga (`puo_eliminarsi`/`puo_gestire_bom`) su lista UoM
  operative e lista articoli
- disattivazione/riattivazione articolo come azioni dedicate (Fase 7)
- defaults pre-compilazione form articolo (Fase 8)

## Contesto

Gli endpoint risiedono sotto `/api/v1/catalogo/` e sono implementati in:
- `apps/catalogo/api/views.py`
- `apps/catalogo/services/catalogo_service.py`
- `apps/catalogo/db/catalogo_repository.py`
- `apps/catalogo/db/catalogo_uom_repository.py`
- `apps/catalogo/db/catalogo_bom_repository.py`

Il backend segue il modello DB-first del progetto:
- PostgreSQL governa vincoli, guard e coerenza strutturale;
- Django orchestra parsing HTTP, validazione applicativa minima, envelope risposta e traduzione errori.

Tutte le risposte usano l'envelope standard:

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
/api/v1/catalogo/
```

---

## 1. Articoli

### 1.1 Lista articoli

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/articoli/` |

#### Query param

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `search` | string | No | Ricerca libera: le colonne le decide il catalogo della lista `catalogo.articoli`. Sotto 3 caratteri: `400` `E_SEARCH_VALIDATION` |
| `attivo` | bool | No | Filtro attivo/disattivo |
| `is_composito` | bool | No | Filtro articoli composti |
| `voce_utility` | bool | No | Filtro articoli utility |
| `tipo_voce_id` | int | No | Filtro tipologia |
| `gruppo_voce_id` | int | No | Filtro gruppo |
| `data_da` | date | No | Filtro data insert da (giorno dell'azienda: vedi sotto) |
| `data_a` | date | No | Filtro data insert a, giorno incluso. I giorni sono giorni **dell'azienda** (fuso `SYSTEM_FUSO_ORARIO`, confini calcolati dal DB col BB `predicato_giorno_operativo`, dal 2026-10-09) (fino ad allora `data_insert::date`, il giorno della sessione e niente indice) |
| `page` | int | No | Numero pagina, default `1` |
| `page_size` | int | No | Righe per pagina, default `25`, max `200` |
| `order_by` | string | No | `codice`, `descrizione`, `uom_codice`, `data_insert`, `data_update` |
| `order_dir` | string | No | `asc` oppure `desc` |

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
        "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
        "codice": "ART-001",
        "descrizione": "Articolo demo",
        "uom_id": 1,
        "uom_codice": "PZ",
        "is_composito": false,
        "is_solo_componente": false,
        "voce_utility": false,
        "attivo": true,
        "puo_gestire_bom": false,
        "motivo_non_gestibile_bom": "ARTICOLO_NON_COMPOSITO"
      }
    ]
  }
}
```

##### Capability BoM (Fase 6)

Ogni riga espone capability data-driven da `vw_articoli_dettaglio`:

- `puo_gestire_bom: bool` — `true` se `is_composito AND NOT is_solo_componente`.
- `motivo_non_gestibile_bom: string | null` — codice motivo quando
  `puo_gestire_bom=false`. Valori:
  - `"ARTICOLO_SOLO_COMPONENTE"` — articolo marcato come solo componente.
  - `"ARTICOLO_NON_COMPOSITO"` — articolo non composito.
  - `null` — quando `puo_gestire_bom=true`.

Il FE usa questi campi per disabilitare l'azione "manage-bom" e mostrare
il motivo via tooltip i18n (chiavi `catalogo.motivo_*`).

### 1.2 Crea articolo

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/catalogo/articoli/` |

#### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `codice` | string | Si | Codice univoco articolo |
| `descrizione` | string | Si | Descrizione articolo |
| `descrizione_breve` | string | No | Descrizione breve |
| `uom_id` | int | No | UoM base |
| `tipo_voce_id` | int | No | Tipologia |
| `gruppo_voce_id` | int | No | Gruppo |
| `spesa_id` | int | No | Spesa |
| `iva_id` | int | No | IVA |
| `conto_contabile_vendita_id` | int | No | Conto vendita |
| `conto_contabile_acquisto_id` | int | No | Conto acquisto |
| `is_composito` | bool | No | Articolo composto |
| `is_solo_componente` | bool | No | Usabile solo come componente |
| `requires_serial` | bool | No | Richiede seriale |
| `voce_utility` | bool | No | Articolo utility |
| `natura_vendita_id` | int | No | Natura di vendita (FK `config.nature_vendita`): decide l'instradamento post-accettazione del modello split (ORDINE/COMMESSA/CONTRATTO). Se omesso → default DB `MERCE`. **Mai null esplicito** (colonna NOT NULL): risponde `E_CATALOGO_VALIDATION` |
| `modo_approvvigionamento_id` | int | No | **Da dove arriva** l'articolo (FK `config.modi_approvvigionamento`: `ACQUISTO` / `PRODUZIONE` / `STOCK` / `NON_APPLICABILE` — 2026-09-14, Blocco B di `brief-db-modifiche-certe-ciclo-vendita-e-articolo`). Dimensione **ortogonale** alla natura di vendita (dice dove *va* la riga, non da dove *viene*). Se omesso → default DB `ACQUISTO`. **Mai null esplicito** (NOT NULL): `E_CATALOGO_VALIDATION` col campo. Lookup: `GET /core/lookup/codici/?rel=config.modi_approvvigionamento` |
| `gestito_a_magazzino` | bool | No | L'articolo **movimenta giacenza**. Default DB `false` (fail-safe: nessun articolo comincia a movimentare per distrazione). ⚠️ Non si deriva da natura `MERCE`: una merce può essere venduta senza passare da giacenza |
| `lead_time_giorni` | int | No | Giorni fra richiesta e disponibilità. **Nullable per modello**: per una prestazione non significa niente, e `0` non è «non si applica». Negativo → `E_CATALOGO_VALIDATION` col campo (anticipa il CHECK) |
| `meta` | object | No | Metadati liberi |

### 1.3 Dettaglio articolo

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/` |

#### Output specifico

Il dettaglio articolo include gli array correlati e i metadata di
immutabilita' (Fase 5):

- `uom_operative` — array UoM operative dell'articolo, ogni riga arricchita
  da capability di riga (Fase 6, vedi §3.1).
- `componenti` — array componenti BoM (popolato solo se `is_composito=true`)
- `note` — array note articolo
- `non_editable_fields: string[]` — Fase 5: chiavi del payload non
  modificabili in PATCH (es. `["codice", "uom_id"]`). Il FE le usa per
  pilotare i `:disabled` invece di cablare regole.
- `puo_gestire_bom: bool`, `motivo_non_gestibile_bom: string | null` —
  Fase 6: capability di gestione BoM (vedi §1.1).
- Natura di vendita (2026-06-10, da `vw_articoli_dettaglio`):
  `natura_vendita_id`, `natura_vendita_codice_interno`,
  `natura_vendita_descrizione`, `natura_vendita_destinazione_tipo`
  (`ORDINE` / `COMMESSA` / `CONTRATTO`). Il FE inizializza il Select
  "Natura di vendita" del drawer da `natura_vendita_id`; gli stessi campi
  sono disponibili anche nelle righe della lista (§1.1).
- Approvvigionamento (2026-09-14, da `vw_articoli_dettaglio`):
  `modo_approvvigionamento_id`, `modo_approvvigionamento_codice_interno`,
  `modo_approvvigionamento_descrizione` (⛔ non `_codice`: il valore viene
  dalla colonna immutabile, linee-guida-sql §6c), `gestito_a_magazzino`,
  `lead_time_giorni`. ⚠️ `ARTICOLI_DETAIL_COLUMNS` è una proiezione **per
  nome**: una colonna nuova della vista non esce finché nessuno la nomina —
  le tre colonne della lista 26 (`ui.lista_colonna` 747-749) sono nate
  `attivo = f` e accese nello stesso commit di questa proiezione.

### 1.4 Aggiorna articolo

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/` |

#### Regole specifiche

- `codice` e `uom_id` sono immutabili a livello API (vedi
  `non_editable_fields` nel detail).
- `natura_vendita_id` e' **mutabile** (decisione 2026-06-10, opzione A):
  cambiarla vale solo per le righe documento future — le righe esistenti
  hanno lo snapshot di natura preso all'inserimento riga. Mai null
  esplicito (NOT NULL a DB): `E_CATALOGO_VALIDATION`.
- `attivo` non e' modificabile via PATCH (Fase 7): risponde
  `E_CATALOGO_VALIDATION` con detail "usa gli endpoint /disattiva/ o
  /riattiva/". La transizione di stato passa solo dagli endpoint
  dedicati (§1.5 e §1.6).
- L'endpoint aggiorna solo i campi presenti nel payload.
- In assenza di campi supportati, restituisce `400`.

### 1.5 Disattiva articolo

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/disattiva/` |

#### Regole specifiche

- Soft delete logico (`attivo=false`)
- Idempotente se l'articolo e' gia' inattivo
- Trigger DB `trgfn_prevent_deactivate_if_children` blocca la
  disattivazione se esistono figli attivi (UoM operative, righe BoM, ecc.)

### 1.6 Riattiva articolo (Fase 7)

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/riattiva/` |

#### Regole specifiche

- Imposta `attivo=true` chiamando `catalogo.fn_riattiva_articolo(uuid)`.
- Idempotente se l'articolo e' gia' attivo (no-op DB, ritorna dettaglio).
- `E_CATALOGO_ARTICOLO_NOT_FOUND` (404) se l'id non esiste (pre-flight
  uniforme con il resto del dominio).
- Pattern "padre prima, figli poi": **non tocca** i figli (UoM operative,
  righe BoM dove l'articolo e' componente, ecc.) — l'admin li riattiva
  esplicitamente in azioni successive.
- Eventuali blocchi del trigger `trgfn_child_requires_active_parent`
  (parent inattivo: iva/gruppo/tipologia) si propagano come
  `E_PARENT_*`.

### 1.6-bis Correzione di struttura (amministratore)

Non ha un endpoint suo: viaggia nel **PATCH dell'articolo** (§1.4), nella chiave
`correzione_struttura`.

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/` |
| **Permesso** | solo SUPER_ADMIN: lo giudica il verbo DB |

Un articolo **usato** (in un documento, un listino, una commessa o in magazzino) non cambia la
sua struttura (`E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE`). La via normale è un articolo nuovo. Per
un errore di caricamento l'amministratore la corregge (A-10 di
brief-db-articoli-ammessi-per-documento).

Body: i campi di sempre più `"correzione_struttura": {"natura_vendita_id": 3}`, le sole colonne
strutturali da cambiare. Quali sono lo dice il dettaglio dell'articolo, `struttura_correggibile`
(dalla sede `catalogo.fn_articolo_colonne_struttura`, la stessa da cui il verbo legge le colonne
ammesse). Il backend chiama prima il verbo `catalogo.fn_articolo_correggi_struttura`, poi
l'aggiornamento, **in una transazione**: un aggiornamento rifiutato annulla anche la correzione.
`correzione_struttura` da sola basta (nessun altro campo richiesto). Risposta: il dettaglio
aggiornato.

* chi non è SUPER_ADMIN: `E_PERMESSO_NEGATO`; `correzione_struttura` vuota o non oggetto, o una
  colonna fuori dalla sede: `400` `E_PARAMETRO_INVALIDO`; articolo inesistente:
  `E_ARTICOLO_NOT_FOUND`; una correzione che renderebbe non valide righe di documenti ancora
  aperti: `409` `E_ARTICOLO_STRUTTURA_RIGHE_APERTE` (i documenti in `dettaglio.righe`) — li solleva
  tutti il verbo, l'unica porta (il backend non ripete nessuna di queste regole);
* gli altri guard dell'articolo parlano lo stesso.

Fino al 2026-10-18 la correzione era `POST …/articoli/{id}/struttura/`, una chiamata a parte prima
del PATCH: un PATCH fallito lasciava la struttura già corretta (R-BE-1). L'endpoint è ritirato.

### 1.7 Defaults form articolo (Fase 8)

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/articoli/form-defaults/` |

Centralizza il consumo dei parametri usati dal FE per pre-compilare il
form di creazione articolo. Tipi gia' **risolti**: il FE non duplica la
conversione di `/core/parameters/defaults/`.

#### Risposta (200)

```json
{
  "data": {
    "default_iva_id": 42
  }
}
```

#### Regole specifiche

- `default_iva_id` si RISOLVE dal parametro **`DEFAULT_IVA`**
  (`config.parameters`), che porta il **`codice_interno`** dell'aliquota — non
  il suo id. Il lookup passa da `resolve_config_id_by_codice_interno` su
  `config.iva`, che filtra `attivo = true` e matcha sulla colonna **lockata**.
- ⛔ **NON si fa `int()` sul valore del parametro**, e la ragione e' che non
  fallirebbe. Il `codice_interno` dell'aliquota ordinaria e' **`22`**, cioe' un
  numero: un lettore rimasto indietro otterrebbe l'**id 22**, che oggi in
  `config.iva` non esiste ma che il modello ammette eccome — e il giorno che
  esistesse sarebbe un'aliquota SBAGLIATA proposta in silenzio, su un dato che
  finisce sui documenti fiscali. Verificato sul DB: `codice_interno = '22'` da'
  **id 16**; `id = 22` non esiste.
- Se il parametro e' assente, vuoto, o punta a un codice inesistente/disattivato,
  ritorna `null` (best-effort, no raise: il form si apre e l'operatore sceglie a
  mano). ⚠️ Ma **non muto**: il ripiego scrive un `logger.warning`, perche' a
  video `null` e' indistinguibile da «non c'e' un default configurato» e un seed
  che punta a un'aliquota disattivata sparirebbe senza lasciare traccia.
- Override per utente/gruppo/emittente fiscale applicato dal `ParameterService`
  con il context standard (superuser bypass).

📌 **Il rename e' del 2026-08-31** (`DEFAULT_IVA_ID` → `DEFAULT_IVA`): e' il
terzo dei quattro passi che `linee-guida-sql §6b` descrive per i parametri che
stoccano un **id** invece di una chiave naturale — l'id e' soggetto a reseed, la
chiave naturale e' il contratto cross-ambiente. Il valore e' validato dal
registry `config.parameter_fk_surrogate`, quindi da quel giorno un codice IVA
inesistente nel seed viene **rifiutato** invece di restare a marcire.
⚠️ Il comportamento a video **non cambia**: il form propone la stessa aliquota
di prima.

---

## 2. Lookup

### 2.1 Lookup articoli

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/articoli/lookup/` |

Due usi, che non si mescolano (dal 2026-10-14, brief-db-articoli-ammessi-per-documento §9.6):

* **la riga di un documento** — con `documento`: quali articoli ammette la riga lo dice il
  database (`catalogo.fn_articoli_ammessi`, la stessa check dei guard di riga). Ogni articolo
  porta il suo `motivo`; prima gli ammessi;
* **le consultazioni** — senza `documento`: ricerca libera coi filtri qui sotto.

#### Query param — la riga di un documento

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `documento` | string | Sì | Codice di `config.tipi_entita`: `PREVENTIVO`, `ORDINE_VENDITA`, `DDT_VENDITA`, `OFFERTA_COMMERCIALE`, `CONTRATTO`, `LISTINO_VERSIONE`, `ARTICOLO` (la distinta), `PROMO_ARTICOLO`. Maiuscolo non richiesto. Sconosciuto: lo rifiuta la funzione (`E_DOC_TIPO_NON_GESTITO`) |
| `documento_id` | int | per i documenti con testata | L'id della testata salvata (o della versione di listino). Mancante: `E_PARAMETRO_INVALIDO` |
| `tipo_eccezione` | string | offerta e contratto | `AGGIUNTA`, `OVERRIDE`, `ESCLUSIONE` (l'enum del DB). Fuori enum: `400` `E_CATALOGO_VALIDATION` |
| `articolo_padre_id` | uuid | distinta | Il padre. Non UUID: `400` `E_VALIDATION_INPUT` |
| `search` | string | No | Come sotto. Il «contiene» lo fa la funzione, letterale e senza distinzione fra maiuscole |
| `limit` | int | No | Default `20`, max `50`; il tetto si applica dopo il giudizio, sull'ordine della funzione |

⛔ Accanto a `documento` **nessun filtro libero** (`attivo`, `is_composito`,
`gestito_a_magazzino`, `solo_oneri`): `400` `E_VALIDATION_INPUT`. La funzione propone solo
articoli attivi, e un filtro in più nasconderebbe un articolo che il guard accetta.

Ogni riga ha le colonne della ricerca libera più `motivo`:
`{codice, reason, reason_key, dettaglio, valori}` — il primo motivo per cui il documento non
ammette l'articolo, lo stesso che il guard solleverebbe — oppure `null` (ammesso). Nella
versione di listino un composito arriva con `COMPOSITO_COME_BUNDLE`: come riga semplice non
entra, ma entra come bundle.

#### Query param — le consultazioni

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `search` | string | No | Ricerca su `codice` e `descrizione` (la lookup non e' una lista: niente catalogo). `%` e `_` sono caratteri, non jolly; spazi ai bordi ignorati. Sotto 3 caratteri: `400` `E_SEARCH_VALIDATION` |
| `attivo` | bool | No | Default API `true` |
| `is_composito` | bool | No | Filtro composti |
| `gestito_a_magazzino` | bool | No | Solo gestiti a magazzino (picker di inventari e rettifiche). Assente = nessun filtro |
| `solo_oneri` | bool | No | Solo articoli-onere; aggiunge la causale ai risultati |
| `limit` | int | No | Default `20`, max `50` |

⛔ `is_solo_componente` ed `escludi_destinazione` sono **ritirati** il 2026-10-14: li usavano solo
le righe di documento, ed erano una seconda copia della regola dei guard. Chi li manda ancora
riceve `400` `E_VALIDATION_INPUT` (`is_solo_componente_ritirato`, `escludi_destinazione_ritirato`),
non un elenco intero spacciato per filtrato.

#### Output specifico

Envelope `{"count", "results", "troncato"}` (`troncato`: il tetto ha tagliato). Campi per
autocomplete cross-dominio: `id`, `codice`, `descrizione`, `uom_codice`, `uom_descrizione`,
`is_composito`, `attivo`, `iva_id`, `iva_codice`, `iva_descrizione`, `iva_aliquota_iva`,
`gestito_a_magazzino`, `requires_lotto`, `requires_serial` (più `motivo` sulla riga di un
documento, e la causale con `solo_oneri`).

### 2.2 Lookup unita` di misura — RIMOSSO

⛔ **`GET /api/v1/catalogo/unita-misura/lookup/` non esiste piu'.** Verificato sul
codice il 2026-08-19: nessuna rotta lo serve, e `catalogo/api/urls.py` lo dichiara
in un commento accanto alle rotte UoM.

**Cosa si usa al suo posto**: il lookup generico
`GET /api/v1/core/lookup/codici/?rel=catalogo.unita_misura` — stessa cosa per le
tipologie, `?rel=catalogo.uom_tipi`. E' la regola di questo repository: le tabelle
codice/descrizione passano dalla whitelist del lookup generico, non da un endpoint
per tabella (vedi `api_lookup_codici.md`).

### 2.3 Lookup modi di arrotondamento UoM (Fase 1)

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/lookup/rounding-modes/` |

Lookup statico dei 5 modi di arrotondamento ammessi su UoM operativa.
Single source of truth: `_ROUNDING_MODE_VALIDI` + `_ROUNDING_MODE_DESCRIZIONI`
in `catalogo_service` (no DB query, no paginazione).

#### Risposta lookup rounding modes (200)

```json
{
  "data": [
    {"codice": "HALF_UP",   "descrizione": "Arrotondamento meta' su (5 va su)",       "ordering": 1},
    {"codice": "HALF_DOWN", "descrizione": "Arrotondamento meta' giu' (5 va giu')",   "ordering": 2},
    {"codice": "HALF_EVEN", "descrizione": "Arrotondamento bancario (5 al pari piu' vicino)", "ordering": 3},
    {"codice": "UP",        "descrizione": "Arrotondamento sempre su (verso infinito)", "ordering": 4},
    {"codice": "DOWN",      "descrizione": "Arrotondamento sempre giu' (verso zero)",   "ordering": 5}
  ]
}
```

L'ordine e' "default-first" (HALF_UP). Consumato dal FE
`RoundingModeSelect` con cache `useGlobalLookup` chiave
`catalogo.uom_rounding_modes`.

---

## 3. UoM operative articolo

### 3.1 Lista UoM operative

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/uom/` |

#### Risposta envelope (Fase 5+6)

```json
{
  "data": {
    "count": 2,
    "results": [
      {
        "id": 1,
        "uom_codice": "PZ",
        "is_base": true,
        "puo_eliminarsi": false,
        "motivo_non_eliminabile": "UOM_BASE_NON_ELIMINABILE"
      },
      {
        "id": 2,
        "uom_codice": "CT",
        "is_base": false,
        "puo_eliminarsi": true,
        "motivo_non_eliminabile": null
      }
    ],
    "non_editable_fields": ["uom_id"]
  }
}
```

`non_editable_fields` e' a livello envelope (non per riga): la regola
e' la stessa per tutte le righe della stessa entita' e il FE legge la
lista come prima chiamata API quando il sub-drawer apre.

##### Capability di riga (Fase 6)

Ogni riga espone capability data-driven da
`vw_articoli_uom_operativa_dettaglio`:

- `puo_eliminarsi: bool` — `true` quando `NOT is_base`. Solo l'UoM
  base blocca l'eliminazione (la mappatura operativa non ha FK reverse:
  righe listino/magazzino/documenti puntano a `catalogo.unita_misura`,
  non a `articoli_uom_operativa.id`).
- `motivo_non_eliminabile: string | null` — codice motivo quando
  `puo_eliminarsi=false`:
  - `"UOM_BASE_NON_ELIMINABILE"` — UoM base.
  - `null` — quando `puo_eliminarsi=true`.

Il FE usa questi campi per disabilitare l'azione "delete" della riga
(non la nasconde, mantiene l'affordance) e mostrare il motivo via
tooltip i18n (`catalogo.motivo_*`).

Stessa proiezione su `GET /uom/{id}/` (singola riga) e su detail articolo
nel campo `uom_operative[]`: la lista e il dettaglio leggono dalla
stessa vista (single source of truth).

### 3.2 Crea UoM operativa

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/uom/` |

#### Body JSON

Campi principali:

- `uom_id` (obbligatorio in create, immutabile dopo)
- `is_base`
- `factor_to_base`
- `is_sell_uom`
- `is_purchase_uom`
- `is_logistic_uom`
- `qty_step`
- `rounding_mode` (uno tra `HALF_UP`, `HALF_DOWN`, `HALF_EVEN`, `UP`, `DOWN`)
- `max_decimals`
- `forbid_fraction`
- `require_lot`
- `gtin`
- `valido_dal` (Fase 4: opzionale, fallback `today` se omesso/null)
- `valido_al`
- `attivo`
- `meta`

#### Defaults Fase 1

I default operativi UoM sono parametrizzati in `config.parameters` (override
emittente disponibile):

| Parametro | Default sistema |
|---|---|
| `CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE` | `1` |
| `CATALOGO_UOM_OP_DEFAULT_QTY_STEP` | `1` |
| `CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE` | `HALF_UP` |
| `CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS` | `6` |
| `CATALOGO_UOM_OP_DEFAULT_FORBID_FRACTION` | `false` |

Letti dal FE via `useParameterDefaults` per popolare il form di create.

#### Risposta create/update (200)

Singola riga arricchita con `non_editable_fields: ["uom_id"]` (Fase 5).

### 3.3 Aggiorna UoM operativa

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/uom/{uom_op_id}/` |

### 3.4 Elimina UoM operativa

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/uom/{uom_op_id}/` |

#### Regole specifiche

- L'unicita` `articolo + uom` resta governata dal DB
- Guard d'uso e blocchi delete restano nel DB

---

## 4. Componenti BoM

### 4.1 Lista componenti

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/componenti/` |

#### Capability di chiusura riga (Fase 2)

Ogni riga della response include 4 campi calcolati per pilotare il dialog
"Chiudi riga" lato FE (single source of truth lato dominio: la riga e'
chiudibile finche' `valido_al IS NULL`):

| Campo | Tipo | Significato |
|---|---|---|
| `puo_chiudersi` | bool | `true` se `valido_al IS NULL` (riga aperta) |
| `data_min_chiusura` | date \| null | `valido_dal` se chiudibile, altrimenti `null` |
| `data_default_chiusura` | date \| null | `GREATEST(valido_dal, today)` se chiudibile, altrimenti `null` |
| `motivo_non_chiudibile` | string \| null | `'RIGA_GIA_CHIUSA'` o `null` |

Su righe non chiudibili i 3 campi data sono `null` (autodocumentante: il
FE non puo' aprire dialog su `null`).

### 4.1-bis La distinta come lista configurabile (lotto C, 2026-09-28)

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/componenti/lista/` (+ `export/?formato=csv\|xlsx`) |
| **Lista a catalogo** | `catalogo.articolo_componenti` (lista 101) |
| **Sorgente** | `catalogo.vw_articoli_componenti_dettaglio` — la stessa di §4.1, sede unica della capability di chiusura |

Envelope paginato standard. Parametri (facoltativi): `valido_al` (data
`YYYY-MM-DD`: le righe **in vigore a quella data o dopo** — senza fine, o con la
fine da quel giorno; assente = tutte le versioni; malformata = `400`),
`search` (codice e descrizione del componente, dal catalogo), `order_by` /
`order_dir` (whitelist `COMPONENTI_SORT_COLUMNS`; assente: `valido_dal` DESC;
`valido_al` vuoto si ordina come «infinito»; le date partono DESC), `limit` /
`offset`.

⭐ **Percorso suo** e non `…/componenti/`: il cancello di perimetro emittente
(`lista_codice`) scatta su ogni metodo della view che lo dichiara, e
`…/componenti/` serve anche la creazione (§4.2). La distinta è «per azienda»
(D-8.2): nessun `emittente_fiscale_id` in query, chi vede più emittenti lo
sceglie come per la lista degli articoli. `GET …/componenti/` (§4.1) resta la
lettura completa (il riepilogo nel drawer dell'articolo).

### 4.2 Crea componente

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/componenti/` |

#### Body JSON

Campi principali:

- `componente_id`
- `coeff_qta` — la quantita' del componente e' sempre `quantita padre ×
  coeff_qta`
- `obbligatorio`
- `esposizione_in_fattura` — il modo in cui il componente compare in fattura:
  codice di `config.esposizioni_componente` (`NASCOSTO`, `DESCRITTIVO`,
  `VALORIZZATO`). Il valore lo giudica la FK: un codice fuori vocabolario torna
  `400 E_CATALOGO_VALIDATION`; `null` non è ammesso (omettere il campo per il
  default). Fino al 2026-10-01 era il booleano `esposto_in_fattura`, oggi
  rifiutato come chiave sconosciuta
- `valido_dal` (Fase 4: opzionale, fallback `today` se omesso/null)
- `valido_al`
- `attivo`
- `meta`

⛔ `partecipa_qta` e `determina_qta_padre` **non esistono più** dal 2026-10-02
(brief-db-bom-flag-quantita-e-kit-in-fattura, D-1): si impostavano ma nessuna
logica li leggeva. Le colonne sono state ritirate a DB, e il backend non li
legge né li scrive.

#### Defaults Fase 2

I default operativi BoM sono parametrizzati in `config.parameters` (override
emittente disponibile):

| Parametro | Default sistema |
|---|---|
| `CATALOGO_BOM_DEFAULT_COEFF_QTA` | `1` |
| `CATALOGO_BOM_DEFAULT_OBBLIGATORIO` | `true` |
| `CATALOGO_BOM_DEFAULT_ESPOSIZIONE_IN_FATTURA` | `NASCOSTO` (un codice di `config.esposizioni_componente`) |

`CATALOGO_BOM_DEFAULT_PARTECIPA_QTA` e `CATALOGO_BOM_DEFAULT_DETERMINA_QTA_PADRE`
sono stati ritirati con i loro due campi (`20261002-67`).

### 4.3 Aggiorna componente

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/componenti/{comp_id}/` |

#### Regole specifiche

- I campi struttura (`componente_id`, `coeff_qta`, `obbligatorio`,
  `esposizione_in_fattura`) sono
  **immutabili** per design: il trigger DB
  `trgfn_articoli_componenti_block_modifica_struttura` blocca le UPDATE.
- L'unico campo struttura modificabile e' `valido_al` (per chiudere la
  riga). Il pattern operativo per cambiare i valori e' "chiudi riga +
  inserisci nuova versione" o usare 4.5 "Duplica versione".

### 4.4 Elimina componente

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/componenti/{comp_id}/` |

#### Regole DELETE

- Un articolo non puo` essere componente di se stesso (guard create).
- Le regole temporali e di coerenza strutturale restano governate dal DB.
- Il delete struttura BoM e' bloccato dal trigger
  `block_modifica_struttura`: usare 4.3 chiudere la riga (`valido_al`).

### ~~4.5 Duplica versione componente~~ — rimosso 2026-05-08

L'endpoint `POST .../duplica-versione/` e la DB function
`catalogo.fn_duplica_componente_versione` sono stati rimossi.
Il flow e' ora realizzato in 2 step FE usando gli endpoint esistenti:

1. PATCH `valido_al` sulla sorgente (§4.3).
2. POST nuova riga dal form precompilato (§4.1) — l'utente puo' personalizzare i valori prima di salvare.

---

## 5. Note articolo

### 5.1 Lista note

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/note/` |

### 5.2 Crea nota articolo

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/note/` |

#### Body JSON

Campi principali:
- `target_riga_id`
- `anchor_tipo`
- `posizione`
- `seq`
- `testo`
- `testo_md`
- `id_stile`
- `id_lingua`
- `visibile`
- `solo_stampa`
- `meta`

### 5.3 Aggiorna nota

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/catalogo/note/{nota_id}/` |

### 5.4 Elimina nota

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/catalogo/note/{nota_id}/` |

---

### 5.3 Note di un componente di distinta

| | |
|---|---|
| **Metodi** | `GET` `POST` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/componenti/{comp_id}/note/` |

Stesse note del §5, ancorate pero' alla **riga di distinta** invece che
all'articolo: il `comp_id` in URL fa da `target_riga_id`, che quindi **non** va
messo nel body. Il resto del contratto — campi, stile, visibilita' — e' quello
del §5.2.


## 6. Conversioni UoM

### 6.1 Lista conversioni

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/conversioni-uom/` |

#### Query param

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `attivo` | bool | No | Filtro attivo/disattivo |
| `uom_id` | int | No | Filtra le conversioni con `uom_id` come from o to |

Lista completa, no paginazione (dataset tipicamente piccolo).

### 6.2 Dettaglio conversione

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/conversioni-uom/{conv_id}/` |

#### Output specifico (Fase 5)

```json
{
  "data": {
    "id": 7,
    "uom_from_id": 1,
    "uom_to_id": 2,
    "fattore": 6.0,
    "valido_dal": "2026-01-01",
    "valido_al": null,
    "attivo": true,
    "non_editable_fields": ["uom_from_id", "uom_to_id"]
  }
}
```

### 6.3 Crea conversione

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/catalogo/conversioni-uom/` |

#### Body JSON

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `uom_from_id` | int | Si | UoM sorgente (immutabile dopo create) |
| `uom_to_id` | int | Si | UoM destinazione (immutabile dopo create) |
| `fattore` | decimal | Si | Fattore di conversione `> 0` |
| `valido_dal` | date | No | Fase 4: opzionale, fallback `today` se omesso/null |
| `valido_al` | date | No | Limite superiore validita' (default `null`) |

### 6.4 Aggiorna conversione

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/catalogo/conversioni-uom/{conv_id}/` |

#### Regole specifiche

- `uom_from_id` e `uom_to_id` sono **immutabili** dopo create (vedi
  `non_editable_fields` nel detail). Solo `fattore`, `valido_dal`,
  `valido_al`, `attivo` sono modificabili.

---

## 7. Unita` di misura e tipologie (anagrafica)

Le UoM **operative di un articolo** stanno al §3; qui c'e' l'anagrafica delle
unita` di misura e delle loro tipologie, che vive per conto suo.

⚠️ Per **leggerle in una combo** non si usano questi endpoint ma il lookup
generico: `GET /api/v1/core/lookup/codici/?rel=catalogo.unita_misura` (oppure
`?rel=catalogo.uom_tipi`). Questi servono a **manutenerle**.

### 7.1 Tipologie UoM

| | |
|---|---|
| **Lista** | `GET /api/v1/catalogo/uom-tipi/` — `search`, `attivo`, `limit`, `offset`, `order_by`, `order_dir` |
| **Crea** | `POST /api/v1/catalogo/uom-tipi/` — `codice`, `codice_interno`, `descrizione` (tutti e tre obbligatori) |
| **Dettaglio / aggiorna** | `GET` `PATCH /api/v1/catalogo/uom-tipi/{tipo_id}/` |

⛔ In `PATCH` sono modificabili **solo `descrizione` e `attivo`**: `codice` e
`codice_interno` sono la chiave con cui il resto del sistema nomina la
tipologia, e non si rinominano da API.

### 7.2 Unita` di misura

| | |
|---|---|
| **Lista** | `GET /api/v1/catalogo/unita-misura/` — stessi query param del §7.1 |
| **Crea** | `POST /api/v1/catalogo/unita-misura/` — `codice`, `descrizione`, `tipo_uom_id` obbligatori; `descrizione_fattura` opzionale |
| **Dettaglio / aggiorna** | `GET` `PATCH /api/v1/catalogo/unita-misura/{uom_id}/` — modificabili `descrizione`, `descrizione_fattura`, `tipo_uom_id`, `attivo` |
| **Disattiva** | `POST /api/v1/catalogo/unita-misura/{uom_id}/disattiva/` — body vuoto |

⛔ Anche qui il `codice` e' immutabile dopo la creazione.

⚠️ **La disattivazione puo' essere rifiutata dal database**, ed e' giusto cosi':
se esistono entita` collegate ancora attive l'`IntegrityError` diventa
`E_CATALOGO_VALIDATION` con «esistono entita' collegate attive». Una UoM
disattivata sotto i piedi di righe listino, magazzino e documenti che la
puntano sarebbe un dato rotto, non una comodita`. Se l'unita` non esiste (o era
gia` disattivata): `E_CATALOGO_UOM_NOT_FOUND`.

Entrambe le liste sono `is_search_endpoint` (throttling di ricerca) e
dichiarano `lista_codice` — `catalogo.uom_tipi` e `catalogo.unita_misura` — con
permesso di **livello oggetto** sui rispettivi modelli.

## Regole trasversali

- Tutti gli endpoint richiedono JWT.
- La ricerca libera delle liste (`search`) cade sulle colonne che il catalogo
  della lista accende. Soglia: articoli e lookup articoli `400` sotto 3 caratteri
  (`require_min_search_length`); tipologie UoM, unita` di misura e conversioni
  sono tabelle di configurazione e cercano da un carattere.
- Tutte le response detail e gli envelope lista UoM operativa includono
  `non_editable_fields: string[]` (Fase 5) — il FE pilota i `:disabled`
  da questa lista invece di cablare regole. Source: vista
  `dbops.vw_non_editable_fields` (alias su `dbops.automation_lock_columns`)
  + gap noti hardcoded in `_NON_EDITABLE_DB_GAPS` (`catalogo_service`).

### Codici errore (404 NOT_FOUND)

- `E_CATALOGO_ARTICOLO_NOT_FOUND`
- `E_CATALOGO_UOM_NOT_FOUND`
- `E_CATALOGO_COMPONENTE_NOT_FOUND`
- `E_CATALOGO_NOTA_NOT_FOUND`
- `E_CATALOGO_CONV_NOT_FOUND`
- `E_BOM_RIGA_NOT_FOUND` (Fase 3 — duplica versione)

### Codici errore (400 VALIDATION)

- `E_CATALOGO_VALIDATION` (catch-all dominio)
- `E_DATA_AL_MINORE_DAL` (propagato dal guard comune delle date
  `script.trgfn_guard_date_validita` quando `chiudi_al < valido_dal`;
  fino al 2026-09-24 rispondeva `E_BOM_VALIDO_AL_INVALIDO`, ora ritirato)
- `E_BOM_PRODOTTO_MISMATCH` (Fase 3 — la riga sorgente non appartiene
  all'articolo target: FE stale)

### Codici errore (409 CONFLICT)

- `E_BOM_SORGENTE_GIA_CHIUSA` (Fase 3 — duplica su riga gia' chiusa)
- `E_BOM_VERSIONE_OVERLAP` (Fase 3 — overlap su EXCLUDE GIST con
  versione futura)

### Idempotency-Key

- `POST /articoli/{id}/componenti/{cid}/duplica-versione/` (Fase 3)
  richiede header `Idempotency-Key: <UUID v4>`. Senza il header il helper
  `handle_post_json(require_idempotency_key=True)` rifiuta con 400
  (`E_IDEMPOTENCY_KEY_REQUIRED`).

### Pattern view

Le view write a regime usano `handle_post_json(...)`. Nel perimetro Fasi
1..5 i `POST` lo usano gia' (con `require_idempotency_key=True` per le
operazioni atomiche stato-changing); alcune `PATCH` legacy del dominio
sono ancora dirette e vanno considerate debito tecnico noto.

## Dipendenze DB

- Tabelle:
  - `catalogo.articoli`
  - `catalogo.articoli_uom_operativa`
  - `catalogo.articoli_componenti`
  - `catalogo.unita_misura`
  - `catalogo.unita_misura_conversioni`
  - `config.note`
  - `config.parameters` (Fasi 1+2: `CATALOGO_UOM_OP_DEFAULT_*`,
    `CATALOGO_BOM_DEFAULT_*`)
  - `dbops.automation_lock_columns` (Fase 5: registro lock_columns)
- Viste/funzioni:
  - `catalogo.vw_articoli_dettaglio`
  - `catalogo.vw_articoli_componenti_dettaglio` (Fase 2: estesa con
    `puo_chiudersi`/`data_min_chiusura`/`data_default_chiusura`/`motivo_non_chiudibile`)
  - `catalogo.vw_articoli_note`
  - `catalogo.fn_get_uom_base(...)`
  - `catalogo.fn_get_uom_factor(...)`
  - `dbops.vw_non_editable_fields` (Fase 5: alias semantico filtrato)

## Note di migrazione

- Il dettaglio articolo e' gia' pensato come payload aggregato per il frontend `catalogo`.
- Le query lista usano viste DB per evitare join Python ripetitivi.
- La documentazione copre il perimetro Fasi 1..5 del WIP refactor catalogo.
- Fasi 3+4+5 (28-04-2026): endpoint atomico duplica versione BoM,
  fallback `valido_dal=today` lato service, metadata `non_editable_fields`
  su detail/envelope. Vedi
  [analisi-refactor.frontend-catalogo](/dev/work-done/analisi-refactor.frontend-catalogo).
