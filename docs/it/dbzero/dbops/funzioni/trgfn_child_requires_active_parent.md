{% include-markdown "it/dbzero/dbops/manual/trgfn_child_requires_active_parent.md" %}
# ⚙️ Funzione `trgfn_child_requires_active_parent`

```sql
CREATE FUNCTION trgfn_child_requires_active_parent()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.trgfn_child_requires_active_parent()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_parent_schema     text;
  v_parent_table      text;
  v_parent_attivo_col text;
  v_fk_col            text;
  v_parent_ref_col    text;        -- colonna referenziata dalla FK (non sempre la PK)
  v_fk_val_text       text;        -- valore FK dal figlio (come text)
  v_parent_ref_type   text;        -- tipo della colonna referenziata (per cast)
  v_sql               text;
  v_active            boolean;
  v_child_attivo_col  text;
  v_child_has_attivo  boolean;
BEGIN
  /*
    Scopo
    -----
    Trigger function (ATTIVO/REQUIRE): impedisce INSERT/UPDATE sul figlio
    se il padre collegato non e' attivo. Se il figlio ha colonna attivo, il
    controllo si applica solo quando il figlio e' attivo.

    Argomenti attesi (TG_ARGV)
    --------------------------
    [0] parent_schema      - schema della tabella padre
    [1] parent_table       - nome tabella padre
    [2] parent_attivo_col  - nome colonna attivo del padre
    [3] fk_col             - nome colonna FK sul figlio
    [4] parent_ref_col     - colonna del padre referenziata dalla FK
                             (puo' essere una UNIQUE diversa da PK).
                             Se omesso, fallback 'id' (DEPRECATO).
  */

  IF array_length(TG_ARGV, 1) < 4 THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_ATTIVO_REQUIRE',
      jsonb_build_object(
        'trigger', TG_NAME,
        'table',   TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
        'tg_argv', TG_ARGV
      ),
      NULL::uuid,
      'Attesi: parent_schema, parent_table, parent_attivo_col, fk_col [, parent_ref_col]'
    );
  END IF;

  v_parent_schema     := TG_ARGV[0];
  v_parent_table      := TG_ARGV[1];
  v_parent_attivo_col := TG_ARGV[2];
  v_fk_col            := TG_ARGV[3];
  v_parent_ref_col    := COALESCE(TG_ARGV[4], 'id');

  -- Avvisa se il chiamante non ha esplicitato la colonna referenziata
  IF TG_ARGV[4] IS NULL THEN
    PERFORM script.fn_log_error_only(
      'database',
      'trgfn_child_requires_active_parent',
      'E_ATTIVO_REQUIRE',
      jsonb_build_object(
        'parent_table', v_parent_schema||'.'||v_parent_table,
        'ref_col',      v_parent_ref_col,
        'note',         'Usata colonna di default id'
      ),
      NULL::uuid,
      'Passa parent_ref_col come 5° parametro per evitare ambiguita'''
    );
  END IF;

  IF NOT (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') THEN
    RETURN NEW;
  END IF;

  -- Se il figlio ha attivo e non e' attivo, nessun controllo
  v_child_attivo_col := dbops.fn_get_override_col(TG_TABLE_SCHEMA, TG_TABLE_NAME, 'ATTIVO_COL', 'attivo');
  v_child_has_attivo := dbops.fn_col_exists(TG_TABLE_SCHEMA, TG_TABLE_NAME, v_child_attivo_col);

  IF v_child_has_attivo THEN
    -- Accesso dinamico alla colonna del figlio via to_jsonb (no EXECUTE per riga)
    IF COALESCE((to_jsonb(NEW)->>v_child_attivo_col)::boolean, FALSE) IS NOT TRUE THEN
      RETURN NEW;
    END IF;
  END IF;

  -- Estrai in modo robusto il valore della FK dal record NEW (via to_jsonb)
  v_fk_val_text := to_jsonb(NEW)->>v_fk_col;

  -- FK NULL ammessa: se non valorizzata, non applicare il controllo sul padre
  IF v_fk_val_text IS NULL THEN
    RETURN NEW;
  END IF;

  -- Ricava il tipo della colonna referenziata sul padre per cast corretto
  SELECT a.atttypid::regtype::text
    INTO v_parent_ref_type
    FROM pg_attribute a
    JOIN pg_class c     ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = v_parent_schema
    AND c.relname = v_parent_table
    AND a.attname = v_parent_ref_col
    AND a.attnum > 0
    AND NOT a.attisdropped;

  IF v_parent_ref_type IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_ATTIVO_REQUIRE',
      jsonb_build_object(
        'parent_table', v_parent_schema||'.'||v_parent_table,
        'ref_col',      v_parent_ref_col
      ),
      NULL::uuid,
      'Colonna referenziata padre non trovata'
    );
  END IF;

  -- Verifica esistenza e stato del padre (cast del parametro al tipo della colonna referenziata)
  v_sql := format(
    'SELECT %I FROM %I.%I WHERE %I = ($1)::%s',
    v_parent_attivo_col, v_parent_schema, v_parent_table,
    v_parent_ref_col, v_parent_ref_type
  );

  BEGIN
    EXECUTE v_sql INTO v_active USING v_fk_val_text;

    IF NOT FOUND THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        TG_NAME,
        'E_ATTIVO_REQUIRE',
        jsonb_build_object(
          'parent_table', v_parent_schema||'.'||v_parent_table,
          'ref_col',      v_parent_ref_col,
          'ref_val',      v_fk_val_text
        ),
        NULL::uuid,
        'Padre non trovato per figlio attivo'
      );
    END IF;

    IF NOT COALESCE(v_active, FALSE) THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        TG_NAME,
        'E_ATTIVO_REQUIRE',
        jsonb_build_object(
          'parent_table', v_parent_schema||'.'||v_parent_table,
          'ref_col',      v_parent_ref_col,
          'ref_val',      v_fk_val_text
        ),
        NULL::uuid,
        'Padre non attivo: figlio attivo non consentito'
      );
    END IF;

  EXCEPTION
    WHEN undefined_column OR undefined_table THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        TG_NAME,
        'E_ATTIVO_REQUIRE',
        jsonb_build_object(
          'parent_table', v_parent_schema||'.'||v_parent_table,
          'fk_col',       v_fk_col
        ),
        NULL::uuid,
        'Configurazione errata: tabella/colonna non esistente'
      );
  END;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION dbops.trgfn_child_requires_active_parent()
IS 'Trigger function (ATTIVO/REQUIRE): impedisce INSERT/UPDATE sul figlio se il padre non e'' attivo. TG_ARGV: parent_schema, parent_table, parent_attivo_col, fk_col [, parent_ref_col]. Il 5° arg e'' la colonna del padre referenziata dalla FK (puo'' essere UNIQUE diversa dalla PK).';
```

</div>

---
{% include-markdown "signature-core.md" %}
