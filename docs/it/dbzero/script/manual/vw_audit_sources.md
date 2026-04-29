# vw_audit_sources

### Scopo

Vista pubblica delle "tabelle audit-abili" esposte dal drawer admin
([AuditLogView](/dev/work-in-progress/analisi-refactor.frontend-amm-software))
(Fase 5 P1 2026-04-29). Sostituisce la lista hardcoded oggi in
[`apps.amm_software.db.amm_software_repository._AUDIT_TABLES`](/backend/amm_software/manual/amm_software_repository)
e le costanti FE `buildAuditTabellaOptions`.

> **Vedi anche**
>
> - [Guida Audit e Tracciabilità](/guide/audit-e-tracciabilita)
> - [audit_sources](/dbzero/dbops/manual/audit_sources) — tabella sottostante
> - [fn_audit_summary](/dbzero/script/manual/fn_audit_summary) — usa la tabella per dispatch dinamico

## Schema

`script` (cross-dominio, contratto API).

## Definizione

```sql
CREATE OR REPLACE VIEW script.vw_audit_sources AS
SELECT
    code,
    label_key,
    area_funzionale
  FROM dbops.audit_sources
 WHERE attivo = true
 ORDER BY code;
```

## Output

| Colonna | Tipo | Significato |
|---|---|---|
| `code` | `text` | Codice stabile usato come riferimento da BE/FE (es. `'user_override_aree'`). |
| `label_key` | `text` | Chiave i18n (es. `'amm.audit_tabella_override_aree'`). Il FE la mappa al locale. |
| `area_funzionale` | `text` | Raggruppamento UI: `PERMESSI \| AUTH \| ANAGRAFICHE \| EMITTENTI \| FATTURAZIONE`. |

## Cosa NON espone (deliberatamente)

`storico_table` e `storico_pk_col` sono colonne tecniche di
`dbops.audit_sources`: dispatch implementativo del framework
storicizzazione, **non parte del contratto API**. Esporle qui
significherebbe legarvi BE/FE e creare attrito ad eventuali rinomini
di schema/colonne lato storico. Restano lette **solo** da
`script.fn_audit_summary` per la dispatch dinamica.

Se in futuro emerge un caso d'uso amministrativo/diagnostico, si
aggiunge una `vw_audit_sources_debug` separata invece di estendere la
pubblica.

## Consumer

| Consumer | Endpoint / Codice |
|---|---|
| Drawer admin AuditLogView | `GET /api/v1/amm-software/lookup/audit-sources/` (Fase 5 BE) |
| Filtro tabella sulla list view | `useGlobalLookup('amm.audit_sources')` (FE) |
| `script.fn_audit_summary` | Internamente (legge da tabella sottostante per metadata tecnico) |

## Caratteristiche

- Vista trivial (no JOIN, no calcoli): proiezione + filtro.
- `attivo = true` filtra i record disabilitati senza che il consumer
  debba conoscerne l'esistenza.
- `ORDER BY code` per output deterministico.
- Auto-aggiornata: aggiungere una riga in
  `dbops.audit_sources` la rende immediatamente disponibile alla vista
  (`runOnChange:true` sul loader CSV).

## Riferimenti

- Migration: `db/changelog/migrations_v2/20_code/script/20260429-06-create-vw-audit-sources-mctit.yaml`
- Tabella sottostante: [dbops.audit_sources](/dbzero/dbops/manual/audit_sources)
- Brief Fase 5: `docs/it/dev/work-in-progress/analisi-refactor.frontend-amm-software.md`
