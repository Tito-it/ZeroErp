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
  v_g            record;   -- riga di dbops.fn_trigger_attivo_argomenti
  v_p            record;   -- riga di dbops.fn_trigger_padre_stato
  v_nuova        jsonb;
  -- la chiave del padre come la scrive la figlia: la nomina il montaggio, testo
  v_fk_val_text  text;
  v_fk_old_text  text;
  -- la colonna di stato la nomina il montaggio: il tipo e' quello di script.fn_e_obsoleto
  v_obsoleto_dal date;
  v_padre        text;
  v_figlia       text;
BEGIN
  /*
    Scopo
    -----
    Trigger function (OBSOLETO/REQUIRE, sulla figlia): una riga nuova,
    o una riga che cambia la FK, non si collega a una voce di
    catalogo ritirata (script.fn_e_obsoleto: obsoleto_dal raggiunta
    alla data operativa). Asse separato dall'attivo: le voci
    ritirate restano attivo = true.

    Argomenti (TG_ARGV): padre_schema, padre_tabella, stato_col
    (obsoleto_dal del padre), fk_col, ref_col, obbligatori; e
    esenzione_col, facoltativo: una colonna della figlia che,
    valorizzata all'INSERT, dice che la riga e' derivata da un altro
    documento e la lascia passare. La grammatica e'
    dbops.fn_trigger_attivo_argomenti.

    Il padre lo legge dbops.fn_trigger_padre_stato, fuori dalla row
    security, come la gemella trgfn_child_requires_active_parent.
  */

  SELECT * INTO v_g
    FROM dbops.fn_trigger_attivo_argomenti('trgfn_child_requires_non_obsolete_parent', TG_ARGV);

  v_nuova := to_jsonb(NEW);

  IF NOT v_g.valido
     OR NOT jsonb_exists(v_nuova, v_g.fk_col)
     OR (v_g.esenzione_col IS NOT NULL AND NOT jsonb_exists(v_nuova, v_g.esenzione_col)) THEN
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
                      format('la tabella non ha la colonna %s',
                             CASE WHEN NOT jsonb_exists(v_nuova, v_g.fk_col)
                                  THEN v_g.fk_col ELSE v_g.esenzione_col END)))
    );
  END IF;

  IF NOT (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') THEN
    RETURN NEW;
  END IF;

  -- FK NULL ammessa: nessun padre da controllare
  v_fk_val_text := v_nuova->>v_g.fk_col;
  IF v_fk_val_text IS NULL THEN
    RETURN NEW;
  END IF;

  -- La riga DERIVATA passa, ma solo alla nascita: sull'UPDATE conta
  -- il cambio della FK, che e' sempre una scelta nuova.
  IF v_g.esenzione_col IS NOT NULL
     AND TG_OP = 'INSERT'
     AND v_nuova->>v_g.esenzione_col IS NOT NULL THEN
    RETURN NEW;
  END IF;

  -- Su UPDATE: se la FK non cambia, nessun controllo. Gli avanzamenti
  -- delle istanze storiche non ripuntano il catalogo.
  IF TG_OP = 'UPDATE' THEN
    v_fk_old_text := to_jsonb(OLD)->>v_g.fk_col;
    IF v_fk_old_text IS NOT DISTINCT FROM v_fk_val_text THEN
      RETURN NEW;
    END IF;
  END IF;

  SELECT * INTO v_p
    FROM dbops.fn_trigger_padre_stato(TG_RELID, TG_NAME, v_fk_val_text);

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

  IF NOT v_p.trovato THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_PADRE_INESISTENTE',
      jsonb_build_object(
        'parent_table', v_padre,
        'child_table',  v_figlia,
        'ref_col',      v_g.ref_col,
        'ref_val',      v_fk_val_text,
        'campo',        v_g.fk_col
      ),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  -- Obsoleto se obsoleto_dal e' valorizzata e raggiunta; NULL o futura: ok.
  v_obsoleto_dal := (v_p.valore #>> '{}')::date;

  IF script.fn_e_obsoleto(v_obsoleto_dal) THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_CATALOGO_OBSOLETO_NUOVA_ISTANZA',
      jsonb_build_object(
        'parent_table',  v_padre,
        'ref_col',       v_g.ref_col,
        'ref_val',       v_fk_val_text,
        'obsoleto_dal',  v_obsoleto_dal,
        'campo',         v_g.fk_col
      ) || jsonb_strip_nulls(jsonb_build_object(
        'bersaglio', script.fn_bersaglio_di_riga(v_g.padre_schema, v_g.padre_tabella,
                                                 v_g.ref_col, v_fk_val_text))),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION dbops.trgfn_child_requires_non_obsolete_parent()
IS 'Trigger function OBSOLETO/REQUIRE, sulla figlia, montata a mano: una riga nuova, o una riga che cambia la FK, non si collega a una voce di catalogo ritirata (script.fn_e_obsoleto: obsoleto_dal raggiunta alla data operativa), con E_CATALOGO_OBSOLETO_NUOVA_ISTANZA (CONFLITTO_STATO, colonna FK in campo), con una frase che non nomina tabelle e il bersaglio del padre (script.fn_bersaglio_di_riga) quando il catalogo dei tipi ne dichiara la tabella; la data del ritiro, il padre, la colonna e il valore stanno nel contesto del diario. Gemella di dbops.trgfn_child_requires_active_parent sull''asse obsoleto_dal: le voci ritirate restano attivo = true. Su UPDATE controlla solo se la FK cambia, cosi'' il ciclo di vita delle istanze storiche non si blocca; FK NULL e obsoleto_dal NULL o futura passano. Un padre assente (possibile dove il collegamento non e'' una FK) solleva E_PADRE_INESISTENTE, senza bersaglio; un montaggio sbagliato (argomenti fuori grammatica, una colonna FK o di esenzione che la figlia non ha, una tabella o una colonna del padre che non esiste) E_TRIGGER_ARGOMENTI_INVALIDI. TG_ARGV nella grammatica di dbops.fn_trigger_attivo_argomenti: padre_schema, padre_tabella, stato_col (obsoleto_dal del padre), fk_col, ref_col, obbligatori; esenzione_col facoltativo, una colonna della figlia che, valorizzata all''INSERT, dice che la riga e'' derivata da un altro documento e la lascia passare (sull''UPDATE non vale). Il padre lo legge dbops.fn_trigger_padre_stato, fuori dalla row security, come la gemella.';
```

</div>

---
{% include-markdown "signature-core.md" %}
