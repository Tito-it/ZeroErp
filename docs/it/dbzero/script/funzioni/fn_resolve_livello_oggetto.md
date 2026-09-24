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
    v_livello   config.user_override_oggetti.livello%TYPE;
    v_ctx_ruolo anagrafiche.identita_digitali.ruolo_applicativo%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Risolve il livello di accesso per un singolo model
    --   Django (app_label + model_name). Se esiste un override
    --   oggetto lo usa, altrimenti risale alla catena area
    --   via fn_resolve_livello_area.
    --
    -- Catena (rev 2026-09-24, gate di contesto):
    --   0. Gate GUC: se app.ruolo_applicativo popolata e
    --      != OPERATORE -> BLOCCATO (fail-closed), come
    --      fn_resolve_livello_area.
    --   1. Assenza identita OPERATORE attiva -> BLOCCATO
    --   2. fn_is_super_admin -> TUTTO
    --   3. Override utente oggetto (se valido)
    --   4. Fallback -> fn_resolve_livello_area
    -- =========================================================

    -- 0. Gate contesto GUC (fail-closed su non-OPERATORE).
    v_ctx_ruolo := NULLIF(
        current_setting('app.ruolo_applicativo', true), ''
    )::config.ruolo_applicativo;

    IF v_ctx_ruolo IS NOT NULL
       AND v_ctx_ruolo <> 'OPERATORE'::config.ruolo_applicativo THEN
        RETURN 'BLOCCATO'::config.livello_accesso;
    END IF;

    -- 1. Identita OPERATORE attiva.
    IF NOT script.fn_has_identita_attiva(
               p_auth_user_id,
               'OPERATORE'::config.ruolo_applicativo) THEN
        RETURN 'BLOCCATO'::config.livello_accesso;
    END IF;

    -- 2. Super admin? Bypass totale.
    IF script.fn_is_super_admin(p_auth_user_id) THEN
        RETURN 'TUTTO'::config.livello_accesso;
    END IF;

    -- 3. Override utente oggetto.
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

    -- 4. Fallback alla catena area.
    RETURN script.fn_resolve_livello_area(p_auth_user_id, p_area_schema_db);
END
$function$

COMMENT ON FUNCTION script.fn_resolve_livello_oggetto(p_auth_user_id integer, p_app_label character varying, p_model_name character varying, p_area_schema_db character varying)
IS 'Risolve il livello di accesso per un model (app_label + model_name): override utente per oggetto, altrimenti la catena d''area (fn_resolve_livello_area). Context-aware: app.ruolo_applicativo valorizzata e diversa da OPERATORE -> BLOCCATO (passo 0, come fn_resolve_livello_area; mancava dal 20260421-04 ed e'' stato aggiunto il 2026-09-24, brief-db-magazzino-verbi-con-permesso §2.4). Poi: identita'' OPERATORE attiva, super admin, override per oggetto valido, fallback d''area. La chiama il backend per gli endpoint con un model (PermissionResolver.get_livello_oggetto).';
```

---
{% include-markdown "signature-core.md" %}
