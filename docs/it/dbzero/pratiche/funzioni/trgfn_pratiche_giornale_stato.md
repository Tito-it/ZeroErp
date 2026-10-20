{% include-markdown "it/dbzero/pratiche/manual/trgfn_pratiche_giornale_stato.md" %}
# ⚙️ Funzione `trgfn_pratiche_giornale_stato`

```sql
CREATE FUNCTION trgfn_pratiche_giornale_stato()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_giornale_stato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  INSERT INTO pratiche.giornale
    (pratica_id, flusso_id, azione, origine, dettaglio, tx_id)
  VALUES (
    NEW.id,
    NULL,
    'STATO_CAMBIATO',
    'SISTEMA',
    jsonb_build_object(
      'stato_precedente_id', OLD.stato_id,
      'stato_nuovo_id', NEW.stato_id
    ),
    coalesce(NEW.tx_id, dbops.fn_get_or_create_session_tx_id())
  );
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_pratiche_giornale_stato()
IS 'AFTER UPDATE su pratiche: logga STATO_CAMBIATO quando stato_id cambia.';
```

</div>

---
{% include-markdown "signature-core.md" %}
