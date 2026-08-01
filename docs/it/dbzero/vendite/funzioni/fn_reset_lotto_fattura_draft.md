{% include-markdown "it/dbzero/vendite/manual/fn_reset_lotto_fattura_draft.md" %}
# ⚙️ Funzione `fn_reset_lotto_fattura_draft`

```sql
CREATE FUNCTION fn_reset_lotto_fattura_draft(p_lotto_id bigint, p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_reset_lotto_fattura_draft(p_lotto_id bigint, p_fattura_id bigint)
 RETURNS TABLE(updated_attivita integer, deleted_fatture integer, deleted_righe integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: toglie UNA fattura DRAFT da un lotto MASSIVO senza
--        annullare il lotto.
-- Regole: C-22 — alla primitiva si passa `NULL` come
--         `p_lock_batch_id`. Passando quello del lotto si
--         attiverebbe il ramo «tutte le attivita' del batch» e si
--         libererebbero anche quelle delle ALTRE fatture, che pero'
--         restano dove sono: documenti esistenti, con righe, le cui
--         attivita' risultano da fatturare. Il ramo per riga, da
--         solo, libera esattamente le attivita' di questa fattura.
DECLARE
    v_tipo_lotto           vendite.fatturazione_lotti.tipo_lotto%TYPE;
    v_stato_doc_fiscale_id vendite.fatturazione_lotti.stato_doc_fiscale_id%TYPE;
    v_draft_id             config.stati_doc_fiscale.id%TYPE;
    v_is_linked            BOOLEAN := FALSE;
    v_updated_attivita     INTEGER := 0;
    v_deleted_fatture      INTEGER := 0;
    v_deleted_righe        INTEGER := 0;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_lotto_fattura_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_lotto_fattura_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id), NULL::uuid, 'p_fattura_id obbligatorio e > 0');
    END IF;

    -- ⚠️ `lock_batch_id` del lotto NON si legge piu': non serve a
    -- questa funzione e averlo a portata di mano e' cio' che ha
    -- portato a passarlo (C-22).
    SELECT fl.tipo_lotto, fl.stato_doc_fiscale_id
      INTO v_tipo_lotto, v_stato_doc_fiscale_id
      FROM vendite.fatturazione_lotti fl WHERE fl.id = p_lotto_id;

    IF v_tipo_lotto IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_lotto_fattura_draft', 'E_VALORE_MANCANTE',
            jsonb_build_object('lotto_id', p_lotto_id), NULL::uuid, concat('lotto_id ', p_lotto_id));
    END IF;

    IF v_tipo_lotto <> 'MASSIVO' THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_lotto_fattura_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'tipo_lotto', 'valore', v_tipo_lotto, 'lotto_id', p_lotto_id),
            NULL::uuid, concat('reset solo per MASSIVO, tipo=', v_tipo_lotto));
    END IF;

    SELECT s.id INTO v_draft_id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE LIMIT 1;
    IF v_draft_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_lotto_fattura_draft', 'E_CONFIG_MANCANTE',
            jsonb_build_object('codice_interno', 'DRAFT'), NULL::uuid, 'stato DRAFT non configurato');
    END IF;

    IF v_stato_doc_fiscale_id IS DISTINCT FROM v_draft_id THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_lotto_fattura_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'stato_doc_fiscale', 'valore', v_stato_doc_fiscale_id, 'lotto_id', p_lotto_id),
            NULL::uuid, concat('reset solo se DRAFT, stato=', v_stato_doc_fiscale_id));
    END IF;

    SELECT EXISTS (
        SELECT 1 FROM vendite.fatturazione_lotti_fatture lf
        JOIN vendite.fatture f ON f.id = lf.fattura_id
        WHERE lf.lotto_id = p_lotto_id AND lf.fattura_id = p_fattura_id AND f.stato_doc_fiscale_id = v_draft_id
    ) INTO v_is_linked;

    IF COALESCE(v_is_linked, FALSE) = FALSE THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_reset_lotto_fattura_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'fattura_non_collegata_o_non_draft', 'lotto_id', p_lotto_id, 'fattura_id', p_fattura_id),
            NULL::uuid, 'fattura non collegata al lotto o non in DRAFT');
    END IF;

    -- C-22: NULL, non il lock_batch_id del lotto.
    SELECT c.deleted_fatture, c.deleted_righe, c.updated_attivita INTO v_deleted_fatture, v_deleted_righe, v_updated_attivita
      FROM vendite.fn_cleanup_fatture_by_ids(ARRAY[p_fattura_id], NULL::uuid) AS c;

    RETURN QUERY SELECT v_updated_attivita, v_deleted_fatture, v_deleted_righe;
END;
$function$

COMMENT ON FUNCTION vendite.fn_reset_lotto_fattura_draft(p_lotto_id bigint, p_fattura_id bigint)
IS 'Reset singola fattura DRAFT in lotto MASSIVO senza annullare il lotto. Da C-22 passa NULL come lock_batch_id alla primitiva di cleanup: col lock_batch_id del lotto si sbloccavano e si smarcavano come non fatturate anche le attivita delle ALTRE fatture del lotto, che pero'' restavano al loro posto. Prerequisito di D-N-bis e della Fase 6.';
```

---
{% include-markdown "signature-core.md" %}
