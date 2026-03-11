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
| `q` | string | Si | — | Termine di ricerca (min 3 caratteri). Cerca su `ragione_sociale_completa` e `id_fiscale_univoco_cf_piva` |
| `tipo_ruolo_id` | int | Si | — | ID tipo ruolo. Solo tipi con `ricerca_visibile = true` in `config.tipi_ruoli` |
| `page` | int | No | 1 | Numero pagina |
| `page_size` | int | No | 25 | Dimensione pagina (min 1, max 100) |

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
        "utility_list": "GAS, EE"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

### GET /api/v1/core/search/\<uuid:soggetto_id\>/detail/ — Dettaglio soggetto (livello 2)

#### Input (query params)

| Parametro | Tipo | Obbl. | Descrizione |
|---|---|---|---|
| `tipo_ruolo_id` | int | Si | ID tipo ruolo per il dettaglio |

#### Output (200)

Output JSONB con struttura variabile per tipo ruolo. Tutti i tipi includono indirizzo e
comune risolti con logica specifica:

- **CLIENTE**: `indirizzo_normalizzato` da istanza, fallback `fn_get_indirizzo(sr.id, 'RES')`
- **FORNITORE**: `fn_get_indirizzo(sr.id, 'SEDEOP')` (sede operativa con catena fallback)
- **Generico**: `fn_get_indirizzo(sr.id, 'RES')` (residenza con catena fallback)

Esempio per CLIENTE:

```json
{
  "data": {
    "tipo_ruolo": "CLIENTE",
    "soggetto_id": "uuid",
    "righe": [
      {
        "codice": "CLI-0042",
        "istanza_codice": "IST-001",
        "utility_descrizione": "GAS",
        "indirizzo": "Via Roma 12",
        "comune": "Bergamo",
        "stato_codice": "AT",
        "stato_descrizione": "Attivo"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

### GET /api/v1/core/lookup/tipi-ruoli/ — Lookup tipi ruolo

#### Input (query params)

| Parametro | Tipo | Obbl. | Descrizione |
|---|---|---|---|
| `ricerca_visibile` | bool | No | Filtra solo tipi con `ricerca_visibile = true` (default true) |

#### Output (200)

```json
{
  "data": {
    "results": [
      { "id": 1, "codice": "CLIENTE", "descrizione": "Cliente" },
      { "id": 2, "codice": "FORNITORE", "descrizione": "Fornitore" }
    ]
  },
  "meta": { "request_id": "..." }
}
```

## Regole

- `q` obbligatorio, minimo 3 caratteri (validato da `require_min_search_length`)
- `tipo_ruolo_id` obbligatorio, validato contro `ricerca_visibile = true` su `config.tipi_ruoli`
- Scope emittente applicato: utenti OPERATIVO con whitelist emittenti vedono solo soggetti nel proprio scope (tramite `PermissionResolver.get_emittenti_ids`)
- Throttling search attivo (`SearchBurstRateThrottle`, `is_search_endpoint = True`)
- Hard cap 10.000 risultati nella funzione DB
- Paginazione LIMIT/OFFSET + COUNT(*) OVER() in un solo round-trip
- Il dettaglio (livello 2) e' caricato lazy — solo quando l'utente espande la riga

## Errori

| Codice | HTTP | Causa |
|---|---|---|
| `E_SEARCH_VALIDATION` | 400 | Parametro mancante, troppo corto (< 3 caratteri), tipo ruolo non visibile, paginazione fuori range |
| `E_SEARCH_NOT_FOUND` | 404 | Dettaglio soggetto non trovato per la combinazione soggetto_id + tipo_ruolo_id |
| `E_VALIDATION_INPUT` | 400 | Parametro numerico non valido (page/page_size non numerici) |

## Dipendenze DB

| Oggetto | Schema | Tipo |
|---|---|---|
| `fn_search_soggetti_universale` | `script` | Funzione — ricerca livello 1 (5 parametri, senza comune_id) |
| `fn_get_search_detail` | `script` | Funzione — dettaglio livello 2 (con indirizzo/comune per tutti i tipi) |
| `fn_get_indirizzo` | `script` | Funzione — risoluzione indirizzo con catena fallback (usata nel livello 2) |
| `tipi_ruoli` | `config` | Tabella — colonna `ricerca_visibile` |
| `fn_get_emittenti_scope` | `script` | Funzione — scope emittente |

## File backend

| File | Ruolo |
|---|---|
| `apps/core/db/search_repository.py` | Repository — accesso DB |
| `apps/core/api/search_view.py` | View API — `SearchUniversaleView`, `SearchDetailView`, `LookupTipiRuoliView` |
| `apps/core/api/urls_v1.py` | Routing — `search/`, `search/<uuid>/detail/`, `lookup/tipi-ruoli/` |
| `apps/core/services/error_policies.py` | Policy errori — `E_SEARCH_VALIDATION`, `E_SEARCH_NOT_FOUND` |
| `apps/core/tests/api/test_search_view.py` | Test unitari (17 test, mock DB) |
| `scripts/tests/smoke-test-core.sh` | Smoke test (sezioni 14-17) |

## Note di migrazione

- La colonna `ricerca_visibile` su `config.tipi_ruoli` deve essere creata prima del deploy
  (changeset Liquibase in Fase 1, step 1.0 del WIP)
- Le funzioni DB `fn_search_soggetti_universale` e `fn_get_search_detail` devono essere
  presenti nello schema `script` (Fase 1, step 1.3 e 1.4)
- `fn_search_soggetti_universale` ha signature a 5 parametri (rimosso `p_comune_id`)
- `fn_get_search_detail` ora include indirizzo e comune per tutti i tipi ruolo
- Lo smoke test sezione 14 gestisce gracefully il caso in cui la funzione DB non sia
  ancora disponibile
