CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_ins_genera_cdsoggetto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE

  seq_val    BIGINT;
  prefix     TEXT;
  sep        TEXT;
  len        INT;
  seq_name   TEXT;
  tipo       TEXT := 'soggetto';  -- il “tipo” da passare al messaggio
BEGIN
-- La funzione genera il codice soggetto con un algoritmo.
-- Il codice viene generato solo se il valore New.codice_soggetto=Null
-- Deve essere configurata la tabella config.sistema_codice con tipo soggetto
-- La funzione viene attivata dal trigger in insert. 
-- Output New.soggetto_codice

  IF NEW.soggetto_codice IS NULL THEN
    SELECT prefisso, separatore, lunghezza_numero, nome_sequenza
      INTO prefix, sep, len, seq_name
      FROM config.sistema_codici
     WHERE codice_tipo = tipo
       AND attivo = TRUE;

    IF seq_name IS NOT NULL THEN
      EXECUTE format('SELECT nextval(%L)', seq_name) INTO seq_val;
      NEW.soggetto_codice := prefix || sep || lpad(seq_val::TEXT, len, '0');
    ELSE
      -- ora il messaggio viene letto dalla tabella e “tipo” passato al posto di %
      RAISE EXCEPTION '%',
        script.fn_get_messaggio('SEQUENZA_NON_CONFIGURATA', tipo);
    END IF;
  END IF;

  RETURN NEW;
END;
$function$
