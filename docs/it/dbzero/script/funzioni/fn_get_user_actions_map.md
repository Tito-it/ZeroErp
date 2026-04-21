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
    v_has_identita boolean;
    v_is_super     boolean;
    v_ctx_ruolo    config.ruolo_applicativo;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Mappa azioni_processo abilitate/disabilitate
    --   (single roundtrip). JSONB { "perm_codename": bool, ... }.
    --
    -- Catena (post PR-B 21-04-2026, context-aware):
    --   1. Guard parametro obbligatorio
    --   2. Gate GUC: se app.ruolo_applicativo popolata e
    --      != OPERATORE -> v_has_identita=false, v_is_super=false
    --      (il CASE nel jsonb_object_agg produce false
    --      per tutte le azioni).
    --   3. Altrimenti pre-calcolo legacy dei due flag.
    --   4. CTE best_per_azione + aggregazione jsonb invariata.
    -- =========================================================

    -- 1. Guard parametro obbligatorio.
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_user_actions_map',
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
        -- Fail-closed: mappa produrra' false per ogni azione.
        v_has_identita := false;
        v_is_super     := false;
    ELSE
        v_has_identita := script.fn_has_identita_attiva(
                              p_auth_user_id,
                              'OPERATORE'::config.ruolo_applicativo);
        v_is_super     := script.fn_is_super_admin(p_auth_user_id);
    END IF;

    -- 4. CTE best_per_azione + aggregazione jsonb.
    RETURN (
        WITH abilitazioni_user AS (
            SELECT paz.azione_id,
                   paz.abilitata,
                   h.priorita
              FROM script.fn_get_profili_accesso_applicabili(p_auth_user_id) h
              JOIN config.profili_accesso_azioni paz
                ON paz.profilo_accesso_id = h.profilo_accesso_id
        ),
        best_per_azione AS (
            SELECT DISTINCT ON (azione_id)
                   azione_id,
                   abilitata
              FROM abilitazioni_user
             ORDER BY azione_id, priorita
        )
        SELECT COALESCE(
            jsonb_object_agg(
                ap.permission_codename,
                CASE
                    WHEN NOT v_has_identita
                        THEN false
                    WHEN v_is_super
                        THEN true
                    ELSE COALESCE(
                        uoa.abilitata,
                        bpaz.abilitata,
                        false
                    )
                END
            ),
            '{}'::jsonb
        )
          FROM config.azioni_processo ap
          LEFT JOIN config.user_override_azioni uoa
            ON uoa.auth_user_id = p_auth_user_id
           AND uoa.azione_id = ap.id
           AND uoa.validita @> CURRENT_DATE
          LEFT JOIN best_per_azione bpaz
            ON bpaz.azione_id = ap.id
         WHERE ap.attivo = TRUE
    );
END;
$function$

COMMENT ON FUNCTION script.fn_get_user_actions_map(p_auth_user_id integer)
IS 'Mappa azioni processo set-based. Context-aware (post PR-B 21-04-2026): gate GUC app.ruolo_applicativo != OPERATORE -> tutti false. Altrimenti catena legacy: has_identita, fn_is_super_admin, override, abilitazioni via helper.';
```

---
{% include-markdown "signature-core.md" %}
