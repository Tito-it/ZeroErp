{% include-markdown "it/dbzero/vendite/manual/fn_resolve_fatturazione_pipeline_step.md" %}
# ⚙️ Funzione `fn_resolve_fatturazione_pipeline_step`

```sql
CREATE FUNCTION fn_resolve_fatturazione_pipeline_step(p_tipo_lotto text, p_stato_doc_fiscale_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_rollback boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_fatturazione_pipeline_step(p_tipo_lotto text, p_stato_doc_fiscale_id bigint, p_utility_id integer DEFAULT NULL::integer, p_tipo_doc_fiscale_id bigint DEFAULT NULL::bigint, p_rollback boolean DEFAULT false)
 RETURNS TABLE(pipeline_id bigint, stato_doc_fiscale_id bigint, descrizione text, ordine smallint, processi jsonb, utility_id integer, tipo_doc_fiscale_id bigint, livello_match text)
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Risolve una configurazione pipeline per step applicando
  --   fallback su utility/tipo_doc_fiscale.
  --
  -- Regole precedenza:
  --   1) utility + tipo_doc_fiscale
  --   2) utility
  --   3) tipo_doc_fiscale
  --   4) fallback globale (entrambi NULL)
  -- =========================================================

  IF p_tipo_lotto IS NULL OR btrim(p_tipo_lotto) = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_resolve_fatturazione_pipeline_step', 'E_GENERICO',
      jsonb_build_object('detail', 'p_tipo_lotto obbligatorio'),
      NULL::uuid,
      'p_tipo_lotto obbligatorio'
    );
  END IF;


  IF p_stato_doc_fiscale_id IS NULL OR p_stato_doc_fiscale_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_resolve_fatturazione_pipeline_step', 'E_GENERICO',
      jsonb_build_object('detail', 'p_stato_doc_fiscale_id obbligatorio'),
      NULL::uuid,
      'p_stato_doc_fiscale_id obbligatorio'
    );
  END IF;

  RETURN QUERY
  SELECT
    fp.id AS pipeline_id,
    fp.stato_doc_fiscale_id,
    fp.descrizione,
    sd.ordine,
    CASE WHEN p_rollback THEN fp.rollback ELSE fp.processi END AS processi,
    fp.utility_id,
    fp.tipo_doc_fiscale_id,
    CASE
      WHEN fp.utility_id IS NOT NULL AND fp.tipo_doc_fiscale_id IS NOT NULL THEN 'UTILITY_TIPO_DOC'
      WHEN fp.utility_id IS NOT NULL AND fp.tipo_doc_fiscale_id IS NULL THEN 'UTILITY'
      WHEN fp.utility_id IS NULL AND fp.tipo_doc_fiscale_id IS NOT NULL THEN 'TIPO_DOC'
      ELSE 'FALLBACK'
    END AS livello_match
  FROM vendite.fatturazione_pipeline fp
  JOIN config.stati_doc_fiscale sd
    ON sd.id = fp.stato_doc_fiscale_id
  WHERE fp.attivo IS TRUE
    AND fp.tipo_lotto = p_tipo_lotto
    AND fp.stato_doc_fiscale_id = p_stato_doc_fiscale_id
    AND (fp.utility_id = p_utility_id OR fp.utility_id IS NULL)
    AND (fp.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id OR fp.tipo_doc_fiscale_id IS NULL)
  ORDER BY
    CASE
      WHEN fp.utility_id IS NOT NULL AND fp.tipo_doc_fiscale_id IS NOT NULL THEN 4
      WHEN fp.utility_id IS NOT NULL AND fp.tipo_doc_fiscale_id IS NULL THEN 3
      WHEN fp.utility_id IS NULL AND fp.tipo_doc_fiscale_id IS NOT NULL THEN 2
      ELSE 1
    END DESC,
    fp.id ASC
  LIMIT 1;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
