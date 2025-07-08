# ⚙️ Funzione `uuid_nil`

```sql
CREATE FUNCTION uuid_nil()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.uuid_nil()
 RETURNS uuid
 LANGUAGE sql
 IMMUTABLE
AS $function$
  SELECT '00000000-0000-0000-0000-000000000000'::uuid;
$function$
```