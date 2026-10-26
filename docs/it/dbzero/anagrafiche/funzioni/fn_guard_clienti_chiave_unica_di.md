# ⚙️ Funzione `fn_guard_clienti_chiave_unica_di`

```sql
CREATE FUNCTION fn_guard_clienti_chiave_unica_di(p_billing_account_id bigint, p_istanza_utility_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_clienti_chiave_unica_di(p_billing_account_id bigint, p_istanza_utility_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    r record;
BEGIN
    -- ⚠️ SECURITY DEFINER: i clienti di un BA o di
    --   un'istanza si cercano sotto RLS altrimenti, e un
    --   cliente fuori perimetro salterebbe il controllo.
    -- Due parametri NULL non vogliono dire «tutti»: non si
    -- controlla niente (il raggio N ha la sua funzione).
    FOR r IN
        SELECT c.id
          FROM anagrafiche.clienti c
         WHERE c.billing_account_id = p_billing_account_id
            OR c.istanza_utility_id = p_istanza_utility_id
         ORDER BY c.id
    LOOP
        PERFORM anagrafiche.fn_guard_cliente_chiave_unica(r.id);
    END LOOP;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_clienti_chiave_unica_di(p_billing_account_id bigint, p_istanza_utility_id bigint)
IS 'Applica anagrafiche.fn_guard_cliente_chiave_unica (E_CLIENTE_STESSA_CHIAVE) ai clienti di un billing account o di un''istanza. La chiamano i constraint trigger sul collegamento BA -> azienda (cambia l''azienda del BA, quindi la chiave dei suoi clienti) e su istanze_utilities.fittizia (l''istanza entra o esce dalla regola). Due NULL: nessun controllo, non «tutti». SECURITY DEFINER: clienti in RLS. Brief: brief-db-cliente-manuale-uno-per-soggetto-e-utility.';
```

</div>

---
{% include-markdown "signature-core.md" %}
