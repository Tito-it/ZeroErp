{% include-markdown "it/dbzero/pratiche/manual/trgfn_note_pratiche_giornale.md" %}
# ⚙️ Funzione `trgfn_note_pratiche_giornale`

```sql
CREATE FUNCTION trgfn_note_pratiche_giornale()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_note_pratiche_giornale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  INSERT INTO pratiche.giornale
    (pratica_id, flusso_id, azione, origine, dettaglio, tx_id)
  VALUES (
    NEW.pratica_id,
    NULL,
    'NOTA_AGGIUNTA',
    'SISTEMA',
    jsonb_build_object(
      'nota_id', NEW.id,
      'tipo_nota_id', NEW.tipo_nota_id
    ),
    coalesce(NEW.tx_id, dbops.fn_get_or_create_session_tx_id())
  );
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_note_pratiche_giornale()
IS 'AFTER INSERT su note_pratiche: logga NOTA_AGGIUNTA nel giornale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
