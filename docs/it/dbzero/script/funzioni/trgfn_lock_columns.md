{% include-markdown "it/dbzero/script/manual/trgfn_lock_columns.md" %}
# Funzione `trgfn_lock_columns`

```sql
CREATE FUNCTION trgfn_lock_columns()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_lock_columns()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
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
--
-- Input : Array di colonne da verificare e codice relativo messaggio di errore
--         passare i parametri a coppie: colonna, msgcode.
--  
  IF n_args % 2 <> 0 THEN
  RAISE EXCEPTION '%',
        script.fn_get_messaggio(
        p_codice => 'E_ARGOMENTI_A_COPPIE'
        );
  END IF;

  FOR i IN 1..n_args BY 2 LOOP
    col     := TG_ARGV[i-1];
    msgcode := TG_ARGV[i];

    EXECUTE format('SELECT ($1).%I::text, ($2).%I::text', col, col)
      USING OLD, NEW INTO oldval, newval;

    IF oldval IS DISTINCT FROM newval THEN
      
    RAISE EXCEPTION '%',
          script.fn_get_messaggio(
          p_codice => 'E_COLONNA_NON_MODIFICABILE' ,
          p_valori => ARRAY[col]    -- qui col va in posizione %s
          -- p_lingua non è specificato, quindi vale 'it'
          );
    END IF;
  END LOOP;

  RETURN NEW;
END;
$function$
```