{% include-markdown "it/dbzero/pratiche/manual/trgfn_sospensioni_guard_coerenza_flusso.md" %}
# ⚙️ Funzione `trgfn_sospensioni_guard_coerenza_flusso`

```sql
CREATE FUNCTION trgfn_sospensioni_guard_coerenza_flusso()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_sospensioni_guard_coerenza_flusso()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: verifica che flusso_id appartenga alla stessa pratica_id della sospensione.
-- Se flusso_id IS NULL (sospensione pratica intera), nessun controllo.
DECLARE
    v_pratica_flusso pratiche.flussi.pratica_id%TYPE;
BEGIN
    IF NEW.flusso_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT pratica_id INTO v_pratica_flusso
    FROM pratiche.flussi WHERE id = NEW.flusso_id;

    IF v_pratica_flusso IS NULL OR v_pratica_flusso <> NEW.pratica_id THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.trgfn_sospensioni_guard_coerenza_flusso',
            'SOSPENSIONI_FLUSSO_NON_COERENTE',
            jsonb_build_object(
                'flusso_id', NEW.flusso_id,
                'pratica_id', NEW.pratica_id
            ),
            NULL::uuid,
            concat('Il flusso ', NEW.flusso_id, ' non appartiene alla pratica ', NEW.pratica_id)
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_sospensioni_guard_coerenza_flusso()
IS 'Guard: verifica coerenza flusso_id/pratica_id su sospensioni.';
```

---
{% include-markdown "signature-core.md" %}
