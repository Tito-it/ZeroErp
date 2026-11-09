{% include-markdown "it/dbzero/dbops/manual/fn_apply_automazione_overlap.md" %}
# ⚙️ Funzione `fn_apply_automazione_overlap`

```sql
CREATE FUNCTION fn_apply_automazione_overlap(p_exec_mode text, p_dry_run boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_apply_automazione_overlap(p_exec_mode text, p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: applica vincoli EXCLUDE GiST su tabelle configurate in
--   dbops.automazione_overlap (active=true). Dual codepath periodo:
--   colonna daterange nativa (range_col) o espressione calcolata
--   (valido_dal/al). Chiavi: colonne semplici (key_columns, array JSON, validate e
--   quotate) + espressioni (key_expressions, array JSON, as-is). EXCLUDE parziali
--   via where_predicate (NULL = totale). Idempotente: salta se esiste
--   gia' il SUO vincolo (per nome) o un temporal UNIQUE sulla colonna periodo.
DECLARE
  rconf                  record;
  v_rel                  regclass;
  v_cols                 text[];
  v_col                  text;
  v_key_expr             text;
  v_range_expr           text;
  v_where                text;
  v_bounds               text;
  v_constraint           text;
  v_constraint_exists    boolean;
  -- text[]: %TYPE non fa array
  v_mancanti             text[];
  -- i dati del rifiuto, letti dall'eccezione
  v_errdetail            text;
  v_sqlstate             dbops.audit_log.sqlstate%TYPE;
  v_temporal_unique_exists boolean;
  v_skip_status          text;
BEGIN
  v_skip_status := CASE WHEN p_dry_run THEN 'DRYRUN' ELSE 'WARN' END;
  FOR rconf IN
    SELECT *
      FROM dbops.automazione_overlap
     WHERE active
       AND (upper(btrim(exec_mode)) = 'AUTO' OR exec_mode = p_exec_mode)
     ORDER BY target_schema, target_table
  LOOP
    -- ⚠️ to_regclass e non ::regclass: il registro non ha una FK verso il
    --   catalogo, e una riga su una tabella che non esiste piu' (rinominata,
    --   ritirata) col cast fermava l'intero giro (42P01), lasciando senza
    --   vincolo anche le tabelle che venivano dopo. Ora e' un salto
    --   dichiarato, come gli altri. Brief: brief-db-revisione-maintenance D6.
    v_rel := to_regclass(format('%I.%I', rconf.target_schema, rconf.target_table));
    IF v_rel IS NULL THEN
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_apply_automazione_overlap',
        p_status        => v_skip_status,
        p_rule_type     => 'OVERLAP',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['OVERLAP'],
        p_dry_run       => p_dry_run,
        p_params        => jsonb_build_object(
                            'table', rconf.target_schema||'.'||rconf.target_table,
                            'reason', 'TABLE_NOT_FOUND'
                          ),
        p_message       => 'Skip: la tabella del registro non esiste'
      );
      CONTINUE;
    END IF;

    -- Serve almeno una chiave: colonna semplice o espressione
    -- key_columns e key_expressions sono array JSON di testi (chk_automazione_overlap_chiavi).
    IF COALESCE(jsonb_array_length(rconf.key_columns), 0) = 0
       AND COALESCE(jsonb_array_length(rconf.key_expressions), 0) = 0 THEN
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_apply_automazione_overlap',
        p_status        => v_skip_status,
        p_rule_type     => 'OVERLAP',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['OVERLAP'],
        p_dry_run       => p_dry_run,
        p_params        => jsonb_build_object(
                            'table', rconf.target_schema||'.'||rconf.target_table,
                            'reason', 'NO_KEY_COLUMNS'
                          ),
        p_message       => 'Skip: nessuna chiave (key_columns e key_expressions vuote)'
      );
      CONTINUE;
    END IF;

    -- Validazione colonne periodo
    IF rconf.range_col IS NOT NULL THEN
      IF NOT dbops.fn_col_exists(rconf.target_schema, rconf.target_table, rconf.range_col) THEN
        PERFORM dbops.fn_audit_log_once(
          p_function_name => 'dbops.fn_apply_automazione_overlap',
          p_status        => v_skip_status,
          p_rule_type     => 'OVERLAP',
          p_exec_mode     => p_exec_mode,
          p_parts         => ARRAY['OVERLAP'],
          p_dry_run       => p_dry_run,
          p_params        => jsonb_build_object(
                              'table', rconf.target_schema||'.'||rconf.target_table,
                              'range_col', rconf.range_col,
                              'reason', 'RANGE_COL_MISSING'
                            ),
          p_message       => 'Skip: range_col not found in table'
        );
        CONTINUE;
      END IF;
    ELSE
      IF NOT dbops.fn_col_exists(rconf.target_schema, rconf.target_table, rconf.valido_dal_col)
         OR NOT dbops.fn_col_exists(rconf.target_schema, rconf.target_table, rconf.valido_al_col) THEN
        PERFORM dbops.fn_audit_log_once(
          p_function_name => 'dbops.fn_apply_automazione_overlap',
          p_status        => v_skip_status,
          p_rule_type     => 'OVERLAP',
          p_exec_mode     => p_exec_mode,
          p_parts         => ARRAY['OVERLAP'],
          p_dry_run       => p_dry_run,
          p_params        => jsonb_build_object(
                              'table', rconf.target_schema||'.'||rconf.target_table,
                              'valido_dal_col', rconf.valido_dal_col,
                              'valido_al_col', rconf.valido_al_col,
                              'reason', 'PERIOD_COLUMNS_MISSING'
                            ),
          p_message       => 'Skip: period columns missing'
        );
        CONTINUE;
      END IF;
    END IF;

    -- Costruzione key expression: 1) colonne semplici (validate+quotate)
    v_cols := ARRAY[]::text[];
    v_mancanti := ARRAY[]::text[];
    IF rconf.key_columns IS NOT NULL THEN
      FOR v_col IN SELECT k.v FROM jsonb_array_elements_text(rconf.key_columns) WITH ORDINALITY AS k(v, i) ORDER BY k.i
      LOOP
        IF dbops.fn_col_exists(rconf.target_schema, rconf.target_table, v_col) THEN
          v_cols := array_append(v_cols, quote_ident(v_col) || ' WITH =');
        ELSE
          v_mancanti := array_append(v_mancanti, v_col);
        END IF;
      END LOOP;
    END IF;

    -- ⭐ Una colonna di chiave che non c'e' ferma la REGOLA, non il giro: senza, il vincolo
    --   nascerebbe con una chiave piu' corta, piu' severo di quello dichiarato, e l'audit
    --   direbbe OK con la chiave registrata.
    IF cardinality(v_mancanti) > 0 THEN
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_apply_automazione_overlap',
        p_status        => v_skip_status,
        p_rule_type     => 'OVERLAP',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['OVERLAP'],
        p_dry_run       => p_dry_run,
        p_params        => jsonb_build_object(
                            'table', rconf.target_schema||'.'||rconf.target_table,
                            'key_columns', rconf.key_columns,
                            'colonne_mancanti', v_mancanti,
                            'reason', 'KEY_COLUMN_MISSING'
                          ),
        p_message       => 'Skip: una colonna della chiave non esiste'
      );
      CONTINUE;
    END IF;

    -- 2) espressioni (key_expressions): iniettate as-is (DDL di fiducia)
    IF rconf.key_expressions IS NOT NULL THEN
      FOR v_col IN SELECT k.v FROM jsonb_array_elements_text(rconf.key_expressions) WITH ORDINALITY AS k(v, i) ORDER BY k.i
      LOOP
        IF COALESCE(btrim(v_col), '') <> '' THEN
          v_cols := array_append(v_cols, v_col || ' WITH =');
        END IF;
      END LOOP;
    END IF;

    IF array_length(v_cols, 1) IS NULL THEN
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_apply_automazione_overlap',
        p_status        => v_skip_status,
        p_rule_type     => 'OVERLAP',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['OVERLAP'],
        p_dry_run       => p_dry_run,
        p_params        => jsonb_build_object(
                            'table', rconf.target_schema||'.'||rconf.target_table,
                            'key_columns', rconf.key_columns,
                            'key_expressions', rconf.key_expressions,
                            'reason', 'KEY_COLUMNS_NOT_FOUND'
                          ),
        p_message       => 'Skip: chiavi non risolte (colonne assenti, nessuna espressione)'
      );
      CONTINUE;
    END IF;

    -- Costruzione range expression: dual codepath
    IF rconf.range_col IS NOT NULL THEN
      v_range_expr := format('%I WITH &&', rconf.range_col);
    ELSE
      v_bounds := COALESCE(NULLIF(btrim(rconf.range_bounds), ''), '[]');
      v_range_expr := format(
        'daterange(%I, COALESCE(%I, ''infinity''::date), %L) WITH &&',
        rconf.valido_dal_col,
        rconf.valido_al_col,
        v_bounds
      );
    END IF;

    v_key_expr := array_to_string(v_cols, ', ');

    -- Coda WHERE per EXCLUDE parziale (where_predicate e' DDL di fiducia,
    -- iniettato as-is). NULL/vuoto => vincolo totale (nessuna coda).
    v_where := CASE
                 WHEN COALESCE(btrim(rconf.where_predicate), '') <> ''
                   THEN ' WHERE (' || rconf.where_predicate || ')'
                 ELSE ''
               END;

    -- Il nome del vincolo: quello della riga, o il template (sede unica del nome).
    v_constraint := dbops.fn_nome_oggetto_dichiarato(
                      rconf.constraint_name, 'ex_{table}_no_overlap',
                      rconf.target_schema, rconf.target_table);

    -- Verifica idempotenza: una scan su pg_constraint con LATERAL
    SELECT
        COALESCE(bool_or(con.contype = 'x' AND con.conname = v_constraint), false),
        COALESCE(bool_or(con.contype = 'u'
                AND cd.cdef ILIKE '%WITHOUT OVERLAPS%'
                AND cd.cdef ILIKE '%' || COALESCE(rconf.range_col, rconf.valido_dal_col) || '%'), false)
    FROM pg_constraint con
    CROSS JOIN LATERAL (SELECT pg_get_constraintdef(con.oid)) AS cd(cdef)
    WHERE con.conrelid = v_rel
    INTO v_constraint_exists, v_temporal_unique_exists;

    -- ⭐ La regola e' applicata solo col SUO vincolo (per nome), non con un qualsiasi EXCLUDE
    --   della tabella che nomina la colonna del periodo: quello puo' avere un'altra chiave.
    --   Resta valido un UNIQUE ... WITHOUT OVERLAPS sul periodo, la forma temporale nativa.
    IF v_constraint_exists OR v_temporal_unique_exists THEN
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_apply_automazione_overlap',
        p_status        => v_skip_status,
        p_rule_type     => 'OVERLAP',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['OVERLAP'],
        p_dry_run       => p_dry_run,
        p_params        => jsonb_build_object(
                            'table', rconf.target_schema||'.'||rconf.target_table,
                            'constraint', v_constraint,
                            'reason', CASE
                              WHEN v_temporal_unique_exists THEN 'TEMPORAL_UNIQUE_EXISTS'
                              ELSE 'EXCLUDE_EXISTS'
                            END
                          ),
        p_message       => CASE
          WHEN v_temporal_unique_exists
            THEN 'Skip: temporal unique (WITHOUT OVERLAPS) already present'
          ELSE 'Skip: exclude constraint already present'
        END
      );
      CONTINUE;
    END IF;

    IF p_dry_run THEN
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_apply_automazione_overlap',
        p_status        => 'DRYRUN',
        p_rule_type     => 'OVERLAP',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['OVERLAP'],
        p_dry_run       => true,
        p_params        => jsonb_build_object(
                            'table', rconf.target_schema||'.'||rconf.target_table,
                            'constraint', v_constraint,
                            'key_columns', rconf.key_columns,
                            'key_expressions', rconf.key_expressions,
                            'range_col', rconf.range_col,
                            'valido_dal_col', rconf.valido_dal_col,
                            'valido_al_col', rconf.valido_al_col,
                            'range_bounds', COALESCE(rconf.range_bounds, '[]'),
                            'where_predicate', rconf.where_predicate,
                            'action', 'DRYRUN_CREATE_EXCLUDE'
                          ),
        p_message       => 'Exclude constraint would be created'
      );
      CONTINUE;
    END IF;

    -- ⭐ I dati gia' sovrapposti sono un difetto dei DATI, da rendere visibile senza fermare le
    --   regole che non c'entrano: la regola resta senza vincolo, l'audit WARN dice quale e
    --   la prima coppia in conflitto (il dettaglio di PostgreSQL), e il giro va avanti. Lo
    --   stesso per un nome gia' preso da un altro oggetto dello schema.
    BEGIN
      EXECUTE format(
        'ALTER TABLE %I.%I ADD CONSTRAINT %I EXCLUDE USING gist (%s, %s)%s',
        rconf.target_schema,
        rconf.target_table,
        v_constraint,
        v_key_expr,
        v_range_expr,
        v_where
      );
    EXCEPTION
      WHEN exclusion_violation OR duplicate_table OR duplicate_object THEN
        GET STACKED DIAGNOSTICS
          v_sqlstate  = RETURNED_SQLSTATE,
          v_errdetail = PG_EXCEPTION_DETAIL;
        PERFORM dbops.fn_audit_log_once(
          p_function_name => 'dbops.fn_apply_automazione_overlap',
          p_status        => 'WARN',
          p_rule_type     => 'OVERLAP',
          p_exec_mode     => p_exec_mode,
          p_parts         => ARRAY['OVERLAP'],
          p_dry_run       => false,
          p_sqlstate      => v_sqlstate,
          p_params        => jsonb_build_object(
                              'table', rconf.target_schema||'.'||rconf.target_table,
                              'constraint', v_constraint,
                              'dettaglio', v_errdetail,
                              'reason', CASE WHEN v_sqlstate = '23P01' THEN 'DATI_SOVRAPPOSTI'
                                             ELSE 'NOME_OCCUPATO' END
                            ),
          p_message       => CASE WHEN v_sqlstate = '23P01'
                                  THEN 'Skip: righe gia'' sovrapposte, il vincolo non nasce'
                                  ELSE 'Skip: il nome del vincolo e'' gia'' preso' END
        );
        CONTINUE;
    END;
    PERFORM dbops.fn_audit_log_once(
      p_function_name => 'dbops.fn_apply_automazione_overlap',
      p_status        => 'OK',
      p_rule_type     => 'OVERLAP',
      p_exec_mode     => p_exec_mode,
      p_parts         => ARRAY['OVERLAP'],
      p_dry_run       => false,
      p_params        => jsonb_build_object(
                          'table', rconf.target_schema||'.'||rconf.target_table,
                          'constraint', v_constraint,
                          'key_columns', rconf.key_columns,
                          'key_expressions', rconf.key_expressions,
                          'range_col', rconf.range_col,
                          'valido_dal_col', rconf.valido_dal_col,
                          'valido_al_col', rconf.valido_al_col,
                          'range_bounds', COALESCE(rconf.range_bounds, '[]'),
                          'where_predicate', rconf.where_predicate,
                          'action', 'CREATE_EXCLUDE'
                        ),
      p_message       => 'Exclude constraint created'
    );
  END LOOP;
END;
$function$

COMMENT ON FUNCTION dbops.fn_apply_automazione_overlap(p_exec_mode text, p_dry_run boolean)
IS 'Applica i vincoli EXCLUDE GiST in base a dbops.automazione_overlap (righe active, exec_mode AUTO o uguale a p_exec_mode). Chiavi: key_columns (array JSON di nomi di colonna, quotati, devono esistere tutti) + key_expressions (array JSON di espressioni, as-is), nell''ordine dell''array. EXCLUDE parziali via where_predicate (NULL = totale). Periodo da range_col o da valido_dal/al. Nome del vincolo: constraint_name o il template ex_<tabella>_no_overlap (dbops.fn_nome_oggetto_dichiarato). La regola e'' applicata solo col suo vincolo (per nome) o con un UNIQUE WITHOUT OVERLAPS sul periodo: un altro EXCLUDE della tabella non conta. Salti dichiarati, che non fermano il giro: TABLE_NOT_FOUND, NO_KEY_COLUMNS, RANGE_COL_MISSING, PERIOD_COLUMNS_MISSING, KEY_COLUMN_MISSING (una colonna della chiave non c''e'': il vincolo nascerebbe piu'' severo), DATI_SOVRAPPOSTI (righe gia'' sovrapposte, 23P01: il vincolo non nasce, l''audit WARN porta il dettaglio della prima coppia), NOME_OCCUPATO. Su una regola spenta il vincolo non si toglie da solo: togliere un vincolo d''integrita'' e'' una decisione. key_expressions e where_predicate sono DDL di fiducia, solo DBA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
