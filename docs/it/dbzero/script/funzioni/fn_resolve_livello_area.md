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
    v_livello config.user_override_aree.livello%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Risolve il livello di accesso effettivo di un utente
    --   per un'area funzionale identificata da schema_db.
    --
    -- Catena (refactor §4.6.B.2 + §4.8 WIP multi-face-auth):
    --   1. Assenza di identita OPERATORE attiva -> BLOCCATO
    --   2. fn_is_super_admin -> TUTTO
    --   3. Override utente area (se valido temporalmente)
    --   4. Profilo via fn_get_profili_accesso_applicabili
    --      (AD_HOC prio 1 > REPARTO/PORTALE prio 2)
    --   5. Default -> BLOCCATO
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

    -- 3. Override utente area (invariato)
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

    -- 4. Profilo via bindings (§4.8 nuovo modello).
    --    Helper ritorna i profili applicabili con priorita;
    --    JOIN a profili_accesso_aree per il livello sull'area
    --    richiesta; ORDER BY priorita LIMIT 1 per scegliere
    --    il piu' specifico (AD_HOC > REPARTO/PORTALE).
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

    -- 5. Default sicuro
    RETURN 'BLOCCATO'::config.livello_accesso;
END
$function$

COMMENT ON FUNCTION script.fn_resolve_livello_area(p_auth_user_id integer, p_area_schema_db character varying)
IS 'Risolve livello accesso area per utente. Refactor §4.6.B.2 + §4.8: ramo ADMIN -> fn_is_super_admin; ramo DISABILITATO -> check identita OPERATORE attiva; profilo via bindings generalizzato (fn_get_profili_accesso_applicabili, AD_HOC > REPARTO/PORTALE).';
```

---
{% include-markdown "signature-core.md" %}
