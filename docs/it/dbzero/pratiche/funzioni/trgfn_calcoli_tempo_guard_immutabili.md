{% include-markdown "it/dbzero/pratiche/manual/trgfn_calcoli_tempo_guard_immutabili.md" %}
# ⚙️ Funzione `trgfn_calcoli_tempo_guard_immutabili`

```sql
CREATE FUNCTION trgfn_calcoli_tempo_guard_immutabili()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_calcoli_tempo_guard_immutabili()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: blocca modifica dei campi di riferimento su calcoli_tempo.
-- Campi immutabili: pratica_id, flusso_da_id, flusso_a_id,
--   formula_tempo_id, giorni_formula, data_inizio_calcolo.
BEGIN
    IF OLD.pratica_id IS DISTINCT FROM NEW.pratica_id THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche', TG_NAME, 'E_COLONNA_NON_MODIFICABILE',
            jsonb_build_object('column', 'pratica_id', 'id', OLD.id),
            NULL::uuid, 'pratica_id');
    END IF;

    IF OLD.flusso_da_id IS DISTINCT FROM NEW.flusso_da_id THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche', TG_NAME, 'E_COLONNA_NON_MODIFICABILE',
            jsonb_build_object('column', 'flusso_da_id', 'id', OLD.id),
            NULL::uuid, 'flusso_da_id');
    END IF;

    IF OLD.flusso_a_id IS DISTINCT FROM NEW.flusso_a_id THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche', TG_NAME, 'E_COLONNA_NON_MODIFICABILE',
            jsonb_build_object('column', 'flusso_a_id', 'id', OLD.id),
            NULL::uuid, 'flusso_a_id');
    END IF;

    IF OLD.formula_tempo_id IS DISTINCT FROM NEW.formula_tempo_id THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche', TG_NAME, 'E_COLONNA_NON_MODIFICABILE',
            jsonb_build_object('column', 'formula_tempo_id', 'id', OLD.id),
            NULL::uuid, 'formula_tempo_id');
    END IF;

    IF OLD.giorni_formula IS DISTINCT FROM NEW.giorni_formula THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche', TG_NAME, 'E_COLONNA_NON_MODIFICABILE',
            jsonb_build_object('column', 'giorni_formula', 'id', OLD.id),
            NULL::uuid, 'giorni_formula');
    END IF;

    IF OLD.data_inizio_calcolo IS DISTINCT FROM NEW.data_inizio_calcolo THEN
        PERFORM script.fn_log_and_raise_error(
            'pratiche', TG_NAME, 'E_COLONNA_NON_MODIFICABILE',
            jsonb_build_object('column', 'data_inizio_calcolo', 'id', OLD.id),
            NULL::uuid, 'data_inizio_calcolo');
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_calcoli_tempo_guard_immutabili()
IS 'Guard: blocca modifica campi immutabili su calcoli_tempo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
