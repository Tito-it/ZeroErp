# ⚙️ Funzione `fn_utility_del_billing_account`

```sql
CREATE FUNCTION fn_utility_del_billing_account(p_billing_account_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_utility_del_billing_account(p_billing_account_id bigint)
 RETURNS integer
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
BEGIN ATOMIC
 SELECT ba.utility_id
    FROM anagrafiche.billing_account ba
   WHERE (ba.id = fn_utility_del_billing_account.p_billing_account_id);
END

COMMENT ON FUNCTION anagrafiche.fn_utility_del_billing_account(p_billing_account_id bigint)
IS 'L''utility di un billing account (billing_account.utility_id); NULL se l''id e'' NULL o non e'' un billing account. Pura, non solleva. SECURITY DEFINER: legge anche un BA fuori dal perimetro di chi chiama, o appena nato e non ancora nel suo perimetro, e risponde solo l''utility. La usa anagrafiche.trgfn_emittenti_fiscali_ba_set_utility.';
```

</div>

---
{% include-markdown "signature-core.md" %}
