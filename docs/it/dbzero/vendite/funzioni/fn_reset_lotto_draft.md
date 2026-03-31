{% include-markdown "it/dbzero/vendite/manual/fn_reset_lotto_draft.md" %}
# ⚙️ Funzione `fn_reset_lotto_draft`

```sql
CREATE FUNCTION fn_reset_lotto_draft(p_lotto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_reset_lotto_draft(p_lotto_id bigint)
 RETURNS TABLE(updated_lotti integer, updated_attivita integer, deleted_fatture integer, deleted_righe integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tipo_lotto           vendite.fatturazione_lotti.tipo_lotto%TYPE;
    v_stato_doc_fiscale_id vendite.fatturazione_lotti.stato_doc_fiscale_id%TYPE;
    v_lock_batch_id        vendite.fatturazione_lotti.lock_batch_id%TYPE;
    v_draft_id             config.stati_doc_fiscale.id%TYPE;
    v_annullata_id         config.stati_doc_fiscale.id%TYPE;
    v_fatture_ids          BIGINT[];
    v_bad_fatture          INTEGER := 0;
    v_updated_lotti        INTEGER := 0;
    v_updated_attivita     INTEGER := 0;
    v_deleted_fatture      INTEGER := 0;
    v_deleted_righe        INTEGER := 0;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_lotto_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    SELECT fl.tipo_lotto, fl.stato_doc_fiscale_id, fl.lock_batch_id
      INTO v_tipo_lotto, v_stato_doc_fiscale_id, v_lock_batch_id
      FROM vendite.fatturazione_lotti fl WHERE fl.id = p_lotto_id;

    IF v_tipo_lotto IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_lotto_draft', 'E_VALORE_MANCANTE',
            jsonb_build_object('lotto_id', p_lotto_id), NULL::uuid, concat('lotto_id ', p_lotto_id));
    END IF;

    IF v_tipo_lotto <> 'MASSIVO' THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_lotto_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'tipo_lotto', 'valore', v_tipo_lotto, 'lotto_id', p_lotto_id),
            NULL::uuid, concat('rollback solo per MASSIVO, tipo=', v_tipo_lotto));
    END IF;

    SELECT s.id INTO v_draft_id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE LIMIT 1;
    IF v_draft_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_lotto_draft', 'E_CONFIG_MANCANTE',
            jsonb_build_object('codice_interno', 'DRAFT'), NULL::uuid, 'stato DRAFT non configurato');
    END IF;

    SELECT s.id INTO v_annullata_id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'ANNULLATA' AND s.attivo IS TRUE LIMIT 1;
    IF v_annullata_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_lotto_draft', 'E_CONFIG_MANCANTE',
            jsonb_build_object('codice_interno', 'ANNULLATA'), NULL::uuid, 'stato ANNULLATA non configurato');
    END IF;

    IF v_stato_doc_fiscale_id IS DISTINCT FROM v_draft_id THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_lotto_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'stato_doc_fiscale', 'valore', v_stato_doc_fiscale_id, 'lotto_id', p_lotto_id),
            NULL::uuid, concat('rollback solo se DRAFT, stato=', v_stato_doc_fiscale_id));
    END IF;

    SELECT count(*) INTO v_bad_fatture
      FROM vendite.fatture f JOIN vendite.fatturazione_lotti_fatture lf ON lf.fattura_id = f.id
     WHERE lf.lotto_id = p_lotto_id AND f.stato_doc_fiscale_id IS DISTINCT FROM v_draft_id;

    IF v_bad_fatture > 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_lotto_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'fatture_non_draft', 'count', v_bad_fatture, 'lotto_id', p_lotto_id),
            NULL::uuid, concat('fatture non DRAFT: ', v_bad_fatture));
    END IF;

    SELECT array_agg(lf.fattura_id) INTO v_fatture_ids
      FROM vendite.fatturazione_lotti_fatture lf WHERE lf.lotto_id = p_lotto_id;
    IF v_fatture_ids IS NULL THEN v_fatture_ids := ARRAY[]::BIGINT[]; END IF;

    SELECT c.deleted_fatture, c.deleted_righe, c.updated_attivita INTO v_deleted_fatture, v_deleted_righe, v_updated_attivita
      FROM vendite.fn_cleanup_fatture_by_ids(v_fatture_ids, v_lock_batch_id) AS c;

    UPDATE vendite.fatturazione_lotti SET stato_operativo = 'CHIUSO', stato_doc_fiscale_id = v_annullata_id, stato_lotto = 'COMPLETATO', data_update = now(), user_update = current_user WHERE id = p_lotto_id;
    GET DIAGNOSTICS v_updated_lotti = ROW_COUNT;

    RETURN QUERY SELECT v_updated_lotti, v_updated_attivita, v_deleted_fatture, v_deleted_righe;
END;
$function$

COMMENT ON FUNCTION vendite.fn_reset_lotto_draft(p_lotto_id bigint)
IS 'Rollback tecnico lotto MASSIVO DRAFT: elimina fatture/righe e ripristina attivita.';
```

---
{% include-markdown "signature-core.md" %}
