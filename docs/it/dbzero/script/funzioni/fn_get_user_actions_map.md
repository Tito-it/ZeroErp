{% include-markdown "it/dbzero/script/manual/fn_get_user_actions_map.md" %}
# ⚙️ Funzione `fn_get_user_actions_map`

```sql
CREATE FUNCTION fn_get_user_actions_map(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_user_actions_map(p_auth_user_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_result  jsonb := '{}'::jsonb;
    v_azione  RECORD;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Ritorna la mappa completa delle azioni di processo
    --   abilitate/disabilitate per l'utente.
    --   Gemella di fn_get_user_permissions_map (aree).
    --
    -- Parametri:
    --   p_auth_user_id: ID utente Django (auth_user.id)
    --
    -- Ritorna:
    --   JSONB tipo {"genera_fatture_lotti": true,
    --              "reset_lotto_draft": false, ...}
    --
    -- Catena di risoluzione (delegata a fn_check_azione_processo):
    --   1. ruolo_sistema (DISABILITATO → false, ADMIN → true)
    --   2. Override utente azione (se presente e valido)
    --   3. Profilo reparto azione (ereditato dall'UO)
    --   4. Default → false (negata)
    -- =========================================================

    -- Guard: parametro obbligatorio e valido
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_user_actions_map',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_auth_user_id', p_auth_user_id),
            NULL::uuid,
            'p_auth_user_id obbligatorio e > 0.'
        );
    END IF;

    -- Loop su tutte le azioni processo attive
    FOR v_azione IN
        SELECT ap.permission_codename
          FROM config.azioni_processo ap
         WHERE ap.attivo = TRUE
         ORDER BY ap.permission_codename
    LOOP
        v_result := v_result || jsonb_build_object(
            v_azione.permission_codename,
            script.fn_check_azione_processo(
                p_auth_user_id, v_azione.permission_codename
            )
        );
    END LOOP;

    RETURN v_result;
END;
$function$

COMMENT ON FUNCTION script.fn_get_user_actions_map(p_auth_user_id integer)
IS 'Mappa azioni_processo abilitate per utente. Loop su config.azioni_processo attive, chiama fn_check_azione_processo per ognuna. Ritorna JSONB {codename: true/false}. Gemella di fn_get_user_permissions_map.';
```

---
{% include-markdown "signature-core.md" %}
