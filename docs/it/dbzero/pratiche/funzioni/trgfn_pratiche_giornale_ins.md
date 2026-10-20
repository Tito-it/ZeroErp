{% include-markdown "it/dbzero/pratiche/manual/trgfn_pratiche_giornale_ins.md" %}
# ⚙️ Funzione `trgfn_pratiche_giornale_ins`

```sql
CREATE FUNCTION trgfn_pratiche_giornale_ins()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_giornale_ins()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  INSERT INTO pratiche.giornale
    (pratica_id, flusso_id, azione, origine, dettaglio, tx_id)
  VALUES (
    NEW.id,
    NULL,
    'PRATICA_CREATA',
    'SISTEMA',
    jsonb_build_object(
      'tipo_prestazione_id', NEW.tipo_prestazione_id,
      'stato_id', NEW.stato_id,
      'priorita_id', NEW.priorita_id,
      'soggetto_id', NEW.soggetto_id,
      'canale_origine_id', NEW.canale_origine_id
    ),
    coalesce(NEW.tx_id, dbops.fn_get_or_create_session_tx_id())
  );
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_pratiche_giornale_ins()
IS 'AFTER INSERT su pratiche: logga PRATICA_CREATA nel giornale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
