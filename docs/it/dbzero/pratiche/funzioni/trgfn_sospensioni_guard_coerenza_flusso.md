{% include-markdown "it/dbzero/pratiche/manual/trgfn_sospensioni_guard_coerenza_flusso.md" %}
# ⚙️ Funzione `trgfn_sospensioni_guard_coerenza_flusso`

```sql
CREATE FUNCTION trgfn_sospensioni_guard_coerenza_flusso()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

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
            'E_SOSPENSIONI_FLUSSO_NON_COERENTE',
            jsonb_build_object(
                'flusso_id', NEW.flusso_id,
                'pratica_id', NEW.pratica_id
            ),
            NULL::uuid,
            -- ⚠️ ARITA' (2026-08-18): il concat() ricostruiva parola per parola
            --   la stessa frase che sta a catalogo («Il flusso %s non appartiene
            --   alla pratica %s») e la passava come valore unico: due segnaposto,
            --   un valore, format() alzava 22023.
            NEW.flusso_id::text, NEW.pratica_id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_sospensioni_guard_coerenza_flusso()
IS 'Guard: verifica coerenza flusso_id/pratica_id su sospensioni.';
```

</div>

---
{% include-markdown "signature-core.md" %}
