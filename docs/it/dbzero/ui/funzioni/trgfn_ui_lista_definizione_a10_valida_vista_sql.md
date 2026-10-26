{% include-markdown "it/dbzero/ui/manual/trgfn_ui_lista_definizione_a10_valida_vista_sql.md" %}
# ⚙️ Funzione `trgfn_ui_lista_definizione_a10_valida_vista_sql`

```sql
CREATE FUNCTION trgfn_ui_lista_definizione_a10_valida_vista_sql()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_ui_lista_definizione_a10_valida_vista_sql()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: verifica che NEW.vista_sql esista come relazione (view o table)
-- NELLO SCHEMA NEW.schema_dati prima di permettere INSERT/UPDATE su
-- lista_definizione.
-- Skip se vista_sql e' NULL o se attivo=FALSE (lista disattivata).
-- rev 2026-09-27: la relazione si cerca nel suo schema, non per solo
--   nome (due omonime in schemi diversi: `comuni` in config e storico).
DECLARE
  v_relazione_esiste BOOLEAN;
BEGIN
  -- Nessuna validazione se vista_sql non e' valorizzata o lista non attiva
  IF NEW.vista_sql IS NULL OR NEW.attivo = FALSE THEN
    RETURN NEW;
  END IF;

  -- Controlla esistenza della relazione nello schema della lista
  SELECT EXISTS (
    SELECT 1
      FROM pg_catalog.pg_class c
      JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = NEW.schema_dati
       AND c.relname = NEW.vista_sql
       AND c.relkind IN ('v', 'm', 'r')
       -- v=view, m=materialized view, r=table (raro ma ammesso)
  ) INTO v_relazione_esiste;

  IF NOT v_relazione_esiste THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'ui.trgfn_ui_lista_definizione_a10_valida_vista_sql',
      'E_UI_VISTA_SQL_NON_TROVATA',
      jsonb_build_object(
        'detail', format('vista_sql = ''%s.%s'' non trovata in pg_catalog',
                         NEW.schema_dati, NEW.vista_sql),
        'codice', NEW.codice
      ),
      NULL,
      NEW.schema_dati || '.' || NEW.vista_sql
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_ui_lista_definizione_a10_valida_vista_sql()
IS 'Guard INSERT/UPDATE: verifica esistenza di vista_sql in pg_catalog. Skip se NULL o attivo=FALSE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
