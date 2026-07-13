# ⚙️ Funzione `trgfn_resi_guard_transizione`

```sql
CREATE FUNCTION trgfn_resi_guard_transizione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: enforcement DB-first del grafo transizioni stato reso.
--   La transizione (OLD.stato -> NEW.stato) e' ammessa solo se
--   presente e attiva in config.transizioni_stati_reso (no grafo
--   hardcodato). Mirror di trgfn_ddt_guard_transizione.
DECLARE
    v_codice_da config.stati_doc_reso.codice_interno%TYPE;
    v_codice_a  config.stati_doc_reso.codice_interno%TYPE;
    v_ammessa   boolean := false;
BEGIN
    -- No-op se lo stato non cambia davvero (UPDATE su altre colonne).
    IF NEW.stato_doc_reso_id IS NOT DISTINCT FROM OLD.stato_doc_reso_id THEN
        RETURN NEW;
    END IF;

    SELECT
        max(CASE WHEN id = OLD.stato_doc_reso_id THEN codice_interno END),
        max(CASE WHEN id = NEW.stato_doc_reso_id THEN codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM config.stati_doc_reso
     WHERE id IN (OLD.stato_doc_reso_id, NEW.stato_doc_reso_id);

    -- La transizione deve esistere ed essere attiva in matrice.
    SELECT EXISTS (
        SELECT 1
          FROM config.transizioni_stati_reso t
         WHERE t.stato_da_id = OLD.stato_doc_reso_id
           AND t.stato_a_id  = NEW.stato_doc_reso_id
           AND t.attivo IS TRUE
    ) INTO v_ammessa;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            'E_STATO_RESO_TRANSIZIONE_NON_VALIDA',
            jsonb_build_object(
                'reso_id',  NEW.id,
                'numero',   NEW.numero,
                'stato_da', v_codice_da,
                'stato_a',  v_codice_a
            ),
            NEW.tx_id,
            NEW.id::text,
            coalesce(v_codice_da, 'NULL'),
            coalesce(v_codice_a,  'NULL')
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_guard_transizione()
IS 'Trigger function: enforcement grafo transizioni stato reso letto da config.transizioni_stati_reso (E_STATO_RESO_TRANSIZIONE_NON_VALIDA). Mirror di trgfn_ddt_guard_transizione. rev 2026-07-13.';
```

---
{% include-markdown "signature-core.md" %}
