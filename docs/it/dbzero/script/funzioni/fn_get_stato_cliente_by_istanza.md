{% include-markdown "it/dbzero/script/manual/fn_get_stato_cliente_by_istanza.md" %}
# ⚙️ Funzione `fn_get_stato_cliente_by_istanza`

```sql
CREATE FUNCTION fn_get_stato_cliente_by_istanza(p_istanza_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_stato_cliente_by_istanza(p_istanza_id integer)
 RETURNS integer
 LANGUAGE sql
AS $function$
   -- 1. Funzione di recupero stato_cliente per un'istanza
  SELECT COALESCE(
    (SELECT c.stato_cliente_id
      FROM anagrafiche.clienti c
      WHERE c.istanza_utility_id = p_istanza_id
      LIMIT 1),
    (SELECT id
      FROM config.stati_cliente
      WHERE codice_interno = 'IS'
      LIMIT 1)
  );
$function$
```

---
{% include-markdown "signature-core.md" %}
