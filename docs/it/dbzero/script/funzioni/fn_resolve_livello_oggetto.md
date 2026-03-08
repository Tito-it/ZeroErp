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
  v_ruolo   anagrafiche.risorse_umane_auth_user.ruolo_sistema%TYPE;
  v_livello config.user_override_oggetti.livello%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Risolve il livello di accesso per un singolo model
  --   Django (app_label + model_name).
  --   Se esiste un override oggetto lo usa, altrimenti
  --   risale alla catena area via fn_resolve_livello_area.
  --
  -- Catena:
  --   1. ruolo_sistema (NULL/DISABILITATO → BLOCCATO, ADMIN → TUTTO)
  --   2. Override utente oggetto (se presente e valido)
  --   3. Fallback → fn_resolve_livello_area
  -- =========================================================

  -- 1. Ruolo sistema
  v_ruolo := script.fn_get_ruolo_sistema(p_auth_user_id);

  IF v_ruolo IS NULL OR v_ruolo = 'DISABILITATO' THEN
    RETURN 'BLOCCATO'::config.livello_accesso;
  END IF;

  IF v_ruolo = 'ADMIN' THEN
    RETURN 'TUTTO'::config.livello_accesso;
  END IF;

  -- 2. Override utente oggetto (OPERATIVO)
  SELECT uoo.livello
    INTO v_livello
    FROM config.user_override_oggetti uoo
   WHERE uoo.auth_user_id = p_auth_user_id
     AND uoo.app_label    = p_app_label
     AND uoo.model_name   = p_model_name
     AND (uoo.valido_dal IS NULL OR uoo.valido_dal <= CURRENT_DATE)
     AND (uoo.valido_al  IS NULL OR uoo.valido_al  >= CURRENT_DATE);

  IF FOUND THEN
    RETURN v_livello;
  END IF;

  -- 3. Fallback alla catena area
  RETURN script.fn_resolve_livello_area(p_auth_user_id, p_area_schema_db);
END
$function$

COMMENT ON FUNCTION script.fn_resolve_livello_oggetto(p_auth_user_id integer, p_app_label character varying, p_model_name character varying, p_area_schema_db character varying)
IS 'Risolve livello accesso per model: override oggetto → catena area → BLOCCATO.';
```

---
{% include-markdown "signature-core.md" %}
