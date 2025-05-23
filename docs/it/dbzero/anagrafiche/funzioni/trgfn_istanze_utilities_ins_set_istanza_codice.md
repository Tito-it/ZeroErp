# Funzione `trgfn_istanze_utilities_ins_set_istanza_codice`

```sql
CREATE FUNCTION trgfn_istanze_utilities_ins_set_istanza_codice()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_istanze_utilities_ins_set_istanza_codice()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  seq_val BIGINT;
  prefix  TEXT;
  sep     TEXT;
  len     INT;
  seq_name TEXT;
  tipo    TEXT := 'istanze_utilities';
BEGIN
  IF NEW.codice_istanza IS NULL THEN
    SELECT prefisso, separatore, lunghezza_numero, nome_sequenza
      INTO prefix, sep, len, seq_name
      FROM config.sistema_codici
     WHERE codice_tipo = tipo
       AND attivo = TRUE
     LIMIT 1;

    IF seq_name IS NOT NULL THEN
      EXECUTE format('SELECT nextval(%L)', seq_name) INTO seq_val;
      NEW.codice_istanza := prefix || sep || lpad(seq_val::TEXT, len, '0');
    ELSE
      RAISE EXCEPTION '%',
        script.fn_get_messaggio('SEQUENZA_NON_CONFIGURATA', tipo);
    END IF;
  END IF;

  RETURN NEW;
END;
$function$
```