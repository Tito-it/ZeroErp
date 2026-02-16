# AGENTS.md


## Quick Start per AI Agent
- Progetto: ERP Django + PostgreSQL
- Stack: Python 3.14, Django 6.01, Liquibase v2
- Prima di implementare: leggi docs in `docs/it/` pertinenti
- Struttura: backend in `backend/`, DB migrations in `db/changelog/migrations_v2/`

## Scope
- Repo: ZeroErp
- Default language: it-IT
- Follow docs in `docs/it/linee-guida-sql.md`, `docs/it/linee-guida-trigger.md`, `docs/it/liquibase-setup-workflow.md`

## Backend (Django)
- Codice backend in `backend/`
- Versioni: Python 3.14, Django 6.01
- Evitare API/metodi deprecati; seguire best practice Django
- Accesso webserver configurato: test migrazione solo su richiesta
- Per i file Python **generati** aggiungere sempre l’header standard in `templates/python-header.txt`.
- Per ogni nuovo file Python (non generato da Django) aggiungere l’header standard di `templates/python-header.txt` e un breve commento iniziale sullo scopo.
- Nei file Python aggiungere commenti sintetici nei blocchi non banali (orchestrazione, transazioni, mapping task/SQL), scritti in italiano.
- Dopo un `ErrorManager.require(... is not None ...)` aggiungere sempre l’`assert` corrispondente per aiutare il type checker.
- Dopo `row = cursor.fetchone()` aggiungere guard (`if not row`) oppure `assert row is not None` prima di usare `row[...]`.
- Nei servizi/classi Python usare nomi metodo espliciti e orientati al dominio (es. `run_pipeline`), evitando nomi generici/ambigui come `run`.
- Per error handling servizi/API usare helper centralizzato in `apps/core/services/error_manager.py`, evitando logica duplicata nei moduli dominio.
- Il mapping `codice errore -> HTTP status -> azione UI` deve essere centralizzato in `apps/core/services/error_policies.py`.
- Struttura consigliata: project config in `backend/zeroerp_backend/`, app in `backend/apps/`
- App per dominio (es. `vendite`, `anagrafiche`), non per dettaglio tecnico; se uno schema DB coincide con un dominio stabile, la cartella app puo` allinearsi allo schema
- Orchestrazione in `apps/<dominio>/services/` (o `usecases/`); accesso DB/SQL in `apps/<dominio>/db/` o `repositories/`
- API in `apps/<dominio>/api/` o `views.py` + `urls.py`; modelli ORM solo dove utili, altrimenti `managed = False`
- Per endpoint API usare il pattern core `handle_post_json(...)` (`apps/core/api/endpoint_helpers.py`) per parsing/error envelope uniforme.
- Evitare `try/except Exception` generici nelle view API dominio: usare `ServiceError` nei service e lasciare fallback al middleware `apps/core/middleware/api_exception_middleware.py`.
- Il middleware eccezioni API si applica solo a `/api/*` e resta disattivabile via `DJANGO_API_EXCEPTION_MIDDLEWARE_ENABLED`.
- Per nuove API lista/search applicare la policy `docs/it/dev/Policy-ricerca-e-paginazione(API-DB).md` e usare gli helper core (`apps/core/api/pagination.py`, `apps/core/api/search_validators.py`).
- Per endpoint search impostare `is_search_endpoint = True` per attivare throttling DRF (`apps/core/api/throttling.py`).

## Liquibase v2 Workflow
- New work only in `db/changelog/migrations_v2/`
- File extension: `.yaml` only
- File naming: `YYYYMMDD-NN-<tipo>-<descrizione>.yaml`
- One changeSet per file
- Always set `logicalFilePath`
- `00_schema` and `20_code` are included via `migrations_v2/changelog-autogen.yaml` (autogen script)
- `80_data`, `85_pgagent`, `90_end` are included via `includeAll` in master

## Regole Documentazione
- I contenuti concettuali principali sono nella documentazione dell’area tecnica (guide).
- Prima di strutturare una soluzione, consultare le guide pertinenti (es. soggetti → guida soggetti e ruoli anagrafici).
- Gli script aggiornati per tabelle/views/funzioni si trovano in `<schema>/tabelle`, `<schema>/views`, `<schema>/funzioni`.
- Non modificare questi file auto-generati: servono solo come riferimento.
- Scrivere o aggiornare solo la documentazione concettuale in `<schema>/manual`.
- Per la documentazione backend (Django), usare sempre una struttura standard nei file manuali:
  - Scopo
  - Contesto
  - Input
  - Output
  - Regole
  - Dipendenze DB
  - Note di migrazione (se applicabile)
- Template di riferimento: `docs/it/backend/_templates/manual-standard.md`

## SQL Conventions
- Schemas/tables/columns naming per `linee-guida-sql.md`
- Prefer UUID for master entities; SERIAL/IDENTITY for technical tables
- Use `tx_id UUID` when required by transaction-id policy
- Audit fields: `date_insert`, `user_insert`, `date_update`, `user_update`
- Index naming: `ix_<table>_<column>`; check duplicates via `dbops.vw_duplicate_indexes`
- FK index policy applied in `90_end` with `dbops.apply_fk_index_policy()`
- FK index: non crearli manualmente; se necessari, rispettare il naming di policy e registrare in `dbops.fk_index_policy` (consentito true/false) tramite `dbops.fn_seed_fk_index_policy()` o `dbops.fn_populate_fk_index_policy()`
- Per variabili PL/pgSQL che riflettono colonne, usare `%TYPE` della colonna (es. `v_uom_base_id catalogo.unita_misura.id%TYPE`)
- Nei blocchi SQL di funzioni/trigger inserire commenti sintetici sullo scopo e sulle regole principali.
- In script complessi con molti filtri/parametri, e per evitare duplicazioni di logica, e` consentito usare SQL dinamico (con attenzione alla sicurezza).
- Quando serve capire struttura o campi di tabelle/funzioni, leggere prima la documentazione in `<schema>/tabelle` e `<schema>/funzioni`, evitando di partire dalle migrations.
- Nelle funzioni SQL, per parametri numerici di tipo ID applicare guard di validazione esplicita: errore se `NULL` o `<= 0` (non normalizzare silenziosamente).

## Trigger Conventions
- Trigger name: `trg_<schema_opzionale>_<tabella>_<fase>_<descrizione>_<eventi>`
- Phases: `_a10_` for guard/block, `_z90_` for final/deferrable
- Event suffixes: `_ins/_upd/_dlt` (combine if needed)
- Use `UPDATE OF colonna` when logic is column-specific
- Errors via `script.fn_log_and_raise_error(...)`

## Guard vs Check Functions
- `fn_check_*`: pure checks returning boolean, no raise
- `fn_guard_*`: fail-fast, can raise/log

## Workflow Safety
- Ask before running DB migrations locally
- Avoid destructive commands without explicit approval

## Test (pgtap)
- Test DB: pgtap
- Percorso: `db/pgtap/`
- Nei file di test, all'inizio inserire un indice dei test eseguiti nei commenti.
- Nei file di test Python/Django, inserire all'inizio un breve indice dei test previsti (nome test/caso).
- Struttura test Django per app: `apps/<schema>/tests/` con sottocartelle minime `api/` e `services/`.
- Esempio esecuzione test Django: `./manage-test.sh apps.core.tests.api -v 2`
- Smoke test API docs/schema: vedi `apps/core/tests/api/test_diagnostics_api.py` (endpoint `/api/docs/` e `/api/schema/`).
