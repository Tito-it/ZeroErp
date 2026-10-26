{% include-markdown "it/dbzero/vendite/manual/fn_list_fatturazione_pipeline_steps.md" %}
# ⚙️ Funzione `fn_list_fatturazione_pipeline_steps`

```sql
CREATE FUNCTION fn_list_fatturazione_pipeline_steps(p_tipo_lotto text, p_utility_id integer, p_tipo_doc_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_fatturazione_pipeline_steps(p_tipo_lotto text, p_utility_id integer DEFAULT NULL::integer, p_tipo_doc_fiscale_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(stato_doc_fiscale_id bigint, descrizione text, ordine smallint)
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF p_tipo_lotto IS NULL OR btrim(p_tipo_lotto) = '' THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_list_fatturazione_pipeline_steps', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_lotto', 'valore', p_tipo_lotto), NULL::uuid, 'p_tipo_lotto obbligatorio');
    END IF;
    IF p_utility_id IS NOT NULL AND p_utility_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_list_fatturazione_pipeline_steps', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_utility_id', 'valore', p_utility_id), NULL::uuid, 'p_utility_id se fornito deve essere > 0');
    END IF;
    IF p_tipo_doc_fiscale_id IS NOT NULL AND p_tipo_doc_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_list_fatturazione_pipeline_steps', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_doc_fiscale_id', 'valore', p_tipo_doc_fiscale_id), NULL::uuid, 'p_tipo_doc_fiscale_id se fornito deve essere > 0');
    END IF;

    RETURN QUERY
    SELECT sd.id, COALESCE(rs.descrizione, sd.descrizione), sd.ordine
      FROM config.stati_doc_fiscale sd
      JOIN LATERAL vendite.fn_resolve_fatturazione_pipeline_step(p_tipo_lotto, sd.id, p_utility_id, p_tipo_doc_fiscale_id, FALSE) rs ON TRUE
     WHERE COALESCE(sd.applica_lotto, FALSE) IS TRUE
     ORDER BY sd.ordine;
END;
$function$

COMMENT ON FUNCTION vendite.fn_list_fatturazione_pipeline_steps(p_tipo_lotto text, p_utility_id integer, p_tipo_doc_fiscale_id bigint)
IS 'Step pipeline fatturazione risolti per tipo_lotto con fallback utility/tipo_doc.';
```

</div>

---
{% include-markdown "signature-core.md" %}
