
--
--liquibase formatted sql
--changeset mctit:20250507-01-trgfn_lock_columns runOnChange:true

-- FUNCTION: script.trgfn_lock_columns()

-- DROP FUNCTION IF EXISTS script.trgfn_lock_columns();

CREATE OR REPLACE FUNCTION script.trgfn_lock_columns()
    RETURNS trigger
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE NOT LEAKPROOF
AS $BODY$
DECLARE
  n_args  int := array_length(TG_ARGV,1);
  i       int;
  col     text;
  msgcode text;
  oldval  text;
  newval  text;
BEGIN

-- Scopo: Verificare per le colonne di input che il loro valore 
--        non sia modificabile. Attenzione passare i parametri a 
--		  coppie: colonna, msgcode.
-- Input : Array di colonne da verificare e codice relativo messaggio di errore

  IF n_args % 2 <> 0 THEN
    RAISE EXCEPTION 'Devi passare argomenti a coppie: colonna,msgcode';
  END IF;

  FOR i IN 1..n_args BY 2 LOOP
    col     := TG_ARGV[i-1];
    msgcode := TG_ARGV[i];

    EXECUTE format('SELECT ($1).%I::text, ($2).%I::text', col, col)
      USING OLD, NEW INTO oldval, newval;

    IF oldval IS DISTINCT FROM newval THEN
      RAISE EXCEPTION '%', script.fn_get_messaggio(msgcode, col);
    END IF;
  END LOOP;

  RETURN NEW;
END;
$BODY$;


COMMENT ON FUNCTION script.trgfn_lock_columns()
    IS 'Controlla che il valore della colonna non sia modificato';
