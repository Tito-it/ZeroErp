{% include-markdown "it/dbzero/ui/manual/trgfn_ui_lista_definizione_a10_valida_vista_sql.md" %}

# ⚙️ Funzione `trgfn_ui_lista_definizione_a10_valida_vista_sql`

```sql
CREATE FUNCTION ui.trgfn_ui_lista_definizione_a10_valida_vista_sql()
RETURNS trigger
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_ui_lista_definizione_a10_valida_vista_sql()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
DECLARE
  v_relazione_esiste BOOLEAN;
BEGIN
  -- Nessuna validazione se vista_sql non e' valorizzata o lista non attiva
  IF NEW.vista_sql IS NULL OR NEW.attivo = FALSE THEN
    RETURN NEW;
  END IF;

  -- Controlla esistenza della relazione in pg_catalog
  SELECT EXISTS (
    SELECT 1
      FROM pg_catalog.pg_class c
      JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
     WHERE c.relname = NEW.vista_sql
       AND c.relkind IN ('v', 'm', 'r')
  ) INTO v_relazione_esiste;

  IF NOT v_relazione_esiste THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'ui.trgfn_ui_lista_definizione_a10_valida_vista_sql',
      'E_UI_VISTA_SQL_NON_TROVATA',
      jsonb_build_object(
        'detail', format('vista_sql = ''%s'' non trovata in pg_catalog', NEW.vista_sql),
        'codice', NEW.codice
      ),
      NULL,
      NEW.vista_sql
    );
  END IF;

  RETURN NEW;
END;
$fn$;

COMMENT ON FUNCTION ui.trgfn_ui_lista_definizione_a10_valida_vista_sql()
IS 'Guard INSERT/UPDATE: verifica esistenza di vista_sql in pg_catalog. Skip se NULL o attivo=FALSE.';
```

**Trigger associato:**

```sql
CREATE TRIGGER trg_ui_lista_definizione_a10_valida_vista_sql_ins_upd
  BEFORE INSERT OR UPDATE OF vista_sql, attivo
  ON ui.lista_definizione
  FOR EACH ROW
  EXECUTE FUNCTION ui.trgfn_ui_lista_definizione_a10_valida_vista_sql();
```

---
{% include-markdown "signature-core.md" %}
