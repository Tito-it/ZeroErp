{% include-markdown "it/dbzero/catalogo/manual/fn_get_uom_base.md" %}
# ⚙️ Funzione `fn_get_uom_base`

```sql
CREATE FUNCTION fn_get_uom_base(p_articolo_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

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
  WHERE a.id = p_articolo_id;

  -- Articolo inesistente: NULL; il chiamante decide se rifiutare.
  RETURN v_uom_base_id;
END;
$function$

COMMENT ON FUNCTION catalogo.fn_get_uom_base(p_articolo_id uuid)
IS 'L''unita'' base dell''articolo, catalogo.articoli.uom_id (NOT NULL). NULL solo se l''articolo non esiste: il chiamante decide se rifiutare.';
```

</div>

---
{% include-markdown "signature-core.md" %}
