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
    v_has_identita boolean;
    v_is_super     boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Mappa livello accesso per tutte le aree funzionali
    --   attive, in un singolo roundtrip DB.
    --
    -- Ritorna:
    --   JSONB { "anagrafiche": "TUTTO", "vendite": "LETTURA", ... }
    --
    -- Catena (refactor §4.6.B.8 + §4.8.5):
    --   1. Guard parametro obbligatorio
    --   2. Pre-calcolo v_has_identita (helper DRY §4.6.B.0)
    --   3. Pre-calcolo v_is_super
    --   4. CTE best_per_area su profili_accesso via helper
    --   5. jsonb_object_agg con CASE su (has_identita, super,
    --      user_override_area, best_per_area, default BLOCCATO)
    -- =========================================================

    -- 1. Guard parametro obbligatorio
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_user_permissions_map',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_auth_user_id', p_auth_user_id),
            NULL::uuid,
            'p_auth_user_id obbligatorio e > 0.'
        );
    END IF;

    -- 2-3. Pre-calcolo flag identita + super (usati nel CASE)
    v_has_identita := script.fn_has_identita_attiva(
                          p_auth_user_id,
                          'OPERATORE'::config.ruolo_applicativo);
    v_is_super := script.fn_is_super_admin(p_auth_user_id);

    -- 4-5. CTE best_per_area + aggregazione jsonb
    RETURN (
        WITH livelli_user AS (
            SELECT paa.area_id,
                   paa.livello,
                   h.priorita
              FROM script.fn_get_profili_accesso_applicabili(p_auth_user_id) h
              JOIN config.profili_accesso_aree paa
                ON paa.profilo_accesso_id = h.profilo_accesso_id
        ),
        best_per_area AS (
            -- DISTINCT ON prende la prima riga per area_id
            -- ordinata per priorita: AD_HOC (1) vince su
            -- REPARTO/PORTALE (2).
            SELECT DISTINCT ON (area_id)
                   area_id,
                   livello
              FROM livelli_user
             ORDER BY area_id, priorita
        )
        SELECT COALESCE(
            jsonb_object_agg(
                af.schema_db,
                CASE
                    WHEN NOT v_has_identita
                        THEN 'BLOCCATO'
                    WHEN v_is_super
                        THEN 'TUTTO'
                    ELSE COALESCE(
                        uoa.livello,
                        bpa.livello,
                        'BLOCCATO'::config.livello_accesso
                    )::text
                END
            ),
            '{}'::jsonb
        )
          FROM config.aree_funzionali af
          LEFT JOIN config.user_override_aree uoa
            ON uoa.auth_user_id = p_auth_user_id
           AND uoa.area_id = af.id
           AND uoa.validita @> CURRENT_DATE
          LEFT JOIN best_per_area bpa
            ON bpa.area_id = af.id
         WHERE af.attivo = TRUE
    );
END;
$function$

COMMENT ON FUNCTION script.fn_get_user_permissions_map(p_auth_user_id integer)
IS 'Mappa permessi aree set-based. Refactor §4.6.B.8 + §4.8.5: gate identita OPERATORE, bypass fn_is_super_admin, catena profili via helper fn_get_profili_accesso_applicabili (AD_HOC > REPARTO/PORTALE). Override utente area invariato.';
```

---
{% include-markdown "signature-core.md" %}
