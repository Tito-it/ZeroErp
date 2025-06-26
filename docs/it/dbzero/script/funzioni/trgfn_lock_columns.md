{% include-markdown "it/dbzero/script/manual/trgfn_lock_columns.md" %}
# ⚙️ Funzione `trgfn_lock_columns`

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
  n_args  int := array_length(TG_ARGV, 1);
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
  -- se il numero di argomenti non è pari, errore

  IF n_args % 2 <> 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME(),
      'E_ARGOMENTI_A_COPPIE',
      jsonb_build_object('expected_pairs', n_args/2)
    );
    -- fn_log_and_raise_error fa già RAISE EXCEPTION
  END IF;

  FOR i IN 1..n_args BY 2 LOOP
    col     := TG_ARGV[i-1];
    msgcode := TG_ARGV[i];

    -- prendo dinamicamente OLD e NEW
    EXECUTE format(
      'SELECT ($1).%I::text, ($2).%I::text',
      col, col
    ) USING OLD, NEW INTO oldval, newval;

    IF oldval IS DISTINCT FROM newval THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        TG_NAME,
        msgcode,  -- qui passi il codice testuale, non l'ID
        jsonb_build_object(
          'column',    col,
          'old_value', oldval,
          'new_value', newval
        ), col
      );
      -- fn_log_and_raise_error fa il rollback e solleva l'eccezione
    END IF;
  END LOOP;

  RETURN NEW;
END;
$function$
```