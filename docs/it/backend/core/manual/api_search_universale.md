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
| `comune_id` | int | No | null | Filtro opzionale per comune |
| `page` | int | No | 1 | Numero pagina |
| `page_size` | int | No | 25 | Dimensione pagina (min 1, max 100) |

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
        "comune_id": 5,
        "comune_descrizione": "Bergamo",
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

Output JSONB con struttura variabile per tipo ruolo. Esempio per CLIENTE:

```json
{
  "data": {
    "tipo_ruolo": "CLIENTE",
    "soggetto_id": "uuid",
    "righe": [
      {
        "cliente_id": 10,
        "istanza": "IST-001",
        "utility": "GAS",
        "stato": "ATTIVO",
        "indirizzo": "Via Roma 12, Bergamo"
      }
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
| `E_SEARCH_VALIDATION` | 400 | Parametro mancante, troppo corto, tipo ruolo non visibile, paginazione fuori range |
| `E_PIPELINE_VALIDATION` | 400 | Termine ricerca troppo corto (< 3 caratteri, da `require_min_search_length`) |
| `E_SEARCH_NOT_FOUND` | 404 | Dettaglio soggetto non trovato per la combinazione soggetto_id + tipo_ruolo_id |
| `E_VALIDATION_INPUT` | 400 | Parametro numerico non valido (page/page_size non numerici) |

## Dipendenze DB

| Oggetto | Schema | Tipo |
|---|---|---|
| `fn_search_soggetti_universale` | `script` | Funzione — ricerca livello 1 |
| `fn_get_search_detail` | `script` | Funzione — dettaglio livello 2 |
| `tipi_ruoli` | `config` | Tabella — colonna `ricerca_visibile` |
| `fn_get_emittenti_scope` | `script` | Funzione — scope emittente |

## File backend

| File | Ruolo |
|---|---|
| `apps/core/db/search_repository.py` | Repository — accesso DB |
| `apps/core/api/search_view.py` | View API — `SearchUniversaleView`, `SearchDetailView` |
| `apps/core/api/urls_v1.py` | Routing — `search/`, `search/<uuid>/detail/` |
| `apps/core/services/error_policies.py` | Policy errori — `E_SEARCH_VALIDATION`, `E_SEARCH_NOT_FOUND` |
| `apps/core/tests/api/test_search_view.py` | Test unitari (16 test, mock DB) |
| `scripts/tests/smoke-test-core.sh` | Smoke test (sezioni 14-17) |

## Note di migrazione

- La colonna `ricerca_visibile` su `config.tipi_ruoli` deve essere creata prima del deploy
  (changeset Liquibase in Fase 1, step 1.0 del WIP)
- Le funzioni DB `fn_search_soggetti_universale` e `fn_get_search_detail` devono essere
  presenti nello schema `script` (Fase 1, step 1.3 e 1.4)
- Lo smoke test sezione 14 gestisce gracefully il caso in cui la funzione DB non sia
  ancora disponibile
