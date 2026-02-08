{% include-markdown "it/dbzero/vendite/manual/fn_list_fatturazione_pipeline_steps.md" %}
# ⚙️ Funzione `fn_list_fatturazione_pipeline_steps`

```sql
CREATE FUNCTION fn_list_fatturazione_pipeline_steps(p_tipo_lotto text, p_utility_id integer, p_tipo_doc_fiscale_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_fatturazione_pipeline_steps(p_tipo_lotto text, p_utility_id integer DEFAULT NULL::integer, p_tipo_doc_fiscale_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(stato_doc_fiscale_id bigint, descrizione text, ordine smallint)
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Elenca gli step pipeline risolti (uno per stato lotto)
  --   applicando la stessa precedenza di fallback.
  -- =========================================================

  IF p_tipo_lotto IS NULL OR btrim(p_tipo_lotto) = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_fatturazione_pipeline_steps', 'E_GENERICO',
      jsonb_build_object('detail', 'p_tipo_lotto obbligatorio'),
      NULL::uuid,
      'p_tipo_lotto obbligatorio'
    );
  END IF;

  RETURN QUERY
  SELECT
    sd.id AS stato_doc_fiscale_id,
    COALESCE(rs.descrizione, sd.descrizione) AS descrizione,
    sd.ordine
  FROM config.stati_doc_fiscale sd
  JOIN LATERAL vendite.fn_resolve_fatturazione_pipeline_step(
    p_tipo_lotto,
    sd.id,
    p_utility_id,
    p_tipo_doc_fiscale_id,
    false
  ) rs ON TRUE
  WHERE COALESCE(sd.applica_lotto, false) IS TRUE
  ORDER BY sd.ordine;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
