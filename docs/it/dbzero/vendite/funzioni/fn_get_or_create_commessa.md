{% include-markdown "it/dbzero/vendite/manual/fn_get_or_create_commessa.md" %}
# ⚙️ Funzione `fn_get_or_create_commessa`

```sql
CREATE FUNCTION fn_get_or_create_commessa(p_billing_account_id bigint, p_utility_id integer, p_tipo_commessa character varying, p_policy_fatturazione character varying, p_fatturazione_immediata boolean, p_priorita_operativa character varying, p_emittente_soggetto_ruolo_id bigint, p_competenza_dal date, p_competenza_al date, p_meta jsonb, p_force_new boolean, p_termine_pagamento_id bigint, p_modalita_pagamento_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_or_create_commessa(p_billing_account_id bigint, p_utility_id integer, p_tipo_commessa character varying DEFAULT 'AUTO'::character varying, p_policy_fatturazione character varying DEFAULT 'DA_DOCUMENTO'::character varying, p_fatturazione_immediata boolean DEFAULT false, p_priorita_operativa character varying DEFAULT 'NORMALE'::character varying, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_competenza_dal date DEFAULT NULL::date, p_competenza_al date DEFAULT NULL::date, p_meta jsonb DEFAULT '{}'::jsonb, p_force_new boolean DEFAULT false, p_termine_pagamento_id bigint DEFAULT NULL::bigint, p_modalita_pagamento_id integer DEFAULT NULL::integer)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: recupera o crea la commessa coerente con il contesto
--        dimensionale. Da D-R la chiave comprende anche le condizioni
--        di pagamento: un documento con termine diverso NON riusa una
--        commessa esistente, ne apre una nuova — cosi' la divergenza
--        emerge al push e non a valle, in fattura.
-- Regole: la chiave vive in TRE posti (hash del lock, WHERE del riuso,
--         INSERT) e i tre vanno tenuti identici. I due parametri nuovi
--         sono in coda e con DEFAULT NULL: nessun chiamante da adeguare
--         subito, e finche' passano NULL il comportamento e' quello di
--         prima.
DECLARE
    v_commessa_id vendite.commesse.id%TYPE;
    v_ba_utility  anagrafiche.billing_account.utility_id%TYPE;
    v_ba_found    BOOLEAN := FALSE;
    v_emittente   vendite.commesse.emittente_soggetto_ruolo_id%TYPE;
    v_codice      vendite.commesse.codice%TYPE;
BEGIN
    -- Guard: parametri obbligatori
    IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_billing_account_id', 'valore', p_billing_account_id),
            NULL::uuid, 'p_billing_account_id obbligatorio e > 0'
        );
    END IF;

    IF p_utility_id IS NULL OR p_utility_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_utility_id', 'valore', p_utility_id),
            NULL::uuid, 'p_utility_id obbligatorio e > 0'
        );
    END IF;

    IF p_competenza_dal IS NOT NULL AND p_competenza_al IS NOT NULL AND p_competenza_dal > p_competenza_al THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_DATA_AL_MINORE_DAL',
            jsonb_build_object('competenza_dal', p_competenza_dal, 'competenza_al', p_competenza_al),
            NULL::uuid, p_competenza_al::text, p_competenza_dal::text
        );
    END IF;

    -- Verifica BA
    SELECT ba.utility_id, TRUE INTO v_ba_utility, v_ba_found
      FROM anagrafiche.billing_account ba WHERE ba.id = p_billing_account_id;

    IF NOT v_ba_found THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_VALORE_MANCANTE',
            jsonb_build_object('billing_account_id', p_billing_account_id),
            NULL::uuid, concat('billing_account_id ', p_billing_account_id)
        );
    END IF;

    IF v_ba_utility IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_BILLING_ACCOUNT_UTILITY_NULL',
            jsonb_build_object('billing_account_id', p_billing_account_id),
            NULL::uuid, p_billing_account_id::text
        );
    END IF;

    IF v_ba_utility <> p_utility_id THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_or_create_commessa', 'E_CLIENTE_UTILITY_MISMATCH_BA',
            jsonb_build_object('billing_account_id', p_billing_account_id, 'ba_utility_id', v_ba_utility, 'utility_id', p_utility_id),
            NULL::uuid, p_billing_account_id::text, p_utility_id::text, v_ba_utility::text
        );
    END IF;

    -- Risolve emittente
    v_emittente := COALESCE(p_emittente_soggetto_ruolo_id, anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id));

    IF NOT p_force_new THEN
        -- SPECCHIO 1 — advisory lock sul contesto dimensionale.
        -- Le due dimensioni nuove entrano QUI: senza, due push
        -- concorrenti con termini diversi non si serializzerebbero
        -- e potrebbero creare due volte la stessa commessa.
        PERFORM pg_advisory_xact_lock(
            hashtext('fn_get_or_create_commessa'),
            hashtext(
                p_billing_account_id::text || E'\x1F' || p_utility_id::text || E'\x1F' ||
                p_tipo_commessa || E'\x1F' || p_policy_fatturazione || E'\x1F' ||
                p_fatturazione_immediata::text || E'\x1F' || p_priorita_operativa || E'\x1F' ||
                COALESCE(v_emittente::text, '') || E'\x1F' ||
                COALESCE(p_competenza_dal::text, '') || E'\x1F' || COALESCE(p_competenza_al::text, '') || E'\x1F' ||
                COALESCE(p_termine_pagamento_id::text, '') || E'\x1F' ||
                COALESCE(p_modalita_pagamento_id::text, '')
            )
        );

        -- SPECCHIO 2 — WHERE della commessa riusabile.
        -- ⚠️ IS NOT DISTINCT FROM sulle due nuove: sono NULL quasi
        -- sempre, e con `=` nessuna commessa verrebbe mai riusata.
        SELECT c.id INTO v_commessa_id
          FROM vendite.commesse c
          JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id AND sc.chiude_commessa = FALSE
         WHERE c.billing_account_id = p_billing_account_id
           AND c.utility_id = p_utility_id
           AND c.tipo_commessa = p_tipo_commessa
           AND c.policy_fatturazione = p_policy_fatturazione
           AND c.fatturazione_immediata = p_fatturazione_immediata
           AND c.priorita_operativa = p_priorita_operativa
           AND COALESCE(c.emittente_soggetto_ruolo_id, -1) = COALESCE(v_emittente, -1)
           AND c.competenza_dal IS NOT DISTINCT FROM p_competenza_dal
           AND c.competenza_al IS NOT DISTINCT FROM p_competenza_al
           AND c.termine_pagamento_id  IS NOT DISTINCT FROM p_termine_pagamento_id
           AND c.modalita_pagamento_id IS NOT DISTINCT FROM p_modalita_pagamento_id
         ORDER BY c.id DESC LIMIT 1;

        IF v_commessa_id IS NOT NULL THEN RETURN v_commessa_id; END IF;
    END IF;

    v_codice := 'CMM-' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS') || '-' || substr(md5(random()::text), 1, 6);

    -- SPECCHIO 3 — INSERT: la commessa nasce con la chiave completa.
    INSERT INTO vendite.commesse (codice, tipo_commessa, policy_fatturazione, fatturazione_immediata,
        priorita_operativa, billing_account_id, utility_id, emittente_soggetto_ruolo_id,
        competenza_dal, competenza_al, meta,
        termine_pagamento_id, modalita_pagamento_id)
    VALUES (v_codice, p_tipo_commessa, p_policy_fatturazione, p_fatturazione_immediata,
        p_priorita_operativa, p_billing_account_id, p_utility_id, v_emittente,
        p_competenza_dal, p_competenza_al, COALESCE(p_meta, '{}'::jsonb),
        p_termine_pagamento_id, p_modalita_pagamento_id)
    RETURNING id INTO v_commessa_id;

    RETURN v_commessa_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_or_create_commessa(p_billing_account_id bigint, p_utility_id integer, p_tipo_commessa character varying, p_policy_fatturazione character varying, p_fatturazione_immediata boolean, p_priorita_operativa character varying, p_emittente_soggetto_ruolo_id bigint, p_competenza_dal date, p_competenza_al date, p_meta jsonb, p_force_new boolean, p_termine_pagamento_id bigint, p_modalita_pagamento_id integer)
IS 'Recupera o crea commessa coerente con BA/utility e fallback emittente fiscale. Da D-R la chiave di raggruppamento comprende anche (termine_pagamento_id, modalita_pagamento_id): un documento sorgente con condizioni diverse apre una commessa NUOVA invece di riusarne una. Advisory lock previene la doppia creazione e include le stesse dimensioni del WHERE.';
```

---
{% include-markdown "signature-core.md" %}
