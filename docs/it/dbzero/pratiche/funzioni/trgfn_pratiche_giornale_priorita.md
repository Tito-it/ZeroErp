{% include-markdown "it/dbzero/pratiche/manual/trgfn_pratiche_giornale_priorita.md" %}
# ⚙️ Funzione `trgfn_pratiche_giornale_priorita`

```sql
CREATE FUNCTION trgfn_pratiche_giornale_priorita()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_giornale_priorita()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  INSERT INTO pratiche.giornale
    (pratica_id, flusso_id, azione, origine, dettaglio, tx_id)
  VALUES (
    NEW.id,
    NULL,
    'PRIORITA_CAMBIATA',
    'SISTEMA',
    jsonb_build_object(
      'priorita_precedente_id', OLD.priorita_id,
      'priorita_nuova_id', NEW.priorita_id
    ),
    coalesce(NEW.tx_id, dbops.fn_get_or_create_session_tx_id())
  );
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_pratiche_giornale_priorita()
IS 'AFTER UPDATE su pratiche: logga PRIORITA_CAMBIATA quando priorita_id cambia.';
```

</div>

---
{% include-markdown "signature-core.md" %}
