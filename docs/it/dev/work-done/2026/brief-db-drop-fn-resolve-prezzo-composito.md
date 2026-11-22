# Brief DB — DROP `vendite.fn_resolve_prezzo_composito` (legacy modello componenti BoM pre-unificato)

> Data: 2026-05-14
> Owner: team DB (`dev/db-tid`)
> Stato: pronto per applicazione
> Backend: ✅ tutti i caller Python rimossi col cleanup `Cleanup legacy resolve_prezzo_composito + 1-JOIN _load_componente_for_modification` (vedi history su `dev/backend-tid`)

## Contesto

La funzione `vendite.fn_resolve_prezzo_composito` (resolver BoM ibrido
A/B1/B2) è stata marcata `COMMENT DEPRECATED` dal migration `20260513-24`
in seguito alla decisione di dominio "modello unificato componenti BoM"
(`docs/it/dev/manual/modello-componenti-bom.md`):

- Padre composito = SEMPRE `SUM(figli × coeff_qta_snapshot)`
- Nessuna distinzione CASO A vs CASO B
- Resolver pricing canonico: `fn_resolve_prezzo_listino_v2(..., p_articolo_padre_contesto)` bundle-aware
- Path Python preventivi/contratti: fn `fn_<sorgente>_riga_componenti_init/preview` (modello unificato) chiamano internamente il resolver bundle-aware

## Verifica caller residui

Lato BE Python al 2026-05-14:

| Caller storico | Status |
|---|---|
| `pricing_repository.resolve_prezzo_composito` | ✅ rimosso |
| `pricing_service.resolve_prezzo_composito` | ✅ rimosso |
| `BoMComponentExpander.expand()` path legacy fallback | ✅ rimosso (path snapshot unico) |
| `BoMComponentExpander._resolve_cached` + `_resolve_cache` | ✅ rimosso |
| Test `test_pricing_service.TestResolveComposito` | ✅ rimosso |
| Test legacy in `test_commesse_source_handlers.py` (caso_a/b/cache_resolver/isolamento_errore/handler_default_invoca_bom_expander) | ✅ rimossi |
| Helper test `_make_resolver_riga` | ✅ sostituito con `_make_snapshot_componente` |

Lato DB: vista/funzione `fn_resolve_prezzo_composito` resta presente in
`docs/it/dbzero/vendite/funzioni/fn_resolve_prezzo_composito.md` e nelle
migration storiche.

## Richiesta

1. **DROP** della funzione DB `vendite.fn_resolve_prezzo_composito`.
2. Rimuovere il file generato `docs/it/dbzero/vendite/funzioni/fn_resolve_prezzo_composito.md` (auto-rigenerato dai script docs).
3. Verificare che non esistano caller residui lato DB (trigger, viste, altre fn): un `grep -r fn_resolve_prezzo_composito db/changelog/` e `\df vendite.fn_resolve_prezzo_composito` su istanza dev.

## File migration suggerito

`db/changelog/migrations_v2/20260514-NN-drop-fn-resolve-prezzo-composito.yaml`

```yaml
databaseChangeLog:
  - changeSet:
      id: 20260514-NN-drop-fn-resolve-prezzo-composito
      author: Tid
      logicalFilePath: vendite/funzioni/drop-fn-resolve-prezzo-composito.sql
      labels: vendite,pricing,cleanup-legacy
      changes:
        - sql:
            splitStatements: false
            sql: |
              -- Cleanup legacy modello componenti BoM 2026-05-13.
              -- Caller Python rimossi col cleanup 2026-05-14 (vedi brief
              -- `brief-db-drop-fn-resolve-prezzo-composito.md`).
              DROP FUNCTION IF EXISTS vendite.fn_resolve_prezzo_composito(
                uuid, integer, date, bigint, integer, bigint, integer
              );
        - rollback:
            sql:
              -- Rollback non praticabile: la fn richiederebbe restore dal migration
              -- originale 20251209-XX-fn-resolve-prezzo-composito + l'allineamento
              -- col modello pre-unificato. Eseguire prima il rollback dei migration
              -- modello unificato (20260513-01..24) se serve davvero ripristinare.
```

## Verifica post-apply

Su istanza dev dopo l'applicazione:

```sql
-- Deve ritornare 0 righe
SELECT proname FROM pg_proc
 WHERE pronamespace = 'vendite'::regnamespace
   AND proname = 'fn_resolve_prezzo_composito';

-- Verifica no callers residui lato DB
SELECT routine_schema, routine_name
  FROM information_schema.routines r
  JOIN pg_proc p ON p.proname = r.routine_name
 WHERE pg_get_functiondef(p.oid) ILIKE '%fn_resolve_prezzo_composito%'
   AND routine_schema != 'pg_catalog';

-- Test BE: i 689 test devono restare verdi (i caller Python sono stati
-- rimossi col commit `Cleanup legacy resolve_prezzo_composito + 1-JOIN`).
```

## Impatto

- **Production**: nessuno. La fn non era mai realmente invocata in produzione:
  - Preventivi push: path snapshot attivo (loader `list_componenti_riga` su `preventivi_righe_componenti`).
  - Ordini push: `fn_list_ordini_da_pushare` ritorna vuoto (modulo ordini Python ancora da costruire, vedi `refactor-componenti.md §G`).
  - Contratti/DDT: handler non orchestrati (`commesse_push_orchestrator.py` registra solo `HandlerPreventivi` + `HandlerOrdini`).
- **Sviluppo futuro**: quando i moduli ordini/ddt verranno costruiti, useranno il pattern snapshot loader (replica `HandlerPreventivi`). Niente reintroduzione del path resolver.
- **Doc auto-generata**: il rebuild di `docs/it/dbzero/vendite/funzioni/` rimuoverà il file `.md` corrispondente.

## Cross-reference

- Decisione dominio: `docs/it/dev/manual/modello-componenti-bom.md` (modello unificato)
- Piano fasi: `docs/it/dev/work-in-progress/refactor-componenti.md` §G (ordini/ddt rinviati) + tabella pendenti #8 (DROP)
- Migration deprecation: `db/changelog/migrations_v2/20260513-24-deprecate-fn-resolve-prezzo-composito.yaml` (COMMENT only, non DROP)
