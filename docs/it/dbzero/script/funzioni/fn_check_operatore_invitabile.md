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
    -- Tipi espliciti: colonne di django.auth_user (niente %TYPE su Django).
    v_trovato          boolean;
    v_email            VARCHAR(254);
    v_n_vesti          integer;
    v_veste_attiva     boolean;
    v_in_finestra      boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire se un operatore puo' ricevere l'invito che ACCENDE
    --   la sua veste OPERATORE (regola unica dell'invito,
    --   rev 20260925-43: la veste nasce spenta, la accende
    --   l'attivazione; il reinvito riapre una veste spenta).
    --
    -- Condizioni:
    --   1. auth_user valido ed esistente
    --   2. almeno una veste OPERATORE
    --   3. nessuna veste OPERATORE gia' attiva (D-8)
    --   4. la veste nella sua finestra temporale
    --   5. auth_user ha un indirizzo email
    --   ⛔ NON contano piu': last_login (D-8) e is_active
    --      (derivato dalle vesti: false per costruzione).
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

    -- Credenziale + le sue vesti OPERATORE, AGGREGATE: il modello
    -- ammette piu' vesti spente sulla stessa credenziale, e
    -- prenderne una a caso deciderebbe per la prima che capita.
    SELECT true,
           au.email,
           count(idg.id),
           bool_or(idg.attivo),
           bool_or(    (idg.valido_dal IS NULL OR idg.valido_dal <= CURRENT_DATE)
                   AND (idg.valido_al  IS NULL OR idg.valido_al  >= CURRENT_DATE))
      INTO v_trovato, v_email, v_n_vesti, v_veste_attiva, v_in_finestra
      FROM django.auth_user au
      LEFT JOIN anagrafiche.identita_digitali idg
        ON idg.auth_user_id = au.id
       AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
     WHERE au.id = p_auth_user_id
     GROUP BY au.email;

    IF v_trovato IS NULL THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'motivo', 'Utente non trovato',
            'email', NULL
        );
    END IF;

    IF v_n_vesti = 0 THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'motivo', 'Nessuna identita OPERATORE',
            'email', v_email
        );
    END IF;

    -- ⛔ D-8: veste gia' attiva → rifiuto. L'accesso c'e' gia': per
    --   una password dimenticata c'e' il reset, non l'invito.
    IF v_veste_attiva THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'motivo', 'Veste OPERATORE gia'' attiva',
            'email', v_email
        );
    END IF;

    IF NOT v_in_finestra THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'motivo', 'Identita fuori finestra temporale',
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

    RETURN jsonb_build_object(
        'invitabile', true,
        'motivo', NULL,
        'email', v_email
    );
END;
$function$

COMMENT ON FUNCTION script.fn_check_operatore_invitabile(p_auth_user_id integer)
IS 'Dice se un operatore puo'' ricevere l''invito che ACCENDE la sua veste OPERATORE. ⭐ Rev 20260925-43 (brief-db-blocco-login-per-credenziale §12; R-1 del piano BE/FE, D-8): regola unica dell''invito — la veste nasce spenta (fn_crea_operatore_v2) e la accende l''attivazione; il reinvito riapre una veste spenta (D-3). Invitabile se: credenziale esistente, almeno una veste OPERATORE, NESSUNA veste OPERATORE gia'' attiva (veste attiva -> rifiuto), veste nella sua finestra, email presente. Non contano piu'' last_login (D-8) ne'' is_active (derivato dalle vesti, false per costruzione con la sola veste spenta). Le vesti OPERATORE della credenziale si aggregano (il modello ne ammette piu'' d''una spenta). Ritorna jsonb {invitabile, motivo, email}; motivo lo legge fn_get_operatore_detail come invite_reason.';
```

---
{% include-markdown "signature-core.md" %}
