{% include-markdown "it/dbzero/dbops/manual/fn_resolve_scope.md" %}
# ⚙️ Funzione `fn_resolve_scope`

```sql
CREATE FUNCTION fn_resolve_scope(p_schemas text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_resolve_scope(p_schemas text[])
 RETURNS text[]
 LANGUAGE plpgsql
AS $function$
   DECLARE
     v_schemas text[];
   BEGIN
     -- 1) Se è stato passato p_schemas, pulisci:
     IF p_schemas IS NOT NULL THEN
       SELECT array_agg(DISTINCT s)
         INTO v_schemas
       FROM unnest(p_schemas) AS t(s)
       WHERE nullif(btrim(s),'') IS NOT NULL       -- elimina ''/spazi
         AND lower(btrim(s)) <> '*all';            -- '*all' = chiedi fallback

       IF v_schemas IS NOT NULL AND array_length(v_schemas,1) > 0 THEN
         RETURN v_schemas;  -- lista esplicita pulita
       END IF;
       -- altrimenti prosegui a leggere scope/fallback
     END IF;

     -- 2) Prova da automation_scope (se esiste)
     IF EXISTS (
       SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
       WHERE n.nspname='dbops' AND c.relname='automation_scope' AND c.relkind='r'
     ) THEN
       SELECT array_agg(schema_name)
         INTO v_schemas
       FROM dbops.automation_scope;
     END IF;

     -- 3) Fallback se assente o vuoto: tutti gli schemi “user” (tranne storico)
     IF v_schemas IS NULL OR array_length(v_schemas,1) IS NULL THEN
       SELECT array_agg(nspname) INTO v_schemas
       FROM pg_namespace
       WHERE nspname NOT LIKE 'pg_%'
         AND nspname <> 'information_schema'
         AND nspname <> 'storico';
     END IF;

     RETURN v_schemas;
   END; $function$
```

</div>

---
{% include-markdown "signature-core.md" %}
