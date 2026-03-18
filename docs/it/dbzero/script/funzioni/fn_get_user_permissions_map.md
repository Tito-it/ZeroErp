{% include-markdown "it/dbzero/script/manual/fn_get_user_permissions_map.md" %}
# ⚙️ Funzione `fn_get_user_permissions_map`

```sql
CREATE FUNCTION fn_get_user_permissions_map(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_user_permissions_map(p_auth_user_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_result  jsonb := '{}'::jsonb;
    v_area    RECORD;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Restituisce la mappa livello accesso per tutte le aree
    --   funzionali attive, in un solo roundtrip DB.
    --   Chiama fn_resolve_livello_area per ogni area.
    --
    -- Parametri:
    --   p_auth_user_id: ID utente Django (auth_user.id)
    --
    -- Ritorna:
    --   JSONB { "anagrafiche": "TUTTO", "vendite": "LETTURA", ... }
    --   Una chiave per ogni area funzionale attiva.
    --   Valore = livello accesso risolto (config.livello_accesso).
    --
    -- Catena di risoluzione per area (delegata a fn_resolve_livello_area):
    --   1. ruolo_sistema (ADMIN → TUTTO, DISABILITATO → BLOCCATO)
    --   2. Override utente area (se presente e valido)
    --   3. Profilo reparto (ereditato da UO)
    --   4. Default → BLOCCATO
    --
    -- Performance:
    --   ~10 aree attive = ~10 chiamate leggere a fn_resolve_livello_area.
    --   Risultato cacheable lato Redis (permissions_cache.py).
    -- =========================================================

    -- Guard: parametro obbligatorio
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_user_permissions_map',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_auth_user_id', p_auth_user_id),
            NULL::uuid,
            'p_auth_user_id obbligatorio e > 0.'
        );
    END IF;

    -- Loop su tutte le aree funzionali attive
    FOR v_area IN
        SELECT af.schema_db
          FROM config.aree_funzionali af
         WHERE af.attivo = TRUE
         ORDER BY af.ordinamento, af.schema_db
    LOOP
        v_result := v_result || jsonb_build_object(
            v_area.schema_db,
            script.fn_resolve_livello_area(
                p_auth_user_id, v_area.schema_db
            )::text
        );
    END LOOP;

    RETURN v_result;
END;
$function$

COMMENT ON FUNCTION script.fn_get_user_permissions_map(p_auth_user_id integer)
IS 'Mappa permessi utente: JSONB {schema_db: livello_accesso} per tutte le aree funzionali attive. Chiama fn_resolve_livello_area per ciascuna. STABLE, cacheable Redis.';
```

---
{% include-markdown "signature-core.md" %}
