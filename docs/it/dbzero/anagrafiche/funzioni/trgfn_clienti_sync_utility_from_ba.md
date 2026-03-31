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
    v_utility_id     config.utilities.id%TYPE;
    v_pdp_utility_id anagrafiche.pdp.utility_id%TYPE;
    v_richiede_pdp   config.utilities.richiede_pdp%TYPE := false;
BEGIN
    -- Nessun billing_account: niente da sincronizzare
    IF NEW.billing_account_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- Recupera utility_id dal billing_account
    SELECT ba.utility_id
      INTO v_utility_id
      FROM anagrafiche.billing_account ba
     WHERE ba.id = NEW.billing_account_id;

    IF v_utility_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.trgfn_clienti_sync_utility_from_ba',
            'E_BILLING_ACCOUNT_UTILITY_NULL',
            jsonb_build_object('billing_account_id', NEW.billing_account_id),
            NEW.tx_id,
            coalesce(NEW.billing_account_id::text, 'NULL')
        );
    END IF;

    -- Sincronizza o verifica coerenza utility_id
    IF NEW.utility_id IS NULL THEN
        NEW.utility_id := v_utility_id;
    ELSIF NEW.utility_id <> v_utility_id THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.trgfn_clienti_sync_utility_from_ba',
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
    END IF;

    -- Verifica policy richiede_pdp dalla utility
    SELECT coalesce(u.richiede_pdp, false)
      INTO v_richiede_pdp
      FROM config.utilities u
     WHERE u.id = v_utility_id;

    IF NOT FOUND THEN
        -- Fix: E_GENERICO → E_CODICE
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.trgfn_clienti_sync_utility_from_ba',
            'E_CODICE',
            jsonb_build_object('utility_id', v_utility_id),
            NEW.tx_id,
            v_utility_id::text, 'config.utilities'
        );
    END IF;

    -- Guard: PDP obbligatorio se utility lo richiede
    IF v_richiede_pdp AND NEW.pdp_id IS NULL THEN
        -- Fix: E_GENERICO → E_PDP_OBBLIGATORIO
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.trgfn_clienti_sync_utility_from_ba',
            'E_PDP_OBBLIGATORIO',
            jsonb_build_object(
                'billing_account_id', NEW.billing_account_id,
                'utility_id', v_utility_id
            ),
            NEW.tx_id,
            v_utility_id::text,
            coalesce(NEW.billing_account_id::text, 'NULL')
        );
    END IF;

    -- Guard: coerenza utility tra billing_account e PDP
    IF NEW.pdp_id IS NOT NULL THEN
        SELECT p.utility_id
          INTO v_pdp_utility_id
          FROM anagrafiche.pdp p
         WHERE p.id = NEW.pdp_id;

        IF v_pdp_utility_id IS NULL OR v_pdp_utility_id::integer <> v_utility_id THEN
            -- Fix: E_GENERICO → E_PDP_UTILITY_MISMATCH
            PERFORM script.fn_log_and_raise_error(
                'database',
                'anagrafiche.trgfn_clienti_sync_utility_from_ba',
                'E_PDP_UTILITY_MISMATCH',
                jsonb_build_object(
                    'billing_account_id', NEW.billing_account_id,
                    'pdp_id', NEW.pdp_id,
                    'utility_da_billing', v_utility_id,
                    'utility_da_pdp', v_pdp_utility_id
                ),
                NEW.tx_id,
                coalesce(NEW.billing_account_id::text, 'NULL'),
                coalesce(NEW.pdp_id::text, 'NULL'),
                v_utility_id::text,
                coalesce(v_pdp_utility_id::text, 'NULL')
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_clienti_sync_utility_from_ba()
IS 'Coerenza clienti.utility_id ↔ billing_account.utility_id; policy richiede_pdp; coerenza utility ↔ PDP.';
```

---
{% include-markdown "signature-core.md" %}
