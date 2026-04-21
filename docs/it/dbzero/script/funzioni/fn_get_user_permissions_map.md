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
    v_ctx_ruolo    config.ruolo_applicativo;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Mappa livello accesso per tutte le aree funzionali
    --   attive (single roundtrip). JSONB { "schema": "LIV", ... }.
    --
    -- Catena (post PR-B 21-04-2026, context-aware):
    --   1. Guard parametro obbligatorio
    --   2. Gate GUC: se app.ruolo_applicativo popolata e
    --      != OPERATORE -> v_has_identita=false, v_is_super=false
    --      (il CASE nel jsonb_object_agg produce BLOCCATO
    --      per tutte le aree).
    --   3. Altrimenti pre-calcolo legacy dei due flag.
    --   4. CTE best_per_area + aggregazione jsonb invariata.
    -- =========================================================

    -- 1. Guard parametro obbligatorio.
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_user_permissions_map',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_auth_user_id', p_auth_user_id),
            NULL::uuid,
            'p_auth_user_id obbligatorio e > 0.'
        );
    END IF;

    -- 2-3. Gate contesto GUC + pre-calcolo flag.
    v_ctx_ruolo := NULLIF(
        current_setting('app.ruolo_applicativo', true), ''
    )::config.ruolo_applicativo;

    IF v_ctx_ruolo IS NOT NULL
       AND v_ctx_ruolo <> 'OPERATORE'::config.ruolo_applicativo THEN
        -- Fail-closed: mappa produrra' BLOCCATO per ogni area.
        v_has_identita := false;
        v_is_super     := false;
    ELSE
        v_has_identita := script.fn_has_identita_attiva(
                              p_auth_user_id,
                              'OPERATORE'::config.ruolo_applicativo);
        v_is_super     := script.fn_is_super_admin(p_auth_user_id);
    END IF;

    -- 4. CTE best_per_area + aggregazione jsonb.
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
IS 'Mappa permessi aree set-based. Context-aware (post PR-B 21-04-2026): gate GUC app.ruolo_applicativo != OPERATORE -> tutti BLOCCATO. Altrimenti catena legacy: has_identita, fn_is_super_admin, override, profili via helper.';
```

---
{% include-markdown "signature-core.md" %}
