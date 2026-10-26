{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_contabili_guard_transizione.md" %}
# ⚙️ Funzione `trgfn_vendite_contabili_guard_transizione`

```sql
CREATE FUNCTION trgfn_vendite_contabili_guard_transizione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_contabili_guard_transizione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_codice_da pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_codice_a  pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_ammessa   boolean := false;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Enforcement DB-first del grafo degli stati della DISTINTA
    --   contabile. La transizione e' ammessa solo se presente e
    --   attiva in pagamenti.transizioni_stati_contabile: nessun
    --   grafo scritto qui dentro.
    --
    -- ⚠️ Solo UPDATE OF stato_id, mai l'INSERT: una distinta puo'
    --    nascere in uno stato qualunque (il giro dei fondi la crea
    --    direttamente in VALIDATA, perche' li' non c'e' digitazione
    --    e nasce gia' finita).
    -- =========================================================

    -- No-op se lo stato non cambia davvero (UPDATE su altre colonne
    -- che nomina comunque stato_id nella SET).
    IF NEW.stato_id IS NOT DISTINCT FROM OLD.stato_id THEN
        RETURN NEW;
    END IF;

    -- I due codici in UNA sola lettura: sono la stessa tabella.
    SELECT
        max(CASE WHEN s.id = OLD.stato_id THEN s.codice_interno END),
        max(CASE WHEN s.id = NEW.stato_id THEN s.codice_interno END)
      INTO v_codice_da, v_codice_a
      FROM pagamenti.vendite_contabili_stati s
     WHERE s.id IN (OLD.stato_id, NEW.stato_id);

    SELECT EXISTS (
        SELECT 1
          FROM pagamenti.transizioni_stati_contabile t
         WHERE t.stato_da_id = OLD.stato_id
           AND t.stato_a_id  = NEW.stato_id
           AND t.attivo IS TRUE
    ) INTO v_ammessa;

    IF NOT v_ammessa THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'pagamenti.trgfn_vendite_contabili_guard_transizione',
            'E_CONTABILE_TRANSIZIONE_NON_AMMESSA',
            jsonb_build_object(
                'contabile_id', NEW.id,
                'codice',       NEW.codice,
                'stato_da_id',  OLD.stato_id,
                'stato_a_id',   NEW.stato_id,
                'stato_da',     v_codice_da,
                'stato_a',      v_codice_a
            ),
            NEW.tx_id,
            NEW.codice,
            COALESCE(v_codice_da, 'NULL'),
            COALESCE(v_codice_a,  'NULL')
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pagamenti.trgfn_vendite_contabili_guard_transizione()
IS 'Guard del grafo degli stati della distinta contabile: la transizione deve esistere e essere attiva in pagamenti.transizioni_stati_contabile. Solo UPDATE OF stato_id — l''INSERT resta libero perche'' una distinta puo'' nascere in uno stato qualunque. Nato il 2026-08-21: fino ad allora pagamenti era l''unico dominio con degli stati e nessuna regola su come ci si passa.';
```

</div>

---
{% include-markdown "signature-core.md" %}
