# ⚙️ Funzione `trgfn_iu_sync_catasto_unita_indirizzo`

```sql
CREATE FUNCTION trgfn_iu_sync_catasto_unita_indirizzo()
```

**Definizione completa:**

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
```

---
{% include-markdown "signature-core.md" %}
