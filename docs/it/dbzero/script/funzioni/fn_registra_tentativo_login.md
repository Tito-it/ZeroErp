{% include-markdown "it/dbzero/script/manual/fn_registra_tentativo_login.md" %}
# ⚙️ Funzione `fn_registra_tentativo_login`

```sql
CREATE FUNCTION fn_registra_tentativo_login(p_auth_user_id integer, p_successo boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_registra_tentativo_login(p_auth_user_id integer, p_successo boolean)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_max_tentativi    integer;
    v_blocco_minuti    integer;
    v_tentativi        smallint;
    v_bloccato         boolean := false;
    v_bloccato_fino_a  timestamptz;
BEGIN
    -- =========================================================
    -- Scopo (refactor §4.6.D.1):
    --   Registra l'esito di un tentativo di login sul nuovo
    --   bridge identita_digitali (OPERATORE). Doppio UPDATE
    --   su risorse_umane_auth_user mantenuto finche' la
    --   vista §4.6.F non sostituisce il legacy (§4.6.H).
    -- =========================================================

    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        RETURN jsonb_build_object(
            'bloccato', false,
            'minuti_rimanenti', 0,
            'tentativi', 0
        );
    END IF;

    -- Verifica identita OPERATORE esistente (fonte primaria)
    IF NOT EXISTS (
        SELECT 1 FROM anagrafiche.identita_digitali
         WHERE auth_user_id = p_auth_user_id
           AND ruolo_applicativo = 'OPERATORE'
    ) THEN
        RETURN jsonb_build_object(
            'bloccato', false,
            'minuti_rimanenti', 0,
            'tentativi', 0
        );
    END IF;

    IF p_successo THEN
        -- Login riuscito: reset contatore su entrambe
        UPDATE anagrafiche.identita_digitali
           SET tentativi_falliti = 0,
               bloccato_fino_a   = NULL
         WHERE auth_user_id = p_auth_user_id
           AND ruolo_applicativo = 'OPERATORE';

        UPDATE anagrafiche.risorse_umane_auth_user
           SET tentativi_falliti = 0,
               bloccato_fino_a   = NULL
         WHERE auth_user_id = p_auth_user_id;

        RETURN jsonb_build_object(
            'bloccato', false,
            'minuti_rimanenti', 0,
            'tentativi', 0
        );
    END IF;

    -- Login fallito: leggi configurazione
    v_max_tentativi := COALESCE(
        (SELECT p.default_value::integer
           FROM config.parameters p
          WHERE p.code = 'login_max_tentativi_falliti'),
        5
    );

    v_blocco_minuti := COALESCE(
        (SELECT p.default_value::integer
           FROM config.parameters p
          WHERE p.code = 'login_blocco_minuti'),
        15
    );

    -- Incrementa su identita_digitali (fonte primaria)
    UPDATE anagrafiche.identita_digitali
       SET tentativi_falliti = tentativi_falliti + 1
     WHERE auth_user_id = p_auth_user_id
       AND ruolo_applicativo = 'OPERATORE'
    RETURNING tentativi_falliti INTO v_tentativi;

    -- Sync legacy RUA (rimovibile al cutover §4.6.H)
    UPDATE anagrafiche.risorse_umane_auth_user
       SET tentativi_falliti = v_tentativi
     WHERE auth_user_id = p_auth_user_id;

    -- Verifica soglia
    IF v_tentativi >= v_max_tentativi THEN
        v_bloccato_fino_a := NOW() + (v_blocco_minuti || ' minutes')::interval;
        v_bloccato := true;

        UPDATE anagrafiche.identita_digitali
           SET bloccato_fino_a = v_bloccato_fino_a
         WHERE auth_user_id = p_auth_user_id
           AND ruolo_applicativo = 'OPERATORE';

        UPDATE anagrafiche.risorse_umane_auth_user
           SET bloccato_fino_a = v_bloccato_fino_a
         WHERE auth_user_id = p_auth_user_id;
    END IF;

    RETURN jsonb_build_object(
        'bloccato', v_bloccato,
        'minuti_rimanenti', CASE WHEN v_bloccato THEN v_blocco_minuti ELSE 0 END,
        'tentativi', v_tentativi
    );
END;
$function$

COMMENT ON FUNCTION script.fn_registra_tentativo_login(p_auth_user_id integer, p_successo boolean)
IS 'Registra esito tentativo login. Refactor §4.6.D.1: source of truth = identita_digitali OPERATORE; doppio UPDATE su RUA legacy mantenuto fino a cutover §4.6.H. Successo: reset. Fallimento: incrementa, se >= max blocca per N minuti.';
```

---
{% include-markdown "signature-core.md" %}
