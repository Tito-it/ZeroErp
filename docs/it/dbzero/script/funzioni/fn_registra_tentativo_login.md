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
    -- Scopo (post-cutover §13.3):
    --   Registra l'esito di un tentativo di login su
    --   anagrafiche.identita_digitali (OPERATORE).
    --   Unica fonte di verita': nessuno scrive piu' su RUA
    --   (che e' ora una vista read-only).
    -- =========================================================

    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        RETURN jsonb_build_object(
            'bloccato', false,
            'minuti_rimanenti', 0,
            'tentativi', 0
        );
    END IF;

    -- Guard: identita OPERATORE deve esistere
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
        -- Login riuscito: reset contatore
        UPDATE anagrafiche.identita_digitali
           SET tentativi_falliti = 0,
               bloccato_fino_a   = NULL
         WHERE auth_user_id = p_auth_user_id
           AND ruolo_applicativo = 'OPERATORE';

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

    -- Incrementa su identita_digitali (unica fonte)
    UPDATE anagrafiche.identita_digitali
       SET tentativi_falliti = tentativi_falliti + 1
     WHERE auth_user_id = p_auth_user_id
       AND ruolo_applicativo = 'OPERATORE'
    RETURNING tentativi_falliti INTO v_tentativi;

    -- Verifica soglia
    IF v_tentativi >= v_max_tentativi THEN
        v_bloccato_fino_a := NOW() + (v_blocco_minuti || ' minutes')::interval;
        v_bloccato := true;

        UPDATE anagrafiche.identita_digitali
           SET bloccato_fino_a = v_bloccato_fino_a
         WHERE auth_user_id = p_auth_user_id
           AND ruolo_applicativo = 'OPERATORE';
    END IF;

    RETURN jsonb_build_object(
        'bloccato', v_bloccato,
        'minuti_rimanenti', CASE WHEN v_bloccato THEN v_blocco_minuti ELSE 0 END,
        'tentativi', v_tentativi
    );
END;
$function$

COMMENT ON FUNCTION script.fn_registra_tentativo_login(p_auth_user_id integer, p_successo boolean)
IS 'Registra esito tentativo login su anagrafiche.identita_digitali (post-cutover §13.3, unica fonte di verita'': RUA e'' ora vista read-only). Successo: reset tentativi. Fallimento: incrementa, se >= max blocca per N minuti. Ritorna jsonb con stato blocco.';
```

---
{% include-markdown "signature-core.md" %}
