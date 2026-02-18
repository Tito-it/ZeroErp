# ⚙️ Funzione `trgfn_stati_doc_fiscale_chiude_lotto_guard`

```sql
CREATE FUNCTION trgfn_stati_doc_fiscale_chiude_lotto_guard()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.trgfn_stati_doc_fiscale_chiude_lotto_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_cnt_true integer;
BEGIN
  -- Scopo:
  --   Garantire cardinalita' esatta del flag chiude_lotto:
  --   deve esistere sempre e solo una riga con chiude_lotto=true.
  SELECT COUNT(*)
    INTO v_cnt_true
    FROM config.stati_doc_fiscale
   WHERE chiude_lotto IS TRUE;

  IF v_cnt_true <> 1 THEN
    PERFORM script.fn_log_and_raise_error(
      'config', TG_NAME, 'E_GENERICO',
      jsonb_build_object(
        'scope', 'LOTTO',
        'severity', 'C',
        'code', 'E_CHIUDE_LOTTO_SINGLETON',
        'lotto_id', NULL,
        'fattura_id', NULL,
        'context', jsonb_build_object(
          'detail', 'chiude_lotto deve avere una sola riga TRUE',
          'current_true_count', v_cnt_true
        )
      ),
      NULL::uuid,
      'chiude_lotto deve avere una sola riga TRUE'
    );
  END IF;
  RETURN NULL;
END;
$function$

COMMENT ON FUNCTION config.trgfn_stati_doc_fiscale_chiude_lotto_guard()
IS 'Guard cardinalita'' chiude_lotto: deve esistere sempre e solo una riga TRUE su config.stati_doc_fiscale.';
```

---
{% include-markdown "signature-core.md" %}
