{% include-markdown "it/dbzero/dbops/manual/fn_schema_in_scope.md" %}
# ⚙️ Funzione `fn_schema_in_scope`

```sql
CREATE FUNCTION fn_schema_in_scope(p_rule_target text, p_schemas text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_schema_in_scope(p_rule_target text, p_schemas text[])
 RETURNS boolean
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
 DECLARE s text;
 BEGIN
   /*  Helper: match rispetto allo scope (array di schemi) */
   IF p_rule_target IS NULL THEN
     RETURN false;
   END IF;
   IF lower(p_rule_target)='*all' THEN
     RETURN true;
   END IF;
   IF p_schemas IS NULL OR array_length(p_schemas,1) IS NULL THEN
     RETURN false;
   END IF;
   FOREACH s IN ARRAY p_schemas LOOP
     IF lower(p_rule_target)=lower(s) THEN
       RETURN true;
     END IF;
   END LOOP;
   RETURN false;
 END;
 $function$

COMMENT ON FUNCTION dbops.fn_schema_in_scope(p_rule_target text, p_schemas text[])
IS 'Il target di schema di una regola delle automazioni (dbops.automation_rules_tbl.target_schema) vale per l''elenco di schemi p_schemas? *all vale per qualunque schema; altrimenti il nome deve stare nell''elenco (confronto senza maiuscole). Target NULL, o elenco vuoto per un target che non e'' *all: false. ⚠️ Qui *all significa «qualunque schema»; in dbops.fn_resolve_scope lo stesso *all nell''elenco degli schemi significa «usa l''ambito di dbops.automation_scope, o il ripiego». IMMUTABLE. La usa dbops.fn_run_automations_attivo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
