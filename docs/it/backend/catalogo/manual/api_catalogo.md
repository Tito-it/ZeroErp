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
| `search` | string | No | Ricerca su `codice` e `descrizione` |
| `attivo` | bool | No | Filtro attivo/disattivo |
| `is_composito` | bool | No | Filtro articoli composti |
| `voce_utility` | bool | No | Filtro articoli utility |
| `tipo_voce_id` | int | No | Filtro tipologia |
| `gruppo_voce_id` | int | No | Filtro gruppo |
| `data_da` | date | No | Filtro data insert da |
| `data_a` | date | No | Filtro data insert a |
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

### 1.7 Defaults form articolo (Fase 8)

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/articoli/form-defaults/` |

Centralizza il consumo dei parametri usati dal FE per pre-compilare il
form di creazione articolo. Tipi gia' castati: il FE non duplica il cast
da stringa generico di `/core/parameters/defaults/`.

#### Risposta (200)

```json
{
  "data": {
    "default_iva_id": 42
  }
}
```

#### Regole specifiche

- `default_iva_id` casta da `DEFAULT_IVA_ID` (parametro `config.parameters`)
  a `int`. Se il parametro e' assente o malformato, ritorna `null`
  (best-effort, no raise: il form mostra senza pre-compile).
- Override per utente/gruppo/emittente fiscale applicato dal `ParameterService`
  con il context standard (superuser bypass).

---

## 2. Lookup

### 2.1 Lookup articoli

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/articoli/lookup/` |

#### Query param

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `search` | string | No | Ricerca su `codice` e `descrizione` |
| `voce_utility` | bool | No | Filtro utility |
| `attivo` | bool | No | Default API `true` |
| `is_composito` | bool | No | Filtro composti |
| `is_solo_componente` | bool | No | Filtro articoli usabili solo come componente BoM |
| `escludi_destinazione` | string (CSV) | No | Esclude gli articoli la cui **natura** ha una `destinazione_tipo` tra quelle elencate (`ORDINE` / `COMMESSA` / `CONTRATTO`). Filtro **data-driven sulla destinazione**, non sul codice natura. Es. `escludi_destinazione=CONTRATTO` per non proporre articoli ricorrenti sulle righe di un **preventivo** (difesa in profondità del blocco DB D9, modello split per natura). Valori normalizzati a maiuscolo; token vuoti ignorati. |
| `limit` | int | No | Default `20`, max `50` |

> **Nota natura (split per natura)**: il filtro fa `LEFT JOIN catalogo.articoli → config.nature_vendita` (`natura_vendita_id`) e applica `(destinazione_tipo IS NULL OR destinazione_tipo <> ALL(escluse))` — **NULL-tolerant**: un articolo con natura NULL non viene nascosto, è escluso solo se la sua destinazione è tra quelle vietate (coerente col "NULL = include" di `fn_list_preventivi_da_pushare`). Senza il parametro il lookup è invariato (nessun JOIN natura). Usato dal FE `ArticoloLookup` via prop `escludiDestinazione` (riga preventivo passa `['CONTRATTO']`).

#### Output specifico

Restituisce campi minimali per autocomplete cross-dominio:
- `id`
- `codice`
- `descrizione`
- `uom_codice`
- `uom_descrizione`
- `is_composito`
- `voce_utility`
- `attivo`

### 2.2 Lookup unita` di misura

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/unita-misura/lookup/` |

#### Query param

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `search` | string | No | Ricerca su `codice` e `descrizione` |
| `limit` | int | No | Default `200` |

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

### 4.2 Crea componente

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/componenti/` |

#### Body JSON

Campi principali:

- `componente_id`
- `coeff_qta`
- `partecipa_qta`
- `determina_qta_padre`
- `obbligatorio`
- `esposto_in_fattura`
- `valido_dal` (Fase 4: opzionale, fallback `today` se omesso/null)
- `valido_al`
- `attivo`
- `meta`

#### Defaults Fase 2

I default operativi BoM sono parametrizzati in `config.parameters` (override
emittente disponibile):

| Parametro | Default sistema |
|---|---|
| `CATALOGO_BOM_DEFAULT_COEFF_QTA` | `1` |
| `CATALOGO_BOM_DEFAULT_PARTECIPA_QTA` | `true` |
| `CATALOGO_BOM_DEFAULT_OBBLIGATORIO` | `true` |
| `CATALOGO_BOM_DEFAULT_DETERMINA_QTA_PADRE` | `false` |
| `CATALOGO_BOM_DEFAULT_ESPOSTO_IN_FATTURA` | `false` |

Allineato lato DDL: `articoli_componenti.partecipa_qta` ha `DEFAULT true`
(migration `20260428-02`) per coerenza tra service e insert SQL diretti.

### 4.3 Aggiorna componente

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/componenti/{comp_id}/` |

#### Regole specifiche

- I campi struttura (`componente_id`, `coeff_qta`, `partecipa_qta`,
  `determina_qta_padre`, `obbligatorio`, `esposto_in_fattura`) sono
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

## Regole trasversali

- Tutti gli endpoint richiedono JWT.
- Gli endpoint search/lista con `search` applicano `require_min_search_length(...)`.
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
- `E_BOM_VALIDO_AL_INVALIDO` (Fase 3 — propagato dal trigger
  `trgfn_articoli_componenti_block_modifica_struttura` quando
  `chiudi_al < valido_dal`)
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
  [analisi-refactor.frontend-catalogo](/dev/work-in-progress/analisi-refactor.frontend-catalogo).
