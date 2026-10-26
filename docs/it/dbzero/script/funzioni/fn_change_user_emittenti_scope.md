{% include-markdown "it/dbzero/script/manual/fn_change_user_emittenti_scope.md" %}
# ⚙️ Funzione `fn_change_user_emittenti_scope`

```sql
CREATE FUNCTION fn_change_user_emittenti_scope(p_auth_user_id integer, p_emittente_ids bigint[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_change_user_emittenti_scope(p_auth_user_id integer, p_emittente_ids bigint[])
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_count_input        integer
        := COALESCE(array_length(p_emittente_ids, 1), 0);
    v_current_emittente  config.user_emittenti_fiscali.emittente_fiscale_id%TYPE;
    v_target_emittente   config.user_emittenti_fiscali.emittente_fiscale_id%TYPE;
    v_new_scope_mode     text;
BEGIN
    -- =========================================================
    -- Update 2026-04-29: i guard parametri ora passano per
    -- script.fn_log_and_raise_error (codice 409
    -- E_OPERATORE_SCOPE_PARAM_NON_VALIDO). Body invariato.
    -- =========================================================

    -- Guard parametri principali
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_change_user_emittenti_scope',
            'E_OPERATORE_SCOPE_PARAM_NON_VALIDO',
            jsonb_build_object(
                'param', 'p_auth_user_id',
                'value', p_auth_user_id
            ),
            NULL::uuid,
            'p_auth_user_id',
            coalesce(p_auth_user_id::text, 'NULL')
        );
    END IF;

    -- Guard MULTI applicativo
    IF v_count_input > 1 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_change_user_emittenti_scope',
            'E_OPERATORE_SCOPE_MULTI_NON_AMMESSO',
            jsonb_build_object(
                'auth_user_id', p_auth_user_id,
                'emittente_ids', p_emittente_ids,
                'count', v_count_input
            ),
            NULL::uuid,
            v_count_input::text
        );
    END IF;

    -- Validazione singolo emittente
    IF v_count_input = 1 THEN
        IF p_emittente_ids[1] IS NULL OR p_emittente_ids[1] <= 0 THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'fn_change_user_emittenti_scope',
                'E_OPERATORE_SCOPE_PARAM_NON_VALIDO',
                jsonb_build_object(
                    'param', 'p_emittente_ids[1]',
                    'value', p_emittente_ids[1]
                ),
                NULL::uuid,
                'p_emittente_ids[1]',
                coalesce(p_emittente_ids[1]::text, 'NULL')
            );
        END IF;
        v_target_emittente := p_emittente_ids[1];
        v_new_scope_mode   := 'SINGLE';
    ELSE
        v_target_emittente := NULL;
        v_new_scope_mode   := 'GLOBAL';
    END IF;

    -- Stato corrente con FOR UPDATE
    SELECT uef.emittente_fiscale_id
      INTO v_current_emittente
      FROM config.user_emittenti_fiscali uef
     WHERE uef.auth_user_id = p_auth_user_id
       FOR UPDATE;

    -- No-op
    IF v_current_emittente IS NOT DISTINCT FROM v_target_emittente THEN
        RETURN jsonb_build_object(
            'changed',      false,
            'scope_mode',   v_new_scope_mode,
            'emittente_id', v_target_emittente
        );
    END IF;

    -- Guard ultimo SA (gia' su fn_log_and_raise_error nel file 04)
    IF script.fn_check_ultimo_super_admin_attivo(p_auth_user_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_change_user_emittenti_scope',
            'E_PROFILO_ULTIMO_SUPER_ADMIN',
            jsonb_build_object(
                'auth_user_id',          p_auth_user_id,
                'current_emittente_id',  v_current_emittente,
                'target_emittente_id',   v_target_emittente,
                'detail', 'Cambio scope vietato sull''ultimo SUPER_ADMIN attivo'
            ),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]
          );
    END IF;

    -- Apply: DELETE (con override) + INSERT
    IF v_current_emittente IS NOT NULL THEN
        SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
        DELETE FROM config.user_emittenti_fiscali
         WHERE auth_user_id = p_auth_user_id;
        SET LOCAL zeroerp.allow_user_emittente_delete_override = '';
    END IF;

    IF v_target_emittente IS NOT NULL THEN
        INSERT INTO config.user_emittenti_fiscali
            (auth_user_id, emittente_fiscale_id)
        VALUES (p_auth_user_id, v_target_emittente);
    END IF;

    RETURN jsonb_build_object(
        'changed',      true,
        'scope_mode',   v_new_scope_mode,
        'emittente_id', v_target_emittente
    );
END;
$function$

COMMENT ON FUNCTION script.fn_change_user_emittenti_scope(p_auth_user_id integer, p_emittente_ids bigint[])
IS 'Orchestrazione atomica del cambio scope emittenti per un auth_user (drawer Operatore Fase 2 P1 2026-04-29; refactor error handling Fase 5 2026-04-29). Contratto array future-proof: NULL/[]=GLOBAL, [id]=SINGLE, multi=raise. Tutti gli errori passano per script.fn_log_and_raise_error: E_OPERATORE_SCOPE_PARAM_NON_VALIDO (409), E_OPERATORE_SCOPE_MULTI_NON_AMMESSO (405), E_PROFILO_ULTIMO_SUPER_ADMIN (384). Override locale di guard_delete via GUC zeroerp.allow_user_emittente_delete_override=on per i passaggi DELETE+INSERT. Ritorna jsonb {changed, scope_mode, emittente_id}.';
```

</div>

---
{% include-markdown "signature-core.md" %}
