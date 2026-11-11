# API Catalogo (Fasi 1..8)

## Scopo

Esporre via HTTP il backend `catalogo` per il perimetro delle Fasi 1..8:

- anagrafica articoli
- lookup articoli, UoM, modi di arrotondamento
- UoM operative articolo
- componenti BoM con capability di chiusura riga
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
| `search` | string | No | Ricerca libera: colonne e soglia le decide il catalogo della lista `catalogo.articoli`. Sotto soglia il termine non filtra (nessun `400`: il `400` `E_SEARCH_VALIDATION` vale solo per il lookup, §2.1) |
| `attivo` | bool | No | Filtro attivo/disattivo |
| `is_composito` | bool | No | Filtro articoli composti |
| `tipo_voce_id` | int | No | Filtro tipologia |
| `gruppo_voce_id` | int | No | Filtro gruppo |
| `listino_tipologia_id` | int | No | Filtro tipologia di listino dell'articolo |
| `data_da` | date | No | Filtro data insert da (giorno dell'azienda: vedi sotto) |
| `data_a` | date | No | Filtro data insert a, giorno incluso. I giorni sono giorni **dell'azienda** (fuso `SYSTEM_FUSO_ORARIO`, confini calcolati dal DB col BB `predicato_giorno_operativo`, dal 2026-10-09) (fino ad allora `data_insert::date`, il giorno della sessione e niente indice) |
| `limit` | int | No | Righe per pagina, default `25`, max `200` |
| `offset` | int | No | Righe da saltare, default `0` |
| `order_by` | string | No | `codice`, `descrizione` (default), `uom_codice`, `attivo`, `data_insert`, `data_update` |
| `order_dir` | string | No | `asc` oppure `desc`. Assente: `asc`, salvo le colonne data (`data_insert`, `data_update`) che partono `desc` |

⚠️ La paginazione è `limit`/`offset`: `page`/`page_size` in query sono un 400 `E_VALIDATION_INPUT` (dal 2026-10-20; prima erano ignorati). In risposta `page` e `page_size` sono calcolati da `limit`/`offset`.

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
        "requires_lotto": false,
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
| `uom_id` | int | Si | UoM base, intero `> 0` (immutabile dopo la creazione). Mancante o non positivo: `400` `E_CATALOGO_VALIDATION` |
| `tipo_voce_id` | int | No | Tipologia |
| `gruppo_voce_id` | int | No | Gruppo |
| `spesa_id` | int | No | Spesa |
| `iva_id` | int | No | IVA |
| `conto_contabile_vendita_id` | int | No | Conto vendita |
| `conto_contabile_acquisto_id` | int | No | Conto acquisto |
| `is_composito` | bool | No | Articolo composto |
| `is_solo_componente` | bool | No | Usabile solo come componente |
| `requires_serial` | bool | No | Richiede seriale |
| `requires_lotto` | bool | No | L'articolo si movimenta per lotti. Fuori dal lock BoM: resta modificabile in PATCH |
| `listino_tipologia_id` | int | No | Tipologia di listino |
| `natura_vendita_id` | int | No | Natura di vendita (FK `config.nature_vendita`): decide l'instradamento post-accettazione del modello split (ORDINE/COMMESSA/CONTRATTO). Se omesso → default DB `MERCE`. **Mai null esplicito** (colonna NOT NULL): risponde `E_CATALOGO_VALIDATION` |
| `modo_approvvigionamento_id` | int | No | **Da dove arriva** l'articolo (FK `config.modi_approvvigionamento`: `ACQUISTO` / `PRODUZIONE` / `STOCK` / `NON_APPLICABILE` — 2026-09-14, Blocco B di `brief-db-modifiche-certe-ciclo-vendita-e-articolo`). Dimensione **ortogonale** alla natura di vendita (dice dove *va* la riga, non da dove *viene*). Se omesso → default DB `ACQUISTO`. **Mai null esplicito** (NOT NULL): `E_CATALOGO_VALIDATION` col campo. Lookup: `GET /core/lookup/codici/?rel=config.modi_approvvigionamento` |
| `gestito_a_magazzino` | bool | No | L'articolo **movimenta giacenza**. Default DB `false` (fail-safe: nessun articolo comincia a movimentare per distrazione). ⚠️ Non si deriva da natura `MERCE`: una merce può essere venduta senza passare da giacenza |
| `lead_time_giorni` | int | No | Giorni fra richiesta e disponibilità. **Nullable per modello**: per una prestazione non significa niente, e `0` non è «non si applica». Negativo → `E_CATALOGO_VALIDATION` col campo (anticipa il CHECK) |
| `meta` | object | No | Metadati liberi |

Una chiave fuori da questo elenco è rifiutata con `400` `E_CATALOGO_VALIDATION`: anche `voce_utility`, che non esiste più (né come campo né come filtro, né in risposta). I booleani si mandano come booleani JSON.

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
- ⛔ niente `note`: ritirato il 2026-11-11 (era una terza lettura delle note,
  senza lettori). Le note dell'articolo si leggono dalla loro lista
  (`/api/v1/catalogo/articoli/{articolo_id}/note/`, §5).
- `non_editable_fields: string[]` — Fase 5: chiavi del payload non
  modificabili in PATCH (es. `["codice", "uom_id"]`). Il FE le usa per
  pilotare i `:disabled` invece di cablare regole.
- `puo_gestire_bom: bool`, `motivo_non_gestibile_bom: string | null` —
  Fase 6: capability di gestione BoM (vedi §1.1).
- Natura di vendita (2026-06-10, da `vw_articoli_dettaglio`):
  `natura_vendita_id`, `natura_vendita_codice_interno`,
  `natura_vendita_descrizione`, `natura_vendita_destinazione_tipo`
  (`ORDINE_VENDITA` / `COMMESSA` / `CONTRATTO`: codici di `config.sorgenti`,
  FK dal 2026-10-19, brief-db-grammatica-unica-documenti lotto 2b). Il FE inizializza il Select
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
- ⭐ **L'IVA di un kit e dei suoi componenti** deve coincidere sui legami
  attivi da oggi in poi (`E_BOM_IVA_DISCORDANTE`, `400`, campo `iva_id`). Dal
  2026-11-10 la regola si giudica **a fine transazione**: il guard
  `catalogo.trgfn_articoli_guard_iva_bom_attiva` è un vincolo differito (D4 e
  D21 di brief-db-revisione-catalogo). Il PATCH apre una transazione sua, e il
  rifiuto arriva al suo COMMIT, fuori dal punto in cui il service traduce gli
  errori d'integrità: lo traduce il traduttore generale, con lo stesso codice
  e lo stesso campo. Prova: `apps/catalogo/tests/db/test_errori_articolo_giro3_db.py`.

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
  colonna fuori dalla sede: `400` `E_PARAMETRO_INVALIDO`; un valore vuoto su una colonna NOT NULL,
  o di un tipo che la colonna non accetta: `400` `E_PARAMETRO_INVALIDO` col **campo** = la colonna
  e il nome leggibile nella frase (dal 2026-11-10, D19); articolo inesistente:
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

### 2.3 Lookup modi di arrotondamento UoM — RITIRATO (2026-11-09)

`GET /api/v1/catalogo/lookup/rounding-modes/` non esiste piu': il modo di
arrotondamento delle unita' operative e' uscito dal modello (Q4 di
brief-db-revisione-catalogo, giro 2). La quantita' operativa rispetta
`max_decimals`, e una quantita' con piu' decimali la rifiuta il DB
(`E_QTA_OPERATIVA_DECIMALI`), non la arrotonda.

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

##### Capability di riga

Ogni riga espone la capability di `vw_articoli_uom_operativa_dettaglio`, che
dal 2026-11-11 la prende dal BB del DB `catalogo.fn_uom_conversione_capability`
(G1-G2 di brief-db-revisione-catalogo): la stessa regola con cui il guard della
storia rifiuta. Il backend la **trasporta**.

| Campo | Che cosa dice |
| --- | --- |
| `puo_eliminarsi` · `motivo_non_eliminabile` | Il cestino. Motivi: `UOM_BASE_NON_ELIMINABILE` (la riga base), `UOM_STORIA_IN_VIGORE` (una mappatura con giorni passati: si chiude, non si cancella) |
| `puo_cambiare_attivo` | L'interruttore «attivo». Stessa regola dell'eliminazione, quindi stesso motivo (`motivo_non_eliminabile`); sulla riga base sempre `false` (Q34) |
| `puo_chiudersi` · `motivo_non_chiudibile` | La data di fine. Motivi: `UOM_BASE` (la riga base non ha fine), `UOM_STORIA_CHIUSA` (una fine già passata non si tocca) |
| `data_min_chiusura` · `data_default_chiusura` | La prima fine ammessa (la più tarda fra l'inizio e ieri) e quella proposta; vuote quando la riga non si chiude |

Il FE spegne cestino, interruttore e data di fine col motivo (chiavi
`catalogo.motivo_*`), non li nasconde; la lettura è l'helper
`src/catalogo/utils/capabilityConversioneUom.js`.

Stessa proiezione nel dettaglio articolo (campo `uom_operative[]`) e nella
riga restituita da create/update (§3.2-3.3): leggono dalla stessa vista.
La singola UoM operativa non ha un `GET` suo: `…/uom/{uom_op_id}/` serve solo
`PATCH` e `DELETE`.

### 3.1-bis Lookup UoM operative (cross-dominio)

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/uom/lookup/` |
| **Permesso** | JWT; `skip_area_check` (nessun permesso sull'area `catalogo`) |

Stessa risposta del §3.1 (envelope `count`/`results` + `non_editable_fields`),
nessun parametro. La usano i drawer riga di vendite (preventivi, contratti,
listini, promo) per la combo dell'UoM, senza chiedere LETTURA sul catalogo.
Articolo inesistente: `404` `E_CATALOGO_ARTICOLO_NOT_FOUND`.

### 3.2 Crea UoM operativa

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/uom/` |

#### Body JSON

Campi principali:

- `uom_id` (obbligatorio in create, immutabile dopo)
- `factor_to_base`
- `is_sell_uom`
- `is_purchase_uom`
- `is_logistic_uom`
- `qty_step`
- `max_decimals`
- `forbid_fraction`
- `gtin`
- `valido_dal` (Fase 4: opzionale, fallback `today` se omesso/null)
- `valido_al`
- `attivo`
- `meta`

⛔ **Fuori contratto (400) dal 2026-11-09** (giro 2 di brief-db-revisione-catalogo):
`is_base` — la riga dell'unita' base nasce con l'articolo e non si crea, non
si sposta, non si toglie (`E_UOM_RIGA_BASE_IMMUTABILE`); `rounding_mode` e
`require_lot` — colonne ritirate.

#### Regole dal DB (giro 2)

- **La mappatura si versiona**: la stessa unita' puo' stare su piu' righe, in
  periodi che non si sovrappongono (`uq_articoli_uom_operativa_no_overlap`,
  `UNIQUE … WITHOUT OVERLAPS`). Per cambiare il fattore da una data: chiudere
  la mappatura in vigore (`valido_al`) e aggiungerne una nuova dal giorno
  dopo. Un periodo sovrapposto e' un 400 `E_CATALOGO_VALIDATION`, senza campo.
- **La riga base e' fissa**: fattore 1 e nessuna data
  (`chk_articoli_uom_operativa_base_fissa`, 400 `E_CATALOGO_VALIDATION`).
- Il fattore di una riga di documento lo legge il DB alla data del documento
  (`catalogo.fn_get_uom_factor`: base, mappatura alla data, conversione
  generale); senza nessuno dei tre la riga si rifiuta (`E_UOM_MISSING`).

#### Defaults Fase 1

I default operativi UoM sono parametrizzati in `config.parameters` (override
emittente disponibile):

| Parametro | Default sistema |
|---|---|
| `CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE` | `1` |
| `CATALOGO_UOM_OP_DEFAULT_QTY_STEP` | `1` |
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

- La riga dell'unita' base non si elimina e non si spegne: la rifiuta il DB con
  `E_UOM_RIGA_BASE_IMMUTABILE`, campo `attivo` per lo spegnimento
  (capability `puo_eliminarsi` e `puo_cambiare_attivo` a `false` in lista).
- Una mappatura con giorni passati non si cancella: `E_UOM_STORIA_IN_VIGORE`
  (capability `puo_eliminarsi = false`, motivo `UOM_STORIA_IN_VIGORE`).
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
| `data_min_chiusura` | date \| null | La prima fine ammessa: la più tarda fra `valido_dal` e **ieri** (la fine non cambia i giorni già passati), se chiudibile; altrimenti `null` |
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

### 4.3 Aggiorna componente — RITIRATO (2026-11-10)

Il `PATCH` di un legame non esiste più, e con lui la rotta
`/api/v1/catalogo/articoli/{articolo_id}/componenti/{comp_id}/` (decisione di
Tid, §14.10.3 di brief-db-revisione-catalogo). La distinta è una storia: i campi
di struttura sono immutabili (`E_BOM_MODIFICA_VIETATA`), e l'unica cosa che di
un legame cambia, la **fine**, passa dal verbo (§4.5), che sa portare la
conferma dei prezzi bundle. Il PATCH su `valido_al` era una seconda strada per
la stessa scrittura, e su un legame con prezzi riceveva un avviso
(`E_BOM_CHIUSURA_CON_PREZZI`) che non poteva confermare.

Per cambiare i valori: chiudere il legame (§4.5) e inserirne uno nuovo
(POST §4.2). Sono due chiamate, senza un endpoint atomico. Le regole della fine
(`E_BOM_CHIUSURA_RETROATTIVA`, `E_BOM_LEGAME_CHIUSO`) le dà il verbo, sul campo
`valido_al`.

### 4.4 Elimina componente — RITIRATO (2026-11-09)

Il `DELETE` di un legame non esiste più (BE11 di brief-db-revisione-catalogo):
la distinta è una storia, e il trigger d'immutabilità rifiuta ogni
cancellazione. Un legame si **chiude** (§4.5). Dal 2026-11-10 la rotta non
esiste più (§4.3).

### 4.5 Chiudi un legame, coi suoi prezzi bundle (2026-11-10)

Un prezzo bundle (`vendite.listini_righe_componenti`) vale solo finché il
componente è nel kit. Chiudere il legame chiude anche i prezzi che vanno oltre
la fine, o li toglie se stanno in una bozza e cominciano dopo, e da quella
data il prezzo del kit in quei listini scende. Per decisione di Tid
(Q19-Q22 di brief-db-revisione-catalogo) questo non succede in silenzio: la
chiusura si **conferma**. Il giro è quello dell'annullo con legami:

1. `POST …/chiudi/` senza `prezzi_confermati`. Se il legame non ha prezzi da
   toccare, si chiude subito.
2. Se ha prezzi: `409 E_BOM_CHIUSURA_CON_PREZZI`, con `ui_action =
   confirm_and_retry` e campo `valido_al`. Il frontend apre la finestra.
3. `GET …/chiusura/?valido_al=` elenca i prezzi e dà il numero (`prezzi`).
4. `POST …/chiudi/` con `prezzi_confermati` = quel numero. Se nel frattempo
   i prezzi sono cambiati, la risposta è di nuovo il passo 2, coi numeri
   aggiornati.

#### 4.5.1 I prezzi che la chiusura tocca

| | |
|---|---|
| **Metodo** | `GET` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/componenti/{comp_id}/chiusura/?valido_al=AAAA-MM-GG` |
| **Sorgente** | `vendite.fn_prezzi_legame_oltre_la_fine` |

Risposta: `{ valido_al, prezzi, righe[] }`. Per ogni riga ci sono `riga_id`,
`listino_versione_id`, `listino_id`, `listino_codice`, `codice_versione`,
`stato_versione`, `valido_dal`, `valido_al`, `prezzo`, `importo_per_kit`
(prezzo × coefficiente del legame), `attivo`, `nel_perimetro` ed `esito`:

| `esito` | Il prezzo… |
| --- | --- |
| `CHIUDE` | comincia entro la fine: prende la stessa fine |
| `TOGLIE` | comincia dopo la fine, in una bozza: si cancella |
| `BLOCCA` | comincia dopo la fine, in una versione non in bozza: la chiusura si rifiuta |

⚠️ Un prezzo in un listino che chi chiama non vede arriva con
`nel_perimetro = false` e tutte le altre colonne vuote: si sa solo che c'è.
`prezzi` è il numero delle righe, ed è quello da dichiarare. Se ci sono righe
`BLOCCA` o fuori perimetro, il verbo rifiuta prima di confrontare il numero.

#### 4.5.2 Chiudi

| | |
|---|---|
| **Metodo** | `POST` |
| **URL** | `/api/v1/catalogo/articoli/{articolo_id}/componenti/{comp_id}/chiudi/` |
| **Verbo DB** | `catalogo.fn_chiudi_legame_distinta` |

Body: `{ "valido_al": "AAAA-MM-GG", "prezzi_confermati": 2 }`
(`prezzi_confermati` va omesso al primo tentativo). Risposta:
`{ componente, prezzi_chiusi, prezzi_tolti }`: `componente` è la riga come la
dà §4.1.

Il backend non giudica niente: verifica solo che il legame sia dell'articolo
del percorso (`404 E_CATALOGO_COMPONENTE_NOT_FOUND`) e che i due campi abbiano
la forma giusta (`400 E_CATALOGO_VALIDATION`, col campo). Il resto lo dice il
verbo:

| Codice | Quando |
| --- | --- |
| `E_BOM_CHIUSURA_CON_PREZZI` (409, `confirm_and_retry`) | Ci sono prezzi da chiudere o togliere, e la conferma manca o non corrisponde |
| `E_BOM_CHIUSURA_PREZZI_ALTRE_AZIENDE` (409) | Ci sono prezzi in listini che chi chiude non vede |
| `E_BOM_CHIUSURA_PRIMA_DEI_PREZZI` (400) | Un prezzo di una versione non in bozza comincia dopo la fine: il messaggio dice la prima fine ammessa |
| `E_PERMESSO_NEGATO` | Manca il livello TUTTO sul catalogo, oppure sui listini quando ci sono prezzi |
| `E_BOM_LEGAME_NOT_FOUND`, `E_BOM_LEGAME_CHIUSO`, `E_BOM_CHIUSURA_RETROATTIVA` | Il legame non c'è, è già finito, oppure la fine è prima di ieri |

Prove: `apps/catalogo/tests/db/test_chiusura_legame_prezzi_db.py` (sul DB
vero) e il pgTAP `catalogo/test-chiudi-legame-con-prezzi-v1`.

---

## 5. Note di catalogo (articolo e legame di distinta)

⭐ Dal 2026-11-11 (giro 4 di brief-db-revisione-catalogo) le note di catalogo
hanno la forma delle note degli altri schemi e passano dal **building block
delle note** (`make_note_views` + `PartitionedNoteService`, lo stesso di
`vendite.note`): stesso contratto, stessi codici `E_NOTA_*`, stesse rotte sotto
il padre. ⛔ La rotta a parte del dettaglio (`/api/v1/catalogo/note/{nota_id}/`)
è **ritirata**: `PATCH` e `DELETE` stanno sotto l'articolo o sotto il legame.

| Padre | Lista e crea (`GET` `POST`) | Dettaglio (`GET` `PATCH` `DELETE`) |
| --- | --- | --- |
| articolo | `/api/v1/catalogo/articoli/{articolo_id}/note/` | `/api/v1/catalogo/articoli/{articolo_id}/note/{note_id}/` |
| legame di distinta | `/api/v1/catalogo/articoli/{articolo_id}/componenti/{comp_id}/note/` | `/api/v1/catalogo/articoli/{articolo_id}/componenti/{comp_id}/note/{note_id}/` |

* La lista è la pagina della lista `catalogo.note` (`search`, `order_by`,
  `order_dir`, `limit`, `offset`; envelope paginato). ⚠️ **Nessun cancello di
  perimetro**: `catalogo.note` è una lista globale (`perimetro_emittente =
  false`), e `emittente_fiscale_id` non serve.
* `POST` vuole l'`Idempotency-Key`.
* **Body** (`POST`/`PATCH`): `testo`, `testo_md` (almeno uno dei due in
  creazione), `posizione`, `seq`, `visibile`, `solo_stampa`, `id_stile` e
  `id_lingua` (in creazione, se mancano, dai parametri `NOTE_DEFAULT_STILE` e
  `NOTE_DEFAULT_LINGUA`), `meta`. Una chiave fuori elenco è un 400.
* ⛔ **Nessuna nota di riga**: una nota di catalogo annota l'articolo o il
  legame interi (CHECK `chk_note_catalogo_ancora_documento`). `anchor_tipo` è
  `DOCUMENTO` per difetto; `RIGA`, o un `target_riga_id`, sono un 400
  `E_NOTA_VALIDATION` col campo `anchor_tipo`, prima del DB.
* Una nota si scrive anche su un articolo o un legame **spento**, e non
  impedisce di spegnerli (Q12: la nota è un'eccezione dell'automazione ATTIVO).
* ⛔ Il legame dev'essere **dell'articolo dell'URL**, su ogni verbo: articolo
  inesistente → 404 `E_CATALOGO_ARTICOLO_NOT_FOUND`, legame inesistente o di un
  altro articolo → 404 `E_CATALOGO_COMPONENTE_NOT_FOUND`, prima di leggere o
  scrivere le note (cancello del padre della factory; dal 2026-10-21).
* Una nota di un altro padre dall'URL di questo: 404 `E_NOTA_NOT_FOUND`. Un
  articolo che non c'è, sulla lista o sulla creazione delle sue note: 404
  `E_NOTA_PARENT_NOT_FOUND`.

Prove: `apps/catalogo/tests/db/test_note_catalogo_db.py` (sul DB vero),
`apps/catalogo/tests/api/test_catalogo_api.py` (rotte e cancello),
`apps/core/tests/services/test_partitioned_note_service.py` (`SedeSenzaRighe`).

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
| `search` | string | No | Ricerca libera (colonne dal catalogo della lista `catalogo.conversioni_uom`) |
| `attivo` | bool | No | Filtro attivo/disattivo |
| `uom_id` | int | No | Filtra le conversioni con `uom_id` come from o to |
| `limit` | int | No | Default `25`, max `200` |
| `offset` | int | No | Default `0` |
| `order_by` | string | No | `uom_from_codice` (default), `uom_to_codice`, `fattore`, `valido_dal`, `valido_al` (vuoto = infinito), `attivo` |
| `order_dir` | string | No | `asc`/`desc`. Assente: `asc`, salvo `valido_dal`/`valido_al` che partono `desc` |

Risposta: envelope paginato standard (`count`, `page`, `page_size`,
`total_pages`, `results`): non è la lista completa. Dal 2026-11-11 la lista
legge la vista `catalogo.vw_unita_misura_conversioni_dettaglio` (la `vista_sql`
della lista 22) e ogni riga porta la stessa capability del §3.1
(`puo_eliminarsi`, `motivo_non_eliminabile`, `puo_cambiare_attivo`,
`puo_chiudersi`, `data_min_chiusura`, `data_default_chiusura`,
`motivo_non_chiudibile`).

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
    "puo_cambiare_attivo": false,
    "puo_chiudersi": true,
    "data_min_chiusura": "2026-11-10",
    "motivo_non_eliminabile": "UOM_STORIA_IN_VIGORE",
    "non_editable_fields": ["fattore", "uom_from_id", "uom_to_id", "valido_dal"]
  }
}
```

Il dettaglio legge la stessa vista della lista, con la stessa capability
(dal 2026-11-11): il drawer spegne interruttore e data di fine col motivo.

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

Una conversione vale per la **coppia non orientata** e il periodo: kg→g e g→kg
in periodi che si sovrappongono sono la stessa conversione, e la rifiuta
`ex_unita_misura_conversioni_coppia_no_overlap` (400 `E_CATALOGO_VALIDATION`).
Fra unita' di tipologia diversa: `E_UOM_CONVERSIONE_TIPO_DIVERSO` dal DB.

### 6.4 Aggiorna conversione

| | |
|---|---|
| **Metodo** | `PATCH` |
| **URL** | `/api/v1/catalogo/conversioni-uom/{conv_id}/` |

#### Regole specifiche

- `uom_from_id`, `uom_to_id`, `fattore` e `valido_dal` sono **immutabili**
  dopo create: li ferma il lock di colonna (`E_UOM_STORIA_IMMUTABILE`, col
  campo), e il detail li dichiara in `non_editable_fields`. Si cambiano
  `valido_al` e `attivo`, nei limiti della capability (§6.2); per valori
  nuovi si chiude e se ne inserisce una nuova.

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
  della lista accende, con la soglia del catalogo: sotto soglia il termine non
  filtra, senza `400`. Solo il lookup articoli (§2.1) risponde `400`
  `E_SEARCH_VALIDATION` sotto 3 caratteri (`require_min_search_length`).
- Liste paginate (articoli, tipologie UoM, unità di misura, conversioni,
  distinta §4.1-bis): `limit`/`offset`, default `25`, max `200`; colonne data
  senza `order_dir` ordinano `desc`.
- `non_editable_fields: string[]` (Fase 5) sta su: dettaglio articolo,
  envelope lista/lookup UoM operative, riga di create/update UoM operativa,
  dettaglio conversione. **Non** c'è su dettaglio unità di misura, dettaglio
  tipologia UoM, create/update componente. Il FE pilota i `:disabled`
  da questa lista invece di cablare regole. Source: vista
  `dbops.vw_non_editable_fields` (il lock vivo), letta dal BB
  `compute_non_editable_fields`. ⛔ Nessun gap Python: `_NON_EDITABLE_DB_GAPS`
  è ritirato il 2026-11-11 (BE21-a), dal giorno in cui il DB dichiara anche
  unità, fattore e inizio di mappature e conversioni.

### Codici errore (404 NOT_FOUND)

- `E_CATALOGO_ARTICOLO_NOT_FOUND`
- `E_CATALOGO_UOM_NOT_FOUND`
- `E_CATALOGO_COMPONENTE_NOT_FOUND`
- `E_NOTA_NOT_FOUND`, `E_NOTA_PARENT_NOT_FOUND` (note, §5: i codici del BB
  delle note; `E_CATALOGO_NOTA_NOT_FOUND` non lo solleva piu' nessuno dal
  2026-11-11)
- `E_CATALOGO_CONV_NOT_FOUND`
- `E_CATALOGO_UOM_TIPO_NOT_FOUND` (tipologia UoM)

### Codici errore (400 VALIDATION)

- `E_CATALOGO_VALIDATION` (catch-all dominio)
- `E_DATA_AL_MINORE_DAL` (propagato dal guard comune delle date
  `script.trgfn_guard_date_validita` quando `chiudi_al < valido_dal`;
  fino al 2026-09-24 rispondeva `E_BOM_VALIDO_AL_INVALIDO`, ora ritirato)

### Pattern view

I `POST` usano `handle_post_json(...)`; nessuno richiede l'header
`Idempotency-Key`. Le `PATCH` leggono il corpo con `corpo_oggetto(request)`.

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
- Fasi 4+5 (28-04-2026): fallback `valido_dal=today` lato service, metadata
  `non_editable_fields` (perimetro in §Regole trasversali). Vedi
  [analisi-refactor.frontend-catalogo](/dev/work-done/analisi-refactor.frontend-catalogo).
