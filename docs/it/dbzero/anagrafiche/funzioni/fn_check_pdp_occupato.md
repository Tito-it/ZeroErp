# ⚙️ Funzione `fn_check_pdp_occupato`

```sql
CREATE FUNCTION fn_check_pdp_occupato(p_pdp_id bigint, p_data date)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_check_pdp_occupato(p_pdp_id bigint, p_data date)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    -- Scopo: un cliente occupa il PDP nel giorno dato? La
    --   misura e' il periodo (C-8), la stessa di
    --   ex_clienti_no_overlap_stesso_pdp.
    -- ⚠️ SECURITY DEFINER: clienti e' in RLS, e il cliente di
    --   un'altra azienda sullo stesso PDP sarebbe invisibile.
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.clienti c
         WHERE c.pdp_id = p_pdp_id
           AND c.periodo @> p_data);
$function$

COMMENT ON FUNCTION anagrafiche.fn_check_pdp_occupato(p_pdp_id bigint, p_data date)
IS 'Check: un cliente occupa il PDP nel giorno dato, cioe'' il suo periodo lo contiene (C-8: la misura di «attivo» e'' il periodo, la stessa di ex_clienti_no_overlap_stesso_pdp). AN e PR non hanno periodo; un sospeso occupa. SECURITY DEFINER: clienti in RLS. Lo legge anagrafiche.trgfn_clienti_sync_stato_pdp. Brief: brief-db-cliente-manuale-uno-per-soggetto-e-utility.';
```

</div>

---
{% include-markdown "signature-core.md" %}
