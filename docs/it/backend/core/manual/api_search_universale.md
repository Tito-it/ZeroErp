# API Ricerca Universale Soggetti

## Scopo

Espone la ricerca universale soggetti a due livelli: lista paginata (livello 1) e
dettaglio per tipo ruolo con row expansion (livello 2).

## Contesto

La ricerca universale e' il punto di ingresso per il contesto globale di navigazione.
L'utente cerca un soggetto per nome o CF/P.IVA, filtrando per tipo ruolo obbligatorio,
e puo' espandere una riga per vedere il dettaglio specifico (clienti con istanze, fornitori
con stato, ecc.). Il backend delega la logica alle funzioni DB
`script.fn_search_soggetti_universale` e `script.fn_get_search_detail`.

## Endpoint

### GET /api/v1/core/search/ — Ricerca soggetti (livello 1)

#### Input (query params)

| Parametro | Tipo | Obbl. | Default | Descrizione |
|---|---|---|---|---|
| `q` | string | Si | — | Termine di ricerca (min 3 caratteri). Cerca su `ragione_sociale_completa`, `id_fiscale_univoco_cf_piva`, `codice` soggetto e codice entita' dinamico |
| `tipo_ruolo_id` | int | Si | — | ID tipo ruolo. Solo tipi con `ricerca_visibile = true` in `config.tipi_ruoli`: gli altri 404 `E_TIPO_RUOLO_NON_RICERCABILE`, un id inesistente 404 `E_TIPO_RUOLO_NON_TROVATO` (lo decide il DB, anche per la lista) |
| `limit` | int | No | 25 | Righe per pagina, max 100: fuori da 1..100 → 400 `E_VALIDATION_INPUT` (`limit_fuori_limiti_1_100`) |
| `offset` | int | No | 0 | Righe da saltare; negativo → 400 (`offset_negativo`) |
| `order_by` | string | No | `ragione_sociale_completa` | Colonna di ordinamento. Valori ammessi: `ragione_sociale_completa`, `soggetto_codice`, `id_fiscale_univoco`. ⛔ `utility_list` ed `emittente_ragione_sociale` non sono ordinabili: sono aggregati calcolati per le sole righe della pagina (400 `E_SEARCH_VALIDATION`) |
| `order_dir` | string | No | `ASC` | Direzione ordinamento: `ASC` o `DESC` |

⛔ `page`/`page_size` in query sono un 400 `E_VALIDATION_INPUT` dal 2026-10-21
(prima erano il contratto di questa ricerca). La risposta porta ancora `page` e
`page_size`, ricavati dall'offset.

**Nota**: il parametro `comune_id` e' stato rimosso. Il filtro per comune nel livello 1
era impraticabile (risoluzione indirizzo row-level su migliaia di righe). Indirizzo e
comune sono ora visibili nel livello 2 (dettaglio per tipo ruolo).

#### Output (200)

```json
{
  "data": {
    "count": 42,
    "page": 1,
    "page_size": 25,
    "total_pages": 2,
    "results": [
      {
        "soggetto_id": "uuid",
        "soggetto_ruolo_id": 100,
        "tipo_ruolo_id": 1,
        "soggetto_codice": "S-0042",
        "ragione_sociale_completa": "Rossi Mario",
        "id_fiscale_univoco": "RSSMRA80A01F205X",
        "utility_list": "GAS, EE",
        "emittente_ragione_sociale": "Azienda SRL"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

### GET /api/v1/core/search/\<uuid:soggetto_id\>/detail/ — Dettaglio soggetto (livello 2)

#### Input (query params)

| Parametro | Tipo | Obbl. | Default | Descrizione |
|---|---|---|---|---|
| `tipo_ruolo_id` | int | Si | — | ID tipo ruolo per il dettaglio |
| `utility_id` | int | No | null | Filtro opzionale per utility specifica (solo CLIENTE). Quando valorizzato, restituisce solo le righe di quella utility |

#### Output (200)

Output JSONB `{tipo_ruolo, righe}` con struttura variabile per tipo ruolo. `tipo_ruolo`
e' il `codice_interno` del tipo ruolo (`CL`, `FO`, ...). Tutti i tipi includono indirizzo e
comune risolti con logica specifica:

- **CL** (cliente): `indirizzo_normalizzato` da istanza, fallback `fn_get_indirizzo(sr.id, 'RES')`
- **FO** (fornitore): `fn_get_indirizzo(sr.id, 'SEDEOP')` (sede operativa con catena fallback)
- **Generico**: `fn_get_indirizzo(sr.id, 'RES')` (residenza con catena fallback)

Campi di ogni riga per ramo:

| Ramo | Campi |
|---|---|
| `CL` | `cliente_id`, `soggetto_ruolo_id`, `codice` (billing account), `istanza_codice`, `istanza_id`, `utility_id`, `utility_codice_interno`, `utility_codice`, `utility_descrizione`, `stato_cliente_id`, `stato_codice_interno`, `stato_descrizione`, `stato_macro`, `indirizzo`, `comune`, `data_attivazione`, `data_sospensione`, `data_riattivazione`, `data_chiusura` |
| `FO` | `fornitore_id`, `soggetto_ruolo_id`, `codice`, `attivo`, `stato_descrizione` (`ATTIVO`/`INATTIVO`), `indirizzo`, `comune` |
| altri | una riga con `soggetto_ruolo_id`, `soggetto_id`, `indirizzo`, `comune`; in piu' `entita_detail` a livello radice (da `fn_get_entita_ruolo_detail`) |

**«Non c'e'» e lista vuota sono due risposte diverse** (contratto deciso da Tid il
2026-10-08, in servizio dal DB il 2026-10-08):

* **404 `E_SEARCH_NOT_FOUND`** quando il soggetto, con quel ruolo, non risulta a
  chi guarda: non esiste, non ha quel ruolo, o il ruolo non ha nessuna riga
  della sua entita' visibile (per `CL` nessun cliente nel perimetro, per `FO`
  nessuna riga in `fornitori`). Inesistente e fuori perimetro escono uguali, di
  proposito: il 404 non rivela un cliente di un'altra azienda;
* **200 con `righe: []`** solo quando il soggetto c'e' e il filtro `utility_id` non
  trova righe.

**Una regola sola per «il soggetto-ruolo si mostra»** (dal 2026-10-10, R-6 di
brief-db-codici-non-trovato-email-e-permessi), la stessa per lista e dettaglio:
il BB `script.fn_predicato_soggetto_ruolo_visibile` legge
`config.tipi_ruoli.entita_esistenza` — la tabella che fa esistere il ruolo (CL →
`clienti`, FO → `fornitori`, VT → `vettori`, BANK_B → `bank_branches`) — e il
soggetto-ruolo si mostra se ne ha almeno una riga visibile; un ruolo senza
entita' si mostra se esiste. Il perimetro lo fa la **RLS** di quella tabella
(per i clienti quella di `anagrafiche.clienti`); `fornitori`, `vettori` e
`bank_branches` non portano un'azienda nel modello e non si filtrano per
emittente. Lo stato dell'entita' non conta: un cliente chiuso o un fornitore
disattivato si trovano, col loro stato. Lo stesso BB valida il tipo ruolo
(inesistente o non ricercabile → 404): il backend non lo pre-controlla piu'.
Prova sul DB vero: `core/tests/db/test_search_detail_non_trovato_db.py`.

Esempio per CL:

```json
{
  "data": {
    "tipo_ruolo": "CL",
    "righe": [
      {
        "cliente_id": 20,
        "codice": "CLI-0042",
        "soggetto_ruolo_id": 64,
        "istanza_codice": "IST-001",
        "istanza_id": 29,
        "utility_id": 2,
        "utility_codice": "GAS",
        "utility_codice_interno": "GAS",
        "utility_descrizione": "Gas naturale",
        "indirizzo": "Via Roma 12",
        "comune": "Bergamo",
        "stato_codice_interno": "AT",
        "stato_descrizione": "Attivo",
        "stato_macro": "AT",
        "stato_cliente_id": 1,
        "data_attivazione": "2024-01-15",
        "data_sospensione": null,
        "data_riattivazione": null,
        "data_chiusura": null
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

> **Naming (2026-06-28)**: per la logica usare i campi `*_codice_interno` (immutabili).
> `stato_codice` è stato **rinominato** in `stato_codice_interno` (chiave `stato_codice`
> non più presente nel detail cliente; il display dello stato è `stato_descrizione` /
> `stato_macro`). `utility_codice` ora porta il `codice` **mutabile** (display); per la
> logica usare il nuovo `utility_codice_interno`. Vedi linee-guida-sql.md §6c.

### GET /api/v1/core/lookup/tipi-ruoli/ — Lookup tipi ruolo

#### Input (query params)

Nessuno. Restituisce sempre e solo i tipi con `ricerca_visibile = true`, ordinati per
`descrizione`. Il parametro `ricerca_visibile`, pur dichiarato nello schema OpenAPI, e'
ignorato. `codice` e' `COALESCE(codice_interno, codice)`.

#### Output (200)

```json
{
  "data": {
    "results": [
      { "id": 1, "codice": "CL", "descrizione": "Cliente" },
      { "id": 2, "codice": "FO", "descrizione": "Fornitore" }
    ]
  },
  "meta": { "request_id": "..." }
}
```

## Ricerca stradario (autocomplete indirizzi)

Due endpoint distinti, e la differenza e' **quando** si usano, non come:

### `GET /api/v1/core/search/stradario/`

Vie di un comune gia' scelto. E' il passo che segue la selezione del comune nel
form indirizzo.

| query param | default | note |
|---|---|---|
| `comune_id` | — | filtra le vie del comune |
| `search` | — | ricerca su toponimo + denominazione |
| `limit` | 30 | **max 100** |

Risposta `{"data": {"results": [...]}}`: ogni riga porta `stradario_id`, via
completa, comune, provincia, CAP — l'indirizzo esce gia' normalizzato, non da
ricomporre a mano.

### `GET /api/v1/core/search/stradario-generale/`

Vie su **tutta Italia**, senza comune ne' CAP: serve quando la via non e' ancora
nello stradario del comune e va inserita nuova. L'operatore cerca prima la via,
**poi** sceglie comune e CAP.

| query param | obbligatorio | note |
|---|---|---|
| `search` | **si'** | qui non si sfoglia: senza testo non si cerca. Minimo 2 caratteri, imposto dalla funzione DB (`E_ADMIN_VALIDAZIONE`, 400) |
| `toponomastica_id` | no | filtro per tipo di toponimo |
| `limit` | no | come sopra |

Risposta: stessa forma, `{"data": {"results": [...]}}`.

⭐ Entrambi sono `is_search_endpoint = True` (throttling di ricerca) e
`skip_area_check = True`: l'indirizzo si compila da qualunque area.

## Regole

- `q` obbligatorio, minimo 3 caratteri (validato da `require_min_search_length`)
- `tipo_ruolo_id` obbligatorio (assente → 400 `E_SEARCH_VALIDATION`) e intero entro `integer` (va a `p_tipo_ruolo_id integer`): non numerico od oltre il tetto → 400 `E_VALIDATION_INPUT` prima del DB. Stessa regola per `utility_id` del dettaglio. Esistenza e `ricerca_visibile` li verifica il DB (404)
- Perimetro dalla RLS dell'entita' del ruolo (vedi sopra): per `CL` operatori con whitelist emittenti vedono solo i clienti del proprio scope, col pattern gestore globale (`is_default=true` in `emittenti_fiscali_billing_account`). Il backend non passa uno scope
- Throttling search attivo (`SearchBurstRateThrottle`, `is_search_endpoint = True`)
- Nessun tetto sui risultati (dal 2026-10-10): `count` è il numero vero delle corrispondenze, e ordine e pagina valgono su tutte. La funzione conta, ordina e taglia la pagina sulle colonne semplici, e calcola gli aggregati (`utility_list`, `emittente_ragione_sociale`) per le sole righe della pagina
- Paginazione LIMIT/OFFSET + COUNT(*) OVER() in un solo round-trip
- Il dettaglio (livello 2) e' caricato lazy — solo quando l'utente espande la riga

## Errori

| Codice | HTTP | Causa |
|---|---|---|
| `E_SEARCH_VALIDATION` | 400 | Parametro mancante, troppo corto (< 3 caratteri) |
| `E_TIPO_RUOLO_NON_RICERCABILE` | 404 | Lista e dettaglio: il tipo ruolo ha `ricerca_visibile = false` (dal DB; fino al 2026-10-10 era `E_SEARCH_VALIDATION` 400 dal backend) |
| `E_TIPO_RUOLO_NON_TROVATO` | 404 | Lista e dettaglio: il tipo ruolo non esiste (la lista prima rispondeva zero righe) |
| `E_SEARCH_NOT_FOUND` | 404 | Dettaglio: soggetto inesistente, senza quel ruolo, o senza righe visibili della sua entita' |
| `E_VALIDATION_INPUT` | 400 | Parametro numerico non valido: `limit`/`offset` non interi o fuori limiti, `tipo_ruolo_id`, `utility_id` non numerici o fuori tetto; `page`/`page_size` presenti |

## Dipendenze DB

| Oggetto | Schema | Tipo |
|---|---|---|
| `fn_search_soggetti_universale` | `script` | Funzione — ricerca livello 1 (6 parametri: p_search_term, p_tipo_ruolo_id, p_limit, p_offset, p_order_by, p_order_dir) |
| `fn_get_search_detail` | `script` | Funzione — dettaglio livello 2 (3 parametri: soggetto_id, tipo_ruolo_id, utility_id opzionale). NULL = «non c'e'» |
| `fn_predicato_soggetto_ruolo_visibile` | `script` | Funzione — la regola unica «il soggetto-ruolo si mostra a chi guarda», resa come predicato per lista e dettaglio; valida anche il tipo ruolo (dal 2026-10-10, al posto di `fn_check_soggetto_ruolo_visibile`) |
| `fn_get_indirizzo` | `script` | Funzione — risoluzione indirizzo con catena fallback (usata nel livello 2) |
| `tipi_ruoli` | `config` | Tabella — colonne `ricerca_visibile` e `entita_esistenza` |
| `fn_get_ba_emittente_sr_id` | `script` | Funzione — «quale emittente fattura questo billing account»; alimenta la colonna `emittente_ragione_sociale` del livello 1 (dal 2026-08-18) |

## File backend

| File | Ruolo |
|---|---|
| `apps/core/db/search_repository.py` | Repository — accesso DB |
| `apps/core/api/search_view.py` | View API — `SearchUniversaleView`, `SearchDetailView`, `LookupTipiRuoliView` |
| `apps/core/api/urls_v1.py` | Routing — `search/`, `search/<uuid>/detail/`, `lookup/tipi-ruoli/` |
| `apps/core/services/error_policies_generated.py` | Classi errori — `E_SEARCH_VALIDATION`, `E_SEARCH_NOT_FOUND`, `E_TIPO_RUOLO_NON_RICERCABILE`, `E_TIPO_RUOLO_NON_TROVATO` |
| `apps/core/tests/api/test_search_view.py` | Test unitari (mock DB) |
| `apps/core/tests/db/test_search_detail_non_trovato_db.py` | Dettaglio sul DB vero: NULL per inesistente, senza ruolo e fornitore senza la sua riga; `righe: []` col filtro utility; ruolo non ricercabile rifiutato dal DB su lista e dettaglio (opt-in `ZEROERP_TEST_DB_E2E`) |
| `scripts/tests/smoke-test-core.sh` | Smoke test (sezioni 14-17) |

## Note di migrazione

- La colonna `ricerca_visibile` su `config.tipi_ruoli` deve essere creata prima del deploy
  (changeset Liquibase in Fase 1, step 1.0 del WIP)
- Le funzioni DB `fn_search_soggetti_universale` e `fn_get_search_detail` devono essere
  presenti nello schema `script` (Fase 1, step 1.3 e 1.4)
- `fn_search_soggetti_universale` ha signature a 6 parametri (`p_search_term`, `p_tipo_ruolo_id`, `p_limit`, `p_offset`, `p_order_by`, `p_order_dir`). I 2 parametri di ordinamento sono opzionali (default `ragione_sociale_completa ASC`)
- `fn_get_search_detail` ha 3 parametri (`p_soggetto_id`, `p_tipo_ruolo_id`, `p_utility_id` opzionale). Restituisce `codice` nel JSONB per CL e FO
- `p_emittente_ids` e' **uscito dalle due firme il 2026-10-10** (R-5 del brief-db-codici-non-trovato-email-e-permessi): il perimetro lo fa la RLS. Il repository chiama per nome e non lo passava gia' dal 2026-10-09
- Lo smoke test sezione 14 gestisce gracefully il caso in cui la funzione DB non sia
  ancora disponibile
- 2026-10-21: la finestra passa da `page`/`page_size` a `limit`/`offset`
  (`pagina_da_query`, default 25, max 100); `page`/`page_size` in query
  diventano un 400. Envelope invariato
