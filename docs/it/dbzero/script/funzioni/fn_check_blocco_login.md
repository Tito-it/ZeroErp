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
    v_bloccato_fino_a  timestamptz;
    v_minuti_rimanenti integer;
BEGIN
    -- =========================================================
    -- Scopo (refactor §4.6.D.2):
    --   Verifica blocco temporaneo login su identita_digitali
    --   (OPERATORE). Se scaduto: auto-unlock su entrambe le
    --   tabelle. Se attivo: raise E_UTENTE_BLOCCATO.
    -- =========================================================

    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        RETURN;
    END IF;

    -- Leggi stato blocco da identita (fonte primaria)
    SELECT id.bloccato_fino_a
      INTO v_bloccato_fino_a
      FROM anagrafiche.identita_digitali id
     WHERE id.auth_user_id = p_auth_user_id
       AND id.ruolo_applicativo = 'OPERATORE';

    -- Nessun record identita o nessun blocco
    IF v_bloccato_fino_a IS NULL THEN
        RETURN;
    END IF;

    -- Blocco scaduto: auto-unlock su entrambe
    IF v_bloccato_fino_a <= NOW() THEN
        UPDATE anagrafiche.identita_digitali
           SET tentativi_falliti = 0,
               bloccato_fino_a   = NULL
         WHERE auth_user_id = p_auth_user_id
           AND ruolo_applicativo = 'OPERATORE';

        UPDATE anagrafiche.risorse_umane_auth_user
           SET tentativi_falliti = 0,
               bloccato_fino_a   = NULL
         WHERE auth_user_id = p_auth_user_id;
        RETURN;
    END IF;

    -- Blocco attivo: calcola minuti rimanenti e raise
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
IS 'Verifica blocco temporaneo login. Refactor §4.6.D.2: lettura da identita_digitali OPERATORE; auto-unlock su identita + RUA durante transizione. Se attivo: raise E_UTENTE_BLOCCATO.';
```

---
{% include-markdown "signature-core.md" %}
