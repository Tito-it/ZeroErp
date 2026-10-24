# ⚙️ Funzione `trgfn_coppie_fattura_provision_registri`

```sql
CREATE FUNCTION trgfn_coppie_fattura_provision_registri()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_coppie_fattura_provision_registri()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Una riga di config.tipi_doc_fiscale o di
    --   config.nature_doc_fiscale che nasce attiva, o si
    --   accende, collega la sua coppia al registro delle
    --   fatture standard di ogni emittente attivo.
    --
    -- Regole:
    --   - solo INSERT attivo o passaggio a attivo: il loader dei
    --     CSV riscrive `attivo` anche quando non cambia;
    --   - la regola sta nella primitiva: qui solo la porta.
    -- =========================================================
    IF NEW.attivo IS NOT TRUE THEN
        RETURN NULL;
    END IF;

    IF TG_OP = 'UPDATE' AND OLD.attivo IS TRUE THEN
        RETURN NULL;
    END IF;

    PERFORM vendite.fn_provision_registri_famiglia('FATTURA');
    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_coppie_fattura_provision_registri()
IS 'Trigger AFTER ROW su config.tipi_doc_fiscale e config.nature_doc_fiscale (2026-10-18): un tipo documento o una natura che nasce attivo, o si accende, collega la sua coppia (tipo documento, natura) al registro delle fatture standard di ogni emittente attivo, facendolo nascere se manca, via vendite.fn_provision_registri_famiglia(''FATTURA''). E'' il gemello di cio'' che la madre di una famiglia fa per i registri delle famiglie. Solo all''INSERT attivo e al passaggio da spento ad acceso: il loader dei CSV riscrive attivo anche quando non cambia, e ricollegare a ogni migrate una coppia scollegata apposta sarebbe un cambio silenzioso. Nessuna regola qui: sta nella primitiva vendite.fn_provision_registri. R-BE-14, D-14a … D-14d di Tid, brief-db-processi-accensione-per-ambiente §6.14.';
```

</div>

---
{% include-markdown "signature-core.md" %}
