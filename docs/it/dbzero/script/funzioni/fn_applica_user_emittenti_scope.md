{% include-markdown "it/dbzero/script/manual/fn_applica_user_emittenti_scope.md" %}
# ⚙️ Funzione `fn_applica_user_emittenti_scope`

```sql
CREATE FUNCTION fn_applica_user_emittenti_scope(p_auth_user_id integer, p_emittente_ids bigint[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_applica_user_emittenti_scope(p_auth_user_id integer, p_emittente_ids bigint[])
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Portare l'operatore p_auth_user_id sull'azienda indicata (un solo
--   emittente), oppure togliergli l'azienda (array vuoto o NULL). La
--   riga di config.user_emittenti_fiscali e' una per operatore: lo
--   spostamento e' DELETE della riga di prima e INSERT della nuova.
--
-- Regole:
--   - parametri: auth_user_id positivo, emittente positivo
--     (E_OPERATORE_SCOPE_PARAM_NON_VALIDO); piu' di un emittente no
--     (E_OPERATORE_SCOPE_MULTI_NON_AMMESSO);
--   - stessa azienda di prima: niente da fare (changed = false);
--   - l'ultimo SUPER_ADMIN attivo non si sposta (E_PROFILO_ULTIMO_SUPER_ADMIN);
--   - il DELETE passa dalla porta zeroerp.allow_user_emittente_delete_override,
--     scritta con l'auth_user_id dell'operatore: il guard
--     config.trgfn_user_emittenti_fiscali_guard_delete la apre solo con quel
--     valore e col proprietario. Una GUC accesa dal chiamante si spegne
--     all'ingresso; la porta si svuota dopo il DELETE, anche in errore.
--
-- ⛔ Nessun permesso qui: e' la primitiva. Il permesso lo chiede il verbo
--   script.fn_change_user_emittenti_scope (SUPER_ADMIN); l'app non la esegue.
DECLARE
    -- un conteggio: nessuna colonna di cui sia il riflesso
    v_count_input        integer
        := COALESCE(array_length(p_emittente_ids, 1), 0);
    v_current_emittente  config.user_emittenti_fiscali.emittente_fiscale_id%TYPE;
    v_target_emittente   config.user_emittenti_fiscali.emittente_fiscale_id%TYPE;
    -- 'SINGLE' o 'GLOBAL', la forma del risultato: nessuna colonna
    v_new_scope_mode     text;
BEGIN
    -- La porta la apre solo questa funzione: quella che il chiamante
    -- avesse acceso si spegne qui.
    PERFORM set_config('zeroerp.allow_user_emittente_delete_override', '', true);

    -- Guard parametri principali
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_applica_user_emittenti_scope',
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

    -- Un'azienda sola per operatore
    IF v_count_input > 1 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_applica_user_emittenti_scope',
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
                'script.fn_applica_user_emittenti_scope',
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

    -- L'ultimo SUPER_ADMIN attivo non si sposta
    IF script.fn_check_ultimo_super_admin_attivo(p_auth_user_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_applica_user_emittenti_scope',
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

    -- Il DELETE passa dalla porta, aperta per la riga di questo operatore.
    -- ⚠️ La si svuota anche in errore: il terzo argomento di set_config lega
    --   il valore alla transazione, non alla chiamata.
    IF v_current_emittente IS NOT NULL THEN
        BEGIN
            PERFORM set_config('zeroerp.allow_user_emittente_delete_override',
                               p_auth_user_id::text, true);
            DELETE FROM config.user_emittenti_fiscali
             WHERE auth_user_id = p_auth_user_id;
            PERFORM set_config('zeroerp.allow_user_emittente_delete_override', '', true);
        EXCEPTION
            WHEN OTHERS THEN
                PERFORM set_config('zeroerp.allow_user_emittente_delete_override', '', true);
                RAISE;
        END;
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

COMMENT ON FUNCTION script.fn_applica_user_emittenti_scope(p_auth_user_id integer, p_emittente_ids bigint[])
IS 'Porta l''operatore sull''azienda indicata (un solo emittente) o gli toglie l''azienda (array vuoto o NULL): la riga di config.user_emittenti_fiscali è una per operatore, e lo spostamento è DELETE della riga di prima e INSERT della nuova. Restituisce changed, scope_mode (SINGLE o GLOBAL) ed emittente_id; la stessa azienda di prima non cambia niente. Rifiuti: parametri non validi (E_OPERATORE_SCOPE_PARAM_NON_VALIDO), più di un emittente (E_OPERATORE_SCOPE_MULTI_NON_AMMESSO), l''ultimo SUPER_ADMIN attivo (E_PROFILO_ULTIMO_SUPER_ADMIN). Il DELETE passa dalla porta zeroerp.allow_user_emittente_delete_override, che la funzione scrive con l''auth_user_id dell''operatore e svuota dopo, anche in errore; una GUC accesa dal chiamante si spegne all''ingresso. Il guard config.trgfn_user_emittenti_fiscali_guard_delete la apre solo con quel valore e col proprietario. È la primitiva, senza permesso: la chiamano il verbo script.fn_change_user_emittenti_scope, che chiede il SUPER_ADMIN, e anagrafiche.fn_provisiona_dati_di_sviluppo. L''applicazione non la esegue.';
```

</div>

---
{% include-markdown "signature-core.md" %}
