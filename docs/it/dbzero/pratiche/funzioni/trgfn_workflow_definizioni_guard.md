{% include-markdown "it/dbzero/pratiche/manual/trgfn_workflow_definizioni_guard.md" %}
# ⚙️ Funzione `trgfn_workflow_definizioni_guard`

```sql
CREATE FUNCTION trgfn_workflow_definizioni_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_workflow_definizioni_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: proteggere il ciclo di vita dell'edizione di workflow.
--   Inv A: transizioni di stato ammesse (BOZZA->PUBBLICATA,
--          PUBBLICATA->RITIRATA).
--   Inv B: header strutturale immutabile fuori da BOZZA.
BEGIN
  -- Inv A: transizioni di stato.
  IF NEW.stato IS DISTINCT FROM OLD.stato THEN
    IF NOT (
         (OLD.stato = 'BOZZA'      AND NEW.stato = 'PUBBLICATA')
      OR (OLD.stato = 'PUBBLICATA' AND NEW.stato = 'RITIRATA')
    ) THEN
      PERFORM script.fn_log_and_raise_error(
        'pratiche',
        'pratiche.trgfn_workflow_definizioni_guard',
        'E_DEFINIZIONE_TRANSIZIONE_NON_AMMESSA',
        jsonb_build_object(
          'definizione_id', NEW.id,
          'stato_da',       OLD.stato,
          'stato_a',        NEW.stato
        ),
        NEW.tx_id,
        OLD.stato,
        NEW.stato
      );
    END IF;
  END IF;

  -- Inv B: header strutturale immutabile fuori da BOZZA.
  IF OLD.stato <> 'BOZZA' AND (
         NEW.tipo_prestazione_id  IS DISTINCT FROM OLD.tipo_prestazione_id
      OR NEW.emittente_fiscale_id IS DISTINCT FROM OLD.emittente_fiscale_id
      OR NEW.versione             IS DISTINCT FROM OLD.versione
      OR NEW.preset_origine_id    IS DISTINCT FROM OLD.preset_origine_id
      OR NEW.versione_origine     IS DISTINCT FROM OLD.versione_origine
  ) THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche',
      'pratiche.trgfn_workflow_definizioni_guard',
      'E_DEFINIZIONE_PUBBLICATA_IMMUTABILE',
      jsonb_build_object(
        'definizione_id', NEW.id,
        'stato',          OLD.stato
      ),
      NEW.tx_id,
      NEW.id::text,
      OLD.stato
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_workflow_definizioni_guard()
IS 'BEFORE UPDATE OF stato/header su pratiche.workflow_definizioni: transizioni ammesse BOZZA->PUBBLICATA e PUBBLICATA->RITIRATA (510); header strutturale (tipo/emittente/versione/provenance) immutabile fuori da BOZZA (509). descrizione/meta sempre correggibili (fuori dall''evento UPDATE OF).';
```

</div>

---
{% include-markdown "signature-core.md" %}
