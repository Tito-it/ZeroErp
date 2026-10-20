{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_billing_account_require_istanza_ha_ba.md" %}
# ⚙️ Funzione `trgfn_billing_account_require_istanza_ha_ba`

```sql
CREATE FUNCTION trgfn_billing_account_require_istanza_ha_ba()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_billing_account_require_istanza_ha_ba()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Al COMMIT: se l'istanza del BA cancellato esiste ancora,
  -- deve avere un altro billing account. Istanza cancellata
  -- nella stessa transazione: il guard non ha niente da dire.
  PERFORM anagrafiche.fn_guard_istanza_ha_ba(OLD.istanza_utility_id);
  RETURN NULL;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_billing_account_require_istanza_ha_ba()
IS 'Constraint trigger function (AFTER DELETE DEFERRABLE INITIALLY DEFERRED su anagrafiche.billing_account): al COMMIT l''istanza del billing account cancellato, se esiste ancora, deve avere un altro BA. Delega ad anagrafiche.fn_guard_istanza_ha_ba (E_ISTANZA_SENZA_BA), lo stesso guard della nascita dell''istanza. Al COMMIT e non subito, perche'' cancellare l''istanza intera insieme ai suoi BA resta lecito. Brief: brief-db-istanza-nasce-col-ba (R-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
