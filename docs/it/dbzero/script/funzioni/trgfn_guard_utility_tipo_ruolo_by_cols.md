{% include-markdown "it/dbzero/script/manual/trgfn_guard_utility_tipo_ruolo_by_cols.md" %}
# ⚙️ Funzione `trgfn_guard_utility_tipo_ruolo_by_cols`

```sql
CREATE FUNCTION trgfn_guard_utility_tipo_ruolo_by_cols()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_guard_utility_tipo_ruolo_by_cols()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_utility_col text;
  v_soggetto_ruolo_col text;
  v_utility_txt text;
  v_soggetto_ruolo_txt text;
  v_utility_id config.utilities.id%TYPE;
  v_soggetto_ruolo_id anagrafiche.soggetti_ruoli.id%TYPE;
  v_tipo_ruolo_id config.tipi_ruoli.id%TYPE;
BEGIN
  -- Argomenti trigger:
  -- TG_ARGV[0] = nome colonna utility_id
  -- TG_ARGV[1] = nome colonna soggetto_ruolo_id
  IF TG_NARGS <> 2 THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.trgfn_guard_utility_tipo_ruolo_by_cols',
      'ERRORE_PARAMETRI',
      jsonb_build_object(
        'detail', 'Sono richiesti 2 argomenti trigger: utility_col, soggetto_ruolo_col',
        'tg_nargs', TG_NARGS,
        'trigger', TG_NAME
      ),
      NULL::uuid,
      concat('Argomenti trigger non validi per ', TG_NAME, ': TG_NARGS=', TG_NARGS::text)
    );
  END IF;

  v_utility_col := TG_ARGV[0];
  v_soggetto_ruolo_col := TG_ARGV[1];

  v_utility_txt := to_jsonb(NEW) ->> v_utility_col;
  v_soggetto_ruolo_txt := to_jsonb(NEW) ->> v_soggetto_ruolo_col;

  -- Se i valori non sono presenti non forziamo il controllo in questa fase.
  IF v_utility_txt IS NULL OR v_soggetto_ruolo_txt IS NULL THEN
    RETURN NEW;
  END IF;

  BEGIN
    v_utility_id := v_utility_txt::integer;
    v_soggetto_ruolo_id := v_soggetto_ruolo_txt::bigint;
  EXCEPTION
    WHEN OTHERS THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        'script.trgfn_guard_utility_tipo_ruolo_by_cols',
        'ERRORE_PARAMETRI',
        jsonb_build_object(
          'detail', 'Valori colonna non castabili a ID',
          'utility_col', v_utility_col,
          'utility_value', v_utility_txt,
          'soggetto_ruolo_col', v_soggetto_ruolo_col,
          'soggetto_ruolo_value', v_soggetto_ruolo_txt
        ),
        NULL::uuid,
        concat(
          'Valori non validi per guard utility/tipo_ruolo: ',
          v_utility_col, '=', coalesce(v_utility_txt, 'NULL'),
          ', ',
          v_soggetto_ruolo_col, '=', coalesce(v_soggetto_ruolo_txt, 'NULL')
        )
      );
  END;

  SELECT sr.tipo_ruolo_id
    INTO v_tipo_ruolo_id
    FROM anagrafiche.soggetti_ruoli sr
   WHERE sr.id = v_soggetto_ruolo_id;

  IF v_tipo_ruolo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.trgfn_guard_utility_tipo_ruolo_by_cols',
      'E_GENERICO',
      jsonb_build_object(
        'detail', 'soggetto_ruolo_id non trovato in anagrafiche.soggetti_ruoli',
        'soggetto_ruolo_id', v_soggetto_ruolo_id,
        'table', concat(TG_TABLE_SCHEMA, '.', TG_TABLE_NAME)
      ),
      NULL::uuid,
      concat(
        'soggetto_ruolo_id non valido per guard utility/tipo_ruolo: ',
        v_soggetto_ruolo_id::text
      )
    );
  END IF;

  PERFORM script.fn_guard_utility_tipo_ruolo(
    p_utility_id => v_utility_id,
    p_tipo_ruolo_id => v_tipo_ruolo_id,
    p_context => concat(TG_TABLE_SCHEMA, '.', TG_TABLE_NAME, ' ', TG_OP)
  );

  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
