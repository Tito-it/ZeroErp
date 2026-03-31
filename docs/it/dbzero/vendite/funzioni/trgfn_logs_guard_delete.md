{% include-markdown "it/dbzero/vendite/manual/trgfn_logs_guard_delete.md" %}
# ⚙️ Funzione `trgfn_logs_guard_delete`

```sql
CREATE FUNCTION trgfn_logs_guard_delete()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_logs_guard_delete()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_allow_logs  TEXT;
    v_allow_reset TEXT;
BEGIN
    v_allow_logs := current_setting('zeroerp.maintenance_allow_delete_logs', true);
    v_allow_reset := current_setting('zeroerp.maintenance_reset_lotto_draft', true);

    IF COALESCE(lower(v_allow_logs), 'off') NOT IN ('on', 'true', '1')
       AND COALESCE(lower(v_allow_reset), 'off') NOT IN ('on', 'true', '1') THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME, 'E_DELETE_NOT_ALLOWED',
            jsonb_build_object('table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME, 'id', OLD.id),
            NULL::uuid, TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME, OLD.id::text
        );
    END IF;

    RETURN OLD;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_logs_guard_delete()
IS 'Blocca DELETE su log fatture/lotti salvo GUC maintenance.';
```

---
{% include-markdown "signature-core.md" %}
