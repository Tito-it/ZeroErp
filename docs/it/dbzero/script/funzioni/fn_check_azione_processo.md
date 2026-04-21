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
    v_ctx_ruolo   config.ruolo_applicativo;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Verifica azione di processo abilitata per l'utente.
    --
    -- Catena (post PR-B 21-04-2026, context-aware):
    --   0. Gate GUC: se app.ruolo_applicativo popolata e
    --      != OPERATORE -> false (fail-closed).
    --   1. Assenza identita OPERATORE attiva -> false
    --   2. fn_is_super_admin -> true
    --   3. Override utente azione (se valido)
    --   4. Azione via fn_get_profili_accesso_applicabili
    --   5. Default -> false (negata)
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

    -- 4. Azione via bindings (helper, 1-arg -> default NULL).
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

    -- 5. Default sicuro.
    RETURN false;
END
$function$

COMMENT ON FUNCTION script.fn_check_azione_processo(p_auth_user_id integer, p_permission_codename character varying)
IS 'Verifica se azione abilitata per utente. Context-aware (post PR-B 21-04-2026): gate GUC app.ruolo_applicativo != OPERATORE -> false. Altrimenti catena legacy: has_identita, fn_is_super_admin, override, azione via helper.';
```

---
{% include-markdown "signature-core.md" %}
