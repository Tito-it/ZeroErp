{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_resellers_guard_attivo.md" %}
# ⚙️ Funzione `trgfn_resellers_guard_attivo`

```sql
CREATE FUNCTION trgfn_resellers_guard_attivo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_resellers_guard_attivo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_has_mapping BOOLEAN;
BEGIN
    -- Solo su disattivazione (attivo: true → false)
    IF TG_OP = 'UPDATE'
       AND NEW.attivo = false
       AND COALESCE(OLD.attivo, true) = true
    THEN
        -- Verifica mapping billing_account
        SELECT EXISTS (
            SELECT 1
              FROM anagrafiche.resellers_billing_account m
             WHERE m.reseller_soggetto_ruolo_id = NEW.soggetto_ruolo_id
        )
        INTO v_has_mapping;

        IF v_has_mapping THEN
            PERFORM script.fn_log_and_raise_error(
                TG_TABLE_SCHEMA,
                TG_NAME,
                'E_RESELLER_DISATTIVAZIONE_BLOCCATA',
                jsonb_build_object(
                    'soggetto_ruolo_id', NEW.soggetto_ruolo_id
                ),
                NULL::uuid,
                NEW.soggetto_ruolo_id::text
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_resellers_guard_attivo()
IS 'Blocca disattivazione reseller se esistono mapping billing_account. Errore: E_RESELLER_DISATTIVAZIONE_BLOCCATA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
