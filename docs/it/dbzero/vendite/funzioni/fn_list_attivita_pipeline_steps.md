{% include-markdown "it/dbzero/vendite/manual/fn_list_attivita_pipeline_steps.md" %}
# ⚙️ Funzione `fn_list_attivita_pipeline_steps`

```sql
CREATE FUNCTION fn_list_attivita_pipeline_steps(p_utility_id integer, p_sorgente_tipo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_attivita_pipeline_steps(p_utility_id integer DEFAULT NULL::integer, p_sorgente_tipo_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(codice_step text, descrizione text, ordine smallint)
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Elenca gli step pipeline dominio attivita_fatturabili
  --   risolti con fallback utility/sorgente.
  -- =========================================================

  IF p_utility_id IS NOT NULL AND p_utility_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_list_attivita_pipeline_steps', 'E_GENERICO',
      jsonb_build_object('detail', 'p_utility_id non valido'),
      NULL::uuid,
      'p_utility_id deve essere > 0'
    );
  END IF;

  IF p_sorgente_tipo_id IS NOT NULL AND p_sorgente_tipo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_list_attivita_pipeline_steps', 'E_GENERICO',
      jsonb_build_object('detail', 'p_sorgente_tipo_id non valido'),
      NULL::uuid,
      'p_sorgente_tipo_id deve essere > 0'
    );
  END IF;

  RETURN QUERY
  SELECT
    rs.codice_step,
    rs.descrizione,
    rs.ordine
  FROM (
    SELECT DISTINCT ap.codice_step
    FROM vendite.attivita_fatturabili_pipeline ap
    WHERE ap.attivo IS TRUE
  ) AS s
  JOIN LATERAL vendite.fn_resolve_attivita_pipeline_step(
    p_codice_step => s.codice_step,
    p_utility_id => p_utility_id,
    p_sorgente_tipo_id => p_sorgente_tipo_id,
    p_rollback => false
  ) rs ON TRUE
  ORDER BY rs.ordine, rs.codice_step;
END;
$function$

COMMENT ON FUNCTION vendite.fn_list_attivita_pipeline_steps(p_utility_id integer, p_sorgente_tipo_id bigint)
IS 'Lista step pipeline attivita_fatturabili risolti con fallback utility/sorgente.';
```

---
{% include-markdown "signature-core.md" %}
