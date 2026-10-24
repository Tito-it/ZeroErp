# API Matrice `categorie_clienti_listini`

## Scopo

CRUD admin per la matrice di pricing **STADIO 2** del resolver listini v5:
la combinazione `categoria_cliente × utility × emittente_fiscale × classe_utenza?`
seleziona il `listino_id` attivo e, opzionalmente, una variazione globale
(`PERCENTUALE` o `VALORE_FISSO`) sul prezzo base del listino.

Riferimento concettuale:
[sviluppo-listini-v5.md](/dev/work-done/sviluppo-listini-v5) §4.2.

## Contesto

La matrice viene consultata dal resolver prezzi v5 **dopo** aver escluso
promo specifiche (STADIO 1) e contratti individuali (non applicabili al
caso). Gli endpoint qui descritti sono il pannello di amministrazione
usato dal back-office per popolare e mantenere la matrice.

La tabella e' **NON una tabella codice/descrizione**: non espone
`codice`/`descrizione`, non e' consultabile via
`GET /api/v1/core/lookup/codici/?rel=anagrafiche.categorie_clienti_listini`.
Le dropdown delle singole dimensioni (categoria, utility, emittente,
classe_utenza, listino) si popolano dai rispettivi lookup specifici.

## Input

### Query params lista (`GET /api/v1/anagrafiche/categorie-clienti-listini/`)

| Parametro | Tipo | Descrizione |
|---|---|---|
| `search` | string | Ricerca libera sulle colonne che il catalogo della lista `anagrafiche.categorie_clienti_listini` accende per l'operatore (le decide il catalogo, non il codice: `ricerca_full` nella configurazione della lista). Da un carattere, senza 400: matrice di configurazione (Tid, 2026-09-24). |
| `attivo` | bool | `true`/`false`/assente |
| `categoria_cliente_id` | int | Filtro dimensionale |
| `utility_id` | int | Filtro dimensionale |
| `emittente_soggetto_ruolo_id` | int | Filtro dimensionale |
| `listino_id` | int | Filtro dimensionale |
| `valid_at` | date ISO | Filtra righe la cui `validita` daterange contiene la data |
| `limit` | int (default 25, max 200) | Paginazione |
| `offset` | int | Paginazione |
| `order_by` | string | `categoria_codice \| categoria_descrizione \| utility_codice \| utility_descrizione \| emittente_ragione_sociale \| listino_codice \| listino_descrizione \| valido_dal \| valido_al \| attivo \| data_insert \| data_update` (default `valido_dal`) |
| `order_dir` | string | `asc \| desc`. Assente: le colonne data (`valido_dal`, `valido_al`, `data_insert`, `data_update`) partono `desc`, le altre `asc`; anche la lista senza `order_by` parte da `valido_dal desc` (fino al 2026-10-20 partiva `asc`) |

### Payload create (`POST`)

```json
{
  "categoria_cliente_id": 1,
  "utility_id": 2,
  "emittente_soggetto_ruolo_id": 3,
  "listino_id": 4,
  "classe_utenza_id": null,
  "tipo_variazione": "PERCENTUALE",
  "valore_variazione": "5.25",
  "valido_dal": "2026-01-01",
  "valido_al": null,
  "meta": {},
  "attivo": true
}
```

Campi obbligatori: `categoria_cliente_id`, `utility_id`,
`emittente_soggetto_ruolo_id`, `listino_id`, `valido_dal`.

`classe_utenza_id = null` = fallback generico (match valido per qualsiasi
classe utenza della quadrupla).

`tipo_variazione` e `valore_variazione` devono essere entrambi valorizzati
oppure entrambi null (coerenza enforce sia lato service sia lato DB via
`chk_categ_cli_listini_variazione_coerente`).

### Payload patch (`PATCH /{record_id}/`)

Solo i seguenti campi sono mutabili. Le 4+1 dimensioni
(categoria, utility, emittente, classe_utenza) sono **immutabili** —
modificarle richiede di disattivare la riga corrente e crearne una nuova:

* `listino_id`
* `tipo_variazione` + `valore_variazione` (coerenti)
* `valido_dal`
* `valido_al`
* `meta`
* `attivo`

## Output

### `GET` lista

Envelope paginato standard:

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
        "categoria_cliente_id": 1,
        "categoria_codice": "STANDARD",
        "categoria_descrizione": "Cliente standard",
        "utility_id": 2,
        "utility_codice": "ELE",
        "utility_descrizione": "Energia elettrica",
        "emittente_soggetto_ruolo_id": 3,
        "emittente_codice_ruolo": "EF.ACME",
        "emittente_ragione_sociale": "Acme S.p.A.",
        "classe_utenza_id": null,
        "classe_utenza_codice": null,
        "classe_utenza_descrizione": null,
        "listino_id": 4,
        "listino_codice": "LST-ELE-STD",
        "listino_descrizione": "Listino energia standard",
        "tipo_variazione": "PERCENTUALE",
        "valore_variazione": "5.2500",
        "valido_dal": "2026-01-01",
        "valido_al": null,
        "meta": {},
        "attivo": true,
        "data_insert": "2026-04-15T10:00:00Z",
        "user_insert": "mctit",
        "data_update": "2026-04-15T10:00:00Z",
        "user_update": "mctit"
      }
    ]
  },
  "meta": {"request_id": "..."}
}
```

**Fase 4 — `non_editable_fields` a livello envelope**: l'envelope GET lista
include `data.non_editable_fields: list[str]` con le 4 dimensioni semanticamente
immutabili (`categoria_cliente_id`, `utility_id`, `emittente_soggetto_ruolo_id`,
`classe_utenza_id`). Il FE costruisce drawer di edit usando la lista al livello
envelope, senza round-trip aggiuntivo.

### `GET` dettaglio / `POST` create / `PATCH` update

Stesso shape della riga di lista, avvolto in `{"data": {...}}`.

**Fase 4 — `non_editable_fields` nel dettaglio**: il `GET /{record_id}/`
include nel dict di response `non_editable_fields: list[str]` (stessa lista
dell'envelope lista). Il FE consuma questo campo nel drawer di edit per
gating dei Select dimensionali.

### Lookup statico tipi di variazione (Fase 4)

`GET /api/v1/anagrafiche/categorie-clienti-listini/lookup/tipi-variazione/` —
ritorna l'enum dei valori ammessi per `tipo_variazione` (CHECK constraint
`chk_categ_cli_listini_tipo_variazione`). Single source of truth lato Python:
nessuna tabella DB. Pattern simmetrico a `/amm-software/lookup/rounding-modes/`.

**Response shape**: `data` e' lista nuda (non envelope `{count, results}`).

```json
{
  "data": [
    { "codice": "PERCENTUALE",  "descrizione": "Variazione percentuale (%)",  "ordering": 1 },
    { "codice": "VALORE_FISSO", "descrizione": "Variazione a valore fisso",   "ordering": 2 }
  ]
}
```

**Consumer FE**: `frontend/src/amministrazione/components/CategoriaClienteListinoDrawer.vue`
con cache modulo-level via `useGlobalLookup('anag.categorie_listini_tipi_variazione')`.

## Regole

### Vincoli di integrita' applicati dal DB

| Vincolo | Tipo | Effetto UI |
|---|---|---|
| `fk_categ_cli_listini_categoria` | FK | `E_ANAG_FK` — "Categoria cliente inesistente." |
| `fk_categ_cli_listini_utility` | FK | `E_ANAG_FK` — "Utility inesistente." |
| `fk_categ_cli_listini_emittente` | FK | `E_ANAG_FK` — "Emittente inesistente." |
| `fk_categ_cli_listini_classe_utenza` | FK | `E_ANAG_FK` — "Classe utenza inesistente." |
| `fk_categ_cli_listini_listino` | FK | `E_ANAG_FK` — "Listino inesistente." |
| `chk_categ_cli_listini_tipo_variazione` | CHECK | `E_ANAG_VALIDAZIONE` — enum invalido. Anticipato lato service. |
| `chk_categ_cli_listini_variazione_coerente` | CHECK | `E_ANAG_VALIDAZIONE` — coppia tipo/valore incoerente. Anticipato lato service. |
| guard comune delle date (`trg_categorie_clienti_listini_a10_date_validita_ins_upd`) | TRIGGER | `E_DATA_AL_MINORE_DAL` (400, campo `valido_al`) — `valido_al < valido_dal`. Il service non lo anticipa (dal 2026-09-23). |
| `ex_categ_cli_listini_no_overlap` | EXCLUDE gist | `E_ANAG_MATRICE_OVERLAP` — due righe attive si sovrappongono sulla stessa quadrupla (categoria, utility, emittente, classe_utenza con sentinel `-1` per NULL) nello stesso periodo. |

### Immutabilita' dimensioni in `PATCH`

Le dimensioni `categoria_cliente_id`, `utility_id`,
`emittente_soggetto_ruolo_id`, `classe_utenza_id` sono **immutabili** a
livello service: la presenza nel payload PATCH produce
`E_ANAG_VALIDAZIONE` con detail esplicito. Motivazione: ogni riga
rappresenta un match semanticamente specifico; cambiare una dimensione
equivale a rimpiazzare la riga con una nuova, operazione che deve essere
esplicita per evitare perdite di audit storico.

### Campo `validita` (daterange)

La colonna `validita` e' una colonna **generata** dal database a partire da
`valido_dal`/`valido_al`. Non e' scrivibile via API ne' esposta in output:
il contratto espone `valido_dal`/`valido_al` che sono semanticamente
equivalenti per gli amministratori.

## Dipendenze DB

* Tabella: `anagrafiche.categorie_clienti_listini` (creata da
  `20260414-07-create-categorie-clienti-listini-mctit.yaml`).
* Ordine delle date: guard comune `script.trgfn_guard_date_validita`
  (automazione `DATE_VALIDITA`), che risponde `E_DATA_AL_MINORE_DAL`.
* Extension: `btree_gist` (baseline).
* FK verso: `anagrafiche.categorie_clienti`, `config.utilities`,
  `anagrafiche.soggetti_ruoli`, `config.classi_utenze`, `vendite.listini`.

## Note di migrazione

F1-DB-08 (whitelist lookup) **non e' applicabile**: la tabella non espone
`codice`/`descrizione` e non e' candidata per il lookup generico
`/core/lookup/codici/`. La consultazione ad alto volume avviene via la
list API dedicata (`GET /api/v1/anagrafiche/categorie-clienti-listini/`).

## Endpoint

| Metodo | URL | Scopo | Permesso |
|---|---|---|---|
| `GET` | `/api/v1/anagrafiche/categorie-clienti-listini/` | Lista paginata + filtri | Admin |
| `POST` | `/api/v1/anagrafiche/categorie-clienti-listini/` | Crea riga matrice | Admin |
| `GET` | `/api/v1/anagrafiche/categorie-clienti-listini/{id}/` | Dettaglio | Admin |
| `PATCH` | `/api/v1/anagrafiche/categorie-clienti-listini/{id}/` | Aggiorna (dimensioni immutabili) | Admin |
| `GET` | `/api/v1/anagrafiche/categorie-clienti-listini/lookup/tipi-variazione/` | Lookup statico enum (Fase 4) | Admin |
