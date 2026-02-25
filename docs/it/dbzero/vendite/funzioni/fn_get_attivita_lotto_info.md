{% include-markdown "it/dbzero/vendite/manual/fn_get_attivita_lotto_info.md" %}
# ⚙️ Funzione `fn_get_attivita_lotto_info`

```sql
CREATE FUNCTION fn_get_attivita_lotto_info(p_lotto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_attivita_lotto_info(p_lotto_id bigint)
 RETURNS TABLE(stato_lotto text, stato_operativo text, is_in_esecuzione boolean)
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituire in un singolo round-trip lo stato runtime e
  --   lo stato operativo del lotto attivita, includendo il flag
  --   booleano di esecuzione.
  --
  -- Regole:
  --   - p_lotto_id obbligatorio e > 0
  --   - se il lotto non esiste: ritorna 0 righe
  -- =========================================================
  IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_attivita_lotto_info', 'E_GENERICO',
      jsonb_build_object(
        'scope', 'ATTIVITA_FATTURABILI',
        'severity', 'C',
        'code', 'E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', NULL,
        'context', jsonb_build_object('detail', 'lotto_id obbligatorio')
      ),
      NULL::uuid,
      'lotto_id obbligatorio e > 0'
    );
  END IF;

  RETURN QUERY
  SELECT
    l.stato_lotto,
    l.stato_operativo,
    (l.stato_lotto = 'IN_ESECUZIONE') AS is_in_esecuzione
  FROM vendite.attivita_fatturabili_lotti l
  WHERE l.id = p_lotto_id;
END
$function$

COMMENT ON FUNCTION vendite.fn_get_attivita_lotto_info(p_lotto_id bigint)
IS 'Ritorna stato_lotto, stato_operativo e flag is_in_esecuzione per il lotto attivita.';
```

---
{% include-markdown "signature-core.md" %}
