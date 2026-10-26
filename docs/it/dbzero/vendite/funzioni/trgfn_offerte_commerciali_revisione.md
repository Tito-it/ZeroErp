{% include-markdown "it/dbzero/vendite/manual/trgfn_offerte_commerciali_revisione.md" %}
# ⚙️ Funzione `trgfn_offerte_commerciali_revisione`

```sql
CREATE FUNCTION trgfn_offerte_commerciali_revisione()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_offerte_commerciali_revisione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: alla nascita di una rev.N+1 (revisione_padre_id NOT NULL)
--   il padre passa nello stato di superamento. Lo scrive la
--   proiezione vendite.fn_offerta_proietta_stato_revisione, che
--   guarda le revisioni vive; la matrice la giudica il guard _a10_
--   di transizione, sul padre.
-- rev 2026-08-28: lookup dal catalogo (is_superato) + guard sull'arita'.
-- rev 2026-10-26 (20261026-18, brief-modello-documento-vendita §13,
--   O-2): l'UPDATE del padre e il guard sull'arita' passano alla
--   proiezione, che scrive attraverso la porta. Il trigger resta come
--   chiamante: prende la causa su ogni strada.
BEGIN
    -- Se non e' una revisione (prima rev.), niente da fare.
    IF NEW.revisione_padre_id IS NULL THEN
        RETURN NEW;
    END IF;

    PERFORM vendite.fn_offerta_proietta_stato_revisione(NEW.revisione_padre_id);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_offerte_commerciali_revisione()
IS 'AFTER INSERT su vendite.offerte_commerciali (_z90_): alla nascita di una revisione (revisione_padre_id NOT NULL) chiama la proiezione vendite.fn_offerta_proietta_stato_revisione sul padre, che lo porta nello stato di superamento (is_superato, guard sull''arita'') attraverso la porta; la matrice la giudica il guard di transizione. rev 2026-10-26 (20261026-18, brief-modello-documento-vendita §13, O-2): prima scriveva il padre con un UPDATE suo, che la porta sullo stato ferma.';
```

</div>

---
{% include-markdown "signature-core.md" %}
