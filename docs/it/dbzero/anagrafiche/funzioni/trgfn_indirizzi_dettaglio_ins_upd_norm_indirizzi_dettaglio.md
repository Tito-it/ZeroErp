# ⚙️ Funzione `trgfn_indirizzi_dettaglio_ins_upd_norm_indirizzi_dettaglio`

```sql
CREATE FUNCTION trgfn_indirizzi_dettaglio_ins_upd_norm_indirizzi_dettaglio()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_dettaglio_ins_upd_norm_indirizzi_dettaglio()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Normalizza descrizione via (maiuscolo e trim)
  SELECT UPPER(TRIM(sg.descrizione))
    INTO STRICT NEW.via_norm
  FROM config.stradario_generale sg
  WHERE sg.id = NEW.stradario_id
  LIMIT 1;

  -- Normalizza civico + estensione (es. "10/BIS")
IF NEW.civico IS NOT NULL THEN
  -- se c’è estensione, la concateno con slash
  IF NEW.estensione_civico IS NOT NULL AND NEW.estensione_civico <> '' THEN
    -- aggiungo ‘/’ se non inizia già con '/'
    IF LEFT(NEW.estensione_civico, 1) <> '/' THEN
      NEW.estensione_civico := '/' || NEW.estensione_civico;
    END IF;

    NEW.civico_norm := UPPER(
      NEW.civico::TEXT
      || NEW.estensione_civico
    );
  ELSE
    -- nessuna estensione: solo numero
    NEW.civico_norm := UPPER(NEW.civico::TEXT);
  END IF;
ELSE
  NEW.civico_norm := '';
END IF;


  RETURN NEW;
END;
$function$
```