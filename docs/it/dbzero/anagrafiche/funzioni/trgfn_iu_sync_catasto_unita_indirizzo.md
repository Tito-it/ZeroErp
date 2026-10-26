{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_iu_sync_catasto_unita_indirizzo.md" %}
# ⚙️ Funzione `trgfn_iu_sync_catasto_unita_indirizzo`

```sql
CREATE FUNCTION trgfn_iu_sync_catasto_unita_indirizzo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Se mancano i dati minimi, non facciamo nulla
  IF NEW.catasto_unita_immobiliare_id IS NULL OR NEW.indirizzo_dettaglio_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Inserimento idempotente nella tabella ponte
  INSERT INTO anagrafiche.catasto_unita_immobiliari_indirizzi (
    catasto_unita_id,
    indirizzo_dettaglio_id
  )
  VALUES (
    NEW.catasto_unita_immobiliare_id,
    NEW.indirizzo_dettaglio_id
  )
  ON CONFLICT ON CONSTRAINT uq_catunitaindir
  DO NOTHING;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo()
IS 'Funzione trigger che garantisce la presenza del legame
    tra catasto_unita_immobiliari e indirizzi_dettaglio nella tabella ponte
    catasto_unita_immobiliari_indirizzi quando istanze_utilities ha entrambi i riferimenti.';
```

</div>

---
{% include-markdown "signature-core.md" %}
