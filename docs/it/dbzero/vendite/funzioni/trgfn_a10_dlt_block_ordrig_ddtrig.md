# ⚙️ Funzione `trgfn_a10_dlt_block_ordrig_ddtrig`

```sql
CREATE FUNCTION trgfn_a10_dlt_block_ordrig_ddtrig()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_a10_dlt_block_ordrig_ddtrig()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_cnt bigint := 0;
BEGIN





  IF TG_TABLE_NAME = 'ordini_righe' THEN
    SELECT COUNT(*) INTO v_cnt
      FROM vendite.ordini_righe_fulfillment f
     WHERE f.ordine_riga_id = OLD.id;

    IF v_cnt > 0 THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_dlt_block_ordrig_ddtrig','E_DELETE_BLOCKED_FUL',
        jsonb_build_object('table','ordini_righe','id',OLD.id),
        NULL::uuid,
        'ordini_righe',
        OLD.id::text
      );
    ELSE
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_dlt_block_ordrig_ddtrig','E_DELETE_NOT_ALLOWED',
        jsonb_build_object('table','ordini_righe','id',OLD.id),
      NULL::uuid,
      'ordini_righe',
      OLD.id::text
      );
    END IF;

  ELSIF TG_TABLE_NAME = 'ddt_righe' THEN
    SELECT COUNT(*) INTO v_cnt
      FROM vendite.ordini_righe_fulfillment f
     WHERE f.ddt_riga_id = OLD.id;

    IF v_cnt > 0 THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_dlt_block_ordrig_ddtrig','E_DELETE_BLOCKED_FUL',
        jsonb_build_object('table','ddt_righe','id',OLD.id,'ddt_id',OLD.ddt_id),
        NULL::uuid,
       'ddt_righe',
       OLD.id::text
      
      );
    ELSE
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_dlt_block_ordrig_ddtrig','E_DELETE_NOT_ALLOWED',
        jsonb_build_object('table','ddt_righe','id',OLD.id,'ddt_id',OLD.ddt_id),
       NULL::uuid,
       'ddt_righe',
       OLD.id::text
      
      );
    END IF;

  ELSE
    
    PERFORM script.fn_log_and_raise_error(
      'database','trgfn_dlt_block_ordrig_ddtrig','E_DELETE_NOT_ALLOWED',
      jsonb_build_object('table',TG_TABLE_NAME,'id',OLD.id),
       NULL::uuid,
       TG_TABLE_NAME,
       OLD.id::text
    );
  END IF;

  RETURN OLD; 
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
