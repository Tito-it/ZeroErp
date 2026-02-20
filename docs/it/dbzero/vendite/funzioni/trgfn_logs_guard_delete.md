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
  v_allow_logs text;
  v_allow_reset text;
  v_scope text;
  v_lotto_id vendite.fatturazione_lotti_log.lotto_id%TYPE;
  v_fattura_id vendite.fatture_log.fattura_id%TYPE;
BEGIN
  v_allow_logs := current_setting('zeroerp.maintenance_allow_delete_logs', true);
  v_allow_reset := current_setting('zeroerp.maintenance_reset_lotto_draft', true);

  IF COALESCE(lower(v_allow_logs), 'off') NOT IN ('on','true','1')
     AND COALESCE(lower(v_allow_reset), 'off') NOT IN ('on','true','1') THEN
    v_scope := CASE
      WHEN TG_TABLE_NAME = 'fatture_log' THEN 'FATTURA'
      ELSE 'LOTTO'
    END;

    IF TG_TABLE_NAME = 'fatture_log' THEN
      v_fattura_id := OLD.fattura_id;
      v_lotto_id := NULL;
    ELSE
      v_lotto_id := OLD.lotto_id;
      v_fattura_id := NULL;
    END IF;

    PERFORM script.fn_log_and_raise_error(
      'vendite',
      TG_NAME,
      'E_GENERICO',
      jsonb_build_object(
        'scope', v_scope,
        'severity', 'C',
        'code', 'E_GENERICO',
        'lotto_id', v_lotto_id,
        'fattura_id', v_fattura_id,
        'context', jsonb_build_object(
          'detail', 'DELETE su log non consentito senza GUC',
          'table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME
        )
      ),
      NULL::uuid,
      'DELETE su log non consentito senza GUC'
    );
  END IF;

  RETURN OLD;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_logs_guard_delete()
IS 'Blocca DELETE su fatture_log/fatturazione_lotti_log salvo GUC zeroerp.maintenance_allow_delete_logs=on (o GUC reset tecnico).';
```

---
{% include-markdown "signature-core.md" %}
