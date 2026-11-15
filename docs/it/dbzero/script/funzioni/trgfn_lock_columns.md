{% include-markdown "it/dbzero/script/manual/trgfn_lock_columns.md" %}
# ⚙️ Funzione `trgfn_lock_columns`

```sql
CREATE FUNCTION trgfn_lock_columns()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_lock_columns()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  -- Tipi nudi DICHIARATI: contatori, nomi di colonna e codici letti
  -- da TG_ARGV, valori di colonne qualunque resi a testo. Nessuna
  -- colonna di cui siano il riflesso.
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
      -- 'campo': la colonna da evidenziare nel form, letta da
      -- script.fn_log_and_raise_error. 'column' resta per chi la legge.
      PERFORM script.fn_log_and_raise_error(
        'database',
        TG_NAME,
        msgcode,
        jsonb_build_object(
          'campo',     col,
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
IS 'Impedisce la modifica delle colonne protette. Argomenti a coppie (colonna, codice_messaggio): per ogni colonna cambiata solleva il suo codice, col nome della colonna come valore del messaggio e nel contesto campo (la colonna da evidenziare nel form), column, old_value, new_value. Argomenti dispari -> E_ARGOMENTI_A_COPPIE. I trigger li genera l''automazione LOCK_COLUMNS da dbops.automation_lock_columns; il form legge le colonne bloccate da dbops.vw_non_editable_fields. Override per la manutenzione: SET LOCAL zeroerp.allow_lock_columns_override = ''on''.';
```

</div>

---
{% include-markdown "signature-core.md" %}
