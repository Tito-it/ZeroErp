{% include-markdown "it/dbzero/script/manual/fn_check_operatore_invitabile.md" %}
# ⚙️ Funzione `fn_check_operatore_invitabile`

```sql
CREATE FUNCTION fn_check_operatore_invitabile(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_operatore_invitabile(p_auth_user_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_is_active        BOOLEAN;
    v_email            VARCHAR(254);
    v_last_login       TIMESTAMPTZ;
    v_identita_attiva  BOOLEAN;
    v_ruolo_applicativo config.ruolo_applicativo;
    v_identita_in_finestra BOOLEAN;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Verifica se un operatore puo' ricevere un invito email
    --   per il primo accesso al sistema.
    --
    -- Condizioni (refactor §4.6.B.10):
    --   1. auth_user esiste e is_active = true
    --   2. identita_digitali OPERATORE attiva esiste
    --   3. ruolo_applicativo <> 'DISABILITATO'
    --   4. identita nella finestra temporale
    --   5. auth_user ha un indirizzo email
    --   6. auth_user.last_login IS NULL (mai loggato)
    --
    -- Ritorna:
    --   JSONB: {invitabile: bool, motivo: text, email: text}
    -- =========================================================

    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'motivo', 'auth_user_id non valido',
            'email', NULL
        );
    END IF;

    -- Recupera dati auth_user + identita OPERATORE in una
    -- sola query. LEFT JOIN: la riga identita puo' mancare
    -- (caso iniziale prima del backfill §4.6.E).
    SELECT au.is_active,
           au.email,
           au.last_login,
           id.attivo,
           id.ruolo_applicativo,
           CASE
               WHEN id.id IS NULL THEN NULL
               ELSE (id.valido_dal IS NULL OR id.valido_dal <= CURRENT_DATE)
                AND (id.valido_al  IS NULL OR id.valido_al  >= CURRENT_DATE)
           END
      INTO v_is_active, v_email, v_last_login,
           v_identita_attiva, v_ruolo_applicativo,
           v_identita_in_finestra
      FROM django.auth_user au
      LEFT JOIN anagrafiche.identita_digitali id
        ON id.auth_user_id = au.id
       AND id.ruolo_applicativo = 'OPERATORE'
     WHERE au.id = p_auth_user_id;

    IF v_is_active IS NULL THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'motivo', 'Utente non trovato',
            'email', NULL
        );
    END IF;

    -- Verifica identita PRIMA di is_active: identita attivo=false
    -- causa is_active=false via trigger sync, il motivo primario
    -- e' identita non attiva.
    IF v_identita_attiva IS NULL THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'motivo', 'Nessuna identita OPERATORE',
            'email', v_email
        );
    END IF;

    IF v_identita_attiva = false THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'motivo', 'Identita OPERATORE non attiva',
            'email', v_email
        );
    END IF;

    IF v_ruolo_applicativo = 'DISABILITATO' THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'motivo', 'Ruolo applicativo DISABILITATO',
            'email', v_email
        );
    END IF;

    IF NOT v_identita_in_finestra THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'motivo', 'Identita fuori finestra temporale',
            'email', v_email
        );
    END IF;

    -- is_active=false senza identita inattiva: disattivazione
    -- diretta su auth_user (non causata dal trigger sync).
    IF v_is_active = false THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'motivo', 'Utente disattivato (is_active=false)',
            'email', v_email
        );
    END IF;

    IF v_email IS NULL OR trim(v_email) = '' THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'motivo', 'Nessun indirizzo email configurato',
            'email', NULL
        );
    END IF;

    IF v_last_login IS NOT NULL THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'motivo', 'Utente ha gia'' effettuato login',
            'email', v_email
        );
    END IF;

    RETURN jsonb_build_object(
        'invitabile', true,
        'motivo', NULL,
        'email', v_email
    );
END;
$function$

COMMENT ON FUNCTION script.fn_check_operatore_invitabile(p_auth_user_id integer)
IS 'Verifica se operatore e'' invitabile. Refactor §4.6.B.10: source of truth = identita_digitali (ruolo_applicativo=OPERATORE) invece del bridge legacy.';
```

---
{% include-markdown "signature-core.md" %}
