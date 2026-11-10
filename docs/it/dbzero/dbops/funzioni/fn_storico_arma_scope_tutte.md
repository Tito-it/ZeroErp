{% include-markdown "it/dbzero/dbops/manual/fn_storico_arma_scope_tutte.md" %}
# ⚙️ Funzione `fn_storico_arma_scope_tutte`

```sql
CREATE FUNCTION fn_storico_arma_scope_tutte(p_dry_run boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_storico_arma_scope_tutte(p_dry_run boolean DEFAULT false)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
-- Scopo: applicare fn_storico_arma_scope a ogni madre che porta il trigger
--   di storico. Il marcatore è il TRIGGER, non un elenco: una madre che
--   entra o esce dalla storicizzazione entra o esce da qui da sola.
DECLARE
    r            record;
    v_esito      jsonb;
    v_tot        int := 0;
    v_allineate  int := 0;
    v_armate     int := 0;
    v_skip_owner int := 0;
    v_no_shadow  int := 0;
BEGIN
    FOR r IN
        SELECT DISTINCT n.nspname AS sch, c.relname AS tab
          FROM pg_catalog.pg_trigger t
          JOIN pg_catalog.pg_class     c ON c.oid = t.tgrelid
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
          JOIN pg_catalog.pg_proc      p ON p.oid = t.tgfoid
         WHERE p.proname = 'trgfn_storico_generic'
           AND NOT t.tgisinternal
         ORDER BY 1, 2
    LOOP
        v_tot   := v_tot + 1;
        v_esito := dbops.fn_storico_arma_scope(r.sch, r.tab, p_dry_run);
        CASE v_esito ->> 'esito'
            WHEN 'ALLINEATA'  THEN v_allineate  := v_allineate + 1;
            WHEN 'SKIP_OWNER' THEN v_skip_owner := v_skip_owner + 1;
            WHEN 'NO_SHADOW'  THEN v_no_shadow  := v_no_shadow + 1;
            ELSE NULL;
        END CASE;
        IF (v_esito ->> 'armata')::boolean THEN
            v_armate := v_armate + 1;
        END IF;
    END LOOP;

    -- Un riepilogo per corsa, come le altre automazioni.
    PERFORM dbops.fn_audit_log_once(
        p_function_name => 'fn_storico_arma_scope_tutte',
        p_status        => CASE WHEN p_dry_run THEN 'DRYRUN'
                                WHEN v_skip_owner > 0 THEN 'WARN' ELSE 'OK' END,
        p_rule_type     => 'STORICO_SCOPE',
        p_dry_run       => p_dry_run,
        p_rows_affected => v_allineate,
        p_params        => jsonb_build_object('madri', v_tot, 'allineate', v_allineate,
                                              'armate', v_armate, 'saltate_owner', v_skip_owner,
                                              'senza_shadow', v_no_shadow),
        p_message       => CASE WHEN v_skip_owner > 0
                                THEN 'Shadow di un altro proprietario saltate: serve il provisioning da superuser'
                                ELSE 'Shadow allineate alla forma dello scope' END);

    RETURN jsonb_build_object('madri', v_tot, 'allineate', v_allineate, 'armate', v_armate,
                              'saltate_owner', v_skip_owner, 'senza_shadow', v_no_shadow,
                              'dry_run', p_dry_run);
END;
$function$

COMMENT ON FUNCTION dbops.fn_storico_arma_scope_tutte(p_dry_run boolean)
IS 'Applica dbops.fn_storico_arma_scope a ogni madre che porta il trigger di storico (il marcatore e'' il trigger, non un elenco) e registra un riepilogo nell''audit: madri viste, shadow allineate, armate, saltate perche'' di un altro proprietario, senza shadow. Rete che converge: la chiamano il 90_end runAlways a ogni migrate e il provisioning da superuser.';
```

</div>

---
{% include-markdown "signature-core.md" %}
