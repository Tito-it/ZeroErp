# ⚙️ Funzione `fn_refresh_mv_ddt_ordini`

```sql
CREATE FUNCTION fn_refresh_mv_ddt_ordini(p_concurrent boolean, p_max_retries integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_refresh_mv_ddt_ordini(p_concurrent boolean DEFAULT true, p_max_retries integer DEFAULT 3)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_locked boolean;
  v_try    integer := 0;
BEGIN

  v_locked := pg_try_advisory_lock(hashtext('vendite.mv_ddt_ordini'));
  IF NOT v_locked THEN

    WHILE v_try < p_max_retries AND NOT v_locked LOOP
      v_try := v_try + 1;
      PERFORM pg_sleep(1);
      v_locked := pg_try_advisory_lock(hashtext('vendite.mv_ddt_ordini'));
    END LOOP;
    IF NOT v_locked THEN
      PERFORM script.fn_log_and_raise_error(
        'database','fn_refresh_mv_ddt_ordini','E_REFRESH_LOCK_TIMEOUT',
        jsonb_build_object('mv','vendite.mv_ddt_ordini','retries',p_max_retries),
        NULL::uuid,
        -- rev 2026-08-04 (bonifica F3): p_max_retries e' integer e il
        --   parametro e' VARIADIC text[]. Senza il cast la chiamata non
        --   si risolve e il guard, proprio quando scade il lock, solleva
        --   «la funzione non esiste» invece del timeout.
        'MV : vendite.mv_ddt_ordini' , p_max_retries::text);
    END IF;
  END IF;

  BEGIN
    IF p_concurrent THEN
      EXECUTE 'REFRESH MATERIALIZED VIEW CONCURRENTLY vendite.mv_ddt_ordini';
    ELSE
      EXECUTE 'REFRESH MATERIALIZED VIEW vendite.mv_ddt_ordini';
    END IF;
  EXCEPTION WHEN others THEN

    IF p_concurrent THEN
      EXECUTE 'REFRESH MATERIALIZED VIEW vendite.mv_ddt_ordini';
    ELSE
      RAISE;
    END IF;
  END;

  PERFORM pg_advisory_unlock(hashtext('vendite.mv_ddt_ordini'));
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
