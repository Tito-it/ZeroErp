{% include-markdown "it/dbzero/vendite/manual/fn_get_or_create_lotto.md" %}
# ⚙️ Funzione `fn_get_or_create_lotto`

```sql
CREATE FUNCTION fn_get_or_create_lotto(p_lotto_id bigint, p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_utility_id integer, p_billing_account_id bigint, p_lock_batch_id uuid, p_meta jsonb, p_tipo_lotto text, p_emittente_soggetto_ruolo_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_or_create_lotto(p_lotto_id bigint DEFAULT NULL::bigint, p_competenza_mese date DEFAULT NULL::date, p_tipo_doc_fiscale_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_billing_account_id bigint DEFAULT NULL::bigint, p_lock_batch_id uuid DEFAULT NULL::uuid, p_meta jsonb DEFAULT NULL::jsonb, p_tipo_lotto text DEFAULT 'MASSIVO'::text, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_lotto_id            vendite.fatturazione_lotti.id%TYPE;
    v_competenza          vendite.fatturazione_lotti.competenza_mese%TYPE;
    v_utility_id          config.utilities.id%TYPE;
    v_tipo_doc_id         config.tipi_doc_fiscale.id%TYPE;
    v_billing_account_id  anagrafiche.billing_account.id%TYPE;
    v_emittente_id        vendite.fatturazione_lotti.emittente_soggetto_ruolo_id%TYPE;
    v_tipo_lotto          vendite.fatturazione_lotti.tipo_lotto%TYPE;
    v_stato_lotto         vendite.fatturazione_lotti.stato_lotto%TYPE;
    v_stato_operativo     vendite.fatturazione_lotti.stato_operativo%TYPE;
    v_tipo_lotto_input    vendite.fatturazione_lotti.tipo_lotto%TYPE;
    v_resolved_utility_id config.utilities.id%TYPE;
    v_resolved_emittente_id vendite.fatturazione_lotti.emittente_soggetto_ruolo_id%TYPE;
BEGIN
    -- Normalizza lotto_id=0 a NULL
    IF p_lotto_id = 0 THEN p_lotto_id := NULL; END IF;

    -- Guard: tipo_lotto valido
    v_tipo_lotto_input := upper(btrim(COALESCE(p_tipo_lotto, '')));
    IF v_tipo_lotto_input IS NULL OR v_tipo_lotto_input = '' OR v_tipo_lotto_input NOT IN ('MASSIVO', 'GIORNALIERO') THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_lotto', 'valore', p_tipo_lotto),
            NULL::uuid, concat('p_tipo_lotto=', coalesce(p_tipo_lotto, 'NULL'), ' (ammessi: MASSIVO, GIORNALIERO)')
        );
    END IF;

    IF p_lotto_id IS NOT NULL AND p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id se fornito deve essere > 0'
        );
    END IF;

    IF p_tipo_doc_fiscale_id IS NOT NULL AND p_tipo_doc_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_doc_fiscale_id', 'valore', p_tipo_doc_fiscale_id),
            NULL::uuid, 'p_tipo_doc_fiscale_id se fornito deve essere > 0'
        );
    END IF;

    -- Risolvi utility/emittente via helper condiviso
    SELECT r.resolved_utility_id, r.resolved_emittente_soggetto_ruolo_id
      INTO v_resolved_utility_id, v_resolved_emittente_id
      FROM vendite.fn_resolve_lotto_utility_emittente(
          p_billing_account_id => p_billing_account_id,
          p_utility_id => p_utility_id,
          p_emittente_soggetto_ruolo_id => p_emittente_soggetto_ruolo_id,
          p_scope => 'LOTTO',
          p_caller => 'fn_get_or_create_lotto',
          p_check_emittente_attivo => TRUE
      ) r;

    -- ============================================
    -- CASO 1: lotto_id fornito → validazione coerenza
    -- ============================================
    IF p_lotto_id IS NOT NULL THEN
        SELECT competenza_mese, utility_id, tipo_doc_fiscale_id, billing_account_id,
               emittente_soggetto_ruolo_id, tipo_lotto, stato_lotto, stato_operativo
          INTO v_competenza, v_utility_id, v_tipo_doc_id, v_billing_account_id,
               v_emittente_id, v_tipo_lotto, v_stato_lotto, v_stato_operativo
          FROM vendite.fatturazione_lotti WHERE id = p_lotto_id;

        IF v_competenza IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'fn_get_or_create_lotto', 'E_VALORE_MANCANTE',
                jsonb_build_object('lotto_id', p_lotto_id),
                NULL::uuid, concat('lotto_id ', p_lotto_id)
            );
        END IF;

        -- Guard coerenza dimensionale (pattern ripetuto)
        IF p_competenza_mese IS NOT NULL AND date_trunc('month', p_competenza_mese)::DATE <> v_competenza THEN
            PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_or_create_lotto', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                jsonb_build_object('parametro', 'competenza_mese', 'atteso', v_competenza, 'ricevuto', p_competenza_mese),
                NULL::uuid, 'competenza_mese', p_lotto_id::text);
        END IF;
        IF v_resolved_utility_id IS NOT NULL AND v_resolved_utility_id <> v_utility_id THEN
            PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_or_create_lotto', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                jsonb_build_object('parametro', 'utility_id', 'atteso', v_utility_id, 'ricevuto', v_resolved_utility_id),
                NULL::uuid, 'utility_id', p_lotto_id::text);
        END IF;
        IF p_tipo_doc_fiscale_id IS NOT NULL AND p_tipo_doc_fiscale_id <> v_tipo_doc_id THEN
            PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_or_create_lotto', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                jsonb_build_object('parametro', 'tipo_doc_fiscale_id', 'atteso', v_tipo_doc_id, 'ricevuto', p_tipo_doc_fiscale_id),
                NULL::uuid, 'tipo_doc_fiscale_id', p_lotto_id::text);
        END IF;
        IF p_billing_account_id IS NOT NULL AND p_billing_account_id <> v_billing_account_id THEN
            PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_or_create_lotto', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                jsonb_build_object('parametro', 'billing_account_id', 'atteso', v_billing_account_id, 'ricevuto', p_billing_account_id),
                NULL::uuid, 'billing_account_id', p_lotto_id::text);
        END IF;
        IF v_resolved_emittente_id IS NOT NULL AND v_resolved_emittente_id <> v_emittente_id THEN
            PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_or_create_lotto', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                jsonb_build_object('parametro', 'emittente', 'atteso', v_emittente_id, 'ricevuto', v_resolved_emittente_id),
                NULL::uuid, 'emittente_soggetto_ruolo_id', p_lotto_id::text);
        END IF;
        IF v_tipo_lotto IS NOT NULL AND v_tipo_lotto <> v_tipo_lotto_input THEN
            PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_or_create_lotto', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                jsonb_build_object('parametro', 'tipo_lotto', 'atteso', v_tipo_lotto, 'ricevuto', v_tipo_lotto_input),
                NULL::uuid, 'tipo_lotto', p_lotto_id::text);
        END IF;

        IF v_stato_lotto = 'IN_ESECUZIONE' AND v_stato_operativo = 'CHIUSO' THEN
            PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_or_create_lotto', 'E_LOTTO_NON_RIUTILIZZABILE',
                jsonb_build_object('lotto_id', p_lotto_id, 'stato_operativo', v_stato_operativo,
                                   -- ⭐ Il bersaglio: qui l'operatore NON e' sul
                                   --    lotto — sta lanciando un'emissione e si
                                   --    sente dire che ce n'e' uno in esecuzione.
                                   --    Il lotto e' appena stato letto: esiste
                                   --    ed e' visibile.
                                   'bersaglio', jsonb_build_array(
                                       jsonb_build_object('tipo', 'LOTTO',
                                                          'id', p_lotto_id::text))),
                NULL::uuid, p_lotto_id::text, v_stato_operativo);
        END IF;

        RETURN p_lotto_id;
    END IF;

    -- ============================================
    -- CASO 2: lock_batch_id fornito → cerca lotto
    -- ============================================
    IF p_lock_batch_id IS NOT NULL THEN
        SELECT id, competenza_mese, utility_id, tipo_doc_fiscale_id, billing_account_id,
               emittente_soggetto_ruolo_id, tipo_lotto, stato_lotto, stato_operativo
          INTO v_lotto_id, v_competenza, v_utility_id, v_tipo_doc_id, v_billing_account_id,
               v_emittente_id, v_tipo_lotto, v_stato_lotto, v_stato_operativo
          FROM vendite.fatturazione_lotti
         WHERE lock_batch_id = p_lock_batch_id
         ORDER BY id DESC LIMIT 1;

        IF v_lotto_id IS NOT NULL THEN
            -- Stessi guard coerenza del caso 1
            IF p_competenza_mese IS NOT NULL AND date_trunc('month', p_competenza_mese)::DATE <> v_competenza THEN
                PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_or_create_lotto', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                    jsonb_build_object('parametro', 'competenza_mese', 'atteso', v_competenza, 'ricevuto', p_competenza_mese),
                    NULL::uuid, 'competenza_mese', v_lotto_id::text);
            END IF;
            IF v_resolved_utility_id IS NOT NULL AND v_resolved_utility_id <> v_utility_id THEN
                PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_or_create_lotto', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                    jsonb_build_object('parametro', 'utility_id', 'atteso', v_utility_id, 'ricevuto', v_resolved_utility_id),
                    NULL::uuid, 'utility_id', v_lotto_id::text);
            END IF;
            IF p_tipo_doc_fiscale_id IS NOT NULL AND p_tipo_doc_fiscale_id <> v_tipo_doc_id THEN
                PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_or_create_lotto', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                    jsonb_build_object('parametro', 'tipo_doc_fiscale_id', 'atteso', v_tipo_doc_id, 'ricevuto', p_tipo_doc_fiscale_id),
                    NULL::uuid, 'tipo_doc_fiscale_id', v_lotto_id::text);
            END IF;
            IF p_billing_account_id IS NOT NULL AND p_billing_account_id <> v_billing_account_id THEN
                PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_or_create_lotto', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                    jsonb_build_object('parametro', 'billing_account_id', 'atteso', v_billing_account_id, 'ricevuto', p_billing_account_id),
                    NULL::uuid, 'billing_account_id', v_lotto_id::text);
            END IF;
            IF v_resolved_emittente_id IS NOT NULL AND v_resolved_emittente_id <> v_emittente_id THEN
                PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_or_create_lotto', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                    jsonb_build_object('parametro', 'emittente', 'atteso', v_emittente_id, 'ricevuto', v_resolved_emittente_id),
                    NULL::uuid, 'emittente_soggetto_ruolo_id', v_lotto_id::text);
            END IF;
            IF v_tipo_lotto IS NOT NULL AND v_tipo_lotto <> v_tipo_lotto_input THEN
                PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_or_create_lotto', 'E_LOTTO_PARAMETRO_NON_COERENTE',
                    jsonb_build_object('parametro', 'tipo_lotto', 'atteso', v_tipo_lotto, 'ricevuto', v_tipo_lotto_input),
                    NULL::uuid, 'tipo_lotto', v_lotto_id::text);
            END IF;

            IF v_stato_lotto = 'IN_ESECUZIONE' AND v_stato_operativo = 'CHIUSO' THEN
                PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_or_create_lotto', 'E_LOTTO_NON_RIUTILIZZABILE',
                    jsonb_build_object('lotto_id', v_lotto_id, 'stato_operativo', v_stato_operativo,
                                   -- ⭐ Il bersaglio: qui l'operatore NON e' sul
                                   --    lotto — sta lanciando un'emissione e si
                                   --    sente dire che ce n'e' uno in esecuzione.
                                   --    Il lotto e' appena stato letto: esiste
                                   --    ed e' visibile.
                                   'bersaglio', jsonb_build_array(
                                       jsonb_build_object('tipo', 'LOTTO',
                                                          'id', v_lotto_id::text))),
                    NULL::uuid, v_lotto_id::text, v_stato_operativo);
            END IF;

            RETURN v_lotto_id;
        END IF;
    END IF;

    -- ============================================
    -- CASO 3: creazione nuovo lotto
    -- ============================================
    v_lotto_id := vendite.fn_create_fatturazione_lotto(
        p_competenza_mese => p_competenza_mese,
        p_tipo_doc_fiscale_id => p_tipo_doc_fiscale_id,
        p_utility_id => COALESCE(v_resolved_utility_id, p_utility_id),
        p_billing_account_id => p_billing_account_id,
        p_lock_batch_id => p_lock_batch_id,
        p_meta => p_meta,
        p_emittente_soggetto_ruolo_id => v_resolved_emittente_id
    );

    UPDATE vendite.fatturazione_lotti
       SET tipo_lotto = v_tipo_lotto_input,
           data_update = now(), user_update = current_user
     WHERE id = v_lotto_id;

    RETURN v_lotto_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_or_create_lotto(p_lotto_id bigint, p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_utility_id integer, p_billing_account_id bigint, p_lock_batch_id uuid, p_meta jsonb, p_tipo_lotto text, p_emittente_soggetto_ruolo_id bigint)
IS 'Recupera o crea lotto con validazione coerenza dimensionale completa. Helper condiviso per utility/emittente. ⭐ rev 2026-08-24: E_LOTTO_NON_RIUTILIZZABILE porta il BERSAGLIO sul lotto, in entrambi i suoi punti. Qui l''operatore NON e'' sul lotto: sta lanciando un''emissione e si sente dire che ce n''e'' gia'' uno in esecuzione — e senza bersaglio dovrebbe cercarselo. Il lotto e'' appena stato letto, quindi esiste ed e'' visibile: nessuna query in piu'', nessun ramo condizionale. Brief: brief-db-bersaglio-errore.md §6 L6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
