{% include-markdown "it/dbzero/vendite/manual/fn_emit_attivita_fatturabili_da_commessa.md" %}
# ⚙️ Funzione `fn_emit_attivita_fatturabili_da_commessa`

```sql
CREATE FUNCTION fn_emit_attivita_fatturabili_da_commessa(p_commessa_id bigint, p_lotto_attivita_id bigint, p_only_approved boolean, p_dry_run boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_emit_attivita_fatturabili_da_commessa(p_commessa_id bigint, p_lotto_attivita_id bigint DEFAULT NULL::bigint, p_only_approved boolean DEFAULT true, p_dry_run boolean DEFAULT false)
 RETURNS TABLE(total_candidate integer, inserted_rows integer, updated_rows integer, skipped_rows integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_commessa              vendite.commesse%ROWTYPE;
    v_root_id               vendite.commesse_sorgenti.id%TYPE;
    v_commessa_source_id    config.sorgenti.id%TYPE;
    v_existing_id           vendite.attivita_fatturabili.id%TYPE;
    v_existing_fatturato    vendite.attivita_fatturabili.fatturato%TYPE;
    v_sorgente_uid_uuid     vendite.attivita_fatturabili.sorgente_uid%TYPE;
    v_row                   RECORD;
BEGIN
    total_candidate := 0;
    inserted_rows := 0;
    updated_rows := 0;
    skipped_rows := 0;

    -- Guard: parametri
    IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_emit_attivita_fatturabili_da_commessa', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_commessa_id', 'valore', p_commessa_id),
            NULL::uuid, 'p_commessa_id obbligatorio e > 0'
        );
    END IF;

    IF p_lotto_attivita_id IS NOT NULL AND p_lotto_attivita_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_emit_attivita_fatturabili_da_commessa', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_attivita_id', 'valore', p_lotto_attivita_id),
            NULL::uuid, 'p_lotto_attivita_id se fornito deve essere > 0'
        );
    END IF;

    -- Recupera commessa
    SELECT c.* INTO v_commessa
      FROM vendite.commesse c WHERE c.id = p_commessa_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_emit_attivita_fatturabili_da_commessa', 'E_VALORE_MANCANTE',
            jsonb_build_object('commessa_id', p_commessa_id),
            NULL::uuid, concat('commessa_id ', p_commessa_id)
        );
    END IF;

    -- Verifica lotto attivita' se fornito
    IF p_lotto_attivita_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM vendite.attivita_fatturabili_lotti l WHERE l.id = p_lotto_attivita_id
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_emit_attivita_fatturabili_da_commessa', 'E_VALORE_MANCANTE',
            jsonb_build_object('lotto_attivita_id', p_lotto_attivita_id),
            NULL::uuid, concat('lotto_attivita_id ', p_lotto_attivita_id)
        );
    END IF;

    -- ROOT source obbligatoria
    SELECT cs.id INTO v_root_id
      FROM vendite.commesse_sorgenti cs
     WHERE cs.commessa_id = p_commessa_id AND cs.ruolo_link = 'ROOT'
     LIMIT 1;

    IF v_root_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_emit_attivita_fatturabili_da_commessa', 'E_VALORE_MANCANTE',
            jsonb_build_object('commessa_id', p_commessa_id),
            NULL::uuid, concat('ROOT source mancante per commessa ', p_commessa_id)
        );
    END IF;

    -- Sorgente COMMESSA
    SELECT s.id INTO v_commessa_source_id
      FROM config.sorgenti s
     WHERE s.codice = 'COMMESSA' AND s.attivo IS TRUE
     LIMIT 1;

    IF v_commessa_source_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_emit_attivita_fatturabili_da_commessa', 'E_CODICE',
            jsonb_build_object('codice', 'COMMESSA'),
            NULL::uuid, 'COMMESSA', 'config.sorgenti'
        );
    END IF;

    -- Loop emissione righe
    FOR v_row IN
        SELECT ca.id, ca.segment_key, ca.articolo_id, ca.istanza_utility_id,
               ca.data_attivita, ca.uom_id, ca.quantita, ca.qta_operativa,
               ca.uom_operativa_id, ca.factor_to_base, ca.competenza_mese,
               ca.competenza_dal, ca.competenza_al, ca.posticipa_al,
               ca.tipo_doc_fiscale_id, ca.valuta_id, ca.area_geografica_id,
               ca.prezzo_snapshot, ca.prezzo_bloccato, ca.stato_approvazione, ca.meta,
               ca.sorgente_tipo_id AS ca_sorgente_tipo_id
          FROM vendite.commesse_attivita ca
         WHERE ca.commessa_id = p_commessa_id
           AND ca.stato_emissione = 'NON_EMESSA'
           AND (p_only_approved IS FALSE OR ca.stato_approvazione = 'APPROVATA')
         ORDER BY ca.id
    LOOP
        total_candidate := total_candidate + 1;

        -- Hash segment_key → UUID deterministico
        v_sorgente_uid_uuid := (
            substr(md5(v_row.segment_key), 1, 8) || '-' ||
            substr(md5(v_row.segment_key), 9, 4) || '-' ||
            substr(md5(v_row.segment_key), 13, 4) || '-' ||
            substr(md5(v_row.segment_key), 17, 4) || '-' ||
            substr(md5(v_row.segment_key), 21, 12)
        )::uuid;

        SELECT a.id, a.fatturato INTO v_existing_id, v_existing_fatturato
          FROM vendite.attivita_fatturabili a
         WHERE a.sorgente_tipo_id = v_commessa_source_id
           AND a.sorgente_uid = v_sorgente_uid_uuid
           FOR UPDATE;

        IF p_dry_run THEN
            IF v_existing_id IS NULL THEN inserted_rows := inserted_rows + 1;
            ELSE updated_rows := updated_rows + 1; END IF;
            CONTINUE;
        END IF;

        IF v_existing_id IS NULL THEN
            INSERT INTO vendite.attivita_fatturabili (
                articolo_id, billing_account_id, istanza_utility_id, data_attivita,
                quantita, competenza_mese, approvato, fatturato, meta, sorgente_riga,
                posticipa_al, sorgente_tipo_id, sorgente_uid, uom_id, qta_operativa,
                uom_operativa_id, factor_to_base, valuta_id, prezzo_unitario,
                lotto_attivita_id, tipo_doc_fiscale_id, competenza_dal, competenza_al,
                area_geografica_id, stato_esecuzione, prezzo_bloccato,
                commessa_id, commessa_attivita_id, sorgente_origine_tipo_id
            )
            VALUES (
                v_row.articolo_id, v_commessa.billing_account_id, v_row.istanza_utility_id,
                v_row.data_attivita, v_row.quantita, v_row.competenza_mese,
                (v_row.stato_approvazione = 'APPROVATA'), false,
                COALESCE(v_row.meta, '{}'::jsonb) || jsonb_build_object(
                    'scope', 'COMMESSE', 'commessa_id', p_commessa_id,
                    'commessa_attivita_id', v_row.id, 'segment_key', v_row.segment_key
                ),
                v_row.id, v_row.posticipa_al, v_commessa_source_id, v_sorgente_uid_uuid,
                v_row.uom_id, v_row.qta_operativa, v_row.uom_operativa_id, v_row.factor_to_base,
                v_row.valuta_id, v_row.prezzo_snapshot, p_lotto_attivita_id,
                v_row.tipo_doc_fiscale_id, v_row.competenza_dal, v_row.competenza_al,
                v_row.area_geografica_id, 'PENDING', v_row.prezzo_bloccato,
                p_commessa_id, v_row.id, v_row.ca_sorgente_tipo_id
            );
            inserted_rows := inserted_rows + 1;
        ELSE
            -- Riga esistente: errore se gia' fatturata
            IF COALESCE(v_existing_fatturato, false) IS TRUE THEN
                PERFORM script.fn_log_and_raise_error(
                    'vendite', 'fn_emit_attivita_fatturabili_da_commessa', 'E_RIGA_GIA_FATTURATA',
                    jsonb_build_object('attivita_fatturabili_id', v_existing_id, 'commessa_attivita_id', v_row.id),
                    NULL::uuid, v_existing_id::text
                );
            END IF;

            UPDATE vendite.attivita_fatturabili a
               SET articolo_id = v_row.articolo_id,
                   billing_account_id = v_commessa.billing_account_id,
                   istanza_utility_id = v_row.istanza_utility_id,
                   data_attivita = v_row.data_attivita,
                   quantita = v_row.quantita,
                   competenza_mese = v_row.competenza_mese,
                   approvato = (v_row.stato_approvazione = 'APPROVATA'),
                   meta = COALESCE(a.meta, '{}'::jsonb) || COALESCE(v_row.meta, '{}'::jsonb) || jsonb_build_object(
                       'scope', 'COMMESSE', 'commessa_id', p_commessa_id,
                       'commessa_attivita_id', v_row.id, 'segment_key', v_row.segment_key
                   ),
                   sorgente_riga = v_row.id,
                   posticipa_al = v_row.posticipa_al,
                   uom_id = v_row.uom_id,
                   qta_operativa = v_row.qta_operativa,
                   uom_operativa_id = v_row.uom_operativa_id,
                   factor_to_base = v_row.factor_to_base,
                   valuta_id = v_row.valuta_id,
                   prezzo_unitario = v_row.prezzo_snapshot,
                   lotto_attivita_id = COALESCE(p_lotto_attivita_id, a.lotto_attivita_id),
                   tipo_doc_fiscale_id = v_row.tipo_doc_fiscale_id,
                   competenza_dal = v_row.competenza_dal,
                   competenza_al = v_row.competenza_al,
                   area_geografica_id = v_row.area_geografica_id,
                   prezzo_bloccato = v_row.prezzo_bloccato,
                   commessa_id = p_commessa_id,
                   commessa_attivita_id = v_row.id,
                   sorgente_origine_tipo_id = v_row.ca_sorgente_tipo_id
             WHERE a.id = v_existing_id;
            updated_rows := updated_rows + 1;
        END IF;

        UPDATE vendite.commesse_attivita ca SET stato_emissione = 'EMESSA' WHERE ca.id = v_row.id;
    END LOOP;

    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION vendite.fn_emit_attivita_fatturabili_da_commessa(p_commessa_id bigint, p_lotto_attivita_id bigint, p_only_approved boolean, p_dry_run boolean)
IS 'Pull da commesse_attivita ad attivita_fatturabili con sorgente COMMESSA+segment_key (hash UUID) e idempotenza.';
```

---
{% include-markdown "signature-core.md" %}
