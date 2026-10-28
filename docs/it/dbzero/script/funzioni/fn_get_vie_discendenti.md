{% include-markdown "it/dbzero/script/manual/fn_get_vie_discendenti.md" %}
# ⚙️ Funzione `fn_get_vie_discendenti`

```sql
CREATE FUNCTION fn_get_vie_discendenti(p_via_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_vie_discendenti(p_via_id integer)
 RETURNS TABLE(id_chain integer, livello integer)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
  RETURN QUERY
  WITH RECURSIVE catena(id_chain, livello) AS (
    SELECT via_id_nuovo, 1
    FROM storico.stradario_trasformazioni
    WHERE via_id_orig = p_via_id

    UNION ALL

    SELECT t.via_id_nuovo, c.livello + 1
    FROM storico.stradario_trasformazioni t
    JOIN catena c ON t.via_id_orig = c.id_chain
  )
  SELECT * FROM catena;
END;
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
