{% include-markdown "it/dbzero/pratiche/manual/trgfn_flussi_giornale_assegnazione.md" %}
# ⚙️ Funzione `trgfn_flussi_giornale_assegnazione`

```sql
CREATE FUNCTION trgfn_flussi_giornale_assegnazione()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_giornale_assegnazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Registra FLUSSO_ASSEGNAZIONE_CAMBIATA nel giornale.
--   Trigger AFTER UPDATE OF risorsa_umana_id, unita_organizzativa_id
--   su pratiche.flussi (mirror del livello pratica).
BEGIN
  INSERT INTO pratiche.giornale
    (pratica_id, flusso_id, azione, origine, dettaglio, tx_id)
  VALUES (
    NEW.pratica_id,
    NEW.id,
    'FLUSSO_ASSEGNAZIONE_CAMBIATA',
    'UTENTE',
    jsonb_build_object(
      'risorsa_umana_precedente_id', OLD.risorsa_umana_id,
      'risorsa_umana_nuova_id', NEW.risorsa_umana_id,
      'unita_organizzativa_precedente_id', OLD.unita_organizzativa_id,
      'unita_organizzativa_nuova_id', NEW.unita_organizzativa_id
    ),
    NEW.tx_id
  );
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pratiche.trgfn_flussi_giornale_assegnazione()
IS 'AFTER UPDATE OF risorsa_umana_id/unita_organizzativa_id su pratiche.flussi: registra FLUSSO_ASSEGNAZIONE_CAMBIATA (origine UTENTE) nel giornale con dettaglio OLD/NEW.';
```

</div>

---
{% include-markdown "signature-core.md" %}
