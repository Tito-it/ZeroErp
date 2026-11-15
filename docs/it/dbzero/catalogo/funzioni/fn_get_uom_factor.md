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
    -- numeric nudo DICHIARATO: l'inversa 1/fattore non sta in numeric(18,6).
    v_factor numeric;
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

    -- 2) La prima fonte in vigore alla data: la mappatura dell'articolo,
    --    poi la conversione generale nei due versi.
    SELECT f.fattore INTO v_factor
      FROM catalogo.fn_uom_fonti_conversione(p_articolo_id, p_uom_id) f
     WHERE f.validita @> p_data
     ORDER BY f.priorita
     LIMIT 1;

    RETURN v_factor;
END;
$function$

COMMENT ON FUNCTION catalogo.fn_get_uom_factor(p_articolo_id uuid, p_uom_id bigint, p_data date)
IS 'Quante unita'' base dell''articolo p_articolo_id vale una unita'' p_uom_id, alla data p_data. L''unita'' base vale 1, a ogni data; per le altre il fattore della fonte di priorita'' piu'' bassa in vigore a p_data fra quelle di catalogo.fn_uom_fonti_conversione: la mappatura dell''articolo, poi la conversione generale fra le due unita'', nel verso in cui e'' scritta o nell''inverso (1/fattore). NULL se non ce n''e'' nessuna, o se p_data e'' NULL per un''unita'' che non e'' la base: la data non si sottintende. La chiama script.fn_fattore_uom_alla_data, che con NULL rifiuta la riga (E_UOM_MISSING).';
```

</div>

---
{% include-markdown "signature-core.md" %}
