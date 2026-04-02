# API Catalogo (Fasi 1..3)

## Scopo

Esporre via HTTP il backend `catalogo` per il perimetro delle Fasi 1..3:
- anagrafica articoli
- lookup articoli e UoM
- UoM operative articolo
- componenti BoM
- note articolo

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
        "voce_utility": false,
        "attivo": true
      }
    ]
  }
}
```

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
| `meta` | object | No | Metadati liberi |

### 1.3 Dettaglio articolo

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/` |

#### Output specifico

Il dettaglio articolo include anche gli array delle Fasi 2..3:
- `uom_operative`
- `componenti`
- `note`

### 1.4 Aggiorna articolo

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/` |

#### Regole specifiche

- `codice` e` immutabile a livello API.
- L'endpoint aggiorna solo i campi presenti nel payload.
- In assenza di campi supportati, restituisce `400`.

### 1.5 Disattiva articolo

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/disattiva/` |

#### Regole specifiche

- Soft delete logico (`attivo=false`)
- Idempotente se l'articolo e` gia` inattivo
- Eventuali blocchi per figli/usi restano governati dal DB

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
| `limit` | int | No | Default `20`, max `50` |

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

---

## 3. UoM operative articolo

### 3.1 Lista UoM operative

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/uom/` |

### 3.2 Crea UoM operativa

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/uom/` |

#### Body JSON

Campi principali:
- `uom_id`
- `is_base`
- `factor_to_base`
- `is_sell_uom`
- `is_purchase_uom`
- `is_logistic_uom`
- `qty_step`
- `rounding_mode`
- `max_decimals`
- `forbid_fraction`
- `require_lot`
- `gtin`
- `valido_dal`
- `valido_al`
- `attivo`
- `meta`

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
- `valido_dal`
- `valido_al`
- `attivo`
- `meta`

### 4.3 Aggiorna componente

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/componenti/{comp_id}/` |

### 4.4 Elimina componente

| | |
|---|---|
| **Metodo** | `DELETE` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/componenti/{comp_id}/` |

#### Regole specifiche

- Un articolo non puo` essere componente di se stesso
- Le regole temporali e di coerenza strutturale restano governate dal DB

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

## Regole trasversali

- Tutti gli endpoint richiedono JWT.
- Gli endpoint search/lista con `search` applicano `require_min_search_length(...)`.
- Le risposte `404` applicative sono centralizzate in `error_policies.py`:
  - `E_CATALOGO_ARTICOLO_NOT_FOUND`
  - `E_CATALOGO_UOM_NOT_FOUND`
  - `E_CATALOGO_COMPONENTE_NOT_FOUND`
  - `E_CATALOGO_NOTA_NOT_FOUND`
- Le view write a regime dovrebbero usare il pattern core `handle_post_json(...)`; nel perimetro Fasi 1..3 i `POST` lo usano gia`, mentre alcune `PATCH` legacy del dominio sono ancora dirette e vanno considerate debito tecnico noto.

## Dipendenze DB

- Tabelle:
  - `catalogo.articoli`
  - `catalogo.articoli_uom_operativa`
  - `catalogo.articoli_componenti`
  - `catalogo.unita_misura`
  - `config.note`
- Viste/funzioni:
  - `catalogo.vw_articoli_dettaglio`
  - `catalogo.vw_articoli_componenti_dettaglio`
  - `catalogo.vw_articoli_note`
  - `catalogo.fn_get_uom_base(...)`
  - `catalogo.fn_get_uom_factor(...)`

## Note di migrazione

- Il dettaglio articolo e` gia` pensato come payload aggregato per il frontend `catalogo`.
- Le query lista usano viste DB per evitare join Python ripetitivi.
- La documentazione copre il perimetro Fasi 1..3 del WIP, non il CRUD separato di `unita-misura`.
