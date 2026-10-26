{% include-markdown "it/dbzero/script/manual/fn_login_freno_passo.md" %}
# ⚙️ Funzione `fn_login_freno_passo`

```sql
CREATE FUNCTION fn_login_freno_passo(p_tentativi_prima integer, p_bloccato_fino_a_prima timestamp with time zone, p_adesso timestamp with time zone, p_max_tentativi integer, p_blocco_minuti integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_login_freno_passo(p_tentativi_prima integer, p_bloccato_fino_a_prima timestamp with time zone, p_adesso timestamp with time zone, p_max_tentativi integer, p_blocco_minuti integer)
 RETURNS TABLE(tentativi integer, bloccato_fino_a timestamp with time zone)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: lo stato della coppia chiave + provenienza dopo UN fallimento,
--   dato quello di prima (0 e NULL per una riga che non c'era).
DECLARE
    v_tentativi config.credenziali_provenienze.tentativi_falliti%TYPE;
BEGIN
    v_tentativi := CASE
                       WHEN p_bloccato_fino_a_prima IS NOT NULL
                        AND p_bloccato_fino_a_prima <= p_adesso THEN 1
                       ELSE COALESCE(p_tentativi_prima, 0) + 1
                   END;

    tentativi       := v_tentativi;
    bloccato_fino_a := CASE
                           WHEN v_tentativi >= p_max_tentativi
                           THEN p_adesso + make_interval(mins => p_blocco_minuti)
                       END;
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION script.fn_login_freno_passo(p_tentativi_prima integer, p_bloccato_fino_a_prima timestamp with time zone, p_adesso timestamp with time zone, p_max_tentativi integer, p_blocco_minuti integer)
IS 'Il passo del freno sulla coppia chiave + provenienza dopo un fallimento di login: un freno scaduto riparte da 1, altrimenti tentativi + 1 (0 per una riga nuova); alla soglia p_max_tentativi il freno dura fino a p_adesso + p_blocco_minuti (un fallimento durante il freno lo rinnova). Pura sui valori (l''istante lo passa il chiamante); STABLE per timestamptz + interval. Regola del 2: la usano i due rami di fn_registra_tentativo_login, credenziale e nome tentato (R-7): due copie frenerebbero in due modi e la differenza direbbe se il nome esiste. Brief: brief-db-blocco-login-per-credenziale §13.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
