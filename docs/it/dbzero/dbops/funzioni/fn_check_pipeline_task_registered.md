{% include-markdown "it/dbzero/dbops/manual/fn_check_pipeline_task_registered.md" %}
# ⚙️ Funzione `fn_check_pipeline_task_registered`

```sql
CREATE FUNCTION fn_check_pipeline_task_registered(p_dominio_id bigint, p_task_code text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_check_pipeline_task_registered(p_dominio_id bigint, p_task_code text)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
-- Scopo: verificare che il task sia registrato e attivo, nel suo
--   dominio attivo. Risponde TRUE o solleva.
DECLARE
    v_chi dbops.error_log.function_name%TYPE := 'dbops.fn_check_pipeline_task_registered';
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

    IF NOT EXISTS (
        SELECT 1
          FROM dbops.pipeline_task_registry r
          JOIN dbops.domini_task d ON d.id = r.dominio_id
         WHERE r.dominio_id = p_dominio_id
           AND r.task_code  = p_task_code
           AND r.attivo IS TRUE
           AND d.attivo IS TRUE)
    THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_PIPELINE_TASK_HANDLER_NOT_FOUND',
            jsonb_build_object('detail', 'task non registrato o non attivo',
                               'dominio_id', p_dominio_id,
                               'task_code', p_task_code),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    RETURN TRUE;
END;
$function$

COMMENT ON FUNCTION dbops.fn_check_pipeline_task_registered(p_dominio_id bigint, p_task_code text)
IS 'Verifica che il task p_task_code sia registrato e attivo in dbops.pipeline_task_registry, nel dominio p_dominio_id attivo. Risponde TRUE; altrimenti solleva E_PIPELINE_TASK_HANDLER_NOT_FOUND, con dominio e task nel contesto: un task non registrato e'' un difetto di configurazione. Dominio o codice mancanti escono con E_DBOPS_CHIAMATA_NON_VALIDA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
