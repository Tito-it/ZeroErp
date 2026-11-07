{% include-markdown "it/dbzero/dbops/manual/fn_get_pipeline_task_implementation.md" %}
# ⚙️ Funzione `fn_get_pipeline_task_implementation`

```sql
CREATE FUNCTION fn_get_pipeline_task_implementation(p_dominio_id bigint, p_task_code text, p_implementation_key text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_get_pipeline_task_implementation(p_dominio_id bigint, p_task_code text, p_implementation_key text DEFAULT NULL::text)
 RETURNS TABLE(handler_code text, implementation_key text, task_registry_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: risolvere l'implementazione di un task. Con una variante
--   chiesta, quella o niente; senza, il default o un errore.
DECLARE
    v_chi dbops.error_log.function_name%TYPE := 'dbops.fn_get_pipeline_task_implementation';
BEGIN
    IF p_dominio_id IS NULL OR p_dominio_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_DBOPS_CHIAMATA_NON_VALIDA',
            jsonb_build_object('campo', 'p_dominio_id', 'dominio_id', p_dominio_id),
            NULL::uuid,
            v_chi, 'manca il dominio del task');
    END IF;

    IF p_task_code IS NULL OR btrim(p_task_code) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_DBOPS_CHIAMATA_NON_VALIDA',
            jsonb_build_object('campo', 'p_task_code'),
            NULL::uuid,
            v_chi, 'manca il codice del task');
    END IF;

    PERFORM dbops.fn_check_pipeline_task_registered(p_dominio_id, p_task_code);

    -- 1) Una variante chiesta: quella, o nessuna riga.
    IF p_implementation_key IS NOT NULL AND btrim(p_implementation_key) <> '' THEN
        RETURN QUERY
        SELECT i.handler_code, i.implementation_key, i.task_registry_id
          FROM dbops.pipeline_task_registry r
          JOIN dbops.pipeline_task_registry_impl i ON i.task_registry_id = r.id
         WHERE r.dominio_id = p_dominio_id
           AND r.task_code = p_task_code
           AND r.attivo IS TRUE
           AND i.attivo IS TRUE
           AND i.implementation_key = p_implementation_key
         ORDER BY i.id
         LIMIT 1;
        RETURN;
    END IF;

    -- 2) Nessuna variante: il default.
    RETURN QUERY
    SELECT i.handler_code, i.implementation_key, i.task_registry_id
      FROM dbops.pipeline_task_registry r
      JOIN dbops.pipeline_task_registry_impl i ON i.task_registry_id = r.id
     WHERE r.dominio_id = p_dominio_id
       AND r.task_code = p_task_code
       AND r.attivo IS TRUE
       AND i.attivo IS TRUE
       AND i.is_default IS TRUE
     ORDER BY i.id
     LIMIT 1;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_PIPELINE_TASK_HANDLER_NOT_FOUND',
            jsonb_build_object('detail', 'nessuna implementazione di default attiva',
                               'dominio_id', p_dominio_id,
                               'task_code', p_task_code),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;
END;
$function$

COMMENT ON FUNCTION dbops.fn_get_pipeline_task_implementation(p_dominio_id bigint, p_task_code text, p_implementation_key text)
IS 'Risolve l''implementazione di un task di pipeline registrato (il controllo lo fa dbops.fn_check_pipeline_task_registered). Con una variante chiesta (p_implementation_key) restituisce quella, se e'' attiva, o nessuna riga: non ripiega sul default, e chi chiama decide (il backend solleva E_PIPELINE_TASK_HANDLER_NOT_FOUND). Senza variante restituisce l''implementazione di default attiva, e se non c''e'' solleva E_PIPELINE_TASK_HANDLER_NOT_FOUND. Dominio o codice mancanti escono con E_DBOPS_CHIAMATA_NON_VALIDA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
