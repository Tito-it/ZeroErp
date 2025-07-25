{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_dettaglio_ins_upd_norm_indirizzi_dettaglio.md" %}
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
  -- 1) Normalizzazione della descrizione della via:
  -- Recupera la descrizione dello stradario dalla view script.vw_indirizzo_completo                  -- Applica TRIM per rimuovere spazi iniziali/finali e UPPER per convertire in maiuscolo
  -- STRICT garantisce che la query deve restituire esattamente una riga
     SELECT UPPER(TRIM(iv.tipo_toponimo || ' ' || iv.nome_strada))
      INTO STRICT NEW.via_norm
     FROM script.vw_indirizzo_completo iv
     WHERE iv.id_stradario = NEW.stradario_id
     LIMIT 1;

  -- 2) Normalizzazione del numero civico con eventuale estensione:
  -- Processa solo se il civico è valorizzato
  IF NEW.civico IS NOT NULL AND NEW.civico <> 0 THEN
    -- Se esiste un'estensione del civico (es: "A" in "12/A")
    IF NEW.estensione_civico IS NOT NULL AND NEW.estensione_civico <> '' THEN
      -- Assicura che l'estensione inizi con "/" (aggiunge se mancante)
      IF LEFT(NEW.estensione_civico,1) <> '/' THEN
        NEW.estensione_civico := '/' || NEW.estensione_civico;
      END IF;
      -- Combina civico ed estensione (es: "12" + "/A" => "12/A")
      NEW.civico_norm := UPPER(NEW.civico::TEXT || NEW.estensione_civico);
    ELSE
      -- Solo civico senza estensione (conversione in maiuscolo)
      NEW.civico_norm := UPPER(NEW.civico::TEXT);
    END IF;
  ELSE
    -- Civico non valorizzato
    NEW.civico_norm := 'SNC';
  END IF;

  -- 3) Costruzione dell'indirizzo completo normalizzato:
  -- Crea una stringa unica concatenando tutti i componenti dell'indirizzo
  -- TRIM rimuove spazi iniziali/finali dal risultato finale
  -- Ogni componente è aggiunto solo se valorizzato, preceduto da un separatore appropriato
  NEW.indirizzo_normalizzato := TRIM(BOTH ' ' FROM (
      NEW.via_norm  -- Via già normalizzata
    || CASE WHEN NEW.civico_norm <> '' THEN ', ' || NEW.civico_norm ELSE '' END  -- Civico (es: ", 12/A")
    || CASE WHEN NEW.palazzina   IS NOT NULL AND NEW.palazzina <> '' 
            THEN ', Pal.'   || NEW.palazzina ELSE '' END  -- Palazzina (es: ", Pal.B")
    || CASE WHEN NEW.scala        IS NOT NULL AND NEW.scala <> '' 
            THEN ', Scala ' || NEW.scala      ELSE '' END  -- Scala (es: ", Scala 2")
    || CASE WHEN NEW.piano        IS NOT NULL AND NEW.piano <> '' 
            THEN ', Piano '     || NEW.piano      ELSE '' END  -- Piano (es: ", P3")
    || CASE WHEN NEW.interno      IS NOT NULL AND NEW.interno <> '' 
            THEN ', Int.'  || NEW.interno    ELSE '' END  -- Interno (es: ", Int.5")
  ));

  -- Restituisce il record modificato con i campi normalizzati
  RETURN NEW;
END;
$function$
```
---
{% include-markdown "signature-core.md" %}
