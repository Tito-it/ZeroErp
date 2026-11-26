{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_guard_cf_piva_obbligatori.md" %}
# ⚙️ Funzione `trgfn_soggetti_guard_cf_piva_obbligatori`

```sql
CREATE FUNCTION trgfn_soggetti_guard_cf_piva_obbligatori()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Guard: la PRESENZA di partita_iva e codice_fiscale secondo la natura
-- (config.tipi_soggetto_dettaglio.piva_obbligatoria, cf_obbligatorio).
-- Il FORMATO lo valida trgfn_soggetti_valida_cf_piva_dispatch; la
-- stringa vuota l'ha gia' fatta NULL trgfn_soggetti_normalize (a01).
DECLARE
    v_piva_obbl  config.tipi_soggetto_dettaglio.piva_obbligatoria%TYPE;
    v_cf_obbl    config.tipi_soggetto_dettaglio.cf_obbligatorio%TYPE;
    v_cod_int    config.tipi_soggetto_dettaglio.codice_interno%TYPE;
    v_natura     config.tipi_soggetto_dettaglio.descrizione%TYPE;
BEGIN
    -- Senza natura non si impone niente; una natura inesistente la dice la FK.
    IF NEW.tipo_soggetto_dettaglio_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT tsd.piva_obbligatoria, tsd.cf_obbligatorio, tsd.codice_interno,
           COALESCE(tsd.descrizione, tsd.codice_interno)
      INTO v_piva_obbl, v_cf_obbl, v_cod_int, v_natura
      FROM config.tipi_soggetto_dettaglio tsd
     WHERE tsd.id = NEW.tipo_soggetto_dettaglio_id;

    IF v_piva_obbl AND NEW.partita_iva IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'trgfn_soggetti_guard_cf_piva_obbligatori',
            'E_PIVA_OBBLIGATORIA',
            jsonb_build_object(
                'campo',                      'partita_iva',
                'soggetto_id',                NEW.id,
                'tipo_soggetto_dettaglio_id', NEW.tipo_soggetto_dettaglio_id,
                'codice_interno',             v_cod_int),
            NEW.tx_id,
            v_natura);
    END IF;

    IF v_cf_obbl AND NEW.codice_fiscale IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'trgfn_soggetti_guard_cf_piva_obbligatori',
            'E_CF_OBBLIGATORIO',
            jsonb_build_object(
                'campo',                      'codice_fiscale',
                'soggetto_id',                NEW.id,
                'tipo_soggetto_dettaglio_id', NEW.tipo_soggetto_dettaglio_id,
                'codice_interno',             v_cod_int),
            NEW.tx_id,
            v_natura);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori()
IS 'Guard di anagrafiche.soggetti (BEFORE INSERT OR UPDATE OF tipo_soggetto_dettaglio_id, partita_iva, codice_fiscale): la PRESENZA di partita IVA e codice fiscale secondo la natura (config.tipi_soggetto_dettaglio.piva_obbligatoria, cf_obbligatorio). Rifiuti E_PIVA_OBBLIGATORIA ed E_CF_OBBLIGATORIO, col campo; la frase nomina la natura per descrizione, senza id. La stringa vuota la fa NULL trgfn_soggetti_normalize (a01); il FORMATO lo valida trgfn_soggetti_valida_cf_piva_dispatch. Senza natura tace.';
```

</div>

---
{% include-markdown "signature-core.md" %}
