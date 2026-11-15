{% include-markdown "it/dbzero/dbops/manual/trgfn_prevent_deactivate_if_children.md" %}
# ⚙️ Funzione `trgfn_prevent_deactivate_if_children`

```sql
CREATE FUNCTION trgfn_prevent_deactivate_if_children()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.trgfn_prevent_deactivate_if_children()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_g            record;   -- riga di dbops.fn_trigger_attivo_argomenti
  v_f            record;   -- riga di dbops.fn_trigger_figlie_presenti
  v_vecchia      jsonb;
  v_old_attivo   boolean;
  v_new_attivo   boolean;
  -- il valore della colonna referenziata: la nomina il montaggio, testo
  v_ref_val      text;
  -- La riga del padre ha il ritiro (obsoleto_dal)? Un interruttore, nessuna colonna lo rispecchia.
  v_si_ritira    boolean;
BEGIN
  /*
    Scopo
    -----
    Trigger function (ATTIVO/BLOCK, BEFORE UPDATE OF <attivo> sul
    padre): impedisce la disattivazione (attivo TRUE -> FALSE) se
    esistono figli collegati; se la figlia ha la colonna attivo,
    contano solo i figli attivi.

    Argomenti (TG_ARGV), tutti obbligatori: figlia_schema,
    figlia_tabella, fk_col, ref_col, stato_col (l'attivo del padre).
    La grammatica e' dbops.fn_trigger_attivo_argomenti.

    Le figlie le cerca dbops.fn_trigger_figlie_presenti, fuori
    dalla row security: che un padre sia usato non dipende da chi
    guarda.
  */

  SELECT * INTO v_g
    FROM dbops.fn_trigger_attivo_argomenti('trgfn_prevent_deactivate_if_children', TG_ARGV);

  v_vecchia := to_jsonb(OLD);

  IF NOT v_g.valido
     OR NOT jsonb_exists(v_vecchia, v_g.ref_col)
     OR NOT jsonb_exists(v_vecchia, v_g.stato_col) THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_ATTIVO_BLOCK_ARGS',
      jsonb_build_object(
        'trigger', TG_NAME,
        'table',   TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
        'tg_argv', to_jsonb(TG_ARGV)
      ),
      NULL::uuid,
      format('%s su %s.%s: %s', TG_NAME, TG_TABLE_SCHEMA, TG_TABLE_NAME,
             COALESCE(v_g.dettaglio,
                      format('la tabella non ha la colonna %s',
                             CASE WHEN NOT jsonb_exists(v_vecchia, v_g.ref_col)
                                  THEN v_g.ref_col ELSE v_g.stato_col END)))
    );
  END IF;

  v_old_attivo := (v_vecchia->>v_g.stato_col)::boolean;
  v_new_attivo := (to_jsonb(NEW)->>v_g.stato_col)::boolean;

  -- Si controlla solo la transizione TRUE -> FALSE
  IF NOT (TG_OP = 'UPDATE'
          AND COALESCE(v_old_attivo, FALSE) IS TRUE
          AND COALESCE(v_new_attivo, FALSE) IS FALSE) THEN
    RETURN NEW;
  END IF;

  v_ref_val := v_vecchia->>v_g.ref_col;

  IF v_ref_val IS NULL THEN
    -- Nessuna figlia puo' riferire una chiave NULL: si registra e si passa.
    PERFORM script.fn_log_error_only(
      'database',
      'trgfn_prevent_deactivate_if_children',
      'E_ATTIVO_BLOCK_REF_NULL',
      jsonb_build_object(
        'parent_table', TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
        'ref_col',      v_g.ref_col,
        'note',         'Colonna referenziata NULL: controllo figli saltato'
      ),
      NULL::uuid,
      format('%s.%s: colonna referenziata %s NULL, controllo figli saltato',
             TG_TABLE_SCHEMA, TG_TABLE_NAME, v_g.ref_col)
    );
    RETURN NEW;
  END IF;

  SELECT * INTO v_f
    FROM dbops.fn_trigger_figlie_presenti(TG_RELID, TG_NAME, v_ref_val);

  IF NOT v_f.configurato THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_ATTIVO_BLOCK_FKCOL_NOT_FOUND',
      jsonb_build_object(
        'parent_table', TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
        'child_table',  v_g.figlia_schema||'.'||v_g.figlia_tabella,
        'fk_col',       v_g.fk_col,
        'ref_col',      v_g.ref_col,
        'dettaglio',    v_f.dettaglio
      ),
      NULL::uuid,
      v_f.dettaglio
    );
  END IF;

  IF v_f.presenti THEN
    -- ⭐ Una voce che ha il ritiro (la colonna obsoleto_dal) e che altri
    --   nominano non si spegne: si ritira. Il rimedio e' la data di
    --   ritiro, non le figlie, e il rifiuto lo dice, col campo sulla data.
    --   La colonna si legge dalla riga che il trigger ha gia': nessuna
    --   query in piu', e vale per ogni tabella col ritiro, anche futura.
    v_si_ritira := jsonb_exists(v_vecchia, 'obsoleto_dal');

    -- Senza ritiro, due codici perche' i rimedi sono due: con la colonna
    -- attivo le figlie si disattivano, senza si tolgono. La frase sta a
    -- catalogo, senza valori: i dati viaggiano nel contesto del diario.
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      CASE WHEN v_si_ritira
           THEN 'E_ATTIVO_BLOCK_SI_RITIRA'
           WHEN v_f.figlia_attivo_col IS NOT NULL
           THEN 'E_ATTIVO_BLOCK_CHILDREN_ACTIVE'
           ELSE 'E_ATTIVO_BLOCK_CHILDREN_EXIST'
      END,
      jsonb_build_object(
        'parent_table',     TG_TABLE_SCHEMA||'.'||TG_TABLE_NAME,
        'child_table',      v_g.figlia_schema||'.'||v_g.figlia_tabella,
        'ref_col',          v_g.ref_col,
        'ref_val',          v_ref_val,
        'fk_col',           v_g.fk_col,
        'child_attivo_col', v_f.figlia_attivo_col,
        'child_has_attivo', v_f.figlia_attivo_col IS NOT NULL,
        'campo',            CASE WHEN v_si_ritira THEN 'obsoleto_dal'
                                 ELSE v_g.stato_col END
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION dbops.trgfn_prevent_deactivate_if_children()
IS 'Trigger function ATTIVO/BLOCK, montata dal generatore dbops.fn_run_automations_attivo come BEFORE UPDATE OF <attivo> sul padre: impedisce la disattivazione (attivo da TRUE a FALSE) se esistono righe figlie collegate. Se il padre ha il ritiro (la colonna obsoleto_dal) il rifiuto e'' E_ATTIVO_BLOCK_SI_RITIRA, col campo obsoleto_dal: una voce che altri nominano non si spegne, si ritira con una data di ritiro, e smette di essere proposta per un uso nuovo. Senza ritiro: se la figlia ha la colonna attivo contano solo le figlie attive e il rifiuto e'' E_ATTIVO_BLOCK_CHILDREN_ACTIVE (rimedio: disattivarle); se non ce l''ha conta ogni riga e il rifiuto e'' E_ATTIVO_BLOCK_CHILDREN_EXIST (rimedio: toglierle). Le frasi non nominano tabelle e non portano bersaglio: padre, figlia, colonna FK, colonna referenziata e suo valore stanno nel contesto del diario. TG_ARGV, tutti obbligatori, nella grammatica di dbops.fn_trigger_attivo_argomenti: figlia_schema, figlia_tabella, fk_col, ref_col (la colonna del padre referenziata dalla FK, anche una UNIQUE non primaria), stato_col (la colonna attivo del padre, con l''override di dbops.automation_overrides_cols). Un montaggio fuori grammatica, o che nomina una colonna che il padre non ha, solleva E_ATTIVO_BLOCK_ARGS; una figlia o una colonna FK che non esiste, E_ATTIVO_BLOCK_FKCOL_NOT_FOUND. Le figlie le cerca dbops.fn_trigger_figlie_presenti, fuori dalla row security: che un padre sia usato non dipende da chi guarda. Con la colonna referenziata NULL nessuna figlia puo'' riferirla: registra E_ATTIVO_BLOCK_REF_NULL in dbops.error_log e lascia passare.';
```

</div>

---
{% include-markdown "signature-core.md" %}
