{% include-markdown "it/dbzero/anagrafiche/manual/fn_check_billing_account_esiste.md" %}
# ⚙️ Funzione `fn_check_billing_account_esiste`

```sql
CREATE FUNCTION fn_check_billing_account_esiste(p_billing_account_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_check_billing_account_esiste(p_billing_account_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
BEGIN ATOMIC
 SELECT
         CASE
             WHEN (p_billing_account_id IS NULL) THEN NULL::boolean
             ELSE (EXISTS ( SELECT 1
                FROM anagrafiche.billing_account ba
               WHERE (ba.id = fn_check_billing_account_esiste.p_billing_account_id)))
         END AS "exists";
END

COMMENT ON FUNCTION anagrafiche.fn_check_billing_account_esiste(p_billing_account_id bigint)
IS 'L''id indicato e'' un billing account? true o false, NULL su un id NULL: che cosa vuol dire «nessun billing account» lo decide il chiamante. Pura, non solleva. SECURITY DEFINER: guarda tutti i billing account, anche quelli fuori dal perimetro di chi chiama, perche'' la domanda e'' se l''id esiste, non se chi chiama lo vede; restituisce solo il booleano. La usano anagrafiche.fn_get_emittente_fiscale_id e anagrafiche.fn_get_emittente_fiscale_pk, che su un id che non e'' un billing account sollevano E_BILLING_ACCOUNT_NOT_FOUND.';
```

</div>

---
{% include-markdown "signature-core.md" %}
