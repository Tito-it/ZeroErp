{% include-markdown "it/dbzero/script/manual/fn_change_user_emittenti_scope.md" %}
# ⚙️ Funzione `fn_change_user_emittenti_scope`

```sql
CREATE FUNCTION fn_change_user_emittenti_scope(p_auth_user_id integer, p_emittente_ids bigint[])
```

**Definizione completa:**

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
    -- Scopo:
    --   Orchestrazione atomica del cambio scope per un
    --   auth_user. Single function = single transazione =
    --   single audit point per le modifiche admin di
    --   user_emittenti_fiscali.
    --
    -- Casi:
    --   - GLOBAL -> SINGLE   : INSERT
    --   - SINGLE -> GLOBAL   : DELETE (con override guard_delete)
    --   - SINGLE -> SINGLE'  : DELETE + INSERT (lock_columns
    --                          impedisce UPDATE su emittente_fiscale_id)
    --   - no-op              : nessuna scrittura
    -- =========================================================

    -- Guard parametri
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        RAISE EXCEPTION 'auth_user_id non valido (NULL o <= 0)'
            USING ERRCODE = '22023';
    END IF;

    -- Guard MULTI applicativo (ridondante con UNIQUE DB ma
    -- da' messaggio specifico al chiamante).
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

    -- Validazione singolo emittente (se presente)
    IF v_count_input = 1 THEN
        IF p_emittente_ids[1] IS NULL OR p_emittente_ids[1] <= 0 THEN
            RAISE EXCEPTION 'emittente_fiscale_id non valido in array (NULL o <= 0)'
                USING ERRCODE = '22023';
        END IF;
        v_target_emittente := p_emittente_ids[1];
        v_new_scope_mode   := 'SINGLE';
    ELSE
        v_target_emittente := NULL;
        v_new_scope_mode   := 'GLOBAL';
    END IF;

    -- Stato corrente (con FOR UPDATE per evitare race con
    -- altre sessioni che potrebbero modificare in parallelo).
    SELECT uef.emittente_fiscale_id
      INTO v_current_emittente
      FROM config.user_emittenti_fiscali uef
     WHERE uef.auth_user_id = p_auth_user_id
       FOR UPDATE;

    -- No-op: stesso scope_mode e stesso emittente -> niente da fare
    IF v_current_emittente IS NOT DISTINCT FROM v_target_emittente THEN
        RETURN jsonb_build_object(
            'changed',      false,
            'scope_mode',   v_new_scope_mode,
            'emittente_id', v_target_emittente
        );
    END IF;

    -- Guard ultimo SA: blocca qualsiasi cambio reale di scope
    -- per l'unico SUPER_ADMIN attivo del sistema. Allineato a
    -- Fase 1 (single source of truth).
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
            NULL::uuid
        );
    END IF;

    -- Applicazione cambio:
    --   1) DELETE riga corrente (se esiste). lock_columns
    --      impedisce UPDATE di emittente_fiscale_id, quindi
    --      anche per SINGLE -> SINGLE' serve DELETE+INSERT.
    --      guard_delete blocca normalmente DELETE su utenti
    --      attivi: SET LOCAL override per questo flusso
    --      amministrativo controllato.
    --   2) INSERT nuova riga (se v_target_emittente IS NOT NULL).
    IF v_current_emittente IS NOT NULL THEN
        SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
        DELETE FROM config.user_emittenti_fiscali
         WHERE auth_user_id = p_auth_user_id;
        -- Reset esplicito (anche se SET LOCAL si auto-resetta a fine
        -- transazione, lo riportiamo a stato neutro per chiarezza).
        SET LOCAL zeroerp.allow_user_emittente_delete_override = '';
    END IF;

    IF v_target_emittente IS NOT NULL THEN
        -- FK fk_user_emittenti_fiscali_emittente +
        -- dbops.trgfn_child_requires_active_parent rifiutano
        -- emittenti inesistenti o non attivi: nessun pre-check
        -- locale necessario.
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
IS 'Orchestrazione atomica del cambio scope emittenti per un auth_user (drawer Operatore Fase 2 P1 2026-04-29). Contratto array future-proof: NULL/[]=GLOBAL, [id]=SINGLE, multi=raise. Guard ultimo SA integrato (E_PROFILO_ULTIMO_SUPER_ADMIN). Override locale di guard_delete via GUC zeroerp.allow_user_emittente_delete_override=on per i passaggi DELETE+INSERT. Ritorna jsonb {changed, scope_mode, emittente_id}.';
```

---
{% include-markdown "signature-core.md" %}
