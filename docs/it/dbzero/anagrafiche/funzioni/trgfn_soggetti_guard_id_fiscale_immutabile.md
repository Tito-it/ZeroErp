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

    -- Lo stato e' meta' della chiave d'unicita' (D-T5-3 a): non e' mai
    -- NULL, quindi per lui la regola e' «solo il SUPER_ADMIN». Anche lo
    -- stato portato a NULL si ferma qui, prima del NOT NULL della colonna.
    IF NEW.stato_id IS DISTINCT FROM OLD.stato_id
       AND anagrafiche.fn_id_fiscale_bloccato(OLD.stato_id::text) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'trgfn_soggetti_guard_id_fiscale_immutabile',
            'E_SOGGETTO_ID_FISCALE_IMMUTABILE',
            jsonb_build_object('campo', 'stato_id', 'soggetto_id', NEW.id),
            NEW.tx_id,
            'stato');
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile()
IS 'Guard di anagrafiche.soggetti (trg_soggetti_a05_guard_id_fiscale_immutabile_upd, BEFORE UPDATE OF codice_fiscale, partita_iva, stato_id; fase a05, perche'' l''immutabilita'' parli prima della presenza e del formato): le parti dell''identificativo fiscale gia'' scritte non si cambiano e non si svuotano, salvo il SUPER_ADMIN; un CF o una P.IVA vuoti si possono riempire. La regola e'' anagrafiche.fn_id_fiscale_bloccato, letta sul valore OLD; la stessa regola spegne i campi nel form (dbops.lock_columns_conditional, anagrafiche.fn_soggetto_id_fiscale_bloccato). Confronta i valori gia'' normalizzati da trgfn_soggetti_normalize (a01). Rifiuto: E_SOGGETTO_ID_FISCALE_IMMUTABILE, con campo = la colonna.';
```

</div>

---
{% include-markdown "signature-core.md" %}
