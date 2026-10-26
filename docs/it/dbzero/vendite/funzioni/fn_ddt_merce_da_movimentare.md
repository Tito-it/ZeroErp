# ⚙️ Funzione `fn_ddt_merce_da_movimentare`

```sql
CREATE FUNCTION fn_ddt_merce_da_movimentare(p_ddt vendite.ddt)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ddt_merce_da_movimentare(p_ddt vendite.ddt)
 RETURNS TABLE(ddt_riga_id bigint, ddt_riga_componente_id bigint, riga_nr integer, articolo_id uuid, qta numeric, prelevata numeric, automatico boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
#variable_conflict use_column
-- Scopo: le VOCI di una bolla che muovono merce, con la regola del kit
--   (D-L3-f) in una sede sola: la riga se il suo articolo e' gestito,
--   altrimenti i componenti gestiti del kit, mai entrambi. Per ogni voce
--   la quantita' da muovere (UoM base), quella gia' coperta dai prelievi
--   e se il prelievo e' AUTOMATICO (nessuna scelta da fare: niente
--   lotto, niente seriale, magazzini senza ubicazioni).
-- Consumatori: script.fn_check_ddt_merce, vendite.fn_ddt_muove_merce,
--   vendite.fn_cambia_stato_ddt (crea i prelievi automatici).
-- ⚠️ automatico e' boolean e non %TYPE: e' calcolato, non ha colonna.
DECLARE
    v_ubicazioni boolean;
BEGIN
    -- Basta un magazzino con ubicazioni (partenza, o arrivo della bolla
    -- di trasferimento) perche' il prelievo abbia una scelta da fare.
    v_ubicazioni :=
           COALESCE((SELECT m.usa_ubicazioni FROM magazzino.magazzini m
                      WHERE m.id = p_ddt.magazzino_id), false)
        OR COALESCE((SELECT m.usa_ubicazioni FROM magazzino.magazzini m
                      WHERE m.id = p_ddt.magazzino_arrivo_id), false);

    RETURN QUERY
    WITH voci AS (
        -- 1. la riga, se il suo articolo e' gestito
        SELECT dr.id AS v_riga, NULL::bigint AS v_comp, dr.riga_nr AS v_nr,
               dr.articolo_id AS v_art, dr.quantita AS v_qta
          FROM vendite.ddt_righe dr
          JOIN catalogo.articoli a ON a.id = dr.articolo_id
         WHERE dr.ddt_id = p_ddt.id
           AND dr.attivo
           AND a.gestito_a_magazzino
        UNION ALL
        -- 2. altrimenti i componenti gestiti del kit
        SELECT dr.id, drc.id, dr.riga_nr, drc.componente_id, drc.quantita
          FROM vendite.ddt_righe dr
          JOIN catalogo.articoli a  ON a.id = dr.articolo_id
          JOIN vendite.ddt_righe_componenti drc ON drc.riga_ddt_id = dr.id
          JOIN catalogo.articoli c  ON c.id = drc.componente_id
         WHERE dr.ddt_id = p_ddt.id
           AND dr.attivo
           AND drc.attivo
           AND NOT a.gestito_a_magazzino
           AND c.gestito_a_magazzino
    )
    SELECT v.v_riga, v.v_comp, v.v_nr, v.v_art, v.v_qta,
           COALESCE((SELECT sum(p.qta)
                       FROM vendite.ddt_righe_prelievi p
                      WHERE p.ddt_riga_id = v.v_riga
                        AND p.ddt_riga_componente_id IS NOT DISTINCT FROM v.v_comp), 0),
           NOT (ar.requires_lotto OR ar.requires_serial OR v_ubicazioni)
      FROM voci v
      JOIN catalogo.articoli ar ON ar.id = v.v_art
     ORDER BY v.v_nr, v.v_riga, v.v_comp NULLS FIRST;
END;
$function$

COMMENT ON FUNCTION vendite.fn_ddt_merce_da_movimentare(p_ddt vendite.ddt)
IS 'Le voci di una bolla che muovono merce, con la regola del kit (D-L3-f) in una sede sola: la riga attiva se il suo articolo e'' gestito a magazzino, altrimenti i componenti attivi e gestiti del suo kit — mai entrambi. Per voce: la quantita'' da muovere (UoM base), quella gia'' coperta dai prelievi, e automatico = il prelievo e'' unico per costruzione (articolo senza lotto ne'' seriale, magazzini della bolla senza ubicazioni), quindi lo crea il verbo e la check non lo chiede. Ordine: numero di riga, poi il componente. Prende la RIGA della bolla (valori nuovi nel guard BEFORE UPDATE). Consumatori: script.fn_check_ddt_merce, vendite.fn_ddt_muove_merce, vendite.fn_cambia_stato_ddt. Brief: brief-db-magazzino-lotto-3-scarico-da-ddt.';
```

</div>

---
{% include-markdown "signature-core.md" %}
