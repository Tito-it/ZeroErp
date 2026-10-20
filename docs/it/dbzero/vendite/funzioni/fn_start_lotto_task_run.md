{% include-markdown "it/dbzero/vendite/manual/fn_start_lotto_task_run.md" %}
# ⚙️ Funzione `fn_start_lotto_task_run`

```sql
CREATE FUNCTION fn_start_lotto_task_run(p_lotto_id bigint, p_pipeline_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying, p_fase character varying, p_meta jsonb, p_correlation_id uuid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_start_lotto_task_run(p_lotto_id bigint, p_pipeline_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying, p_fase character varying DEFAULT NULL::character varying, p_meta jsonb DEFAULT '{}'::jsonb, p_correlation_id uuid DEFAULT NULL::uuid)
 RETURNS TABLE(task_run_id bigint, tentativo smallint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tentativo vendite.fatturazione_lotti_task_runs.tentativo%TYPE;
BEGIN
    -- Scopo: apre un tentativo di task sul lotto (stato IN_ESECUZIONE),
    --        numerandolo, e — dal 2026-08-22 — legandolo al GIRO che lo ha
    --        prodotto. Il numero di tentativo si conta per (lotto, task,
    --        stato_doc_fiscale): e' la chiave con cui la pipeline decide se
    --        riprendere o saltare.

    -- ── I tre guard di chiamata ──────────────────────────────────────────
    --   ⚠️ Erano `E_PARAMETRO_INVALIDO` con dentro «p_lotto_id obbligatorio e
    --   > 0» come frase per l'operatore. Il codice e' un debito dichiarato
    --   (D11 di brief-db-be-classe-codici-errore: split rimandato) e non e' la
    --   sede del nuovo: qui il dato lo produce SOLO un chiamante rotto, quindi
    --   la classe e' TECNICO e il codice e' il gemello vendite di
    --   E_PAGAMENTI_CHIAMATA_NON_VALIDA (2026-08-21). Il messaggio nomina il
    --   parametro DI PROPOSITO: il suo lettore e' chi ha scritto la chiamata.
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_start_lotto_task_run', 'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid,
            'vendite.fn_start_lotto_task_run',
            'p_lotto_id obbligatorio e maggiore di zero');
    END IF;

    IF p_pipeline_id IS NULL OR p_pipeline_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_start_lotto_task_run', 'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_pipeline_id', 'valore', p_pipeline_id),
            NULL::uuid,
            'vendite.fn_start_lotto_task_run',
            'p_pipeline_id obbligatorio e maggiore di zero');
    END IF;

    IF p_task_code IS NULL OR btrim(p_task_code) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_start_lotto_task_run', 'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_task_code', 'valore', p_task_code),
            NULL::uuid,
            'vendite.fn_start_lotto_task_run',
            'p_task_code obbligatorio');
    END IF;

    -- Il tentativo successivo per questa terna. `IS NOT DISTINCT FROM` perche'
    -- lo stato documento e' nullable: con `=` una terna a stato NULL non si
    -- ritroverebbe mai e ogni corsa ripartirebbe da 1.
    SELECT COALESCE(MAX(r.tentativo), 0)::SMALLINT + 1
      INTO v_tentativo
      FROM vendite.fatturazione_lotti_task_runs r
     WHERE r.lotto_id = p_lotto_id
       AND r.task_code = p_task_code
       AND r.stato_doc_fiscale_id IS NOT DISTINCT FROM p_stato_doc_fiscale_id::INTEGER;

    RETURN QUERY
    INSERT INTO vendite.fatturazione_lotti_task_runs AS r (
        lotto_id, pipeline_id, stato_doc_fiscale_id, task_code, fase, tentativo,
        task_stato, started_at, ended_at, error_code, error_message, meta,
        correlation_id,
        attivo, data_insert, user_insert, data_update, user_update
    ) VALUES (
        -- ⭐ R-1 (24-08-2026): `started_at` all'orologio della scrittura.
        --    ⛔ E la chiusura DEVE stare sullo stesso orologio: con
        --    `ended_at = now()` un tentativo aperto e chiuso nella
        --    stessa transazione finirebbe con la fine PRIMA
        --    dell'inizio, e chk_fatt_lotti_task_runs_timestamps lo
        --    rifiuterebbe. Vedi fn_set_runtime_task_run_esito, qui
        --    sotto: i due si spostano insieme o non si spostano.
        --    ⚠️ I `now()` in coda sono i campi di AUDIT e restano.
        p_lotto_id, p_pipeline_id, p_stato_doc_fiscale_id::INTEGER, p_task_code, p_fase, v_tentativo,
        'IN_ESECUZIONE', clock_timestamp(), NULL, NULL, NULL, COALESCE(p_meta, '{}'::JSONB),
        p_correlation_id,
        TRUE, now(), current_user, now(), current_user
    ) RETURNING r.id, r.tentativo;
END;
$function$

COMMENT ON FUNCTION vendite.fn_start_lotto_task_run(p_lotto_id bigint, p_pipeline_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying, p_fase character varying, p_meta jsonb, p_correlation_id uuid)
IS 'Apre un task run del lotto in stato IN_ESECUZIONE e incrementa il tentativo. rev 2026-08-22: ⭐ prende p_correlation_id — l''identita'' del GIRO (D-7 di brief-db-event-log-scope-e-riga-parlante), generata dal runner e condivisa con gli eventi e con la riga di commesse_push_log. Nullable: le righe anteriori a BE-2 non hanno un giro e un uuid inventato sarebbe un filo che non lega niente. ⛔ La firma vecchia a sei parametri e'' stata DROPpata nello stesso changeSet: un settimo parametro con DEFAULT non sostituisce, affianca — e una chiamata a sei argomenti soddisferebbe entrambe («la funzione non e'' unica»). ⚠️ p_stato_doc_fiscale_id resta bigint e non e'' ancorato con %TYPE: in tabella la colonna e'' integer, e bigint -> integer non e'' implicito. I tre guard di chiamata sono passati da E_PARAMETRO_INVALIDO a E_VENDITE_CHIAMATA_NON_VALIDA (TECNICO): li'' il valore lo produce solo un chiamante rotto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
