{% include-markdown "it/dbzero/pratiche/manual/trgfn_allegati_pratiche_giornale.md" %}
# ⚙️ Funzione `trgfn_allegati_pratiche_giornale`

```sql
CREATE FUNCTION trgfn_allegati_pratiche_giornale()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_allegati_pratiche_giornale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Registra ALLEGATO_AGGIUNTO nel giornale a livello pratica.
  --   Trigger AFTER INSERT su pratiche.allegati_pratiche.
  --
  -- Dettaglio:
  --   flusso_id e' NULL perche' l'allegato e' a livello pratica.
  --   La tabella allegati_pratiche non ha tx_id (immutabile),
  --   quindi tx_id nel giornale e' NULL.
  -- =========================================================

  INSERT INTO pratiche.giornale
    (pratica_id, flusso_id, azione, origine, dettaglio)
  VALUES (
    NEW.pratica_id,
    NULL,
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

COMMENT ON FUNCTION pratiche.trgfn_allegati_pratiche_giornale()
IS 'AFTER INSERT su allegati_pratiche: logga ALLEGATO_AGGIUNTO nel giornale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
