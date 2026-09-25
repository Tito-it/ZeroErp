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
    v_has_identita boolean;   -- flag calcolato (fn_has_identita_attiva)
    v_is_super     boolean;   -- flag calcolato (fn_is_super_admin)
    v_ctx_ruolo    anagrafiche.identita_digitali.ruolo_applicativo%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Mappa azioni_processo abilitate/disabilitate
    --   (single roundtrip). JSONB { "perm_codename": bool, ... }.
    --
    -- Catena (context-aware dal 21-04-2026):
    --   1. Guard parametro obbligatorio
    --   2. Gate GUC: se app.ruolo_applicativo popolata e
    --      != OPERATORE -> v_has_identita=false, v_is_super=false
    --      (il CASE nel jsonb_object_agg produce false
    --      per tutte le azioni).
    --   3. Altrimenti pre-calcolo dei due flag.
    --   4. Per azione attiva: override, poi ereditato
    --      (fn_get_permessi_ereditati_azioni), poi false.
    -- Rev 20260925-86: l'ereditato non si ricalcola qui (erano le
    -- CTE abilitazioni_user/best_per_azione): lo da' il building
    -- block, sede unica dello spareggio e della veste OPERATORE.
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

    -- 4. Aggregazione jsonb: override, poi ereditato, poi false.
    RETURN (
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
                        e.abilitata,
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
          LEFT JOIN script.fn_get_permessi_ereditati_azioni(p_auth_user_id) e
            ON e.azione_id = ap.id
         WHERE ap.attivo = TRUE
    );
END;
$function$

COMMENT ON FUNCTION script.fn_get_user_actions_map(p_auth_user_id integer)
IS 'Mappa delle azioni di processo di un utente, tutte le azioni attive in una chiamata ({permission_codename: bool}). Stessa catena di script.fn_check_azione_processo: gate di contesto (veste diversa da OPERATORE -> tutto false), identita'' OPERATORE attiva, super admin -> true, override utente, ereditato dal profilo (script.fn_get_permessi_ereditati_azioni: sola veste OPERATORE), default negata. Rev 20260925-86 (brief-db-pgtap-permessi-ereditati, D-1 e D-2): l''ereditato non si ricalcola qui, e non conta piu'' i profili delle altre vesti dell''utente.';
```

---
{% include-markdown "signature-core.md" %}
