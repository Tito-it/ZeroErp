{% include-markdown "it/dbzero/pratiche/manual/trgfn_allegati_flussi_giornale.md" %}
# ⚙️ Funzione `trgfn_allegati_flussi_giornale`

```sql
CREATE FUNCTION trgfn_allegati_flussi_giornale()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_allegati_flussi_giornale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_pratica_id pratiche.pratiche.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Registra ALLEGATO_AGGIUNTO nel giornale a livello flusso.
  --   Trigger AFTER INSERT su pratiche.allegati_flussi.
  --
  -- Dettaglio:
  --   Recupera pratica_id dal flusso per inserire nel giornale.
  --   La tabella allegati_flussi non ha tx_id (immutabile),
  --   quindi tx_id nel giornale e' NULL.
  -- =========================================================

  -- Recupera pratica_id dal flusso
  SELECT f.pratica_id INTO v_pratica_id
    FROM pratiche.flussi f
   WHERE f.id = NEW.flusso_id;

  INSERT INTO pratiche.giornale
    (pratica_id, flusso_id, azione, origine, dettaglio)
  VALUES (
    v_pratica_id,
    NEW.flusso_id,
    'ALLEGATO_AGGIUNTO',
    'SISTEMA',
    jsonb_build_object(
      'allegato_id', NEW.id,
      'tipo_allegato_id', NEW.tipo_allegato_id,
      'nome_file', NEW.nome_file
    )
  );
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_allegati_flussi_giornale()
IS 'AFTER INSERT su allegati_flussi: logga ALLEGATO_AGGIUNTO nel giornale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
