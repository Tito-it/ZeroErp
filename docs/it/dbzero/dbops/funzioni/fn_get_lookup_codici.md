{% include-markdown "it/dbzero/dbops/manual/fn_get_lookup_codici.md" %}
# ⚙️ Funzione `fn_get_lookup_codici`

```sql
CREATE FUNCTION fn_get_lookup_codici(p_rel regclass, p_order_col text, p_order_dir text, p_attivo_only boolean, p_limit integer, p_offset integer, p_includi_obsoleti boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_get_lookup_codici(p_rel regclass, p_order_col text DEFAULT 'descrizione'::text, p_order_dir text DEFAULT 'ASC'::text, p_attivo_only boolean DEFAULT true, p_limit integer DEFAULT 500, p_offset integer DEFAULT 0, p_includi_obsoleti boolean DEFAULT true)
 RETURNS TABLE(id bigint, codice text, codice_interno text, descrizione text, attivo boolean)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_order_col   text    := lower(btrim(COALESCE(p_order_col, 'descrizione')));
  v_order_dir   text    := upper(btrim(COALESCE(p_order_dir, 'ASC')));
  v_offset      integer := COALESCE(p_offset, 0);
  v_id_type     text;
  v_has_codice          boolean;
  v_has_codice_interno  boolean;
  v_has_descrizione     boolean;
  v_has_attivo          boolean;
  v_attivo_is_boolean   boolean;
  v_has_obsoleto        boolean;
  v_obsoleto_is_date    boolean;
  v_conds       text[]  := ARRAY[]::text[];
  v_sql         text;
  -- Override dichiarativi da automation_overrides_cols.
  v_rel_schema              text;
  v_rel_table               text;
  v_codice_col_override         text;
  v_codice_interno_col_override text;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Estrazione lookup veloce per tabelle con colonne
  --   id/codice/codice_interno/descrizione/attivo, con filtri
  --   opzionali su attivo e obsoleto_dal.
  --
  -- Regole:
  --   - id deve essere integer/bigint (uuid non ammesso)
  --   - ordinamento ammesso solo su codice|descrizione e ASC|DESC
  --   - se la tabella ha colonna attivo e p_attivo_only=true,
  --     applica attivo IS TRUE
  --   - se la tabella ha colonna obsoleto_dal e
  --     p_includi_obsoleti=false, esclude i record con
  --     obsoleto_dal <= CURRENT_DATE (selezione per il nuovo).
  --     Default p_includi_obsoleti=true: mostra tutto (storico).
  --   - attivo e obsoleto_dal sono OPZIONALI: se la colonna manca,
  --     il relativo predicato non viene applicato (lista intera).
  --   - codice: colonna 'codice' o override CODICE_COL,
  --     altrimenti COALESCE(codice_interno/override, id::text)
  --   - codice_interno: colonna 'codice_interno' o override
  --     CODICE_INTERNO_COL, altrimenti NULL::text
  --   - Override dichiarativi in automation_overrides_cols
  --     (col_role CODICE_COL / CODICE_INTERNO_COL) hanno
  --     precedenza sull'introspezione pg_attribute
  -- =========================================================

  IF p_rel IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops', 'fn_get_lookup_codici', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('detail', 'p_rel obbligatorio'),
      NULL::uuid,
      'p_rel non puo'' essere NULL'
    );
  END IF;

  IF v_order_col NOT IN ('descrizione', 'codice') THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops', 'fn_get_lookup_codici', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('detail', 'p_order_col non valido', 'p_order_col', p_order_col),
      NULL::uuid,
      format('p_order_col=%s non ammesso (solo: descrizione, codice)', p_order_col)
    );
  END IF;

  IF v_order_dir NOT IN ('ASC', 'DESC') THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops', 'fn_get_lookup_codici', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('detail', 'p_order_dir non valido', 'p_order_dir', p_order_dir),
      NULL::uuid,
      format('p_order_dir=%s non ammesso (solo: ASC, DESC)', p_order_dir)
    );
  END IF;

  IF p_limit IS NOT NULL AND p_limit <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops', 'fn_get_lookup_codici', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('detail', 'p_limit non valido', 'p_limit', p_limit),
      NULL::uuid,
      format('p_limit deve essere > 0 (ricevuto %s)', p_limit)
    );
  END IF;

  IF v_offset < 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops', 'fn_get_lookup_codici', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('detail', 'p_offset non valido', 'p_offset', p_offset),
      NULL::uuid,
      format('p_offset deve essere >= 0 (ricevuto %s)', v_offset)
    );
  END IF;

  -- Check colonna id (obbligatoria, integer/bigint)
  SELECT t.typname
    INTO v_id_type
    FROM pg_attribute a
    JOIN pg_type t ON t.oid = a.atttypid
   WHERE a.attrelid = p_rel
     AND a.attname = 'id'
     AND a.attnum > 0
     AND NOT a.attisdropped;

  IF v_id_type IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops', 'fn_get_lookup_codici', 'E_LOOKUP_STRUTTURA_TABELLA_INVALIDA',
      jsonb_build_object('detail', 'colonna id mancante', 'tabella', p_rel::text),
      NULL::uuid,
      p_rel::text, 'colonna id mancante'
    );
  END IF;

  IF v_id_type = 'uuid' THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops', 'fn_get_lookup_codici', 'E_LOOKUP_STRUTTURA_TABELLA_INVALIDA',
      jsonb_build_object('detail', 'id uuid non ammesso', 'tabella', p_rel::text),
      NULL::uuid,
      p_rel::text, 'id uuid non ammesso (serve integer/bigint)'
    );
  END IF;

  IF v_id_type NOT IN ('int2', 'int4', 'int8') THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops', 'fn_get_lookup_codici', 'E_LOOKUP_STRUTTURA_TABELLA_INVALIDA',
      jsonb_build_object('detail', 'tipo id non supportato', 'tabella', p_rel::text, 'id_type', v_id_type),
      NULL::uuid,
      p_rel::text, format('tipo colonna id non supportato: %s (serve integer/bigint)', v_id_type)
    );
  END IF;

  -- Legge schema e table name dall'OID (piu' robusto di split_part su text).
  SELECT ns.nspname, c.relname
    INTO v_rel_schema, v_rel_table
    FROM pg_catalog.pg_class c
    JOIN pg_catalog.pg_namespace ns ON ns.oid = c.relnamespace
   WHERE c.oid = p_rel;

  -- Override dichiarativi per colonne codice/codice_interno non-standard.
  SELECT col_name INTO v_codice_col_override
    FROM dbops.automation_overrides_cols
   WHERE schema_name = v_rel_schema
     AND table_name  = v_rel_table
     AND col_role    = 'CODICE_COL';

  SELECT col_name INTO v_codice_interno_col_override
    FROM dbops.automation_overrides_cols
   WHERE schema_name = v_rel_schema
     AND table_name  = v_rel_table
     AND col_role    = 'CODICE_INTERNO_COL';

  -- Check colonna codice (pg_attribute, poi override)
  SELECT EXISTS (
    SELECT 1 FROM pg_attribute a
     WHERE a.attrelid = p_rel AND a.attname = 'codice'
       AND a.attnum > 0 AND NOT a.attisdropped
  ) INTO v_has_codice;

  -- Check colonna codice_interno (pg_attribute, poi override)
  SELECT EXISTS (
    SELECT 1 FROM pg_attribute a
     WHERE a.attrelid = p_rel AND a.attname = 'codice_interno'
       AND a.attnum > 0 AND NOT a.attisdropped
  ) INTO v_has_codice_interno;

  -- Applica override: se presente segnala la colonna come disponibile.
  IF v_codice_col_override IS NOT NULL THEN
    v_has_codice := TRUE;
  END IF;
  IF v_codice_interno_col_override IS NOT NULL THEN
    v_has_codice_interno := TRUE;
  END IF;

  -- Almeno una tra codice e codice_interno (reale o via override) deve esistere.
  IF NOT v_has_codice AND NOT v_has_codice_interno THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops', 'fn_get_lookup_codici', 'E_LOOKUP_STRUTTURA_TABELLA_INVALIDA',
      jsonb_build_object('detail', 'ne codice ne codice_interno presenti', 'tabella', p_rel::text),
      NULL::uuid,
      p_rel::text, 'serve colonna codice, codice_interno o override CODICE_COL/CODICE_INTERNO_COL'
    );
  END IF;

  -- Check colonna descrizione (obbligatoria)
  SELECT EXISTS (
    SELECT 1 FROM pg_attribute a
     WHERE a.attrelid = p_rel AND a.attname = 'descrizione'
       AND a.attnum > 0 AND NOT a.attisdropped
  ) INTO v_has_descrizione;

  IF NOT v_has_descrizione THEN
    PERFORM script.fn_log_and_raise_error(
      'dbops', 'fn_get_lookup_codici', 'E_LOOKUP_STRUTTURA_TABELLA_INVALIDA',
      jsonb_build_object('detail', 'colonna descrizione mancante', 'tabella', p_rel::text),
      NULL::uuid,
      p_rel::text, 'colonna descrizione mancante'
    );
  END IF;

  -- Check colonna attivo (opzionale, deve essere boolean)
  SELECT EXISTS (
    SELECT 1 FROM pg_attribute a
     WHERE a.attrelid = p_rel AND a.attname = 'attivo'
       AND a.attnum > 0 AND NOT a.attisdropped
  ) INTO v_has_attivo;

  IF v_has_attivo THEN
    SELECT EXISTS (
      SELECT 1 FROM pg_attribute a
      JOIN pg_type t ON t.oid = a.atttypid
      WHERE a.attrelid = p_rel AND a.attname = 'attivo'
        AND a.attnum > 0 AND NOT a.attisdropped AND t.typname = 'bool'
    ) INTO v_attivo_is_boolean;

    IF NOT v_attivo_is_boolean THEN
      PERFORM script.fn_log_and_raise_error(
        'dbops', 'fn_get_lookup_codici', 'E_LOOKUP_STRUTTURA_TABELLA_INVALIDA',
        jsonb_build_object('detail', 'colonna attivo non booleana', 'tabella', p_rel::text),
        NULL::uuid,
        p_rel::text, 'colonna attivo presente ma non di tipo boolean'
      );
    END IF;
  END IF;

  -- Check colonna obsoleto_dal (opzionale, deve essere date).
  -- Gemella di attivo: se manca, nessun filtro (lista intera).
  SELECT EXISTS (
    SELECT 1 FROM pg_attribute a
     WHERE a.attrelid = p_rel AND a.attname = 'obsoleto_dal'
       AND a.attnum > 0 AND NOT a.attisdropped
  ) INTO v_has_obsoleto;

  IF v_has_obsoleto THEN
    SELECT EXISTS (
      SELECT 1 FROM pg_attribute a
      JOIN pg_type t ON t.oid = a.atttypid
      WHERE a.attrelid = p_rel AND a.attname = 'obsoleto_dal'
        AND a.attnum > 0 AND NOT a.attisdropped AND t.typname = 'date'
    ) INTO v_obsoleto_is_date;

    IF NOT v_obsoleto_is_date THEN
      PERFORM script.fn_log_and_raise_error(
        'dbops', 'fn_get_lookup_codici', 'E_LOOKUP_STRUTTURA_TABELLA_INVALIDA',
        jsonb_build_object('detail', 'colonna obsoleto_dal non date', 'tabella', p_rel::text),
        NULL::uuid,
        p_rel::text, 'colonna obsoleto_dal presente ma non di tipo date'
      );
    END IF;
  END IF;

  -- Risolvi colonna effettiva per ORDER BY 'codice'.
  -- Se override CODICE_COL: usa il nome reale (es. 'codice_iso').
  -- Se codice non esiste (neanche override): fallback a 'descrizione'.
  IF v_order_col = 'codice' THEN
    IF v_codice_col_override IS NOT NULL THEN
      v_order_col := v_codice_col_override;
    ELSIF NOT v_has_codice THEN
      v_order_col := 'descrizione';
    END IF;
  END IF;

  -- Costruzione SQL dinamico con override colonne.
  v_sql := format(
    'SELECT t.id::bigint, %s, %s, t.descrizione::text, %s FROM %s t',
    CASE WHEN v_has_codice
         THEN format('t.%I::text', COALESCE(v_codice_col_override, 'codice'))
         ELSE format('COALESCE(t.%I::text, t.id::text)', COALESCE(v_codice_interno_col_override, 'codice_interno'))
    END,
    CASE WHEN v_has_codice_interno
         THEN format('t.%I::text', COALESCE(v_codice_interno_col_override, 'codice_interno'))
         ELSE 'NULL::text AS codice_interno'
    END,
    CASE WHEN v_has_attivo
         THEN 't.attivo::boolean'
         ELSE 'NULL::boolean AS attivo'
    END,
    p_rel::text
  );

  -- Accumulatore predicati: con piu' filtri possibili (attivo +
  -- obsoleto) le condizioni si concatenano con AND. Concatenare
  -- piu' "WHERE" produrrebbe SQL invalido.
  IF p_attivo_only AND v_has_attivo THEN
    v_conds := array_append(v_conds, 't.attivo IS TRUE');
  END IF;

  IF NOT p_includi_obsoleti AND v_has_obsoleto THEN
    v_conds := array_append(v_conds, '(t.obsoleto_dal IS NULL OR t.obsoleto_dal > (SELECT script.fn_data_operativa()))');
  END IF;

  IF array_length(v_conds, 1) > 0 THEN
    v_sql := v_sql || ' WHERE ' || array_to_string(v_conds, ' AND ');
  END IF;

  v_sql := v_sql || format(' ORDER BY t.%I %s NULLS LAST', v_order_col, v_order_dir);

  IF p_limit IS NOT NULL THEN
    v_sql := v_sql || format(' LIMIT %s', p_limit);
  END IF;

  IF v_offset > 0 THEN
    v_sql := v_sql || format(' OFFSET %s', v_offset);
  END IF;

  RETURN QUERY EXECUTE v_sql;
END;
$function$

COMMENT ON FUNCTION dbops.fn_get_lookup_codici(p_rel regclass, p_order_col text, p_order_dir text, p_attivo_only boolean, p_limit integer, p_offset integer, p_includi_obsoleti boolean)
IS 'Lookup generico id/codice/codice_interno/descrizione/attivo. Filtri opzionali e introspettivi: attivo (p_attivo_only, DEFAULT true) e obsoleto_dal (p_includi_obsoleti, DEFAULT true = mostra tutto; false = esclude obsoleto_dal <= CURRENT_DATE, selezione per il nuovo). Colonne attivo/obsoleto_dal opzionali: se assenti il filtro non si applica. Consulta automation_overrides_cols (CODICE_COL/CODICE_INTERNO_COL). Base: 20260520-04.';
```

</div>

---
{% include-markdown "signature-core.md" %}
