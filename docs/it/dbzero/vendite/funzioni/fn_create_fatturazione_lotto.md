{% include-markdown "it/dbzero/vendite/manual/fn_create_fatturazione_lotto.md" %}
# ⚙️ Funzione `fn_create_fatturazione_lotto`

```sql
CREATE FUNCTION fn_create_fatturazione_lotto(p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_utility_id integer, p_billing_account_id bigint, p_lock_batch_id uuid, p_meta jsonb, p_emittente_soggetto_ruolo_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_create_fatturazione_lotto(p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_utility_id integer DEFAULT NULL::integer, p_billing_account_id bigint DEFAULT NULL::bigint, p_lock_batch_id uuid DEFAULT NULL::uuid, p_meta jsonb DEFAULT NULL::jsonb, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_competenza          vendite.fatturazione_lotti.competenza_mese%TYPE;
    v_utility_id          config.utilities.id%TYPE;
    v_lock_batch_id       vendite.fatturazione_lotti.lock_batch_id%TYPE;
    v_lotto_id            vendite.fatturazione_lotti.id%TYPE;
    v_map_exists          BOOLEAN;
    v_emittente_id        vendite.fatturazione_lotti.emittente_soggetto_ruolo_id%TYPE;
    v_single_emittente_count BIGINT;
BEGIN
    -- Guard: parametri obbligatori
    IF p_competenza_mese IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_create_fatturazione_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_competenza_mese', 'valore', NULL),
            NULL::uuid, 'p_competenza_mese obbligatoria'
        );
    END IF;

    IF p_tipo_doc_fiscale_id IS NULL OR p_tipo_doc_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_create_fatturazione_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_doc_fiscale_id', 'valore', p_tipo_doc_fiscale_id),
            NULL::uuid, 'p_tipo_doc_fiscale_id obbligatorio e > 0'
        );
    END IF;

    IF p_utility_id IS NOT NULL AND p_utility_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_create_fatturazione_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_utility_id', 'valore', p_utility_id),
            NULL::uuid, 'p_utility_id se fornito deve essere > 0'
        );
    END IF;

    IF p_billing_account_id IS NOT NULL AND p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_create_fatturazione_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_billing_account_id', 'valore', p_billing_account_id),
            NULL::uuid, 'p_billing_account_id se fornito deve essere > 0'
        );
    END IF;

    IF p_emittente_soggetto_ruolo_id IS NOT NULL AND p_emittente_soggetto_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_create_fatturazione_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_emittente_soggetto_ruolo_id', 'valore', p_emittente_soggetto_ruolo_id),
            NULL::uuid, 'p_emittente_soggetto_ruolo_id se fornito deve essere > 0'
        );
    END IF;

    -- Competenza normalizzata al primo del mese
    v_competenza := date_trunc('month', p_competenza_mese)::DATE;

    -- Risolvi utility da BA se fornito
    v_utility_id := p_utility_id;
    IF p_billing_account_id IS NOT NULL THEN
        SELECT ba.utility_id
          INTO v_utility_id
          FROM anagrafiche.billing_account ba
         WHERE ba.id = p_billing_account_id;

        IF v_utility_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'fn_create_fatturazione_lotto', 'E_VALORE_MANCANTE',
                jsonb_build_object('billing_account_id', p_billing_account_id),
                NULL::uuid, concat('utility non risolta da BA ', p_billing_account_id)
            );
        END IF;

        IF p_utility_id IS NOT NULL AND p_utility_id <> v_utility_id THEN
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'fn_create_fatturazione_lotto', 'E_CLIENTE_UTILITY_MISMATCH_BA',
                jsonb_build_object('billing_account_id', p_billing_account_id, 'utility_da_parametro', p_utility_id, 'utility_da_ba', v_utility_id),
                NULL::uuid, p_billing_account_id::text, p_utility_id::text, v_utility_id::text
            );
        END IF;
    END IF;

    IF v_utility_id IS NULL OR v_utility_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_create_fatturazione_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'utility_id', 'valore', v_utility_id),
            NULL::uuid, 'utility_id obbligatoria (da parametro o da billing_account)'
        );
    END IF;

    -- Risolvi emittente fiscale (fallback operativo)
    v_emittente_id := p_emittente_soggetto_ruolo_id;

    IF v_emittente_id IS NULL AND p_billing_account_id IS NOT NULL THEN
        v_emittente_id := anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id);
    END IF;

    IF v_emittente_id IS NULL THEN
        SELECT COUNT(*)::BIGINT INTO v_single_emittente_count
          FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.attivo IS TRUE;

        IF v_single_emittente_count = 1 THEN
            SELECT ef.soggetto_ruolo_id INTO v_emittente_id
              FROM anagrafiche.emittenti_fiscali ef
             WHERE ef.attivo IS TRUE
             LIMIT 1;
        END IF;
    END IF;

    IF v_emittente_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_create_fatturazione_lotto', 'E_EMITTENTE_DEFAULT_MISSING',
            jsonb_build_object('billing_account_id', p_billing_account_id),
            NULL::uuid, 'Emittente fiscale non determinabile'
        );
    END IF;

    -- Verifica emittente attivo
    SELECT EXISTS (
        SELECT 1 FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.soggetto_ruolo_id = v_emittente_id AND ef.attivo IS TRUE
    ) INTO v_map_exists;

    IF NOT v_map_exists THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_create_fatturazione_lotto', 'E_CODICE',
            jsonb_build_object('emittente_soggetto_ruolo_id', v_emittente_id),
            NULL::uuid, v_emittente_id::text, 'anagrafiche.emittenti_fiscali'
        );
    END IF;

    -- Verifica tipo doc fiscale attivo
    SELECT EXISTS (
        SELECT 1 FROM config.tipi_doc_fiscale t
         WHERE t.id = p_tipo_doc_fiscale_id AND t.attivo IS TRUE
    ) INTO v_map_exists;

    IF NOT v_map_exists THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_create_fatturazione_lotto', 'E_CODICE',
            jsonb_build_object('tipo_doc_fiscale_id', p_tipo_doc_fiscale_id),
            NULL::uuid, p_tipo_doc_fiscale_id::text, 'config.tipi_doc_fiscale'
        );
    END IF;

    -- Verifica mapping tipo_doc → registro
    SELECT EXISTS (
        SELECT 1 FROM vendite.tipi_doc_fiscale_registri m
         WHERE m.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id
    ) INTO v_map_exists;

    IF NOT v_map_exists THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_create_fatturazione_lotto', 'E_CONFIG_MANCANTE',
            jsonb_build_object('tipo_doc_fiscale_id', p_tipo_doc_fiscale_id),
            NULL::uuid, concat('mapping tipo_doc_fiscale→registro per id ', p_tipo_doc_fiscale_id)
        );
    END IF;

    -- Lo stato non si sceglie qui: il lotto nasce nello stato
    -- iniziale del vocabolario, messo dal trigger della nascita
    -- (trg_fatturazione_lotti_a05_stato_iniziale_ins).
    v_lock_batch_id := COALESCE(p_lock_batch_id, uuidv7());

    -- Creazione lotto
    INSERT INTO vendite.fatturazione_lotti (
        lock_batch_id, competenza_mese, utility_id, billing_account_id,
        emittente_soggetto_ruolo_id, tipo_doc_fiscale_id, meta
    )
    VALUES (
        v_lock_batch_id, v_competenza, v_utility_id, p_billing_account_id,
        v_emittente_id, p_tipo_doc_fiscale_id, COALESCE(p_meta, '{}'::jsonb)
    )
    RETURNING id INTO v_lotto_id;

    RETURN v_lotto_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_create_fatturazione_lotto(p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_utility_id integer, p_billing_account_id bigint, p_lock_batch_id uuid, p_meta jsonb, p_emittente_soggetto_ruolo_id bigint)
IS 'Crea un lotto di fatturazione: valida competenza, utility (dal parametro o dal billing account), tipo di documento fiscale e la sua mappa sul registro, risolve l''emittente fiscale (dal parametro, poi dal billing account, poi l''unico emittente attivo) e inserisce il lotto, di cui ritorna l''id. Lo stato non lo sceglie: il lotto nasce nello stato iniziale di config.stati_doc_fiscale, messo dal trigger trg_fatturazione_lotti_a05_stato_iniziale_ins (script.trgfn_doc_stato_iniziale). Errori: E_PARAMETRO_INVALIDO, E_VALORE_MANCANTE, E_CLIENTE_UTILITY_MISMATCH_BA, E_EMITTENTE_DEFAULT_MISSING, E_CODICE, E_CONFIG_MANCANTE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
