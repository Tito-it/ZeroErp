{% include-markdown "it/dbzero/script/manual/fn_login_parametri.md" %}
# ⚙️ Funzione `fn_login_parametri`

```sql
CREATE FUNCTION fn_login_parametri()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_login_parametri()
 RETURNS TABLE(max_tentativi integer, blocco_minuti integer, tetto_credenziale integer, attesa_base_secondi integer, attesa_max_secondi integer)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: i parametri del login, dal default nudo di config.parameters.
--   Fail-loud: un parametro assente, vuoto o non intero positivo e' una
--   installazione rotta (E_CONFIG_MANCANTE), mai un valore di ripiego.
DECLARE
    -- ⚠️ text[] esplicito: `%TYPE[]` non e' sintassi valida.
    v_codici text[] := ARRAY[
        'login_max_tentativi_falliti',
        'login_blocco_minuti',
        'login_tetto_credenziale',
        'login_attesa_base_secondi',
        'login_attesa_max_secondi'];
    v_codice config.parameters.code%TYPE;
    v_valori jsonb;
BEGIN
    SELECT jsonb_object_agg(p.code, p.default_value)
      INTO v_valori
      FROM config.parameters p
     WHERE p.code = ANY (v_codici);

    FOREACH v_codice IN ARRAY v_codici LOOP
        IF COALESCE(v_valori ->> v_codice, '') !~ '^[1-9][0-9]{0,5}$' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.fn_login_parametri', 'E_CONFIG_MANCANTE',
                jsonb_build_object('config',    'config.parameters',
                                   'parametro', v_codice,
                                   'valore',    v_valori ->> v_codice),
                NULL::uuid,
                VARIADIC ARRAY[format('parametro %s (intero positivo)', v_codice)]);
        END IF;
    END LOOP;

    max_tentativi       := (v_valori ->> 'login_max_tentativi_falliti')::integer;
    blocco_minuti       := (v_valori ->> 'login_blocco_minuti')::integer;
    tetto_credenziale   := (v_valori ->> 'login_tetto_credenziale')::integer;
    attesa_base_secondi := (v_valori ->> 'login_attesa_base_secondi')::integer;
    attesa_max_secondi  := (v_valori ->> 'login_attesa_max_secondi')::integer;
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION script.fn_login_parametri()
IS 'I parametri del login in una lettura sola (regola del 2: la usano fn_check_blocco_login e fn_registra_tentativo_login): login_max_tentativi_falliti e login_blocco_minuti (freno sulla coppia credenziale + provenienza), login_tetto_credenziale, login_attesa_base_secondi e login_attesa_max_secondi (attesa crescente sulla credenziale). Default NUDO di config.parameters, non la cascata di override: la protezione del login non si personalizza, e prima del login l''utente non e'' noto. Fail-loud: un parametro assente, vuoto o non intero positivo solleva E_CONFIG_MANCANTE, mai un ripiego nel codice. Brief: brief-db-blocco-login-per-credenziale §2.4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
