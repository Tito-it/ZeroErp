{% include-markdown "it/dbzero/script/manual/trgfn_lock_columns.md" %}
# ⚙️ Funzione `trgfn_lock_columns`

```sql
CREATE FUNCTION trgfn_lock_columns()
```

**Definizione completa:**

<div data-search-exclude markdown>

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
  -- 0) GUC override per manutenzione
  IF current_setting('zeroerp.allow_lock_columns_override', true) = 'on' THEN
    RETURN NEW;
  END IF;

  -- 1) Se il numero di argomenti non e pari, errore
  IF n_args % 2 <> 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_ARGOMENTI_A_COPPIE',
      jsonb_build_object('expected_pairs', n_args/2),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  -- 2) Ciclo sulle coppie (colonna, codice messaggio)
  FOR i IN 1..n_args BY 2 LOOP
    col     := TG_ARGV[i-1];
    msgcode := TG_ARGV[i];

    -- Leggo dinamicamente OLD.col e NEW.col
    EXECUTE format(
      'SELECT ($1).%I::text, ($2).%I::text',
      col, col
    ) USING OLD, NEW INTO oldval, newval;

    IF oldval IS DISTINCT FROM newval THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        TG_NAME,
        msgcode,
        jsonb_build_object(
          'column',    col,
          'old_value', oldval,
          'new_value', newval
        ),
        NULL::uuid,
        col
      );
    END IF;
  END LOOP;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_lock_columns()
IS 'Impedisce modifica colonne protette. Override: SET LOCAL zeroerp.allow_lock_columns_override = ''on''. Argomenti a coppie (colonna, codice_messaggio).';
```

</div>

---
{% include-markdown "signature-core.md" %}
