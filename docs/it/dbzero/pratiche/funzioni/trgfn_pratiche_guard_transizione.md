{% include-markdown "it/dbzero/pratiche/manual/trgfn_pratiche_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_pratiche_guard_transizione`

```sql
CREATE FUNCTION trgfn_pratiche_guard_transizione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: blocca transizioni di stato non ammesse per le pratiche.
-- Consulta la matrice config.transizioni_stati_pratiche (solo righe attive).
-- Risolve i codici interni degli stati per messaggi di errore leggibili.
DECLARE
    v_codice_da config.stati_pratiche.codice_interno%TYPE;
    v_codice_a  config.stati_pratiche.codice_interno%TYPE;
BEGIN
    -- Nessuna transizione: niente da validare
    IF OLD.stato_id = NEW.stato_id THEN
        RETURN NEW;
    END IF;

    -- Verifica che la transizione sia ammessa
    IF NOT EXISTS (
        SELECT 1 FROM config.transizioni_stati_pratiche
        WHERE stato_da_id = OLD.stato_id
          AND stato_a_id  = NEW.stato_id
          AND attivo = true
    ) THEN
        SELECT codice_interno INTO v_codice_da
        FROM config.stati_pratiche WHERE id = OLD.stato_id;

        SELECT codice_interno INTO v_codice_a
        FROM config.stati_pratiche WHERE id = NEW.stato_id;

        PERFORM script.fn_log_and_raise_error(
            'pratiche',
            'pratiche.trgfn_pratiche_guard_transizione',
            'E_PRATICHE_TRANSIZIONE_NON_AMMESSA',
            jsonb_build_object(
                'stato_da', v_codice_da,
                'stato_a', v_codice_a
            ),
            NULL::uuid,
            concat('Transizione pratica non ammessa: ', v_codice_da, ' -> ', v_codice_a)
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_pratiche_guard_transizione()
IS 'BEFORE UPDATE OF stato_id: blocca transizioni non ammesse per le pratiche.';
```

</div>

---
{% include-markdown "signature-core.md" %}
