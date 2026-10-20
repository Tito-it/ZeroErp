# ⚙️ Funzione `fn_ddt_muove_merce`

```sql
CREATE FUNCTION fn_ddt_muove_merce(p_ddt vendite.ddt)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ddt_muove_merce(p_ddt vendite.ddt)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la bolla muove merce? La causale di trasporto e' mappata
--   (D-L3-g) E almeno una voce e' gestita (D-L3-f). E' la condizione
--   della porta del registro (D-L3-e, affinata da Tid il 28-09): solo
--   una bolla che muove merce deve passare dal verbo.
BEGIN
    RETURN vendite.fn_ddt_causale_magazzino(p_ddt) IS NOT NULL
       AND EXISTS (SELECT 1 FROM vendite.fn_ddt_merce_da_movimentare(p_ddt));
END;
$function$

COMMENT ON FUNCTION vendite.fn_ddt_muove_merce(p_ddt vendite.ddt)
IS 'La bolla muove merce: la sua causale di trasporto e'' mappata su una causale di magazzino (fn_ddt_causale_magazzino) e almeno una voce e'' gestita (fn_ddt_merce_da_movimentare). Condizione della porta del registro nel guard di transizione, della check della merce e del verbo (D-L3-e). Brief: brief-db-magazzino-lotto-3-scarico-da-ddt.';
```

</div>

---
{% include-markdown "signature-core.md" %}
