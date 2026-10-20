{% include-markdown "it/dbzero/pratiche/manual/trgfn_flussi_giornale_ins.md" %}
# ⚙️ Funzione `trgfn_flussi_giornale_ins`

```sql
CREATE FUNCTION trgfn_flussi_giornale_ins()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_giornale_ins()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  INSERT INTO pratiche.giornale
    (pratica_id, flusso_id, azione, origine, dettaglio, tx_id)
  VALUES (
    NEW.pratica_id,
    NEW.id,
    'FLUSSO_CREATO',
    'SISTEMA',
    jsonb_build_object(
      'template_flusso_id', NEW.template_flusso_id,
      'stato_id', NEW.stato_id,
      'sequenza', NEW.sequenza
    ),
    coalesce(NEW.tx_id, dbops.fn_get_or_create_session_tx_id())
  );
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_flussi_giornale_ins()
IS 'AFTER INSERT su flussi: logga FLUSSO_CREATO nel giornale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
