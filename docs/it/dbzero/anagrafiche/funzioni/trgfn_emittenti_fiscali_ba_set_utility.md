# ⚙️ Funzione `trgfn_emittenti_fiscali_ba_set_utility`

```sql
CREATE FUNCTION trgfn_emittenti_fiscali_ba_set_utility()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_emittenti_fiscali_ba_set_utility()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo: il collegamento nasce con l'utility del suo
    --   billing account; la riga predefinita, senza BA, senza.
    --   Montata BEFORE INSERT, fase a20.
    -- =========================================================
    NEW.utility_id := anagrafiche.fn_utility_del_billing_account(NEW.billing_account_id);
    RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_emittenti_fiscali_ba_set_utility()
IS 'BEFORE INSERT su anagrafiche.emittenti_fiscali_billing_account, fase a20: utility_id e'' l''utility del billing account del collegamento (anagrafiche.fn_utility_del_billing_account), NULL sulla riga predefinita. Un valore scritto da chi inserisce si sostituisce. Il collegamento non cambia BA, e il cambio diretto di utility_id lo ferma il lucchetto di colonna.';
```

</div>

---
{% include-markdown "signature-core.md" %}
