{% include-markdown "it/dbzero/script/manual/fn_login_attesa_secondi.md" %}
# ⚙️ Funzione `fn_login_attesa_secondi`

```sql
CREATE FUNCTION fn_login_attesa_secondi(p_fallimenti integer, p_tetto integer, p_attesa_base_secondi integer, p_attesa_max_secondi integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_login_attesa_secondi(p_fallimenti integer, p_tetto integer, p_attesa_base_secondi integer, p_attesa_max_secondi integer)
 RETURNS integer
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
-- Scopo: quanti secondi deve aspettare il prossimo tentativo di una
--   credenziale con p_fallimenti fallimenti consecutivi. Zero sotto il
--   tetto; dal tetto in su raddoppia a partire dalla base, fino al massimo.
BEGIN
    IF COALESCE(p_fallimenti, 0) < p_tetto THEN
        RETURN 0;
    END IF;

    RETURN LEAST(
        p_attesa_max_secondi::numeric,
        p_attesa_base_secondi * power(2::numeric, LEAST(p_fallimenti - p_tetto, 30))
    )::integer;
END;
$function$

COMMENT ON FUNCTION script.fn_login_attesa_secondi(p_fallimenti integer, p_tetto integer, p_attesa_base_secondi integer, p_attesa_max_secondi integer)
IS 'Attesa crescente sulla credenziale (D-1 riletta, D-B2): zero sotto il tetto, poi LEAST(max, base * 2^(fallimenti - tetto)) — al tetto esatto la base, raddoppia a ogni fallimento, si ferma al massimo. Rallenta senza chiudere: il titolare aspetta al piu'' il massimo, e ha il reset. Pura sui valori (i parametri li legge script.fn_login_parametri), IMMUTABLE; regola del 2: la usano fn_check_blocco_login e fn_registra_tentativo_login. Brief: brief-db-blocco-login-per-credenziale §2.4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
