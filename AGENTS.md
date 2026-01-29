# AGENTS.md

## Scope
- Repo: ZeroErp
- Default language: it-IT
- Follow docs in `docs/it/linee-guida-sql.md`, `docs/it/linee-guida-trigger.md`, `docs/it/liquibase-setup-workflow.md`

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
