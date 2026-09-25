{% include-markdown "it/dbzero/script/manual/fn_check_azione_processo.md" %}
# ⚙️ Funzione `fn_check_azione_processo`

```sql
CREATE FUNCTION fn_check_azione_processo(p_auth_user_id integer, p_permission_codename character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_azione_processo(p_auth_user_id integer, p_permission_codename character varying)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_abilitata   config.user_override_azioni.abilitata%TYPE;
    v_ctx_ruolo   anagrafiche.identita_digitali.ruolo_applicativo%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Verifica azione di processo abilitata per l'utente.
    --
    -- Catena (context-aware dal 21-04-2026):
    --   0. Gate GUC: se app.ruolo_applicativo popolata e
    --      != OPERATORE -> false (fail-closed).
    --   1. Assenza identita OPERATORE attiva -> false
    --   2. fn_is_super_admin -> true
    --   3. Override utente azione (se valido)
    --   4. Ereditato dal profilo: fn_get_permessi_ereditati_azioni
    --      (sola veste OPERATORE; AD_HOC 1 > REPARTO 2 > PORTALE 3)
    --   5. Default -> false (negata)
    -- Rev 20260925-84: il passo 4 non riscrive lo spareggio, lo
    -- legge dal building block (sede unica, D-2) — e con esso la
    -- veste OPERATORE (D-1).
    -- =========================================================

    -- 0. Gate contesto GUC (fail-closed su non-OPERATORE).
    v_ctx_ruolo := NULLIF(
        current_setting('app.ruolo_applicativo', true), ''
    )::config.ruolo_applicativo;

    IF v_ctx_ruolo IS NOT NULL
       AND v_ctx_ruolo <> 'OPERATORE'::config.ruolo_applicativo THEN
        RETURN false;
    END IF;

    -- 1. Identita OPERATORE attiva.
    IF NOT script.fn_has_identita_attiva(
               p_auth_user_id,
               'OPERATORE'::config.ruolo_applicativo) THEN
        RETURN false;
    END IF;

    -- 2. Super admin? Bypass totale.
    IF script.fn_is_super_admin(p_auth_user_id) THEN
        RETURN true;
    END IF;

    -- 3. Override utente azione (invariato).
    SELECT uoa.abilitata
      INTO v_abilitata
      FROM config.user_override_azioni uoa
      JOIN config.azioni_processo ap ON ap.id = uoa.azione_id
     WHERE uoa.auth_user_id = p_auth_user_id
       AND ap.permission_codename = p_permission_codename
       AND (uoa.valido_dal IS NULL OR uoa.valido_dal <= CURRENT_DATE)
       AND (uoa.valido_al  IS NULL OR uoa.valido_al  >= CURRENT_DATE);

    IF FOUND THEN
        RETURN v_abilitata;
    END IF;

    -- 4. Ereditato dal profilo: una riga al massimo per azione
    --    (DISTINCT ON nel building block, permission_codename unico).
    SELECT e.abilitata
      INTO v_abilitata
      FROM script.fn_get_permessi_ereditati_azioni(p_auth_user_id) e
      JOIN config.azioni_processo ap
        ON ap.id = e.azione_id
     WHERE ap.permission_codename = p_permission_codename;

    IF FOUND THEN
        RETURN v_abilitata;
    END IF;

    -- 5. Default sicuro.
    RETURN false;
END
$function$

COMMENT ON FUNCTION script.fn_check_azione_processo(p_auth_user_id integer, p_permission_codename character varying)
IS 'Verifica se un''azione di processo e'' abilitata per un utente. Catena: gate di contesto (app.ruolo_applicativo valorizzata e diversa da OPERATORE -> false), identita'' OPERATORE attiva, super admin -> true, override utente valido, ereditato dal profilo (script.fn_get_permessi_ereditati_azioni: sola veste OPERATORE, AD_HOC > REPARTO > PORTALE), default negata. Rev 20260925-84 (brief-db-pgtap-permessi-ereditati, D-1 e D-2): il passo 4 non riscrive lo spareggio e non conta piu'' i profili delle altre vesti dell''utente.';
```

---
{% include-markdown "signature-core.md" %}
