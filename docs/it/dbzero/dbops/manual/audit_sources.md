# audit_sources

### Scopo

Lookup table delle "tabelle audit-abili" esposte al drawer admin
([AuditLogView](/dev/work-in-progress/analisi-refactor.frontend-amm-software)).
Single source of truth della lista "quali storico.* sono navigabili
da UI" + metadata per l'i18n (`label_key`) e il raggruppamento UI
(`area_funzionale`).

Sostituisce la lista hardcoded oggi in
[`apps.amm_software.db.amm_software_repository._AUDIT_TABLES`](/backend/amm_software/manual/amm_software_repository)
e le costanti FE `buildAuditTabellaOptions`.

> **Vedi anche**
>
> - [Guida Audit e Tracciabilità](/guide/audit-e-tracciabilita) — strato 1 (audit DB)
> - [vw_audit_sources](/dbzero/script/manual/vw_audit_sources) — vista pubblica (3 colonne contratto)
> - [fn_audit_summary](/dbzero/script/manual/fn_audit_summary) — dispatch dinamico via `storico_table` + `storico_pk_col`

## Schema

`dbops` (lookup tecnico, non dominio).

## Modello

| Colonna | Tipo | Ruolo |
|---|---|---|
| `id` | `smallserial` PK | Lookup tecnico |
| `code` | `text` UNIQUE | Codice stabile usato dal BE/FE (es. `'user_override_aree'`). Coincide tipicamente col nome tabella sorgente. |
| `storico_table` | `text` | Nome qualificato `schema.tabella` della storico target (es. `'storico.user_override_aree'`). **Colonna tecnica, non esposta dalla vista pubblica**. |
| `storico_pk_col` | `text` | Nome della colonna che identifica la riga originale nello storico (es. `'user_override_aree_id'`). Usata da `fn_audit_summary` per il `PARTITION BY` del LAG diff. **Tecnica**. |
| `label_key` | `text` | Chiave i18n usata dal FE (es. `'amm.audit_tabella_override_aree'`). Il DB non traduce. |
| `area_funzionale` | `text` | Vocabolario controllato (no `CHECK`, validato in pgTAP): `PERMESSI \| AUTH \| ANAGRAFICHE \| EMITTENTI \| FATTURAZIONE`. |
| `attivo` | `boolean` | Soft-disable per fasi di transizione. La vista filtra `attivo=true`. |
| audit standard | — | `data_insert/update`, `user_insert/update`, `tx_id`, `storicizza` |

## Vincoli

- `pk_audit_sources` su `id`
- `uq_audit_sources_code` UNIQUE su `code`

## Trigger applicati dal framework automazioni

- `trgfn_audit_data_user_generic` (audit standard `data_*`/`user_*`)
- `trgfn_tx_id_managed` (tx_id)
- `trgfn_storico_generic` (storicizzazione su UPDATE/DELETE)

I trigger non sono scritti manualmente in migration: vengono creati
automaticamente da `dbops.fn_run_automations` post-deploy (vedi
[guida automazioni](/guide/audit-e-tracciabilita)).

## Aggiungere una nuova storico al drawer admin

Tre passi, tutti dati-non-codice:

1. La tabella sorgente deve essere già storicizzata (colonne
   `storicizza, tx_id` + `storico.<tabella>` provvisionata via
   `dbops.fn_run_automations(... STORICO ...)`).
2. Append una riga in
   `db/changelog/migrations_v2/80_data/sql/dbops/audit_sources.csv`
   con `code, storico_table, storico_pk_col, label_key, area_funzionale`.
3. `liquibase update` — il loader `runOnChange:false` esistente upserta
   la riga via `loadUpdateData` su PK `id`.

Nessuna modifica di schema, nessun nuovo file YAML, nessun cambio BE.
La vista `vw_audit_sources` riflette automaticamente il nuovo lookup;
`fn_audit_summary` lo prende in carico via il dispatch dinamico.

## Vocabolario `area_funzionale`

Convenzione documentata, validata in
`db/pgtap/dbops/test-audit-sources-seed.sql`. Cinque valori stabili:

| Valore | Tabelle attese |
|---|---|
| `PERMESSI` | `user_override_*`, `profili_accesso_aree/_azioni/_bindings` |
| `AUTH` | `risorse_umane_auth_user` (legacy), `identita_digitali` |
| `ANAGRAFICHE` | (futuro) `soggetti`, `clienti`, `fornitori` |
| `EMITTENTI` | `user_emittenti_fiscali`, `emittenti_fiscali` |
| `FATTURAZIONE` | (futuro) `fatture`, `lotti` |

Aggiungere un sesto valore senza prima aggiornare il vocabolario
documentato + il test fa fallire il pgTAP — by design.

## Riferimenti

- DDL: `db/changelog/migrations_v2/00_schema/dbops/20260429-05-create-audit-sources-mctit.yaml`
- Seed: `db/changelog/migrations_v2/80_data/sql/dbops/audit_sources.csv` (9 righe attive: 5 user_override/emittenti/RUA + identita + 3 profili_accesso_*)
- Cleanup legacy: `db/changelog/migrations_v2/80_data/changelog/20260505-01-delete-audit-sources-profili-reparto-mctit.yaml`
- Loader: `db/changelog/migrations_v2/80_data/changelog/20260429-08-upsert-audit-sources-mctit.yaml`
- Test pgTAP: `db/pgtap/dbops/test-audit-sources-seed.sql`
- Brief Fase 5: `docs/it/dev/work-in-progress/analisi-refactor.frontend-amm-software.md`
