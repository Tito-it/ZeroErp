{% include-markdown "it/dbzero/script/manual/uuid_nil.md" %}
# ⚙️ Funzione `uuid_nil`

### 🎯 Scopo Principale
* Fornire un valore UUID costante, composto interamente da zeri.
* Usato come **fallback** o **default** quando non è possibile generare o recuperare un UUID valido.

---

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