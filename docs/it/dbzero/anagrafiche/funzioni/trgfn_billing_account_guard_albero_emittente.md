{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_billing_account_guard_albero_emittente.md" %}
# ⚙️ Funzione `trgfn_billing_account_guard_albero_emittente`

```sql
CREATE FUNCTION trgfn_billing_account_guard_albero_emittente()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_billing_account_guard_albero_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Il lavoro vero sta nel guard, che e' SECURITY DEFINER perche'
    -- deve vedere padre e figli anche fuori dal perimetro di chi
    -- scrive (brief §11.1). Qui resta solo il quando.
    PERFORM anagrafiche.fn_guard_albero_ba_emittente(NEW.id);
    RETURN NULL;   -- trigger AFTER: il valore di ritorno e' ignorato
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_billing_account_guard_albero_emittente()
IS 'Trigger AFTER INSERT OR UPDATE OF parent_account_id su anagrafiche.billing_account: delega a fn_guard_albero_ba_emittente la verifica che l''albero non attraversi due emittenti. AFTER e non BEFORE perche'' l''emittente del BA nuovo nasce dal mapping creato da trg_billing_account_z90_link_ef_ins, che e'' AFTER INSERT: un guard BEFORE leggerebbe il gestore globale al posto dell''emittente reale. Brief P-1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
