# ⚙️ Funzione `fn_get_uom_factor`

```sql
CREATE FUNCTION fn_get_uom_factor(p_articolo_id uuid, p_uom_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_get_uom_factor(p_articolo_id uuid, p_uom_id bigint)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_uom_base_id bigint;
  v_factor      numeric;
BEGIN

  -- Ritorna il fattore UoM operativa → UoM base per l’articolo
  -- Se p_uom_id = base ⇒ 1
  -- Altrimenti legge da catalogo.articoli_uom_operativa; se assente ⇒ NULL


  -- Base dall'articolo
  v_uom_base_id := catalogo.fn_get_uom_base(p_articolo_id);

  IF v_uom_base_id IS NULL THEN
    RETURN NULL; -- chiamante/trigger gestirà fallback/errore
  END IF;

  -- Se la UoM richiesta è la base, fattore 1
  IF p_uom_id = v_uom_base_id THEN
    RETURN 1;
  END IF;

  -- Cerca fattore nella mappatura operativa attiva e valida temporalmente
  SELECT auo.factor_to_base
    INTO v_factor
  FROM catalogo.articoli_uom_operativa auo
  WHERE auo.articolo_id = p_articolo_id
    AND auo.uom_id      = p_uom_id
    AND auo.attivo      = TRUE
    AND (auo.valido_dal IS NULL OR auo.valido_dal <= CURRENT_DATE)
    AND (auo.valido_al  IS NULL OR auo.valido_al  >= CURRENT_DATE)
  LIMIT 1;

  -- Se non trovata una riga valida o fattore non positivo ⇒ NULL
  IF v_factor IS NULL OR v_factor <= 0 THEN
    RETURN NULL;
  END IF;

  RETURN v_factor;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
