{% include-markdown "it/dbzero/config/manual/trgfn_parameters_guard_default_tipo_soggetto_dettaglio.md" %}
# ⚙️ Funzione `trgfn_parameters_guard_default_tipo_soggetto_dettaglio`

```sql
CREATE FUNCTION trgfn_parameters_guard_default_tipo_soggetto_dettaglio()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.trgfn_parameters_guard_default_tipo_soggetto_dettaglio()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: sostituire la FK mancante tra config.parameters e
-- config.tipi_soggetto_dettaglio per i parametri di pattern
-- DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<RUOLO>. Verifica che il
-- default_value esista come codice_interno (immutabile per
-- lock_columns) in tipi_soggetto_dettaglio.
-- Il trigger ha clausola WHEN che limita lo scope al prefisso:
-- gli altri parametri (DEFAULT_IVA_ID, VENDITE_MAX_*,
-- soggetto_default_*, etc.) non vengono toccati.
BEGIN
    IF NEW.default_value IS NULL THEN
        -- NULL ammesso: significa "no default per questo ruolo".
        -- script.fn_get_parameter_full restituira' NULL al
        -- caller, che applichera' il proprio fallback.
        RETURN NEW;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM config.tipi_soggetto_dettaglio tsd
         WHERE tsd.codice_interno = NEW.default_value
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID',
            jsonb_build_object(
                'parameter_id',  NEW.id,
                'code',          NEW.code,
                'default_value', NEW.default_value
            ),
            NEW.tx_id,
            NEW.code,
            NEW.default_value
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_parameters_guard_default_tipo_soggetto_dettaglio()
IS 'Guard FK-surrogata su config.parameters per pattern DEFAULT_TIPO_SOGGETTO_DETTAGLIO_*: valida default_value contro tipi_soggetto_dettaglio.codice_interno. Raise E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID.';
```

---
{% include-markdown "signature-core.md" %}
