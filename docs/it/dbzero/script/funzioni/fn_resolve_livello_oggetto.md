{% include-markdown "it/dbzero/script/manual/fn_resolve_livello_oggetto.md" %}
# ⚙️ Funzione `fn_resolve_livello_oggetto`

```sql
CREATE FUNCTION fn_resolve_livello_oggetto(p_auth_user_id integer, p_app_label character varying, p_model_name character varying, p_area_schema_db character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_resolve_livello_oggetto(p_auth_user_id integer, p_app_label character varying, p_model_name character varying, p_area_schema_db character varying)
 RETURNS config.livello_accesso
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_livello config.user_override_oggetti.livello%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Risolve il livello di accesso per un singolo model
    --   Django (app_label + model_name). Se esiste un override
    --   oggetto lo usa, altrimenti risale alla catena area
    --   via fn_resolve_livello_area.
    --
    -- Catena (refactor §4.6.B.3):
    --   1. Assenza identita OPERATORE attiva -> BLOCCATO
    --   2. fn_is_super_admin -> TUTTO
    --   3. Override utente oggetto (se valido)
    --   4. Fallback -> fn_resolve_livello_area
    -- =========================================================

    -- 1. Identita OPERATORE attiva (helper DRY §4.6.B.0).
    IF NOT script.fn_has_identita_attiva(
               p_auth_user_id,
               'OPERATORE'::config.ruolo_applicativo) THEN
        RETURN 'BLOCCATO'::config.livello_accesso;
    END IF;

    -- 2. Super admin? Bypass totale.
    IF script.fn_is_super_admin(p_auth_user_id) THEN
        RETURN 'TUTTO'::config.livello_accesso;
    END IF;

    -- 3. Override utente oggetto (OPERATIVO)
    SELECT uoo.livello
      INTO v_livello
      FROM config.user_override_oggetti uoo
     WHERE uoo.auth_user_id = p_auth_user_id
       AND uoo.app_label    = p_app_label
       AND uoo.model_name   = p_model_name
       AND uoo.validita @> CURRENT_DATE;

    IF FOUND THEN
        RETURN v_livello;
    END IF;

    -- 4. Fallback alla catena area
    RETURN script.fn_resolve_livello_area(p_auth_user_id, p_area_schema_db);
END
$function$

COMMENT ON FUNCTION script.fn_resolve_livello_oggetto(p_auth_user_id integer, p_app_label character varying, p_model_name character varying, p_area_schema_db character varying)
IS 'Risolve livello accesso oggetto per utente. Refactor §4.6.B.3: ramo ADMIN -> fn_is_super_admin; ramo DISABILITATO -> check identita OPERATORE attiva. Fallback area invariato.';
```

---
{% include-markdown "signature-core.md" %}
