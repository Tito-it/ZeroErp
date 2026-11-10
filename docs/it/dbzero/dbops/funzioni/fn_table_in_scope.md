{% include-markdown "it/dbzero/dbops/manual/fn_table_in_scope.md" %}
# ⚙️ Funzione `fn_table_in_scope`

```sql
CREATE FUNCTION fn_table_in_scope(p_schema text, p_table text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_table_in_scope(p_schema text, p_table text)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
  DECLARE
    v_total      int;
    v_for_schema int;
    v_any_all    int;
    v_like       int;
  BEGIN
    -- Se la tabella scope non esiste, nessun filtro tabellare
    IF NOT EXISTS (
      SELECT 1
      FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='dbops' AND c.relname='automation_scope' AND c.relkind='r'
    ) THEN
      RETURN true;
    END IF;

    -- Se lo scope è vuoto, non filtrare per tabella
    SELECT count(*) INTO v_total FROM dbops.automation_scope;
    IF v_total = 0 THEN
      RETURN true;
    END IF;

    -- Righe per questo schema?
    SELECT count(*) INTO v_for_schema
    FROM dbops.automation_scope
    WHERE lower(schema_name)=lower(p_schema);

    -- Nessuna riga per lo schema ⇒ interpreta come "tutte le tabelle" di quello schema
    IF v_for_schema = 0 THEN
      RETURN true;
    END IF;

    -- Presenza di '*all' per lo schema ⇒ tutte le tabelle
    SELECT count(*) INTO v_any_all
    FROM dbops.automation_scope
    WHERE lower(schema_name)=lower(p_schema)
      AND table_like='*all';
    IF v_any_all > 0 THEN
      RETURN true;
    END IF;

    -- Match LIKE su almeno una riga
    SELECT count(*) INTO v_like
    FROM dbops.automation_scope
    WHERE lower(schema_name)=lower(p_schema)
      AND p_table LIKE table_like;

    RETURN v_like > 0;
  END;
  $function$

COMMENT ON FUNCTION dbops.fn_table_in_scope(p_schema text, p_table text)
IS 'La tabella p_schema.p_table e'' nell''ambito delle automazioni secondo dbops.automation_scope? true se la tabella di ambito non c''e'' o e'' vuota, se non ha righe per quello schema (lo schema intero), se una riga dello schema ha table_like = *all, o se p_table soddisfa il LIKE di una riga dello schema. Lo schema si confronta senza maiuscole, table_like cosi'' com''e''. Il filtro sugli schemi lo fa prima dbops.fn_resolve_scope: qui si decide solo la tabella. STABLE. La usano i generatori e i riconciliatori delle automazioni.';
```

</div>

---
{% include-markdown "signature-core.md" %}
