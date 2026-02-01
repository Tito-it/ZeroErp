{% include-markdown "it/dbzero/vendite/manual/pr_run_lotto_pipeline.md" %}
# ⚙️ Procedura `pr_run_lotto_pipeline`

```sql
CREATE PROCEDURE pr_run_lotto_pipeline(IN p_lotto_id bigint, IN p_competenza_mese date, IN p_tipo_doc_fiscale_id bigint, IN p_utility_id integer, IN p_billing_account_id bigint, IN p_lock_batch_id uuid, IN p_meta jsonb, IN p_dry_run boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE PROCEDURE vendite.pr_run_lotto_pipeline(IN p_lotto_id bigint DEFAULT NULL::bigint, IN p_competenza_mese date DEFAULT NULL::date, IN p_tipo_doc_fiscale_id bigint DEFAULT NULL::bigint, IN p_utility_id integer DEFAULT NULL::integer, IN p_billing_account_id bigint DEFAULT NULL::bigint, IN p_lock_batch_id uuid DEFAULT NULL::uuid, IN p_meta jsonb DEFAULT NULL::jsonb, IN p_dry_run boolean DEFAULT false)
 LANGUAGE plpgsql
AS $procedure$
DECLARE
  v_step record;
  v_lotto_id vendite.fatturazione_lotti.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Orchestrazione pipeline lotto: imposta stato job,
  --   aggiorna stato_doc_fiscale_id per step e invoca i task.
  --
  -- Regole:
  --   - stato_lotto: IN_ESECUZIONE -> COMPLETATO/ERRORE
  --   - ordine step determinato da config.stati_doc_fiscale.ordine
  -- =========================================================

  v_lotto_id := vendite.fn_get_or_create_lotto(
    p_lotto_id,
    p_competenza_mese,
    p_tipo_doc_fiscale_id,
    p_utility_id,
    p_billing_account_id,
    p_lock_batch_id,
    p_meta
  );

  -- Imposta stato lotto in esecuzione
  PERFORM vendite.fn_set_fatturazione_lotto_stato(
    v_lotto_id, 'IN_ESECUZIONE', 'Avvio pipeline'
  );

  FOR v_step IN
    SELECT fp.stato_doc_fiscale_id, fp.descrizione, sd.ordine
      FROM vendite.fatturazione_pipeline fp
      JOIN config.stati_doc_fiscale sd
        ON sd.id = fp.stato_doc_fiscale_id
     WHERE fp.attivo IS TRUE
       AND COALESCE(sd.applica_lotto, false) IS TRUE
     ORDER BY sd.ordine
  LOOP
    -- Aggiorna stato lotto allo step corrente
    UPDATE vendite.fatturazione_lotti
       SET stato_doc_fiscale_id = v_step.stato_doc_fiscale_id,
           data_update = now(),
           user_update = current_user
     WHERE id = v_lotto_id;

    -- Log fase (info)
    PERFORM vendite.fn_log_pipeline_fase(
      v_lotto_id,
      v_step.stato_doc_fiscale_id,
      COALESCE(v_step.descrizione, 'Esecuzione step'),
      'I',
      NULL,
      jsonb_build_object('ordine', v_step.ordine, 'dry_run', p_dry_run)
    );

    -- Esecuzione task dello step
    PERFORM vendite.fn_execute_pipeline_step(
      v_lotto_id,
      v_step.stato_doc_fiscale_id,
      false,
      p_dry_run
    );
  END LOOP;

  -- Stato lotto completato
  PERFORM vendite.fn_set_fatturazione_lotto_stato(
    v_lotto_id, 'COMPLETATO', 'Pipeline completata'
  );
EXCEPTION
  WHEN OTHERS THEN
    PERFORM vendite.fn_set_fatturazione_lotto_stato(
      v_lotto_id, 'ERRORE', 'Errore pipeline'
    );
    RAISE;
END
$procedure$
```

---
{% include-markdown "signature-core.md" %}
