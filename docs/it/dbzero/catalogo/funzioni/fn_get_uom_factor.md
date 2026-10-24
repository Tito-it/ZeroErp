{% include-markdown "it/dbzero/catalogo/manual/fn_get_uom_factor.md" %}
# ⚙️ Funzione `fn_get_uom_factor`

```sql
CREATE FUNCTION fn_get_uom_factor(p_articolo_id uuid, p_uom_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_get_uom_factor(p_articolo_id uuid, p_uom_id bigint)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_uom_base_id catalogo.unita_misura.id%TYPE;
  v_factor      catalogo.articoli_uom_operativa.factor_to_base%TYPE;
  v_conv        catalogo.unita_misura_conversioni.fattore%TYPE;
BEGIN

  /*
  Restituisce il fattore di conversione tra l''UoM base dell''articolo e l''UoM richiesta.
   Cerca prima nella mappatura operativa attiva e valida temporalmente.
   Se non trovata, cerca nella tabella di conversioni globali tra UoM (catalogo.unita_misura_conversioni).
   Se non trovata, cerca la conversione inversa e restituisce il reciproco.
   Restituisce NULL se non trovata.

  Parametri:
    p_articolo_id: UUID dell'articolo
    p_uom_id:     ID della unita' di misura richiesta (bigint)    
  */  

  -- Base dall'articolo
  v_uom_base_id := catalogo.fn_get_uom_base(p_articolo_id);

  IF v_uom_base_id IS NULL THEN
    RETURN NULL; -- chiamante/trigger gestira' fallback/errore
  END IF;

  -- Se la UoM richiesta e' la base, fattore 1
  IF p_uom_id = v_uom_base_id THEN
    RETURN 1;
  END IF;

  -- 1) Cerca fattore nella mappatura operativa attiva e valida temporalmente
  SELECT auo.factor_to_base
    INTO v_factor
  FROM catalogo.articoli_uom_operativa auo
  WHERE auo.articolo_id = p_articolo_id
    AND auo.uom_id      = p_uom_id
    AND auo.attivo      = TRUE
    AND (auo.valido_dal IS NULL OR auo.valido_dal <= (SELECT script.fn_data_operativa()))
    AND (auo.valido_al  IS NULL OR auo.valido_al  >= (SELECT script.fn_data_operativa()))
  LIMIT 1;

  IF v_factor IS NOT NULL AND v_factor > 0 THEN
    RETURN v_factor;
  END IF;

  -- 2) Fallback: conversione globale UoM (p_uom_id -> base)
  SELECT c.fattore
    INTO v_conv
  FROM catalogo.unita_misura_conversioni c
  WHERE c.uom_from_id = p_uom_id
    AND c.uom_to_id   = v_uom_base_id
    AND c.attivo      = TRUE
    AND c.fattore     > 0
    AND (c.valido_dal IS NULL OR c.valido_dal <= (SELECT script.fn_data_operativa()))
    AND (c.valido_al   IS NULL OR c.valido_al   >= (SELECT script.fn_data_operativa()))
  LIMIT 1;

  IF v_conv IS NOT NULL THEN
    RETURN v_conv;
  END IF;

  -- 3) Fallback inverso (base -> p_uom_id)
  SELECT c.fattore
    INTO v_conv
  FROM catalogo.unita_misura_conversioni c
  WHERE c.uom_from_id = v_uom_base_id
    AND c.uom_to_id   = p_uom_id
    AND c.attivo      = TRUE
    AND c.fattore     > 0
    AND (c.valido_dal IS NULL OR c.valido_dal <= (SELECT script.fn_data_operativa()))
    AND (c.valido_al   IS NULL OR c.valido_al   >= (SELECT script.fn_data_operativa()))
  LIMIT 1;

  IF v_conv IS NOT NULL THEN
    RETURN 1 / v_conv;
  END IF;

  RETURN NULL;
END;
$function$

COMMENT ON FUNCTION catalogo.fn_get_uom_factor(p_articolo_id uuid, p_uom_id bigint)
IS 'Restituisce il fattore di conversione tra l''UoM base dell''articolo e l''UoM richiesta.
   Cerca prima nella mappatura operativa attiva e valida temporalmente.
   Se non trovata, cerca nella tabella di conversioni globali tra UoM (catalogo.unita_misura_conversioni).
   Se non trovata, cerca la conversione inversa e restituisce il reciproco.
   Restituisce NULL se non trovata.';
```

</div>

---
{% include-markdown "signature-core.md" %}
