{% include-markdown "it/dbzero/dbops/manual/fn_storico_backfill_scope_tutte.md" %}
# ⚙️ Funzione `fn_storico_backfill_scope_tutte`

```sql
CREATE FUNCTION fn_storico_backfill_scope_tutte()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_storico_backfill_scope_tutte()
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
-- Scopo: applicare fn_storico_backfill_scope a ogni madre col trigger di storico.
DECLARE
    r             record;
    v_esito       jsonb;
    v_madri       int := 0;
    v_aggiornate  bigint := 0;
    v_residue     bigint := 0;
    v_saltate     int := 0;
BEGIN
    FOR r IN
        SELECT DISTINCT n.nspname AS sch, c.relname AS tab
          FROM pg_catalog.pg_trigger t
          JOIN pg_catalog.pg_class     c ON c.oid = t.tgrelid
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
          JOIN pg_catalog.pg_proc      p ON p.oid = t.tgfoid
         WHERE p.proname = 'trgfn_storico_generic' AND NOT t.tgisinternal
         ORDER BY 1, 2
    LOOP
        v_madri := v_madri + 1;
        v_esito := dbops.fn_storico_backfill_scope(r.sch, r.tab);
        IF v_esito ->> 'esito' IN ('SENZA_COLONNE', 'NON_ATTRIBUIBILE', 'NO_SHADOW') THEN
            v_saltate := v_saltate + 1;
        END IF;
        v_aggiornate := v_aggiornate + COALESCE((v_esito ->> 'aggiornate')::bigint, 0);
    END LOOP;

    -- Le residue si contano A FINE GIRO, per shadow distinta: nelle shadow
    -- condivise la prima madre vede ancora le righe che la seconda sta per
    -- attribuire, e sommare i conteggi per chiamata le conterebbe due volte.
    FOR r IN
        SELECT c.oid::regclass AS sto
          FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'storico' AND c.relkind = 'r'
           AND EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
                        WHERE a.attrelid = c.oid AND a.attname = 'origine_schema'
                          AND NOT a.attisdropped)
    LOOP
        EXECUTE format('SELECT count(*) FROM %s WHERE origine_schema IS NULL', r.sto) INTO v_esito;
        v_residue := v_residue + (v_esito #>> '{}')::bigint;
    END LOOP;

    PERFORM dbops.fn_audit_log_once(
        p_function_name => 'fn_storico_backfill_scope_tutte',
        p_status        => CASE WHEN v_saltate > 0 THEN 'WARN' ELSE 'OK' END,
        p_rule_type     => 'STORICO_SCOPE',
        p_rows_affected => v_aggiornate::int,
        p_params        => jsonb_build_object('madri', v_madri, 'aggiornate', v_aggiornate,
                                              'residue_null', v_residue, 'saltate', v_saltate),
        p_message       => 'Backfill dello scope di storico su tutte le madri col trigger');

    RETURN jsonb_build_object('madri', v_madri, 'aggiornate', v_aggiornate,
                              'residue_null', v_residue, 'saltate', v_saltate);
END;
$function$

COMMENT ON FUNCTION dbops.fn_storico_backfill_scope_tutte()
IS 'Applica dbops.fn_storico_backfill_scope a ogni madre col trigger di storico e registra un riepilogo nell''audit (madri, versioni aggiornate, residue a NULL, saltate). Idempotente: la chiamano il 90_end una volta e il provisioning da superuser.';
```

</div>

---
{% include-markdown "signature-core.md" %}
