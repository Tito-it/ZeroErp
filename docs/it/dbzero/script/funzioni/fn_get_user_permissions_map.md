{% include-markdown "it/dbzero/script/manual/fn_get_user_permissions_map.md" %}
# ⚙️ Funzione `fn_get_user_permissions_map`

```sql
CREATE FUNCTION fn_get_user_permissions_map(p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_user_permissions_map(p_auth_user_id integer)
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
    --   Mappa livello accesso per tutte le aree funzionali
    --   attive (single roundtrip). JSONB { "schema": "LIV", ... }.
    --
    -- Catena (context-aware dal 21-04-2026):
    --   1. Guard parametro obbligatorio
    --   2. Gate GUC: se app.ruolo_applicativo popolata e
    --      != OPERATORE -> v_has_identita=false, v_is_super=false
    --      (il CASE nel jsonb_object_agg produce BLOCCATO
    --      per tutte le aree).
    --   3. Altrimenti pre-calcolo dei due flag.
    --   4. Per area attiva: override, poi ereditato
    --      (fn_get_permessi_ereditati_aree), poi BLOCCATO.
    -- Rev 20260925-85: l'ereditato non si ricalcola qui (erano le
    -- CTE livelli_user/best_per_area): lo da' il building block,
    -- sede unica dello spareggio e della veste OPERATORE (D-1, D-2).
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

    -- 4. Aggregazione jsonb: override, poi ereditato, poi BLOCCATO.
    RETURN (
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
                        e.livello,
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
           AND uoa.validita @> (SELECT script.fn_data_operativa())
          LEFT JOIN script.fn_get_permessi_ereditati_aree(p_auth_user_id) e
            ON e.area_id = af.id
         WHERE af.attivo = TRUE
    );
END;
$function$

COMMENT ON FUNCTION script.fn_get_user_permissions_map(p_auth_user_id integer)
IS 'Mappa dei livelli di accesso di un utente su tutte le aree attive, in una chiamata ({schema_db: livello}). Stessa catena di script.fn_resolve_livello_area: gate di contesto (veste diversa da OPERATORE -> tutto BLOCCATO), identita'' OPERATORE attiva, super admin -> TUTTO, override utente, ereditato dal profilo (script.fn_get_permessi_ereditati_aree: sola veste OPERATORE), default BLOCCATO. Rev 20260925-85 (brief-db-pgtap-permessi-ereditati, D-1 e D-2): l''ereditato non si ricalcola qui, e non conta piu'' i profili delle altre vesti dell''utente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
