{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_cliente.md" %}
# ⚙️ Funzione `fn_crea_cliente`

```sql
CREATE FUNCTION fn_crea_cliente(p_soggetto_id uuid, p_utility_id integer, p_campi jsonb, p_billing_account jsonb, p_contatto jsonb, p_indirizzi jsonb, p_billing_account_id bigint, p_istanza_utility_id bigint, p_istanza jsonb, p_emittente_soggetto_ruolo_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_cliente(p_soggetto_id uuid, p_utility_id integer DEFAULT NULL::integer, p_campi jsonb DEFAULT '{}'::jsonb, p_billing_account jsonb DEFAULT '{}'::jsonb, p_contatto jsonb DEFAULT NULL::jsonb, p_indirizzi jsonb DEFAULT '[]'::jsonb, p_billing_account_id bigint DEFAULT NULL::bigint, p_istanza_utility_id bigint DEFAULT NULL::bigint, p_istanza jsonb DEFAULT '{}'::jsonb, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(cliente_id bigint, billing_account_id bigint, istanza_utility_id bigint, soggetto_ruolo_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_campi      jsonb := jsonb_strip_nulls(COALESCE(p_campi, '{}'::jsonb));
    v_ba         jsonb := COALESCE(p_billing_account, '{}'::jsonb);
    v_istanza    jsonb := COALESCE(p_istanza, '{}'::jsonb);
    v_nascita    jsonb := '{}'::jsonb;
    v_estranea   text;
    v_sr_id      anagrafiche.clienti.soggetto_ruolo_id%TYPE;
    v_ba_id      anagrafiche.clienti.billing_account_id%TYPE := p_billing_account_id;
    v_ist_id     anagrafiche.clienti.istanza_utility_id%TYPE := p_istanza_utility_id;
    v_cliente_id anagrafiche.clienti.id%TYPE;
    -- Le chiavi del backend (_CLIENTE_CREATE_ALLOWED), meno la
    -- fornitura che decide la madre; piu' le date degli stati.
    c_ammesse    CONSTANT text[] := ARRAY[
        'termine_pagamento_id', 'modalita_pagamento_id', 'servizio_da_fatturare',
        'garanzia_tipo', 'garanzia_importo',
        'stato_cliente_id', 'data_attivazione', 'data_sospensione', 'data_chiusura'];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Fare di un soggetto un cliente: il ruolo CL
    --   (get_or_create), il billing account (nuovo per
    --   p_utility_id dal BB, oppure p_billing_account_id), la
    --   riga di clienti coi campi di p_campi, il contatto (se
    --   c'e') e gli indirizzi del ruolo. Ritorna (cliente_id,
    --   billing_account_id, istanza_utility_id,
    --   soggetto_ruolo_id).
    --
    -- Regole:
    --   - senza stato: AT, attivazione alla data operativa;
    --     con uno stato, le date sono di chi chiama (guard);
    --   - chiave estranea: E_CAMPO_NON_AMMESSO; null = assente;
    --   - BA esistente insieme ai dati di uno nuovo, o nessuno
    --     dei due: E_SCRIPT_CHIAMATA_NON_VALIDA.
    -- =========================================================
    IF p_soggetto_id IS NULL
       OR jsonb_typeof(v_campi) <> 'object' OR jsonb_typeof(v_ba) <> 'object'
       OR jsonb_typeof(v_istanza) <> 'object'
       OR (p_billing_account_id IS NULL AND p_utility_id IS NULL)
       OR (p_billing_account_id IS NOT NULL
           AND (v_ba <> '{}'::jsonb OR v_istanza <> '{}'::jsonb
                OR p_emittente_soggetto_ruolo_id IS NOT NULL)) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_crea_cliente', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('soggetto_id',        p_soggetto_id,
                               'utility_id',         p_utility_id,
                               'billing_account_id', p_billing_account_id,
                               'tipo_campi',         jsonb_typeof(v_campi)),
            NULL::uuid,
            'anagrafiche.fn_crea_cliente',
            'soggetto mancante, campi non oggetti, o billing account esistente e nuovo insieme (o nessuno dei due)');
    END IF;

    v_estranea := script.fn_prima_chiave_estranea(v_campi, c_ammesse);
    IF v_estranea IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_crea_cliente', 'E_CAMPO_NON_AMMESSO',
            jsonb_build_object('campo', v_estranea, 'soggetto_id', p_soggetto_id),
            NULL::uuid,
            v_estranea);
    END IF;

    v_sr_id := script.fn_get_or_create_soggetto_ruolo(
                   p_soggetto_id  := p_soggetto_id,
                   p_cd_int_ruolo := 'CL');

    -- 1. La fornitura: un BA nuovo dal BB, o quello indicato.
    IF v_ba_id IS NULL THEN
        SELECT b.billing_account_id, b.istanza_utility_id
          INTO v_ba_id, v_ist_id
          FROM anagrafiche.fn_crea_billing_account(
                   v_sr_id, p_utility_id, v_ba, p_istanza_utility_id, v_istanza,
                   p_emittente_soggetto_ruolo_id) b;
    ELSIF v_ist_id IS NULL THEN
        SELECT ba.istanza_utility_id
          INTO v_ist_id
          FROM anagrafiche.billing_account ba
         WHERE ba.id = v_ba_id;
    END IF;

    -- 2. Lo stato di nascita: senza stato, AT dalla data operativa
    --    (le chiavi di chi chiama vincono, la data compresa).
    IF NOT jsonb_exists(v_campi, 'stato_cliente_id') THEN
        v_nascita := jsonb_build_object(
            'stato_cliente_id', (SELECT sc.id FROM config.stati_cliente sc
                                  WHERE sc.codice_interno = 'AT'),
            'data_attivazione', script.fn_data_operativa());
    END IF;

    -- 3. Il cliente, riletto a istruzione finita
    --    (uq_clienti_billing_account): sotto la RLS, come il BA.
    v_cliente_id := (script.fn_scrivi_riga_da_jsonb(
                         'anagrafiche.clienti'::regclass,
                         v_nascita || v_campi
                         || jsonb_build_object('billing_account_id', v_ba_id,
                                               'istanza_utility_id', v_ist_id,
                                               'soggetto_ruolo_id',  v_sr_id),
                         NULL,
                         ARRAY['billing_account_id'])
                     ->> 'id')::bigint;

    -- 4. Contatto e indirizzi del ruolo, dai loro BB.
    IF p_contatto IS NOT NULL THEN
        PERFORM anagrafiche.fn_crea_contatto(p_soggetto_id, v_sr_id, p_contatto);
    END IF;

    PERFORM anagrafiche.fn_crea_indirizzi_ruolo(v_sr_id, p_indirizzi);

    RETURN QUERY SELECT v_cliente_id, v_ba_id, v_ist_id, v_sr_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_cliente(p_soggetto_id uuid, p_utility_id integer, p_campi jsonb, p_billing_account jsonb, p_contatto jsonb, p_indirizzi jsonb, p_billing_account_id bigint, p_istanza_utility_id bigint, p_istanza jsonb, p_emittente_soggetto_ruolo_id bigint)
IS 'Madre (2026-10-18): fa di un soggetto un cliente in una sola istruzione: il ruolo CL (script.fn_get_or_create_soggetto_ruolo), il billing account (nuovo per p_utility_id da anagrafiche.fn_crea_billing_account, coi campi p_billing_account, l''istanza p_istanza_utility_id o una fittizia coi campi p_istanza, il legame a p_emittente_soggetto_ruolo_id; oppure quello esistente p_billing_account_id, con l''istanza letta dal BA se non indicata), la riga di anagrafiche.clienti, il contatto del ruolo (anagrafiche.fn_crea_contatto, se p_contatto non e'' NULL) e gli indirizzi del ruolo (anagrafiche.fn_crea_indirizzi_ruolo). p_campi: termine_pagamento_id, modalita_pagamento_id, servizio_da_fatturare, garanzia_tipo, garanzia_importo, stato_cliente_id, data_attivazione, data_sospensione, data_chiusura; le assenti e le null al DEFAULT; chiave estranea: E_CAMPO_NON_AMMESSO. Senza stato il cliente nasce AT con la data operativa come attivazione (la regola del backend); con uno stato indicato le date sono di chi chiama e le pretende trgfn_clienti_guard_stato_date (il modello non dice ancora in quali stati un cliente puo'' nascere: D32). La riga si rilegge a istruzione finita per billing_account_id (sotto la RLS). BA esistente insieme ai campi di un BA o di un''istanza nuovi o a un emittente, o ne'' BA ne'' utility: E_SCRIPT_CHIAMATA_NON_VALIDA. Il resto lo dicono guard e vincoli (FK composte della fornitura, uq_clienti_billing_account, amministratore globale sul BA). Non controlla il permesso (backend); una utility che richiede il PDP, senza PDP, la rifiuta trgfn_clienti_sync_pdp. INVOKER. Ritorna (cliente_id, billing_account_id, istanza_utility_id, soggetto_ruolo_id). Prende il posto di ClientiService._execute_creazione (2b-2) e dell''INSERT di dbops.fn_pgtap_crea_cliente. Brief: brief-db-processi-accensione-per-ambiente (2b-1, lotto 5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
