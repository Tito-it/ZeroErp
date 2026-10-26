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
-- Guard: verifica la presenza obbligatoria di partita_iva e/o codice_fiscale
-- in base alla configurazione di config.tipi_soggetto_dettaglio.
-- Complementare a trgfn_soggetti_valida_cf_piva_dispatch che valida il FORMATO.
-- Questa funzione valida la PRESENZA.
DECLARE
    v_det RECORD;
    v_error_ctx jsonb;
BEGIN
    -- Se tipo_soggetto_dettaglio_id e' NULL, non possiamo imporre nulla
    IF NEW.tipo_soggetto_dettaglio_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- Recupero configurazione obbligatorieta' dal tipo di dettaglio
    SELECT tsd.piva_obbligatoria, tsd.cf_obbligatorio, tsd.codice_interno
      INTO v_det
      FROM config.tipi_soggetto_dettaglio tsd
     WHERE tsd.id = NEW.tipo_soggetto_dettaglio_id;

    -- Guard partita_iva obbligatoria
    IF v_det.piva_obbligatoria = true AND NEW.partita_iva IS NULL THEN
        v_error_ctx := jsonb_build_object(
            'campo', 'partita_iva',
            'soggetto_id', NEW.id,
            'tipo_soggetto_dettaglio_id', NEW.tipo_soggetto_dettaglio_id,
            'codice_interno', v_det.codice_interno
        );
        PERFORM script.fn_log_and_raise_error(
            'database',
            'trgfn_soggetti_guard_cf_piva_obbligatori',
            'E_PIVA_OBBLIGATORIA',
            v_error_ctx,
            NEW.tx_id,
            v_det.codice_interno::text,
            NEW.id::text
        );
    END IF;

    -- Guard codice_fiscale obbligatorio
    IF v_det.cf_obbligatorio = true AND NEW.codice_fiscale IS NULL THEN
        v_error_ctx := jsonb_build_object(
            'campo', 'codice_fiscale',
            'soggetto_id', NEW.id,
            'tipo_soggetto_dettaglio_id', NEW.tipo_soggetto_dettaglio_id,
            'codice_interno', v_det.codice_interno
        );
        PERFORM script.fn_log_and_raise_error(
            'database',
            'trgfn_soggetti_guard_cf_piva_obbligatori',
            'E_CF_OBBLIGATORIO',
            v_error_ctx,
            NEW.tx_id,
            v_det.codice_interno::text,
            NEW.id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori()
IS 'Guard trigger: verifica la presenza obbligatoria di partita_iva e/o codice_fiscale
in base alla configurazione di config.tipi_soggetto_dettaglio (piva_obbligatoria, cf_obbligatorio).
Se tipo_soggetto_dettaglio_id e'' NULL, nessun controllo viene eseguito.
Complementare a trgfn_soggetti_valida_cf_piva_dispatch che valida il FORMATO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
