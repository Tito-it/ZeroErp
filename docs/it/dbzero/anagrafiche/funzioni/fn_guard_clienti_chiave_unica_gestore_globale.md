# ⚙️ Funzione `fn_guard_clienti_chiave_unica_gestore_globale`

```sql
CREATE FUNCTION fn_guard_clienti_chiave_unica_gestore_globale()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_clienti_chiave_unica_gestore_globale()
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    r record;
BEGIN
    -- ⚠️ RAGGIO N: spostare l'azienda predefinita cambia la
    --   chiave di TUTTI i clienti dei BA senza collegamento.
    --   Si controllano quelli fittizi; un doppione fra due
    --   collegati non nasce da questo movimento.
    FOR r IN
        SELECT c.id
          FROM anagrafiche.clienti c
          JOIN anagrafiche.istanze_utilities iu
            ON iu.id = c.istanza_utility_id
         WHERE iu.fittizia
           AND c.periodo IS NOT NULL
           AND NOT EXISTS (
                   SELECT 1
                     FROM anagrafiche.emittenti_fiscali_billing_account e
                    WHERE e.billing_account_id = c.billing_account_id)
         ORDER BY c.id
    LOOP
        PERFORM anagrafiche.fn_guard_cliente_chiave_unica(r.id);
    END LOOP;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_clienti_chiave_unica_gestore_globale()
IS 'Raggio N di anagrafiche.fn_guard_cliente_chiave_unica (E_CLIENTE_STESSA_CHIAVE): quando l''azienda predefinita cambia o sparisce, cambia la chiave di tutti i clienti dei BA senza collegamento; si controllano quelli delle istanze fittizie. La chiama il constraint trigger sul collegamento BA -> azienda per la riga di default. Gemella di anagrafiche.fn_guard_istanza_ba_gestore_globale. SECURITY DEFINER: clienti in RLS. Brief: brief-db-cliente-manuale-uno-per-soggetto-e-utility.';
```

</div>

---
{% include-markdown "signature-core.md" %}
