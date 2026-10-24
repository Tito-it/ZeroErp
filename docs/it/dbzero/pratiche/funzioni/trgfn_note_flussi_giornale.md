{% include-markdown "it/dbzero/pratiche/manual/trgfn_note_flussi_giornale.md" %}
# ⚙️ Funzione `trgfn_note_flussi_giornale`

```sql
CREATE FUNCTION trgfn_note_flussi_giornale()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_note_flussi_giornale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_pratica_id pratiche.pratiche.id%TYPE;
BEGIN
  SELECT f.pratica_id INTO v_pratica_id
    FROM pratiche.flussi f
   WHERE f.id = NEW.flusso_id;

  INSERT INTO pratiche.giornale
    (pratica_id, flusso_id, azione, origine, dettaglio, tx_id)
  VALUES (
    v_pratica_id,
    NEW.flusso_id,
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

COMMENT ON FUNCTION pratiche.trgfn_note_flussi_giornale()
IS 'AFTER INSERT su note_flussi: logga NOTA_AGGIUNTA nel giornale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
