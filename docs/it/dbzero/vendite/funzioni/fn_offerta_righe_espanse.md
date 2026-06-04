{% include-markdown "it/dbzero/vendite/manual/fn_offerta_righe_espanse.md" %}
# ⚙️ Funzione `fn_offerta_righe_espanse`

```sql
CREATE FUNCTION fn_offerta_righe_espanse(p_offerta_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_offerta_righe_espanse(p_offerta_id bigint)
 RETURNS TABLE(articolo_id uuid, articolo_codice character varying, descrizione character varying, is_composito boolean, quantita numeric, uom_operativa_id bigint, qta_operativa numeric, factor_to_base numeric, prezzo_unitario numeric, sconto_perc numeric, iva_id integer, iva_perc numeric, tipo_eccezione vendite.tipo_eccezione_contratto, origine character varying, componenti jsonb)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: righe effettive ordine-ready di un'offerta (listino + variazione
--   globale + eccezioni). Parte 1 dal core fn_espandi_listino_versione +
--   overlay OVERRIDE (ESCLUSIONE rimossa); Parte 2 AGGIUNTA standalone+bundle.
--   iva risolta dall'articolo (listino non porta iva). sconto NULL: lo sconto
--   e' espresso come prezzo override (prezzo_unitario = prezzo finale netto).
--   quantita default 1 per righe da-listino senza eccezione.
DECLARE
    v_listino_id          vendite.offerte_commerciali.listino_id%TYPE;
    v_listino_versione_id vendite.offerte_commerciali.listino_versione_id%TYPE;
    v_tipo_var            vendite.offerte_commerciali.tipo_variazione_globale%TYPE;
    v_valore_var          vendite.offerte_commerciali.valore_variazione_globale%TYPE;
BEGIN
    SELECT o.listino_id, o.listino_versione_id,
           o.tipo_variazione_globale, o.valore_variazione_globale
      INTO v_listino_id, v_listino_versione_id, v_tipo_var, v_valore_var
      FROM vendite.offerte_commerciali o
     WHERE o.id = p_offerta_id;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Versione operativa se snapshot non fissato (offerta BOZZA).
    -- listino_id e' NOT NULL: niente ramo "senza listino".
    IF v_listino_versione_id IS NULL THEN
        SELECT lv.id
          INTO v_listino_versione_id
          FROM vendite.listini_versioni lv
         WHERE lv.listino_id = v_listino_id
           AND lv.attivo     = TRUE
           AND lv.stato      IN ('ATTIVA', 'CHIUSA')
           AND lv.validita  @> CURRENT_DATE
         ORDER BY (lv.stato = 'ATTIVA') DESC
         LIMIT 1;
    END IF;

    -- PARTE 1: righe dal listino (core) + overlay OVERRIDE; ESCLUSIONE rimossa.
    RETURN QUERY
    SELECT
        base.articolo_id,
        base.articolo_codice,
        base.articolo_descrizione,
        base.is_composito,
        COALESCE(ecc.quantita, 1)::numeric,
        COALESCE(ecc.uom_operativa_id, base.uom_id),
        COALESCE(ecc.qta_operativa, COALESCE(ecc.quantita, 1))::numeric,
        COALESCE(ecc.factor_to_base, 1)::numeric,
        CASE
            WHEN ecc.tipo_eccezione = 'OVERRIDE' THEN ecc.prezzo_unitario
            ELSE                                      base.prezzo_da_listino
        END,
        NULL::numeric,
        a.iva_id::integer,
        iv.aliquota_iva,
        ecc.tipo_eccezione,
        CASE
            WHEN ecc.tipo_eccezione = 'OVERRIDE' THEN 'OVERRIDE'
            ELSE                                      'DA_LISTINO'
        END::varchar,
        base.componenti
      FROM vendite.fn_espandi_listino_versione(
               v_listino_versione_id, v_tipo_var, v_valore_var
           ) base
      JOIN catalogo.articoli a ON a.id = base.articolo_id
      LEFT JOIN config.iva iv   ON iv.id = a.iva_id
      LEFT JOIN vendite.offerte_commerciali_eccezioni ecc
             ON ecc.offerta_id            = p_offerta_id
            AND ecc.articolo_id           = base.articolo_id
            AND ecc.tipo_eccezione        IN (
                    'OVERRIDE'::vendite.tipo_eccezione_contratto,
                    'ESCLUSIONE'::vendite.tipo_eccezione_contratto
                )
            AND COALESCE(ecc.attivo, TRUE) = TRUE
     WHERE ecc.tipo_eccezione IS DISTINCT FROM 'ESCLUSIONE'::vendite.tipo_eccezione_contratto;

    -- PARTE 2a: AGGIUNTA standalone (articolo non a listino).
    RETURN QUERY
    SELECT
        a.id, a.codice, a.descrizione, FALSE,
        COALESCE(ecc.quantita, 1)::numeric,
        COALESCE(ecc.uom_operativa_id, a.uom_id),
        COALESCE(ecc.qta_operativa, COALESCE(ecc.quantita, 1))::numeric,
        COALESCE(ecc.factor_to_base, 1)::numeric,
        ecc.prezzo_unitario,
        NULL::numeric,
        a.iva_id::integer,
        iv.aliquota_iva,
        ecc.tipo_eccezione,
        'AGGIUNTA'::varchar,
        NULL::jsonb
      FROM vendite.offerte_commerciali_eccezioni ecc
      JOIN catalogo.articoli a
        ON a.id = ecc.articolo_id AND a.is_composito = FALSE AND a.attivo = TRUE
      LEFT JOIN config.iva iv ON iv.id = a.iva_id
     WHERE ecc.offerta_id           = p_offerta_id
       AND ecc.tipo_eccezione        = 'AGGIUNTA'::vendite.tipo_eccezione_contratto
       AND COALESCE(ecc.attivo, TRUE) = TRUE;

    -- PARTE 2b: AGGIUNTA bundle. Componenti da offerte_commerciali_eccezioni_componenti.
    RETURN QUERY
    SELECT
        a.id, a.codice, a.descrizione, TRUE,
        COALESCE(ecc.quantita, 1)::numeric,
        COALESCE(ecc.uom_operativa_id, a.uom_id),
        COALESCE(ecc.qta_operativa, COALESCE(ecc.quantita, 1))::numeric,
        COALESCE(ecc.factor_to_base, 1)::numeric,
        ecc.prezzo_unitario,
        NULL::numeric,
        a.iva_id::integer,
        iv.aliquota_iva,
        ecc.tipo_eccezione,
        'AGGIUNTA'::varchar,
        (
            SELECT jsonb_agg(jsonb_build_object(
                'articolo_componente_id', oecc_c.articolo_componente_id,
                'componente_id',          af.id,
                'componente_codice',      af.codice,
                'componente_descrizione', af.descrizione,
                'uom_id',                 af.uom_id,
                'uom_codice',             umf.codice,
                'coeff_qta',              oecc_c.coeff_qta_snapshot,
                'prezzo',                 oecc_c.prezzo_unitario,
                'qta_operativa',          oecc_c.qta_operativa,
                'uom_operativa_id',       oecc_c.uom_operativa_id,
                'factor_to_base',         oecc_c.factor_to_base
            ) ORDER BY oecc_c.ordine, oecc_c.id)
              FROM vendite.offerte_commerciali_eccezioni_componenti oecc_c
              JOIN catalogo.articoli af ON af.id = oecc_c.componente_id
              JOIN catalogo.unita_misura umf ON umf.id = af.uom_id
             WHERE oecc_c.eccezione_offerta_id = ecc.id
               AND oecc_c.attivo               = TRUE
        )
      FROM vendite.offerte_commerciali_eccezioni ecc
      JOIN catalogo.articoli a
        ON a.id = ecc.articolo_id AND a.is_composito = TRUE AND a.attivo = TRUE
      LEFT JOIN config.iva iv ON iv.id = a.iva_id
     WHERE ecc.offerta_id           = p_offerta_id
       AND ecc.tipo_eccezione        = 'AGGIUNTA'::vendite.tipo_eccezione_contratto
       AND COALESCE(ecc.attivo, TRUE) = TRUE;
END;
$function$

COMMENT ON FUNCTION vendite.fn_offerta_righe_espanse(p_offerta_id bigint)
IS 'Righe effettive ordine-ready di un''offerta (listino + variazione globale + eccezioni) per la conversione offerta->ordine. Parte 1 dal core fn_espandi_listino_versione + overlay OVERRIDE (ESCLUSIONE rimossa); Parte 2 AGGIUNTA standalone+bundle. iva da articolo; sconto NULL (prezzo gia'' netto); quantita default 1 per righe da-listino. listino_id NOT NULL: nessun ramo senza listino.';
```

---
{% include-markdown "signature-core.md" %}
