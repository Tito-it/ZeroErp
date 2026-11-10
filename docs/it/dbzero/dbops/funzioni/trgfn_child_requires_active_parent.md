{% include-markdown "it/dbzero/dbops/manual/trgfn_child_requires_active_parent.md" %}
# ⚙️ Funzione `trgfn_child_requires_active_parent`

```sql
CREATE FUNCTION trgfn_child_requires_active_parent()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.trgfn_child_requires_active_parent()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_g                record;   -- riga di dbops.fn_trigger_attivo_argomenti
  v_p                record;   -- riga di dbops.fn_trigger_padre_stato
  v_nuova            jsonb;
  v_child_attivo_col dbops.automation_overrides_cols.col_name%TYPE;
  -- la chiave del padre come la scrive la figlia: la nomina il montaggio, testo
  v_fk_val           text;
  v_padre            text;
  v_figlia           text;
BEGIN
  /*
    Scopo
    -----
    Trigger function (ATTIVO/REQUIRE, sulla figlia; il generatore la
    monta come CONSTRAINT TRIGGER differito): una figlia attiva non
    si collega a un padre disattivato. Se la figlia non ha la
    colonna attivo, il controllo vale per ogni riga.

    Argomenti (TG_ARGV), tutti obbligatori: padre_schema,
    padre_tabella, stato_col (l'attivo del padre), fk_col, ref_col.
    La grammatica e' dbops.fn_trigger_attivo_argomenti.

    Il padre lo legge dbops.fn_trigger_padre_stato, fuori dalla row
    security: il trigger e' differito, e al commit il contesto e'
    quello di chi chiude la transazione.
  */

  SELECT * INTO v_g
    FROM dbops.fn_trigger_attivo_argomenti('trgfn_child_requires_active_parent', TG_ARGV);

  v_nuova := to_jsonb(NEW);

  IF NOT v_g.valido OR NOT jsonb_exists(v_nuova, v_g.fk_col) THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_TRIGGER_ARGOMENTI_INVALIDI',
      jsonb_build_object(
        'trigger', TG_NAME,
        'table',   TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
        'tg_argv', to_jsonb(TG_ARGV)
      ),
      NULL::uuid,
      format('%s su %s.%s: %s', TG_NAME, TG_TABLE_SCHEMA, TG_TABLE_NAME,
             COALESCE(v_g.dettaglio,
                      format('la tabella non ha la colonna %s', v_g.fk_col)))
    );
  END IF;

  IF NOT (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') THEN
    RETURN NEW;
  END IF;

  -- Una figlia spenta non chiede niente al padre.
  v_child_attivo_col := dbops.fn_get_override_col(TG_TABLE_SCHEMA, TG_TABLE_NAME, 'ATTIVO_COL', 'attivo');
  IF jsonb_exists(v_nuova, v_child_attivo_col)
     AND COALESCE((v_nuova->>v_child_attivo_col)::boolean, FALSE) IS NOT TRUE THEN
    RETURN NEW;
  END IF;

  -- FK NULL ammessa: nessun padre da controllare
  v_fk_val := v_nuova->>v_g.fk_col;
  IF v_fk_val IS NULL THEN
    RETURN NEW;
  END IF;

  SELECT * INTO v_p
    FROM dbops.fn_trigger_padre_stato(TG_RELID, TG_NAME, v_fk_val);

  IF NOT v_p.configurato THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_TRIGGER_ARGOMENTI_INVALIDI',
      jsonb_build_object(
        'trigger',      TG_NAME,
        'table',        TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
        'parent_table', v_g.padre_schema||'.'||v_g.padre_tabella,
        'tg_argv',      to_jsonb(TG_ARGV)
      ),
      NULL::uuid,
      format('%s su %s.%s: %s', TG_NAME, TG_TABLE_SCHEMA, TG_TABLE_NAME, v_p.dettaglio)
    );
  END IF;

  v_padre  := v_g.padre_schema||'.'||v_g.padre_tabella;
  v_figlia := TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME;

  -- Le due frasi non hanno valori: padre, figlia, colonna e valore
  -- stanno nel contesto del diario. QUALE riga lo dice il bersaglio,
  -- solo sul padre che esiste.
  IF NOT v_p.trovato THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_PADRE_INESISTENTE',
      jsonb_build_object(
        'parent_table', v_padre,
        'child_table',  v_figlia,
        'ref_col',      v_g.ref_col,
        'ref_val',      v_fk_val,
        'campo',        v_g.fk_col
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  IF NOT COALESCE((v_p.valore #>> '{}')::boolean, FALSE) THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_ATTIVO_PADRE_NON_ATTIVO',
      jsonb_build_object(
        'parent_table', v_padre,
        'child_table',  v_figlia,
        'ref_col',      v_g.ref_col,
        'ref_val',      v_fk_val,
        'campo',        v_g.fk_col
      ) || jsonb_strip_nulls(jsonb_build_object(
        'bersaglio', script.fn_bersaglio_di_riga(v_g.padre_schema, v_g.padre_tabella,
                                                 v_g.ref_col, v_fk_val))),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION dbops.trgfn_child_requires_active_parent()
IS 'Trigger function ATTIVO/REQUIRE, sulla figlia (il generatore dbops.fn_run_automations_attivo la monta come CONSTRAINT TRIGGER differito; qualche montaggio a mano e'' immediato): una figlia attiva non si collega a un padre disattivato. Se la figlia non ha la colonna attivo (con l''override di dbops.automation_overrides_cols) il controllo vale per ogni riga; una FK NULL non controlla niente. Rifiuti per l''operatore: E_ATTIVO_PADRE_NON_ATTIVO (CONFLITTO_STATO) e E_PADRE_INESISTENTE (DATO_ERRATO: nessuna riga padre con quella chiave, possibile dove il collegamento non e'' una FK), con una frase che non nomina tabelle e la colonna FK in campo. E_ATTIVO_PADRE_NON_ATTIVO porta anche il bersaglio del padre (script.fn_bersaglio_di_riga) quando il catalogo dei tipi ne dichiara la tabella; E_PADRE_INESISTENTE no, perche'' la riga non c''e''. Padre, figlia, colonna referenziata e valore stanno nel contesto del diario. Un montaggio sbagliato (argomenti fuori grammatica, una colonna FK che la figlia non ha, una tabella o una colonna del padre che non esiste) solleva E_TRIGGER_ARGOMENTI_INVALIDI. TG_ARGV, tutti obbligatori, nella grammatica di dbops.fn_trigger_attivo_argomenti: padre_schema, padre_tabella, stato_col (la colonna attivo del padre), fk_col, ref_col (la colonna del padre referenziata dalla FK, anche una UNIQUE non primaria). Il padre lo legge dbops.fn_trigger_padre_stato, fuori dalla row security: lo stato di un padre non dipende da chi guarda, e un trigger differito legge al commit, col contesto di chi chiude la transazione. Gemella sull''asse obsoleto_dal: dbops.trgfn_child_requires_non_obsolete_parent.';
```

</div>

---
{% include-markdown "signature-core.md" %}
