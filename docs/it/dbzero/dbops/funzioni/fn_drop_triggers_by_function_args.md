{% include-markdown "it/dbzero/dbops/manual/fn_drop_triggers_by_function_args.md" %}
# ⚙️ Funzione `fn_drop_triggers_by_function_args`

```sql
CREATE FUNCTION fn_drop_triggers_by_function_args(p_rel regclass, p_func_schema name, p_func_name name, VARIADIC p_args text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_drop_triggers_by_function_args(p_rel regclass, p_func_schema name, p_func_name name, VARIADIC p_args text[])
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
  -- la funzione trigger risolta per schema e nome
  v_funzione pg_catalog.pg_trigger.tgfoid%TYPE;
  r          record;
  -- un conteggio: nessuna colonna di cui sia il riflesso
  n          integer := 0;
BEGIN
  -- Scopo: togliere da una tabella i trigger che chiamano questa
  --   funzione con esattamente questi argomenti; restituisce quanti.
  v_funzione := pg_catalog.to_regprocedure(
                  format('%I.%I()', p_func_schema, p_func_name));
  IF v_funzione IS NULL THEN
    RETURN 0;
  END IF;

  FOR r IN
    SELECT t.tgname, ns.nspname, c.relname
      FROM pg_catalog.pg_trigger t
      JOIN pg_catalog.pg_class c      ON c.oid = t.tgrelid
      JOIN pg_catalog.pg_namespace ns ON ns.oid = c.relnamespace
     WHERE t.tgrelid = p_rel
       AND NOT t.tgisinternal
       -- Un clone del trigger di un padre partizionato (tgparentid) si governa sul padre: un
       -- DROP sulla partizione lo rifiuterebbe. Un trigger montato sulla partizione stessa
       -- (tgparentid = 0, il caso di una FK dichiarata sulla partizione) si toglie qui.
       AND t.tgparentid = 0
       AND t.tgfoid = v_funzione
       AND dbops.fn_trigger_argomenti(t.tgargs) = p_args
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I.%I', r.tgname, r.nspname, r.relname);
    n := n + 1;
  END LOOP;

  RETURN n;
END;
$function$

COMMENT ON FUNCTION dbops.fn_drop_triggers_by_function_args(p_rel regclass, p_func_schema name, p_func_name name, VARIADIC p_args text[])
IS 'Toglie da una tabella i trigger che chiamano la funzione indicata (schema e nome) con esattamente questi argomenti, e restituisce quanti ne ha tolti. Riconosce la funzione per OID (to_regprocedure di schema.nome(), quindi con qualunque search_path) e confronta gli argomenti di pg_trigger.tgargs (dbops.fn_trigger_argomenti) con l''array chiesto: stesso numero, stesso ordine, stesso testo. Generica: la grammatica di una famiglia di trigger la applica chi chiama. Una funzione che non esiste risponde 0. Non tocca i cloni dei trigger di un padre partizionato (tgparentid), che si governano sul padre; un trigger montato su una partizione stessa si toglie. La chiama dbops.fn_run_automations_attivo per riconciliare block e require prima di montarli.';
```

</div>

---
{% include-markdown "signature-core.md" %}
