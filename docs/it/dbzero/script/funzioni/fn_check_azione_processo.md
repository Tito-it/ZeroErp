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
    v_abilitata config.user_override_azioni.abilitata%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Verifica se un'azione di processo e' abilitata per
    --   un utente. Funzione fn_check_*: puro boolean, no raise.
    --
    -- Catena (refactor §4.6.B.4 + §4.8):
    --   1. Assenza identita OPERATORE attiva -> false
    --   2. fn_is_super_admin -> true
    --   3. Override utente azione (se valido)
    --   4. Azione via fn_get_profili_accesso_applicabili
    --      (AD_HOC prio 1 > REPARTO/PORTALE prio 2)
    --   5. Default -> false (negata)
    -- =========================================================

    -- 1. Identita OPERATORE attiva (helper DRY §4.6.B.0).
    IF NOT script.fn_has_identita_attiva(
               p_auth_user_id,
               'OPERATORE'::config.ruolo_applicativo) THEN
        RETURN false;
    END IF;

    -- 2. Super admin? Bypass totale.
    IF script.fn_is_super_admin(p_auth_user_id) THEN
        RETURN true;
    END IF;

    -- 3. Override utente azione (invariato)
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

    -- 4. Azione via bindings (§4.8 nuovo modello).
    SELECT paz.abilitata
      INTO v_abilitata
      FROM script.fn_get_profili_accesso_applicabili(p_auth_user_id) h
      JOIN config.profili_accesso_azioni paz
        ON paz.profilo_accesso_id = h.profilo_accesso_id
      JOIN config.azioni_processo ap
        ON ap.id = paz.azione_id
     WHERE ap.permission_codename = p_permission_codename
     ORDER BY h.priorita
     LIMIT 1;

    IF FOUND THEN
        RETURN v_abilitata;
    END IF;

    -- 5. Default sicuro
    RETURN false;
END
$function$

COMMENT ON FUNCTION script.fn_check_azione_processo(p_auth_user_id integer, p_permission_codename character varying)
IS 'Verifica se azione e'' abilitata per l''utente. Refactor §4.6.B.4 + §4.8: ramo ADMIN -> fn_is_super_admin; ramo DISABILITATO -> check identita OPERATORE attiva; azione via bindings generalizzato (fn_get_profili_accesso_applicabili, AD_HOC > REPARTO/PORTALE).';
```

---
{% include-markdown "signature-core.md" %}
