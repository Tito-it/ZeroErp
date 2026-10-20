{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_contabili_righe_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_vendite_contabili_righe_guard_transizione`

```sql
CREATE FUNCTION trgfn_vendite_contabili_righe_guard_transizione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_codice_da pagamenti.vendite_contabili_righe_stati.codice_interno%TYPE;
    v_codice_a  pagamenti.vendite_contabili_righe_stati.codice_interno%TYPE;
    v_ammessa   boolean := false;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Enforcement DB-first del grafo degli stati della RIGA
    --   contabile, da pagamenti.transizioni_stati_contabile_riga.
    --
    -- ⭐ POSTATA e' TERMINALE, ed e' la meta' del difetto C-2 che
    --    si chiude qui: il sync dei fondi non puo' piu' riportare
    --    ad ABBINATA una riga il cui movimento esiste gia'.
    --
    -- ⚠️ Solo UPDATE OF stato_id: il sync dei fondi crea le sue
    --    righe direttamente in ABBINATA.
    -- =========================================================

    IF NEW.stato_id IS NOT DISTINCT FROM OLD.stato_id THEN
        RETURN NEW;
    END IF;

    SELECT
        max(CASE WHEN s.id = OLD.stato_id THEN s.codice_interno END),
        max(CASE WHEN s.id = NEW.stato_id THEN s.codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM pagamenti.vendite_contabili_righe_stati s
     WHERE s.id IN (OLD.stato_id, NEW.stato_id);

    SELECT EXISTS (
        SELECT 1
          FROM pagamenti.transizioni_stati_contabile_riga t
         WHERE t.stato_da_id = OLD.stato_id
           AND t.stato_a_id  = NEW.stato_id
           AND t.attivo IS TRUE
    ) INTO v_ammessa;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'pagamenti.trgfn_vendite_contabili_righe_guard_transizione',
            'E_RIGA_CONTABILE_TRANSIZIONE_NON_AMMESSA',
            jsonb_build_object(
                'contabile_riga_id', NEW.id,
                'contabile_id',      NEW.contabile_id,
                'stato_da_id',       OLD.stato_id,
                'stato_a_id',        NEW.stato_id,
                'stato_da',          v_codice_da,
                'stato_a',           v_codice_a
            ),
            NEW.tx_id,
            NEW.id::text,
            COALESCE(v_codice_da, 'NULL'),
            COALESCE(v_codice_a,  'NULL')
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_transizione()
IS 'Guard del grafo degli stati della riga contabile, da pagamenti.transizioni_stati_contabile_riga. Solo UPDATE OF stato_id. ⭐ Con POSTATA terminale chiude per costruzione il difetto C-2: il sync dei fondi non puo'' piu'' riportare ad ABBINATA una riga il cui movimento esiste gia''.';
```

</div>

---
{% include-markdown "signature-core.md" %}
