{% include-markdown "it/dbzero/script/manual/uuid_nil.md" %}
# ⚙️ Funzione `uuid_nil`

```sql
CREATE FUNCTION uuid_nil()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.uuid_nil()
 RETURNS uuid
 LANGUAGE sql
 IMMUTABLE
AS $function$
  SELECT '00000000-0000-0000-0000-000000000000'::uuid;
$function$

COMMENT ON FUNCTION script.uuid_nil()
IS 'Restituisce l’UUID nil (all-zeros) come helper per usi in trigger e funzioni';
```

</div>

---
{% include-markdown "signature-core.md" %}
