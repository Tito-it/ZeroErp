{% include-markdown "it/dbzero/script/manual/fn_resolve_livello_area.md" %}
# ⚙️ Funzione `fn_resolve_livello_area`

```sql
CREATE FUNCTION fn_resolve_livello_area(p_auth_user_id integer, p_area_schema_db character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_resolve_livello_area(p_auth_user_id integer, p_area_schema_db character varying)
 RETURNS config.livello_accesso
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_livello    config.user_override_aree.livello%TYPE;
    v_ctx_ruolo  config.ruolo_applicativo;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Risolve livello accesso area per un'area funzionale.
    --
    -- Catena (post PR-B 21-04-2026, context-aware):
    --   0. Gate GUC: se app.ruolo_applicativo popolata e
    --      != OPERATORE -> BLOCCATO (fail-closed).
    --   1. Assenza identita OPERATORE attiva -> BLOCCATO
    --   2. fn_is_super_admin -> TUTTO
    --   3. Override utente area (se valido temporalmente)
    --   4. Profilo via fn_get_profili_accesso_applicabili
    --      (AD_HOC prio 1 > REPARTO/PORTALE prio 2)
    --   5. Default -> BLOCCATO
    -- =========================================================

    -- 0. Gate contesto GUC (fail-closed su non-OPERATORE).
    v_ctx_ruolo := NULLIF(
        current_setting('app.ruolo_applicativo', true), ''
    )::config.ruolo_applicativo;

    IF v_ctx_ruolo IS NOT NULL
       AND v_ctx_ruolo <> 'OPERATORE'::config.ruolo_applicativo THEN
        RETURN 'BLOCCATO'::config.livello_accesso;
    END IF;

    -- 1. Identita OPERATORE attiva (helper DRY).
    IF NOT script.fn_has_identita_attiva(
               p_auth_user_id,
               'OPERATORE'::config.ruolo_applicativo) THEN
        RETURN 'BLOCCATO'::config.livello_accesso;
    END IF;

    -- 2. Super admin? Bypass totale.
    IF script.fn_is_super_admin(p_auth_user_id) THEN
        RETURN 'TUTTO'::config.livello_accesso;
    END IF;

    -- 3. Override utente area (invariato).
    SELECT uoa.livello
      INTO v_livello
      FROM config.user_override_aree uoa
      JOIN config.aree_funzionali af ON af.id = uoa.area_id
     WHERE uoa.auth_user_id = p_auth_user_id
       AND af.schema_db = p_area_schema_db
       AND uoa.validita @> CURRENT_DATE;

    IF FOUND THEN
        RETURN v_livello;
    END IF;

    -- 4. Profilo via bindings (helper, 1-arg -> default NULL).
    SELECT paa.livello
      INTO v_livello
      FROM script.fn_get_profili_accesso_applicabili(p_auth_user_id) h
      JOIN config.profili_accesso_aree paa
        ON paa.profilo_accesso_id = h.profilo_accesso_id
      JOIN config.aree_funzionali af
        ON af.id = paa.area_id
     WHERE af.schema_db = p_area_schema_db
     ORDER BY h.priorita
     LIMIT 1;

    IF FOUND THEN
        RETURN v_livello;
    END IF;

    -- 5. Default sicuro.
    RETURN 'BLOCCATO'::config.livello_accesso;
END
$function$

COMMENT ON FUNCTION script.fn_resolve_livello_area(p_auth_user_id integer, p_area_schema_db character varying)
IS 'Risolve livello accesso area per utente. Context-aware (post PR-B 21-04-2026): gate GUC app.ruolo_applicativo != OPERATORE -> BLOCCATO. Altrimenti catena legacy: has_identita, fn_is_super_admin, override, profili via helper.';
```

---
{% include-markdown "signature-core.md" %}
