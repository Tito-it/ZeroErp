{% include-markdown "it/dbzero/catalogo/manual/fn_get_uom_base.md" %}
# ⚙️ Funzione `fn_get_uom_base`

```sql
CREATE FUNCTION fn_get_uom_base(p_articolo_id uuid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_get_uom_base(p_articolo_id uuid)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_uom_base_id bigint;
BEGIN
  -- Ritorna la UoM BASE dell’articolo da catalogo.articoli.uom_id

  SELECT a.uom_id
    INTO v_uom_base_id
  FROM catalogo.articoli a
  WHERE a.id = p_articolo_id
  LIMIT 1;

  -- Se non presente, ritorna NULL; il chiamante decide se bloccare/loggare
  RETURN v_uom_base_id;
END;
$function$

COMMENT ON FUNCTION catalogo.fn_get_uom_base(p_articolo_id uuid)
IS 'Ritorna la UoM BASE (uom_id) dell’articolo indicato. Se articolo non trovato o senza UoM, ritorna NULL.';
```

</div>

---
{% include-markdown "signature-core.md" %}
