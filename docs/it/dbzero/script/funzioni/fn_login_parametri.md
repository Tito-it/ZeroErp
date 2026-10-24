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
--   installazione rotta (E_CONFIG_MANCANTE, dalla regola unica
--   script.fn_intero_positivo_da_testo), mai un valore di ripiego.
DECLARE
    -- i valori grezzi dei cinque parametri, per codice: un oggetto
    -- costruito qui, nessuna colonna
    v_valori jsonb;
BEGIN
    SELECT jsonb_object_agg(p.code, p.default_value)
      INTO v_valori
      FROM config.parameters p
     WHERE p.code IN ('login_max_tentativi_falliti',
                      'login_blocco_minuti',
                      'login_tetto_credenziale',
                      'login_attesa_base_secondi',
                      'login_attesa_max_secondi');

    -- Un parametro alla volta, nell'ordine di prima: il primo
    -- sbagliato e' quello che si segnala.
    max_tentativi := script.fn_intero_positivo_da_testo(
        v_valori ->> 'login_max_tentativi_falliti',
        'login_max_tentativi_falliti', 'script.fn_login_parametri');
    blocco_minuti := script.fn_intero_positivo_da_testo(
        v_valori ->> 'login_blocco_minuti',
        'login_blocco_minuti', 'script.fn_login_parametri');
    tetto_credenziale := script.fn_intero_positivo_da_testo(
        v_valori ->> 'login_tetto_credenziale',
        'login_tetto_credenziale', 'script.fn_login_parametri');
    attesa_base_secondi := script.fn_intero_positivo_da_testo(
        v_valori ->> 'login_attesa_base_secondi',
        'login_attesa_base_secondi', 'script.fn_login_parametri');
    attesa_max_secondi := script.fn_intero_positivo_da_testo(
        v_valori ->> 'login_attesa_max_secondi',
        'login_attesa_max_secondi', 'script.fn_login_parametri');
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION script.fn_login_parametri()
IS 'I parametri del login in una lettura sola (regola del 2: la usano fn_check_blocco_login e fn_registra_tentativo_login): login_max_tentativi_falliti e login_blocco_minuti (freno sulla coppia credenziale + provenienza), login_tetto_credenziale, login_attesa_base_secondi e login_attesa_max_secondi (attesa crescente sulla credenziale). Default NUDO di config.parameters, non la cascata di override: la protezione del login non si personalizza, e prima del login l''utente non e'' noto. Fail-loud: un parametro assente, vuoto o non intero positivo solleva E_CONFIG_MANCANTE (script.fn_intero_positivo_da_testo, la regola unica), mai un ripiego nel codice. Brief: brief-db-blocco-login-per-credenziale §2.4, brief-be-verifica-documentazione-api §I.11.0.';
```

</div>

---
{% include-markdown "signature-core.md" %}
