{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_clienti_sync_utility_from_ba.md" %}
# ⚙️ Funzione `trgfn_clienti_sync_utility_from_ba`

```sql
CREATE FUNCTION trgfn_clienti_sync_utility_from_ba()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_clienti_sync_utility_from_ba()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_utility_id integer;
BEGIN
    -- Se non è valorizzato il billing_account, non facciamo nulla
    IF NEW.billing_account_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- Recupero utility_id dal billing_account
    SELECT ba.utility_id
      INTO v_utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.id = NEW.billing_account_id;

    IF v_utility_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'trgfn_clienti_sync_utility_from_ba',
            'E_BILLING_ACCOUNT_UTILITY_NULL',
            jsonb_build_object(
                'billing_account_id', NEW.billing_account_id
            ),
            NEW.tx_id,
            coalesce(NEW.billing_account_id::text, 'NULL')
        );
        --RAISE EXCEPTION 'Billing account % senza utility associata.', NEW.billing_account_id
        --    USING ERRCODE = 'P0001';
    END IF;

    -- Se il cliente non ha ancora utility, la eredita dal billing_account
    IF NEW.utility_id IS NULL THEN
        NEW.utility_id := v_utility_id;
    ELSIF NEW.utility_id <> v_utility_id THEN
        -- Coerenza violata: utility del cliente diversa da quella del BA
        PERFORM script.fn_log_and_raise_error(
            'database',
            'trgfn_clienti_sync_utility_from_ba',
            'E_CLIENTE_UTILITY_MISMATCH_BA',
            jsonb_build_object(
                'billing_account_id', NEW.billing_account_id,
                'utility_da_cliente', NEW.utility_id,
                'utility_da_billing', v_utility_id
            ),
            NEW.tx_id,
            coalesce(NEW.billing_account_id::text, 'NULL'),
            coalesce(NEW.utility_id::text, 'NULL'),
            coalesce(v_utility_id::text, 'NULL')
        );
       /* RAISE EXCEPTION
            'Utility del cliente (%) diversa da quella del billing_account (%).',
            NEW.utility_id, v_utility_id
            USING ERRCODE = 'P0001';  */
    END IF;

    RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
