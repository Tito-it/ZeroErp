{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_dettaglio_normalize.md" %}
# ⚙️ Funzione `trgfn_indirizzi_dettaglio_normalize`

```sql
CREATE FUNCTION trgfn_indirizzi_dettaglio_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Normalizza la descrizione della via da vw_indirizzo_completo
  SELECT UPPER(TRIM(iv.tipo_toponimo || ' ' || iv.nome_strada))
    INTO STRICT NEW.via_norm
    FROM script.vw_indirizzo_completo iv
   WHERE iv.id_stradario = NEW.stradario_id
   LIMIT 1;

  -- Normalizzazione del numero civico con eventuale estensione
  IF NEW.civico IS NOT NULL AND NEW.civico <> 0 THEN
    IF NEW.estensione_civico IS NOT NULL AND NEW.estensione_civico <> '' THEN
      IF LEFT(NEW.estensione_civico,1) <> '/' THEN
        NEW.estensione_civico := '/' || NEW.estensione_civico;
      END IF;
      NEW.civico_norm := UPPER(NEW.civico::text || NEW.estensione_civico);
    ELSE
      NEW.civico_norm := UPPER(NEW.civico::text);
    END IF;
  ELSE
    NEW.civico_norm := 'SNC';
  END IF;

  -- Costruzione dell'indirizzo completo normalizzato
  NEW.indirizzo_normalizzato := TRIM(BOTH ' ' FROM (
      NEW.via_norm
    || CASE WHEN NEW.civico_norm <> '' THEN ', ' || NEW.civico_norm ELSE '' END
    || CASE WHEN NEW.palazzina IS NOT NULL AND NEW.palazzina <> ''
            THEN ', Pal.' || NEW.palazzina ELSE '' END
    || CASE WHEN NEW.scala IS NOT NULL AND NEW.scala <> ''
            THEN ', Scala ' || NEW.scala ELSE '' END
    || CASE WHEN NEW.piano IS NOT NULL AND NEW.piano <> ''
            THEN ', Piano ' || NEW.piano ELSE '' END
    || CASE WHEN NEW.interno IS NOT NULL AND NEW.interno <> ''
            THEN ', Int.' || NEW.interno ELSE '' END
  ));

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_normalize()
IS 'Normalizza via/civico/indirizzo_normalizzato su anagrafiche.indirizzi_dettaglio usando script.vw_indirizzo_completo.';
```

---
{% include-markdown "signature-core.md" %}
