{% include-markdown "it/dbzero/dbops/manual/trgfn_child_requires_non_obsolete_parent.md" %}
# ⚙️ Funzione `trgfn_child_requires_non_obsolete_parent`

```sql
CREATE FUNCTION trgfn_child_requires_non_obsolete_parent()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_parent_schema       text;
  v_parent_table        text;
  v_parent_obsoleto_col text;
  v_fk_col              text;
  v_parent_ref_col      text;   -- colonna referenziata dalla FK (non sempre la PK)
  v_fk_val_text         text;   -- valore FK dal figlio (come text)
  v_fk_old_text         text;   -- valore FK precedente (su UPDATE)
  v_parent_ref_type     text;   -- tipo della colonna referenziata (per cast)
  v_sql                 text;
  v_obsoleto_dal        date;
BEGIN
  /*
    Scopo
    -----
    Trigger function (OBSOLETO/REQUIRE): impedisce INSERT/UPDATE sul
    figlio se il catalogo padre referenziato e' OBSOLETO
    (obsoleto_dal <= CURRENT_DATE). Asse separato da attivo: serve
    perche' i record obsoleti restano attivo=true (il REQUIRE-ATTIVO
    non li intercetta).

    Argomenti attesi (TG_ARGV)
    --------------------------
    [0] parent_schema       - schema della tabella padre
    [1] parent_table        - nome tabella padre
    [2] parent_obsoleto_col - nome colonna obsoleto_dal del padre
    [3] fk_col              - nome colonna FK sul figlio
    [4] parent_ref_col      - colonna del padre referenziata dalla FK
                              (puo' essere UNIQUE diversa da PK).
                              Se omesso, fallback 'id'.
  */

  IF array_length(TG_ARGV, 1) < 4 THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_CATALOGO_OBSOLETO_NUOVA_ISTANZA',
      jsonb_build_object(
        'trigger', TG_NAME,
        'table',   TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
        'tg_argv', TG_ARGV
      ),
      NULL::uuid,
      'Attesi: parent_schema, parent_table, parent_obsoleto_col, fk_col [, parent_ref_col]'
    );
  END IF;

  v_parent_schema       := TG_ARGV[0];
  v_parent_table        := TG_ARGV[1];
  v_parent_obsoleto_col := TG_ARGV[2];
  v_fk_col              := TG_ARGV[3];
  v_parent_ref_col      := COALESCE(TG_ARGV[4], 'id');

  IF NOT (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') THEN
    RETURN NEW;
  END IF;

  -- Estrai il valore della FK dal record NEW (via to_jsonb, no EXECUTE per riga)
  v_fk_val_text := to_jsonb(NEW)->>v_fk_col;

  -- FK NULL ammessa: se non valorizzata, nessun controllo sul padre
  IF v_fk_val_text IS NULL THEN
    RETURN NEW;
  END IF;

  -- Su UPDATE: se la FK NON cambia, nessun controllo. Gli avanzamenti
  -- di lifecycle (cambio stato, ecc.) sulle istanze storiche non
  -- ri-puntano il catalogo e non devono mai essere bloccati.
  IF TG_OP = 'UPDATE' THEN
    v_fk_old_text := to_jsonb(OLD)->>v_fk_col;
    IF v_fk_old_text IS NOT DISTINCT FROM v_fk_val_text THEN
      RETURN NEW;
    END IF;
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
      'E_CATALOGO_OBSOLETO_NUOVA_ISTANZA',
      jsonb_build_object(
        'parent_table', v_parent_schema||'.'||v_parent_table,
        'ref_col',      v_parent_ref_col
      ),
      NULL::uuid,
      'Colonna referenziata padre non trovata'
    );
  END IF;

  -- Legge obsoleto_dal del padre (cast del parametro al tipo della colonna referenziata)
  v_sql := format(
    'SELECT %I FROM %I.%I WHERE %I = ($1)::%s',
    v_parent_obsoleto_col, v_parent_schema, v_parent_table,
    v_parent_ref_col, v_parent_ref_type
  );

  BEGIN
    EXECUTE v_sql INTO v_obsoleto_dal USING v_fk_val_text;

    IF NOT FOUND THEN
      -- Coerente con REQUIRE: il padre dovrebbe esistere (FK), ma se
      -- non trovato segnaliamo configurazione/dato incoerente.
      PERFORM script.fn_log_and_raise_error(
        'database',
        TG_NAME,
        'E_CATALOGO_OBSOLETO_NUOVA_ISTANZA',
        jsonb_build_object(
          'parent_table', v_parent_schema||'.'||v_parent_table,
          'ref_col',      v_parent_ref_col,
          'ref_val',      v_fk_val_text
        ),
        NULL::uuid,
        'Catalogo padre non trovato per la FK indicata'
      );
    END IF;

    -- Obsoleto se obsoleto_dal valorizzata e raggiunta. NULL o futura = ok.
    IF v_obsoleto_dal IS NOT NULL AND v_obsoleto_dal <= script.fn_data_operativa() THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        TG_NAME,
        'E_CATALOGO_OBSOLETO_NUOVA_ISTANZA',
        jsonb_build_object(
          'parent_table',  v_parent_schema||'.'||v_parent_table,
          'ref_col',       v_parent_ref_col,
          'ref_val',       v_fk_val_text,
          'obsoleto_dal',  v_obsoleto_dal
        ),
        NULL::uuid,
        format('Catalogo %s.%s obsoleto dal %s: non utilizzabile per nuove istanze',
               v_parent_schema, v_parent_table, v_obsoleto_dal)
      );
    END IF;

  EXCEPTION
    WHEN undefined_column OR undefined_table THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        TG_NAME,
        'E_CATALOGO_OBSOLETO_NUOVA_ISTANZA',
        jsonb_build_object(
          'parent_table', v_parent_schema||'.'||v_parent_table,
          'fk_col',       v_fk_col,
          'obsoleto_col', v_parent_obsoleto_col
        ),
        NULL::uuid,
        'Configurazione errata: tabella/colonna non esistente'
      );
  END;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION dbops.trgfn_child_requires_non_obsolete_parent()
IS 'Trigger function (OBSOLETO/REQUIRE): impedisce INSERT/UPDATE sul figlio se il catalogo padre referenziato ha obsoleto_dal <= CURRENT_DATE. Gemella di trgfn_child_requires_active_parent sull''asse obsoleto_dal. TG_ARGV: parent_schema, parent_table, parent_obsoleto_col, fk_col [, parent_ref_col]. Su UPDATE controlla solo se la FK cambia (lifecycle delle istanze storiche mai bloccato). FK NULL e obsoleto_dal NULL/futura = consentiti.';
```

</div>

---
{% include-markdown "signature-core.md" %}
