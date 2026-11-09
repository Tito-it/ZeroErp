{% include-markdown "it/dbzero/catalogo/manual/fn_get_uom_factor.md" %}
# ⚙️ Funzione `fn_get_uom_factor`

```sql
CREATE FUNCTION fn_get_uom_factor(p_articolo_id uuid, p_uom_id bigint, p_data date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_get_uom_factor(p_articolo_id uuid, p_uom_id bigint, p_data date)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_base   catalogo.articoli.uom_id%TYPE;
    v_factor catalogo.articoli_uom_operativa.factor_to_base%TYPE;
    -- numeric nudo DICHIARATO: l'inversa 1/fattore non sta in numeric(18,6).
    v_conv   numeric;
BEGIN
    IF p_uom_id IS NULL THEN
        RETURN NULL;
    END IF;

    v_base := catalogo.fn_get_uom_base(p_articolo_id);
    IF v_base IS NULL THEN
        RETURN NULL;
    END IF;

    -- 1) L'unita' base: 1, a ogni data.
    IF p_uom_id = v_base THEN
        RETURN 1;
    END IF;

    -- Per le altre la data non si sottintende: senza data, nessun fattore.
    IF p_data IS NULL THEN
        RETURN NULL;
    END IF;

    -- 2) La mappatura dell'articolo alla data.
    SELECT m.factor_to_base INTO v_factor
      FROM catalogo.fn_uom_operativa_alla_data(p_articolo_id, p_uom_id, p_data) m;
    IF v_factor IS NOT NULL THEN
        RETURN v_factor;
    END IF;

    -- 3) La conversione generale alla data: una sola per coppia di unita', in
    --    un verso o nell'altro (ex_unita_misura_conversioni_coppia_no_overlap).
    --    fattore = quante uom_to vale una uom_from.
    SELECT CASE WHEN c.uom_from_id = p_uom_id THEN c.fattore ELSE 1 / c.fattore END
      INTO v_conv
      FROM catalogo.unita_misura_conversioni c
     WHERE c.attivo IS TRUE
       AND c.validita @> p_data
       AND ((c.uom_from_id = p_uom_id AND c.uom_to_id = v_base)
         OR (c.uom_from_id = v_base   AND c.uom_to_id = p_uom_id));

    RETURN v_conv;
END;
$function$

COMMENT ON FUNCTION catalogo.fn_get_uom_factor(p_articolo_id uuid, p_uom_id bigint, p_data date)
IS 'Quante unita'' base dell''articolo p_articolo_id vale una unita'' p_uom_id, alla data p_data. L''unita'' base vale 1; poi la mappatura dell''articolo (catalogo.fn_uom_operativa_alla_data); poi la conversione generale di catalogo.unita_misura_conversioni fra le due unita'', in vigore a p_data, nel verso in cui e'' scritta o nell''inverso (1/fattore). NULL se non c''e'' nessuna delle tre, o se p_data e'' NULL per un''unita'' che non e'' la base: la data non si sottintende. Sede unica del fattore: la chiama script.trgfn_qta_from_operativa, che con NULL rifiuta la riga (E_UOM_MISSING).';
```

</div>

---
{% include-markdown "signature-core.md" %}
