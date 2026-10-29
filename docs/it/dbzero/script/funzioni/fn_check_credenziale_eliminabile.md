{% include-markdown "it/dbzero/script/manual/fn_check_credenziale_eliminabile.md" %}
# ⚙️ Funzione `fn_check_credenziale_eliminabile`

```sql
CREATE FUNCTION fn_check_credenziale_eliminabile(p_auth_user_id integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_credenziale_eliminabile(p_auth_user_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    -- Nudo: e' l'array dei motivi che la funzione restituisce.
    v_motivi   jsonb := '[]'::jsonb;
    -- Nudo: la tabella di django puo' non esserci ancora (prima di
    -- manage.py migrate), quindi si risolve con to_regclass.
    v_auth_user regclass;
    -- Le tabelle che tengono la credenziale, `schema.tabella`.
    v_dove     text[] := ARRAY[]::text[];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire perche' una credenziale NON si puo' eliminare.
    --   '[]' = si puo'. Non solleva: sollevare e' mestiere
    --   della madre script.fn_elimina_credenziale.
    --
    -- Motivi (in ordine: il primo e' quello che la madre
    -- solleva e il tooltip mostra):
    --   1. CON_VESTI: almeno una veste, anche spenta (D-1)
    --   2. STORIA_NON_VERIFICABILE: le FK verso django.auth_user
    --      non ci sono (fail-closed)
    --   3. CON_STORIA: una riga la tiene con una FK RESTRICT o
    --      NO ACTION (D-2), le tabelle derivate da pg_constraint
    --      (script.fn_tabelle_che_trattengono)
    --   Con il motivo 1 si esce: la storia non si cerca.
    -- =========================================================

    -- Guard parametro: un id assente o non positivo non esce da
    -- nessuna interfaccia, lo produce un chiamante rotto.
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_check_credenziale_eliminabile', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_auth_user_id', 'valore', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_check_credenziale_eliminabile',
                           'credenziale assente o non valida']);
    END IF;

    -- 1. Almeno una veste, anche spenta: la regola di NESSUNA_VESTE.
    IF script.fn_credenziale_ha_vesti(p_auth_user_id) THEN
        v_motivi := v_motivi || jsonb_build_array(jsonb_build_object(
            'codice',     'E_CREDENZIALE_CON_VESTI',
            'reason',     'CON_VESTI',
            'reason_key', 'amministrazione.accessi.elimina_reason.con_vesti',
            'dettaglio',  jsonb_build_object('auth_user_id', p_auth_user_id),
            -- Frase chiusa: niente da infilare nei segnaposto.
            'valori',     jsonb_build_array()));
        -- Con le vesti la storia non si cerca (vedi testata).
        RETURN v_motivi;
    END IF;

    -- 2. Le FK del ponte django: senza quella di identita_digitali
    --    i legami non ci sono, e non si sa dove sta la storia.
    v_auth_user := to_regclass('django.auth_user');
    IF NOT EXISTS (
        SELECT 1
          FROM pg_catalog.pg_constraint c
         WHERE c.contype   = 'f'
           AND c.conrelid  = to_regclass('anagrafiche.identita_digitali')
           AND c.confrelid = v_auth_user) THEN
        v_motivi := v_motivi || jsonb_build_array(jsonb_build_object(
            'codice',     'E_CREDENZIALE_STORIA_NON_VERIFICABILE',
            'reason',     'STORIA_NON_VERIFICABILE',
            'reason_key', 'amministrazione.accessi.elimina_reason.storia_non_verificabile',
            'dettaglio',  jsonb_build_object('auth_user_id', p_auth_user_id),
            'valori',     jsonb_build_array()));
        RETURN v_motivi;
    END IF;

    -- 3. La storia: le tabelle che trattengono la credenziale con una
    --    FK RESTRICT o NO ACTION, derivate da pg_constraint dal BB comune
    --    script.fn_tabelle_che_trattengono (20261028-34), tranne
    --    identita_digitali (e' il motivo 1).
    v_dove := script.fn_tabelle_che_trattengono(
                  v_auth_user,
                  ARRAY[p_auth_user_id]::bigint[],
                  ARRAY[to_regclass('anagrafiche.identita_digitali')]);

    IF cardinality(v_dove) > 0 THEN
        v_motivi := v_motivi || jsonb_build_array(jsonb_build_object(
            'codice',     'E_CREDENZIALE_CON_STORIA',
            'reason',     'CON_STORIA',
            'reason_key', 'amministrazione.accessi.elimina_reason.con_storia',
            'dettaglio',  jsonb_build_object('auth_user_id', p_auth_user_id,
                                             'dove',         to_jsonb(v_dove)),
            -- Il dove, per chi lo deve riferire allo sviluppo.
            'valori',     jsonb_build_array(array_to_string(v_dove, ', '))));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_credenziale_eliminabile(p_auth_user_id integer)
IS 'I motivi per cui una CREDENZIALE non si puo'' eliminare (linee-guida-sql §12.5.1): ''[]'' se si puo'', altrimenti l''array ORDINATO {codice, reason, reason_key, dettaglio, valori}. In ordine: CON_VESTI (E_CREDENZIALE_CON_VESTI, amministrazione.accessi.elimina_reason.con_vesti: almeno una veste anche spenta, script.fn_credenziale_ha_vesti, la regola di NESSUNA_VESTE del presidio; D-1), STORIA_NON_VERIFICABILE (E_CREDENZIALE_STORIA_NON_VERIFICABILE, amministrazione.accessi.elimina_reason.storia_non_verificabile: manca la FK di anagrafiche.identita_digitali verso django.auth_user, cioe'' il ponte django non e'' nato; fail-closed, decisione di Tid del 2026-10-06) e CON_STORIA (E_CREDENZIALE_CON_STORIA, amministrazione.accessi.elimina_reason.con_storia: la credenziale compare in una tabella che la tiene con una FK RESTRICT o NO ACTION, derivata da pg_constraint dal BB comune script.fn_tabelle_che_trattengono; dettaglio.dove e il valore le nominano; le righe della stessa tabella che la seguono in CASCADE non contano; D-2). Con CON_VESTI esce senza cercare la storia. La chiama script.fn_elimina_credenziale e ne solleva il primo motivo (§12.5.2); la legge il backend per can_delete/delete_reason sulle righe di «Altri accessi». SECURITY DEFINER del proprietario, search_path bloccato: la storia sta anche sotto RLS, e il motivo e'' uno stato, non una visibilita''. Restituisce solo nomi di tabelle. Id NULL o <= 0 -> E_AUTH_CHIAMATA_NON_VALIDA. STABLE. Brief: brief-db-elimina-credenziale-senza-veste §4.1. Rev 2026-10-28 (20261028-35, brief-modello-documento-vendita §16.11): l''elenco delle tabelle di storia dal BB comune script.fn_tabelle_che_trattengono, che lo usa anche la versione di listino; la regola non cambia.';
```

</div>

---
{% include-markdown "signature-core.md" %}
