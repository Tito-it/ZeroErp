{% include-markdown "it/dbzero/pratiche/manual/trgfn_pratiche_giornale_assegnazione.md" %}
# ⚙️ Funzione `trgfn_pratiche_giornale_assegnazione`

```sql
CREATE FUNCTION trgfn_pratiche_giornale_assegnazione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_giornale_assegnazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  INSERT INTO pratiche.giornale
    (pratica_id, flusso_id, azione, origine, dettaglio, tx_id)
  VALUES (
    NEW.id,
    NULL,
    'ASSEGNAZIONE_CAMBIATA',
    'SISTEMA',
    jsonb_build_object(
      'risorsa_umana_precedente_id', OLD.risorsa_umana_id,
      'risorsa_umana_nuova_id', NEW.risorsa_umana_id,
      'unita_organizzativa_precedente_id', OLD.unita_organizzativa_id,
      'unita_organizzativa_nuova_id', NEW.unita_organizzativa_id
    ),
    coalesce(NEW.tx_id, dbops.fn_get_or_create_session_tx_id())
  );
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_pratiche_giornale_assegnazione()
IS 'AFTER UPDATE su pratiche: logga ASSEGNAZIONE_CAMBIATA quando risorsa/UO cambia.';
```

</div>

---
{% include-markdown "signature-core.md" %}
