{% include-markdown "it/dbzero/vendite/manual/fn_resolve_attivita_pipeline_step.md" %}
# ⚙️ Funzione `fn_resolve_attivita_pipeline_step`

```sql
CREATE FUNCTION fn_resolve_attivita_pipeline_step(p_codice_step text, p_utility_id integer, p_sorgente_tipo_id bigint, p_rollback boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_attivita_pipeline_step(p_codice_step text, p_utility_id integer DEFAULT NULL::integer, p_sorgente_tipo_id bigint DEFAULT NULL::bigint, p_rollback boolean DEFAULT false)
 RETURNS TABLE(pipeline_id bigint, codice_step text, descrizione text, ordine smallint, processi jsonb, utility_id integer, sorgente_tipo_id bigint, livello_match text)
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Risolve la configurazione di uno step pipeline dominio
  --   attivita_fatturabili applicando fallback.
  --
  -- Regole precedenza:
  --   1) utility + sorgente
  --   2) utility
  --   3) sorgente
  --   4) fallback globale
  -- =========================================================

  IF p_codice_step IS NULL OR btrim(p_codice_step) = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_resolve_attivita_pipeline_step', 'E_GENERICO',
      jsonb_build_object('detail', 'p_codice_step obbligatorio'),
      NULL::uuid,
      'p_codice_step obbligatorio'
    );
  END IF;

  IF p_utility_id IS NOT NULL AND p_utility_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_resolve_attivita_pipeline_step', 'E_GENERICO',
      jsonb_build_object('detail', 'p_utility_id non valido'),
      NULL::uuid,
      'p_utility_id deve essere > 0'
    );
  END IF;

  IF p_sorgente_tipo_id IS NOT NULL AND p_sorgente_tipo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_resolve_attivita_pipeline_step', 'E_GENERICO',
      jsonb_build_object('detail', 'p_sorgente_tipo_id non valido'),
      NULL::uuid,
      'p_sorgente_tipo_id deve essere > 0'
    );
  END IF;

  RETURN QUERY
  SELECT
    ap.id AS pipeline_id,
    ap.codice_step,
    ap.descrizione,
    ap.ordine,
    CASE WHEN p_rollback THEN ap.rollback ELSE ap.processi END AS processi,
    ap.utility_id,
    ap.sorgente_tipo_id,
    CASE
      WHEN ap.utility_id IS NOT NULL AND ap.sorgente_tipo_id IS NOT NULL THEN 'UTILITY_SORGENTE'
      WHEN ap.utility_id IS NOT NULL AND ap.sorgente_tipo_id IS NULL THEN 'UTILITY'
      WHEN ap.utility_id IS NULL AND ap.sorgente_tipo_id IS NOT NULL THEN 'SORGENTE'
      ELSE 'FALLBACK'
    END AS livello_match
  FROM vendite.attivita_fatturabili_pipeline ap
  WHERE ap.attivo IS TRUE
    AND ap.codice_step = p_codice_step
    AND (ap.utility_id = p_utility_id OR ap.utility_id IS NULL)
    AND (ap.sorgente_tipo_id = p_sorgente_tipo_id OR ap.sorgente_tipo_id IS NULL)
  ORDER BY
    CASE
      WHEN ap.utility_id IS NOT NULL AND ap.sorgente_tipo_id IS NOT NULL THEN 4
      WHEN ap.utility_id IS NOT NULL AND ap.sorgente_tipo_id IS NULL THEN 3
      WHEN ap.utility_id IS NULL AND ap.sorgente_tipo_id IS NOT NULL THEN 2
      ELSE 1
    END DESC,
    ap.id ASC
  LIMIT 1;
END;
$function$

COMMENT ON FUNCTION vendite.fn_resolve_attivita_pipeline_step(p_codice_step text, p_utility_id integer, p_sorgente_tipo_id bigint, p_rollback boolean)
IS 'Risoluzione step pipeline attivita_fatturabili con fallback utility/sorgente e precedenza deterministica.';
```

---
{% include-markdown "signature-core.md" %}
