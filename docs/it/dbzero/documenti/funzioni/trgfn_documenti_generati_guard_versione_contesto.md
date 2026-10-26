{% include-markdown "it/dbzero/documenti/manual/trgfn_documenti_generati_guard_versione_contesto.md" %}
# ⚙️ Funzione `trgfn_documenti_generati_guard_versione_contesto`

```sql
CREATE FUNCTION trgfn_documenti_generati_guard_versione_contesto()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.trgfn_documenti_generati_guard_versione_contesto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: una stampa si registra solo se il contesto congelato ha la forma
--   che la versione di template legge. La regola sta in
--   documenti.fn_guard_versione_contesto; qui si legge solo la forma dei dati.
DECLARE
    -- La forma com'e' scritta nel contesto, per decidere se e' un intero.
    v_forma_json documenti.documenti_generati.context_json%TYPE
                     := NEW.context_json -> '_meta' -> 'context_version';
    v_forma      documenti.template_documenti_versioni.versione_contesto%TYPE;
BEGIN
    v_forma := CASE
                   WHEN jsonb_typeof(v_forma_json) = 'number'
                    AND (v_forma_json #>> '{}') ~ '^[0-9]{1,9}$'
                   THEN (v_forma_json #>> '{}')::integer
               END;

    PERFORM documenti.fn_guard_versione_contesto(NEW.template_versione_id, v_forma);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION documenti.trgfn_documenti_generati_guard_versione_contesto()
IS 'Guard sull''INSERT di documenti.documenti_generati: la forma dichiarata dal contesto congelato (context_json -> _meta -> context_version, un intero JSON; altrimenti NULL = non dichiarata) deve essere quella che la versione di template legge. Delega a documenti.fn_guard_versione_contesto (E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA / _NON_VERIFICABILE). Solo INSERT: il contesto e la versione di una stampa non cambiano dopo (protect_snapshot). Brief: brief-db-documenti-versione-contesto-template.';
```

</div>

---
{% include-markdown "signature-core.md" %}
