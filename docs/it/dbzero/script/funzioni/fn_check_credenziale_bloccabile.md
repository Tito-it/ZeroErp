{% include-markdown "it/dbzero/script/manual/fn_check_credenziale_bloccabile.md" %}
# ⚙️ Funzione `fn_check_credenziale_bloccabile`

```sql
CREATE FUNCTION fn_check_credenziale_bloccabile(p_auth_user_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_credenziale_bloccabile(p_auth_user_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- Nudo: e' l'array dei motivi che la funzione restituisce.
    v_motivi jsonb := '[]'::jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire perche' una credenziale NON si puo' bloccare.
    --   '[]' = si puo'. Non solleva: sollevare e' mestiere
    --   della madre script.fn_blocca_credenziale.
    --
    -- Motivi (in ordine: il primo e' quello che la madre
    -- solleva e il tooltip mostra):
    --   1. la credenziale e' di SISTEMA (script.fn_categoria_accesso):
    --      l'utente di un processo automatico o un API_CLIENT
    --   2. e' l'ultimo SUPER_ADMIN raggiungibile
    --      (script.fn_check_ultimo_super_admin_attivo, stato PRIMA)
    --   In pratica non convivono: una veste di sistema e una di
    --   persona sulla stessa credenziale le rifiuta il guard della
    --   natura. L'ordine resta scritto: lo specifico batte il resto.
    -- =========================================================

    -- Guard parametro: un id assente o non positivo non esce da
    -- nessuna interfaccia, lo produce un chiamante rotto.
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_check_credenziale_bloccabile', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_auth_user_id', 'valore', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_check_credenziale_bloccabile',
                           'credenziale assente o non valida']);
    END IF;

    -- 1. Credenziale di sistema (R-DB-A6).
    IF script.fn_categoria_accesso(p_auth_user_id) = 'SISTEMA' THEN
        v_motivi := v_motivi || jsonb_build_array(jsonb_build_object(
            'codice',     'E_CREDENZIALE_DI_SISTEMA',
            'reason',     'CREDENZIALE_DI_SISTEMA',
            'reason_key', 'amministrazione.accessi.blocca_reason.credenziale_di_sistema',
            'dettaglio',  jsonb_build_object('auth_user_id', p_auth_user_id),
            -- Frase chiusa: niente da infilare nei segnaposto.
            'valori',     jsonb_build_array()));
    END IF;

    -- 2. Ultimo SUPER_ADMIN raggiungibile (anti-lockout).
    IF script.fn_check_ultimo_super_admin_attivo(p_auth_user_id) THEN
        v_motivi := v_motivi || jsonb_build_array(jsonb_build_object(
            'codice',     'E_PROFILO_ULTIMO_SUPER_ADMIN',
            'reason',     'ULTIMO_SUPER_ADMIN',
            'reason_key', 'amministrazione.accessi.blocca_reason.ultimo_super_admin',
            'dettaglio',  jsonb_build_object('auth_user_id', p_auth_user_id),
            'valori',     jsonb_build_array()));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_credenziale_bloccabile(p_auth_user_id integer)
IS 'I motivi per cui una CREDENZIALE non si puo'' bloccare (linee-guida-sql §12.5.1): ''[]'' se si puo'', altrimenti l''array ORDINATO {codice, reason, reason_key, dettaglio, valori}. In ordine: CREDENZIALE_DI_SISTEMA (E_CREDENZIALE_DI_SISTEMA, amministrazione.accessi.blocca_reason.credenziale_di_sistema: categoria SISTEMA di script.fn_categoria_accesso, l''utente di un processo o un API_CLIENT) e ULTIMO_SUPER_ADMIN (E_PROFILO_ULTIMO_SUPER_ADMIN, amministrazione.accessi.blocca_reason.ultimo_super_admin: script.fn_check_ultimo_super_admin_attivo, stato prima del blocco). La legge il backend per la capability can_block/block_reason/block_reason_key del dettaglio credenziale; la chiama script.fn_blocca_credenziale e ne solleva il primo motivo (§12.5.2), salvo il motivo di sistema dalla sessione del migratore. Non la chiama il guard config.trgfn_credenziali_guard_ultimo_super_admin, che e'' AFTER ROW (stato dopo) e resta la rete per le corse. Id NULL o <= 0 -> E_AUTH_CHIAMATA_NON_VALIDA. STABLE, SECURITY INVOKER. Brief: brief-db-credenziale-verbi-amministratore (R-DB-A5, R-DB-A6).';
```

</div>

---
{% include-markdown "signature-core.md" %}
