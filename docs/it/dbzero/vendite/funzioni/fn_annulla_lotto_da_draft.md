{% include-markdown "it/dbzero/vendite/manual/fn_annulla_lotto_da_draft.md" %}
# ⚙️ Funzione `fn_annulla_lotto_da_draft`

```sql
CREATE FUNCTION fn_annulla_lotto_da_draft(p_lotto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_annulla_lotto_da_draft(p_lotto_id bigint)
 RETURNS TABLE(updated_lotti integer, updated_attivita integer, deleted_fatture integer, deleted_righe integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: rollback tecnico di un lotto in DRAFT — cancella le
--        fatture PRE-FISCALI (DRAFT/EMESSA), ripristina le
--        attivita' e CHIUDE il lotto portandolo ad ANNULLATA.
-- Perimetro (D-L pt.2 + D-T): vale per MASSIVO **e** GIORNALIERO.
--        Il vincolo al solo MASSIVO e' caduto quando D-T ha reso
--        lecita la transizione DRAFT->ANNULLATA per entrambi.
-- rev 2026-08-04: le precondizioni NON si scrivono piu' qui.
--        Arrivano da script.fn_check_lotto_annullabile, la stessa
--        che alimenta enabled/reasons di
--        script.fn_available_actions_lotto. Il pulsante e la
--        funzione non possono piu' divergere.
DECLARE
    v_lock_batch_id        vendite.fatturazione_lotti.lock_batch_id%TYPE;
    v_annullata_id         config.stati_doc_fiscale.id%TYPE;
    v_motivi               jsonb;
    v_fatture_ids          BIGINT[];
    v_updated_lotti        INTEGER := 0;
    v_updated_attivita     INTEGER := 0;
    v_deleted_fatture      INTEGER := 0;
    v_deleted_righe        INTEGER := 0;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_annulla_lotto_da_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    -- PRECONDIZIONI — sede unica. Il check verifica anche
    -- l'esistenza del lotto (E_LOTTO_NON_TROVATO) e solleva
    -- il codice del PRIMO motivo; il context porta l'elenco
    -- completo, cosi' il BE puo' mostrarli tutti.
    v_motivi := script.fn_check_lotto_annullabile(p_lotto_id);
    IF jsonb_array_length(v_motivi) > 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_annulla_lotto_da_draft',
            v_motivi -> 0 ->> 'codice',
            jsonb_build_object('lotto_id', p_lotto_id, 'motivi', v_motivi),
            NULL::uuid,
            v_motivi -> 0 ->> 'dettaglio');
    END IF;

    SELECT fl.lock_batch_id
      INTO v_lock_batch_id
      FROM vendite.fatturazione_lotti fl WHERE fl.id = p_lotto_id;

    SELECT s.id INTO v_annullata_id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'ANNULLATA' AND s.attivo IS TRUE LIMIT 1;
    IF v_annullata_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_annulla_lotto_da_draft', 'E_CONFIG_MANCANTE',
            jsonb_build_object('codice_interno', 'ANNULLATA'), NULL::uuid, 'stato ANNULLATA non configurato');
    END IF;

    SELECT array_agg(lf.fattura_id) INTO v_fatture_ids
      FROM vendite.fatturazione_lotti_fatture lf WHERE lf.lotto_id = p_lotto_id;
    IF v_fatture_ids IS NULL THEN v_fatture_ids := ARRAY[]::BIGINT[]; END IF;

    -- ⚠️ Qui il lock_batch_id SI passa, ed e' corretto: il reset
    -- globale deve liberare anche le attivita' agganciate al lotto
    -- che non sono mai diventate riga. E' il per-fattura che deve
    -- passare NULL (C-22).
    SELECT c.deleted_fatture, c.deleted_righe, c.updated_attivita INTO v_deleted_fatture, v_deleted_righe, v_updated_attivita
      FROM vendite.fn_cleanup_fatture_by_ids(v_fatture_ids, v_lock_batch_id) AS c;

    UPDATE vendite.fatturazione_lotti SET stato_operativo = 'CHIUSO', stato_doc_fiscale_id = v_annullata_id, stato_lotto = 'COMPLETATO', data_update = now(), user_update = current_user WHERE id = p_lotto_id;
    GET DIAGNOSTICS v_updated_lotti = ROW_COUNT;

    RETURN QUERY SELECT v_updated_lotti, v_updated_attivita, v_deleted_fatture, v_deleted_righe;
END;
$function$

COMMENT ON FUNCTION vendite.fn_annulla_lotto_da_draft(p_lotto_id bigint)
IS 'Rollback tecnico di un lotto in DRAFT: elimina fatture/righe PRE-FISCALI (DRAFT/EMESSA), ripristina le attivita e CHIUDE il lotto portandolo ad ANNULLATA. Rinominata da fn_reset_lotto_draft il 2026-08-01 (D-L pt.1): il nome vecchio prometteva un ritorno in bozza che non fa. Dal 2026-08-02 (D-L pt.2 + D-T) vale per MASSIVO **e** GIORNALIERO. Il task_code del registry resta reset_lotto_draft, che e'' il nome del TASK. rev 2026-08-04: le precondizioni non sono piu'' scritte qui — arrivano da script.fn_check_lotto_annullabile, la STESSA che alimenta enabled/reasons di script.fn_available_actions_lotto, cosi'' il pulsante e la funzione non possono divergere (lezione del vicolo cieco 2026-07-31). Solleva il codice del PRIMO motivo (E_LOTTO_NON_ANNULLABILE / E_LOTTO_FATTURE_NON_PRE_FISCALI / E_LOTTO_NON_TROVATO, non piu'' E_PARAMETRO_INVALIDO) e mette l''elenco completo dei motivi nel context.';
```

---
{% include-markdown "signature-core.md" %}
