{% include-markdown "it/dbzero/script/manual/fn_get_user_object_permissions_map.md" %}
# ⚙️ Funzione `fn_get_user_object_permissions_map`

```sql
CREATE FUNCTION fn_get_user_object_permissions_map(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_user_object_permissions_map(p_auth_user_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Restituisce la mappa completa degli override oggetto
    --   attivi per un utente, in un solo roundtrip DB.
    --
    -- Ritorna:
    --   JSONB { "anagrafiche.conto_bancario": "BLOCCATO",
    --           "vendite.fattura": "LETTURA", ... }
    --
    -- Regole:
    --   - considera solo override attivi alla data corrente
    --   - nessun override attivo -> {}::jsonb
    -- =========================================================

    -- Guard: parametro obbligatorio e valido
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_user_object_permissions_map',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_auth_user_id', p_auth_user_id),
            NULL::uuid,
            'p_auth_user_id obbligatorio e > 0.'
        );
    END IF;

    RETURN (
        SELECT COALESCE(
            jsonb_object_agg(
                uo.app_label || '.' || uo.model_name,
                uo.livello::text
            ),
            '{}'::jsonb
        )
          FROM config.user_override_oggetti uo
         WHERE uo.auth_user_id = p_auth_user_id
           AND uo.validita @> CURRENT_DATE
    );
END;
$function$

COMMENT ON FUNCTION script.fn_get_user_object_permissions_map(p_auth_user_id integer)
IS 'Mappa override oggetti set-based. Migrazione daterange: filtro temporale via validita @>.';
```

---
{% include-markdown "signature-core.md" %}
