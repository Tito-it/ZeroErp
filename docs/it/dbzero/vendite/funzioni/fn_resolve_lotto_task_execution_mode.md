{% include-markdown "it/dbzero/vendite/manual/fn_resolve_lotto_task_execution_mode.md" %}
# ⚙️ Funzione `fn_resolve_lotto_task_execution_mode`

```sql
CREATE FUNCTION fn_resolve_lotto_task_execution_mode(p_lotto_id bigint, p_pipeline_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_lotto_task_execution_mode(p_lotto_id bigint, p_pipeline_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying)
 RETURNS TABLE(execution_mode text, annullabile boolean, resume_mode character varying, last_task_stato character varying, last_tentativo smallint, policy_meta jsonb, run_meta jsonb)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_policy   vendite.fatturazione_pipeline_task_policy%ROWTYPE;
    v_last_run vendite.fatturazione_lotti_task_runs%ROWTYPE;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_resolve_lotto_task_execution_mode', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;
    IF p_pipeline_id IS NULL OR p_pipeline_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_resolve_lotto_task_execution_mode', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_pipeline_id', 'valore', p_pipeline_id), NULL::uuid, 'p_pipeline_id obbligatorio e > 0');
    END IF;
    IF p_task_code IS NULL OR btrim(p_task_code) = '' THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_resolve_lotto_task_execution_mode', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_task_code', 'valore', p_task_code), NULL::uuid, 'p_task_code obbligatorio');
    END IF;

    SELECT p.* INTO v_policy FROM vendite.fatturazione_pipeline_task_policy p
     WHERE p.pipeline_id = p_pipeline_id AND p.task_code = p_task_code AND p.attivo IS TRUE;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_resolve_lotto_task_execution_mode', 'E_CONFIG_MANCANTE',
            jsonb_build_object('pipeline_id', p_pipeline_id, 'task_code', p_task_code), NULL::uuid,
            concat('policy task pipeline:', p_pipeline_id, ' task:', p_task_code));
    END IF;

    SELECT r.* INTO v_last_run FROM vendite.fatturazione_lotti_task_runs r
     WHERE r.lotto_id = p_lotto_id AND r.task_code = p_task_code
       AND r.stato_doc_fiscale_id IS NOT DISTINCT FROM p_stato_doc_fiscale_id
     ORDER BY r.tentativo DESC, r.id DESC LIMIT 1;

    IF NOT FOUND THEN
        RETURN QUERY SELECT 'RUN'::TEXT, v_policy.annullabile, v_policy.resume_mode,
            NULL::CHARACTER VARYING, NULL::SMALLINT, COALESCE(v_policy.meta, '{}'::JSONB), '{}'::JSONB;
        RETURN;
    END IF;

    RETURN QUERY SELECT
        CASE WHEN v_last_run.task_stato = 'COMPLETATO' THEN 'SKIP'
             WHEN v_last_run.task_stato IN ('IN_ESECUZIONE', 'ERRORE') THEN
                 -- rev 2026-09-12: RESUME_STEP e' RITIRATO (00_schema/20260912-32).
                 --   Era trattato identico a RESUME_TASK e nessuno lo implementava;
                 --   la «ripresa a livello di step» vive nell'orchestratore.
                 CASE WHEN v_policy.resume_mode = 'RESUME_TASK' THEN 'RESUME' ELSE 'RESET_REQUIRED' END
             WHEN v_last_run.task_stato = 'ANNULLATO' THEN 'RUN' ELSE 'RUN' END::TEXT,
        v_policy.annullabile, v_policy.resume_mode, v_last_run.task_stato,
        v_last_run.tentativo, COALESCE(v_policy.meta, '{}'::JSONB), COALESCE(v_last_run.meta, '{}'::JSONB);
END;
$function$

COMMENT ON FUNCTION vendite.fn_resolve_lotto_task_execution_mode(p_lotto_id bigint, p_pipeline_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying)
IS 'Decide PER TASK come il runner deve trattare un task dello step al (ri)lancio di un lotto, leggendo la policy attiva e l''ULTIMA corsa di quel task: nessuna corsa → RUN; COMPLETATO → SKIP; IN_ESECUZIONE/ERRORE → RESUME se resume_mode = RESUME_TASK, altrimenti RESET_REQUIRED; ANNULLATO → RUN. ⚠️ Risponde alla domanda che gli si fa, per task: la domanda «qualcosa a monte e'' stato eseguito in QUESTO giro?» la sa solo l''orchestratore, ed e'' li'' che vive la regola di catena (a valle di un task eseguito nessun task si salta — PipelineStepExecutor, 12-09-2026). Rev 2026-09-12: RESUME_STEP ritirato dal vocabolario (brief-db-rilancio-step-non-rivede-le-proprie-commesse §10.3).';
```

</div>

---
{% include-markdown "signature-core.md" %}
