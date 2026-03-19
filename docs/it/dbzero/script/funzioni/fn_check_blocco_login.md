{% include-markdown "it/dbzero/script/manual/fn_check_blocco_login.md" %}
# ⚙️ Funzione `fn_check_blocco_login`

```sql
CREATE FUNCTION fn_check_blocco_login(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_blocco_login(p_auth_user_id integer)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_bloccato_fino_a  anagrafiche.risorse_umane_auth_user.bloccato_fino_a%TYPE;
    v_minuti_rimanenti integer;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Verifica se l'utente e' bloccato per tentativi falliti.
    --   Se bloccato_fino_a e' scaduto, resetta automaticamente
    --   (tentativi_falliti = 0, bloccato_fino_a = NULL).
    --   Se blocco ancora attivo, lancia errore con minuti
    --   rimanenti.
    --   Da chiamare PRIMA di verificare le credenziali.
    --
    -- Parametri:
    --   p_auth_user_id: ID utente Django (auth_user.id)
    --
    -- Errori:
    --   E_UTENTE_BLOCCATO: blocco attivo
    -- =========================================================

    -- Guard
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        RETURN;
    END IF;

    -- Leggi stato blocco
    SELECT rau.bloccato_fino_a
      INTO v_bloccato_fino_a
      FROM anagrafiche.risorse_umane_auth_user rau
     WHERE rau.auth_user_id = p_auth_user_id;

    -- Nessun record ponte o nessun blocco
    IF v_bloccato_fino_a IS NULL THEN
        RETURN;
    END IF;

    -- Blocco scaduto: reset automatico
    IF v_bloccato_fino_a <= NOW() THEN
        UPDATE anagrafiche.risorse_umane_auth_user
           SET tentativi_falliti = 0,
               bloccato_fino_a  = NULL
         WHERE auth_user_id = p_auth_user_id;
        RETURN;
    END IF;

    -- Blocco attivo: calcola minuti rimanenti e lancia errore
    v_minuti_rimanenti := GREATEST(1,
        CEIL(EXTRACT(EPOCH FROM (v_bloccato_fino_a - NOW())) / 60)::integer
    );

    PERFORM script.fn_log_and_raise_error(
        'database', 'script.fn_check_blocco_login',
        'E_UTENTE_BLOCCATO',
        jsonb_build_object('auth_user_id', p_auth_user_id,
                          'bloccato_fino_a', v_bloccato_fino_a,
                          'minuti_rimanenti', v_minuti_rimanenti),
        NULL::uuid,
        'Utente temporaneamente bloccato. Riprovare tra ' || v_minuti_rimanenti || ' minuti.'
    );
END;
$function$

COMMENT ON FUNCTION script.fn_check_blocco_login(p_auth_user_id integer)
IS 'Verifica blocco temporaneo login. Se scaduto resetta. Se attivo lancia E_UTENTE_BLOCCATO con minuti rimanenti. Chiamare PRIMA della verifica credenziali.';
```

---
{% include-markdown "signature-core.md" %}
