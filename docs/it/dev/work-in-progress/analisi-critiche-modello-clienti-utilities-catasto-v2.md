# Analisi Critiche v2 — Orchestrator Django ClienteService

**Data**: 2026-03-18
**Stato**: APERTO
**Prerequisiti completati**: Analisi + DB (guard, disdetta, doc) tutti RISOLTI
**Documento principale**: `docs/it/dev/work-done/analisi-critiche-modello-clienti-utilities-catasto.md`

---

## Contesto

L'analisi originale (v1) ha identificato e risolto 11 finding su 12.
L'unico punto aperto e' il **2.6b**: Orchestrator Django `ClienteService`.

Le fasi DB sono completate:
- Guard dissociazione parent_account_id (DB-01..03)
- `script.fn_disdetta_cliente` + pgTAP (DB-04..09)
- Tutte le correzioni documentali (9 su 9 RISOLTE)

---

## Piano di sviluppo: ClienteService

### Repository: `backend/apps/anagrafiche/db/anagrafiche_repository.py`

| Metodo | SQL |
|--------|-----|
| `get_soggetto(soggetto_id)` | SELECT da `anagrafiche.soggetti` |
| `get_or_create_soggetto_ruolo(soggetto_id, codice_ruolo)` | `SELECT script.fn_get_or_create_soggetto_ruolo(...)` |
| `create_istanza_utilities(soggetto_id, indirizzo_dettaglio_id, pdp_id, fittizia)` | INSERT INTO `anagrafiche.istanze_utilities` RETURNING id |
| `create_billing_account(istanza_utility_id, soggetto_ruolo_id, utility_id, parent_account_id)` | INSERT INTO `anagrafiche.billing_account` RETURNING id |
| `create_cliente(istanza_utility_id, billing_account_id, soggetto_ruolo_id, stato_cliente_id, data_attivazione, ...)` | INSERT INTO `anagrafiche.clienti` RETURNING id |
| `close_previous_client(pdp_id, data_attivazione)` | `SELECT script.fn_subentro_cliente(...)` |
| `disdetta_cliente(cliente_id, data_cessazione)` | `SELECT script.fn_disdetta_cliente(...)` |
| `get_stato_cliente_by_codice(codice_interno)` | SELECT id FROM `config.stati_cliente` WHERE codice_interno = ... |

- [ ] **DJ-01** Creare repository con tutti i metodi

### Types: `backend/apps/anagrafiche/types.py`

- [ ] **DJ-02** Creare `CreaClienteParams` dataclass

### Service: `backend/apps/anagrafiche/services/cliente_service.py`

Metodi:
- `crea_cliente(params)` — orchestrazione completa: soggetto -> ruolo -> [subentro] -> istanza -> BA -> cliente
- `disdetta_cliente(cliente_id, data_cessazione)` — cessazione senza subentro
- `subentro_cliente(params)` — alias crea_cliente con pdp_id obbligatorio

- [ ] **DJ-03** Creare `ClienteService`

### API

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `POST /api/v1/anagrafiche/clienti/` | `crea_cliente` | Creazione completa |
| `POST /api/v1/anagrafiche/clienti/{id}/disdetta` | `disdetta_cliente` | Cessazione |
| `POST /api/v1/anagrafiche/clienti/subentro` | `subentro_cliente` | Subentro |

- [ ] **DJ-04** Creare view + url `crea_cliente`
- [ ] **DJ-05** Creare view + url `disdetta_cliente`
- [ ] **DJ-06** Creare view + url `subentro_cliente`

### Test

- [ ] **DJ-07** Test service: happy path crea_cliente
- [ ] **DJ-08** Test service: happy path subentro_cliente
- [ ] **DJ-09** Test service: happy path disdetta_cliente
- [ ] **DJ-10** Test service: error path soggetto non trovato
- [ ] **DJ-11** Test service: error path PDP obbligatorio per subentro
- [ ] **DJ-12** Test API: smoke test tutti gli endpoint

---

## Pattern di riferimento

- Repository: `backend/apps/vendite/db/pipeline_repository.py`
- Service: `backend/apps/vendite/services/pipeline_runner.py`
- Error handling: `backend/apps/core/services/error_manager.py`
- API helper: `backend/apps/core/api/endpoint_helpers.py`
