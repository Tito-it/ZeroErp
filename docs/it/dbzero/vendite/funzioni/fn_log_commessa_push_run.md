{% include-markdown "it/dbzero/vendite/manual/fn_log_commessa_push_run.md" %}
# ⚙️ Funzione `fn_log_commessa_push_run`

```sql
CREATE FUNCTION fn_log_commessa_push_run(p_dry_run boolean, p_source_types text[], p_risultato jsonb, p_stato character varying, p_durata_ms integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_log_commessa_push_run(p_dry_run boolean DEFAULT false, p_source_types text[] DEFAULT NULL::text[], p_risultato jsonb DEFAULT '{}'::jsonb, p_stato character varying DEFAULT 'COMPLETATO'::character varying, p_durata_ms integer DEFAULT NULL::integer)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_id    vendite.commesse_push_log.id%TYPE;
    v_stato vendite.commesse_push_log.stato%TYPE;
BEGIN
    v_stato := upper(COALESCE(NULLIF(btrim(p_stato), ''), ''));

    IF v_stato = '' THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_log_commessa_push_run', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_stato', 'valore', p_stato), NULL::uuid, 'p_stato obbligatorio');
    END IF;

    IF v_stato NOT IN ('COMPLETATO', 'PARZIALE', 'ERRORE') THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_log_commessa_push_run', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_stato', 'valore', v_stato), NULL::uuid, concat('p_stato=', v_stato, ' (ammessi: COMPLETATO, PARZIALE, ERRORE)'));
    END IF;

    IF p_durata_ms IS NOT NULL AND p_durata_ms < 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_log_commessa_push_run', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_durata_ms', 'valore', p_durata_ms), NULL::uuid, 'p_durata_ms se fornito deve essere >= 0');
    END IF;

    INSERT INTO vendite.commesse_push_log (dry_run, source_types, risultato, stato, durata_ms)
    VALUES (COALESCE(p_dry_run, FALSE), p_source_types, COALESCE(p_risultato, '{}'::jsonb), v_stato, p_durata_ms)
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_log_commessa_push_run(p_dry_run boolean, p_source_types text[], p_risultato jsonb, p_stato character varying, p_durata_ms integer)
IS 'Registra run push commesse in commesse_push_log con validazioni stato/durata.';
```

---
{% include-markdown "signature-core.md" %}
