{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_guard_id_fiscale_immutabile.md" %}
# ⚙️ Funzione `trgfn_soggetti_guard_id_fiscale_immutabile`

```sql
CREATE FUNCTION trgfn_soggetti_guard_id_fiscale_immutabile()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.codice_fiscale IS DISTINCT FROM OLD.codice_fiscale
       AND anagrafiche.fn_id_fiscale_bloccato(OLD.codice_fiscale) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'trgfn_soggetti_guard_id_fiscale_immutabile',
            'E_SOGGETTO_ID_FISCALE_IMMUTABILE',
            jsonb_build_object('campo', 'codice_fiscale', 'soggetto_id', NEW.id),
            NEW.tx_id,
            'codice fiscale');
    END IF;

    IF NEW.partita_iva IS DISTINCT FROM OLD.partita_iva
       AND anagrafiche.fn_id_fiscale_bloccato(OLD.partita_iva) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'trgfn_soggetti_guard_id_fiscale_immutabile',
            'E_SOGGETTO_ID_FISCALE_IMMUTABILE',
            jsonb_build_object('campo', 'partita_iva', 'soggetto_id', NEW.id),
            NEW.tx_id,
            'partita IVA');
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile()
IS 'Guard di anagrafiche.soggetti (BEFORE UPDATE OF codice_fiscale, partita_iva): un codice fiscale o una partita IVA gia'' scritti non si cambiano e non si svuotano, salvo il SUPER_ADMIN; un campo vuoto si puo'' riempire. La regola e'' anagrafiche.fn_id_fiscale_bloccato, letta sul valore OLD; la stessa regola spegne i due campi nel form (dbops.lock_columns_conditional, anagrafiche.fn_soggetto_id_fiscale_bloccato). Rifiuto: E_SOGGETTO_ID_FISCALE_IMMUTABILE, con campo = la colonna.';
```

</div>

---
{% include-markdown "signature-core.md" %}
