{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_billing_account.md" %}
# ⚙️ Funzione `fn_crea_billing_account`

```sql
CREATE FUNCTION fn_crea_billing_account(p_soggetto_ruolo_id bigint, p_utility_id integer, p_campi jsonb, p_istanza_utility_id bigint, p_istanza jsonb, p_emittente_soggetto_ruolo_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_billing_account(p_soggetto_ruolo_id bigint, p_utility_id integer, p_campi jsonb DEFAULT '{}'::jsonb, p_istanza_utility_id bigint DEFAULT NULL::bigint, p_istanza jsonb DEFAULT '{}'::jsonb, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(billing_account_id bigint, istanza_utility_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_campi       jsonb := COALESCE(p_campi, '{}'::jsonb);
    v_istanza     jsonb := COALESCE(p_istanza, '{}'::jsonb);
    v_estranea    text;
    v_soggetto_id anagrafiche.soggetti_ruoli.soggetto_id%TYPE;
    v_ist_id      anagrafiche.billing_account.istanza_utility_id%TYPE := p_istanza_utility_id;
    v_ba_id       anagrafiche.billing_account.id%TYPE;
    v_link_sr     anagrafiche.emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id%TYPE;
    c_ammesse_ba  CONSTANT text[] := ARRAY[
        'categoria_cliente_id', 'codice', 'fatturazione_ordini',
        'parent_account_id', 'valuta_id'];
    c_ammesse_ist CONSTANT text[] := ARRAY['codice', 'indirizzo_dettaglio_id'];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Creare il billing account di un ruolo per una utility:
    --   l'istanza fittizia (se p_istanza_utility_id e' NULL, coi
    --   campi di p_istanza), il BA coi campi di p_campi (riletto
    --   a istruzione finita), il legame all'emittente se
    --   p_emittente_soggetto_ruolo_id e' indicato. Ritorna
    --   (billing_account_id, istanza_utility_id).
    --
    -- Regole:
    --   - chiave estranea: E_CAMPO_NON_AMMESSO; null = assente;
    --   - istanza esistente e campi di un'istanza nuova insieme,
    --     o un legame discorde: E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - il resto lo dicono i guard e i vincoli delle tabelle.
    -- =========================================================
    IF p_soggetto_ruolo_id IS NULL OR p_utility_id IS NULL
       OR jsonb_typeof(v_campi) <> 'object' OR jsonb_typeof(v_istanza) <> 'object'
       OR (p_istanza_utility_id IS NOT NULL AND v_istanza <> '{}'::jsonb) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_crea_billing_account', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('soggetto_ruolo_id',  p_soggetto_ruolo_id,
                               'utility_id',         p_utility_id,
                               'istanza_utility_id', p_istanza_utility_id,
                               'tipo_campi',         jsonb_typeof(v_campi),
                               'tipo_istanza',       jsonb_typeof(v_istanza)),
            NULL::uuid,
            'anagrafiche.fn_crea_billing_account',
            'ruolo o utility mancanti, campi non oggetti, o istanza esistente con i campi di una nuova');
    END IF;

    v_estranea := COALESCE(script.fn_prima_chiave_estranea(v_campi, c_ammesse_ba),
                           script.fn_prima_chiave_estranea(v_istanza, c_ammesse_ist));
    IF v_estranea IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_crea_billing_account', 'E_CAMPO_NON_AMMESSO',
            jsonb_build_object('campo', v_estranea, 'soggetto_ruolo_id', p_soggetto_ruolo_id),
            NULL::uuid,
            v_estranea);
    END IF;

    SELECT sr.soggetto_id
      INTO v_soggetto_id
      FROM anagrafiche.soggetti_ruoli sr
     WHERE sr.id = p_soggetto_ruolo_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'anagrafiche.fn_crea_billing_account', 'E_SOGGETTO_RUOLO_NON_TROVATO',
            jsonb_build_object('soggetto_ruolo_id', p_soggetto_ruolo_id),
            NULL::uuid,
            p_soggetto_ruolo_id::text);
    END IF;

    -- 1. L'istanza fittizia, se non se ne indica una.
    IF v_ist_id IS NULL THEN
        v_ist_id := (script.fn_scrivi_riga_da_jsonb(
                         'anagrafiche.istanze_utilities'::regclass,
                         jsonb_strip_nulls(v_istanza)
                         || jsonb_build_object('soggetto_id', v_soggetto_id,
                                               'fittizia',    true))
                     ->> 'id')::bigint;
    END IF;

    -- 2. Il BA, riletto a istruzione finita per la coppia
    --    (uq_billing_instance_utility): sotto la RLS la riga si
    --    vede solo dopo il legame scritto dal trigger AFTER.
    v_ba_id := (script.fn_scrivi_riga_da_jsonb(
                    'anagrafiche.billing_account'::regclass,
                    jsonb_strip_nulls(v_campi)
                    || jsonb_build_object('istanza_utility_id', v_ist_id,
                                          'soggetto_ruolo_id',  p_soggetto_ruolo_id,
                                          'utility_id',         p_utility_id),
                    NULL,
                    ARRAY['istanza_utility_id', 'utility_id'])
                ->> 'id')::bigint;

    -- 3. Il legame all'emittente, se chiesto. is_default = false:
    --    e' il legame di QUESTO BA, non il default dell'installazione.
    IF p_emittente_soggetto_ruolo_id IS NOT NULL THEN
        SELECT efba.emittente_soggetto_ruolo_id
          INTO v_link_sr
          FROM anagrafiche.emittenti_fiscali_billing_account efba
         WHERE efba.billing_account_id = v_ba_id;

        IF v_link_sr IS NULL THEN
            INSERT INTO anagrafiche.emittenti_fiscali_billing_account
                (emittente_soggetto_ruolo_id, billing_account_id, is_default)
            VALUES (p_emittente_soggetto_ruolo_id, v_ba_id, false);
        ELSIF v_link_sr <> p_emittente_soggetto_ruolo_id THEN
            -- Con un operatore in sessione il trigger z90 l'ha gia'
            -- legato all'emittente di chi agisce.
            PERFORM script.fn_log_and_raise_error(
                'anagrafiche', 'anagrafiche.fn_crea_billing_account', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
                jsonb_build_object('billing_account_id',       v_ba_id,
                                   'emittente_legato',         v_link_sr,
                                   'emittente_chiesto',        p_emittente_soggetto_ruolo_id),
                NULL::uuid,
                'anagrafiche.fn_crea_billing_account',
                'il BA e'' gia'' legato all''emittente di chi agisce, non a quello chiesto');
        END IF;
    END IF;

    RETURN QUERY SELECT v_ba_id, v_ist_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_billing_account(p_soggetto_ruolo_id bigint, p_utility_id integer, p_campi jsonb, p_istanza_utility_id bigint, p_istanza jsonb, p_emittente_soggetto_ruolo_id bigint)
IS 'BB (2026-10-18): crea il billing account di un ruolo per una utility, in una sola istruzione. Se p_istanza_utility_id e'' NULL nasce l''istanza utility fittizia del soggetto del ruolo, coi campi di p_istanza (codice, indirizzo_dettaglio_id); con un''istanza indicata p_istanza deve essere vuoto. Il BA coi campi di p_campi (categoria_cliente_id, codice, fatturazione_ordini, parent_account_id, valuta_id; le assenti e le null al DEFAULT, il codice lo genera il trigger; la categoria non ha default: risponde il NOT NULL), riletto a istruzione finita per (istanza_utility_id, utility_id) con script.fn_scrivi_riga_da_jsonb(..., p_rileggi_per): sotto la RLS il BA si vede solo dopo il legame scritto dal trigger AFTER z90_link_ef. Se p_emittente_soggetto_ruolo_id e'' indicato il BA si lega a quell''emittente (is_default = false); se z90 lo ha gia'' legato a un altro (operatore in sessione): E_SCRIPT_CHIAMATA_NON_VALIDA. Chiave estranea: E_CAMPO_NON_AMMESSO; ruolo inesistente: E_SOGGETTO_RUOLO_NON_TROVATO; chiamata malformata: E_SCRIPT_CHIAMATA_NON_VALIDA. Il resto (amministratore globale, coerenza soggetto/istanza, albero, unicita'') lo dicono i guard e i vincoli. Non cambia il modo dei vincoli: l''istanza vuole un satellite al commit (vincolo differito), e la finestra e'' di chi chiama. Limite: il guard z95 (un''istanza ha i BA di una sola azienda) scatta all''INSERT, prima del legame chiesto; senza sessione un secondo BA con un emittente esplicito su un''istanza esistente non passa (con la sessione il legame lo scrive z90, prima di z95). INVOKER. Ritorna (billing_account_id, istanza_utility_id). Prende il posto dei passi 2 e 3 di ClientiService._execute_creazione (2b-2, via anagrafiche.fn_crea_cliente) e degli INSERT di dbops.fn_pgtap_crea_cliente_ba. Brief: brief-db-processi-accensione-per-ambiente (2b-1, lotto 5).';
```

</div>

---
{% include-markdown "signature-core.md" %}
