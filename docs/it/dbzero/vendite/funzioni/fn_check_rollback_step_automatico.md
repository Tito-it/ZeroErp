# ⚙️ Funzione `fn_check_rollback_step_automatico`

```sql
CREATE FUNCTION fn_check_rollback_step_automatico(p_tipo_lotto text, p_stato_doc_fiscale_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_check_rollback_step_automatico(p_tipo_lotto text, p_stato_doc_fiscale_id bigint, p_utility_id integer DEFAULT NULL::integer, p_tipo_doc_fiscale_id bigint DEFAULT NULL::bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT COALESCE(( SELECT (fp.auto_step_rollback AND (jsonb_array_length(s.processi) > 0) AND (NOT (EXISTS ( SELECT 1
                    FROM jsonb_array_elements(s.processi) t(elem)
                   WHERE (NOT (EXISTS ( SELECT 1
                            FROM (dbops.pipeline_task_registry r
                              JOIN dbops.domini_task d ON ((d.id = r.dominio_id)))
                           WHERE ((d.codice = 'FATTURAZIONE'::text) AND d.attivo AND (r.task_code = (t.elem ->> 'task'::text)) AND r.attivo AND (NOT r.distruttivo)))))))))
            FROM (vendite.fn_resolve_fatturazione_pipeline_step(fn_check_rollback_step_automatico.p_tipo_lotto, fn_check_rollback_step_automatico.p_stato_doc_fiscale_id, fn_check_rollback_step_automatico.p_utility_id, fn_check_rollback_step_automatico.p_tipo_doc_fiscale_id, true) s(pipeline_id, stato_doc_fiscale_id, descrizione, ordine, processi, utility_id, tipo_doc_fiscale_id, livello_match)
              JOIN vendite.fatturazione_pipeline fp ON ((fp.id = s.pipeline_id)))), false) AS "coalesce";
END

COMMENT ON FUNCTION vendite.fn_check_rollback_step_automatico(p_tipo_lotto text, p_stato_doc_fiscale_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint)
IS 'Il rollback dello step può partire da solo, al rilancio di un lotto in errore? Lo step si risolve come in vendite.fn_resolve_fatturazione_pipeline_step (stessi argomenti, stessa precedenza, p_rollback true). True solo se la sua pipeline ha auto_step_rollback acceso, il rollback ha almeno un task e ogni task è registrato e attivo in dbops.pipeline_task_registry, nel dominio FATTURAZIONE attivo, e non è distruttivo. Un task distruttivo, spento o sconosciuto dà false: il rollback resta eseguibile solo su richiesta esplicita. Step che non si risolve: false. Parametri invalidi: E_PARAMETRO_INVALIDO, dalla risoluzione dello step. Lo chiama il runner della pipeline prima del rollback automatico. STABLE, SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
