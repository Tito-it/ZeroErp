{% include-markdown "it/dbzero/vendite/manual/fn_espandi_listino_versione.md" %}
# ⚙️ Funzione `fn_espandi_listino_versione`

```sql
CREATE FUNCTION fn_espandi_listino_versione(p_listino_versione_id bigint, p_tipo_var character varying, p_valore_var numeric)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_espandi_listino_versione(p_listino_versione_id bigint, p_tipo_var character varying, p_valore_var numeric)
 RETURNS TABLE(articolo_id uuid, articolo_codice character varying, articolo_descrizione character varying, is_composito boolean, uom_id bigint, uom_codice character varying, prezzo_listino numeric, prezzo_da_listino numeric, componenti jsonb)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: espande una versione di listino in righe piatte.
--   STANDALONE (is_composito=FALSE): prezzo_da_listino = listino +/- variazione globale.
--   BUNDLE (is_composito=TRUE): prezzo_da_listino = SUM(componenti) (NO variazione,
--     come fn_contratto_righe_preview); componenti aggregati in jsonb.
--   prezzo_listino: prezzo unitario di riga listino (NULL per bundle).
-- Core condiviso: nessuna eccezione di dominio.
BEGIN
    IF p_listino_versione_id IS NULL THEN
        RETURN;
    END IF;

    -- STANDALONE: articoli semplici dal listino, prezzo con variazione globale.
    RETURN QUERY
    SELECT
        a.id,
        a.codice,
        a.descrizione,
        FALSE,
        lr.uom_id,
        um.codice,
        lr.prezzo,
        CASE
            WHEN p_tipo_var = 'PERCENTUALE'  THEN lr.prezzo * (1 + p_valore_var / 100.0)
            WHEN p_tipo_var = 'VALORE_FISSO' THEN lr.prezzo + p_valore_var
            ELSE                                  lr.prezzo
        END,
        NULL::jsonb
      FROM vendite.listini_righe lr
      JOIN catalogo.articoli a
        ON a.id           = lr.articolo_id
       AND a.is_composito = FALSE
       AND a.attivo       = TRUE
      JOIN catalogo.unita_misura um ON um.id = lr.uom_id
     WHERE lr.listino_versione_id = p_listino_versione_id
       AND lr.attivo              = TRUE;

    -- BUNDLE: padri compositi; prezzo = SUM(componenti) (NO variazione).
    RETURN QUERY
    SELECT
        a.id,
        a.codice,
        a.descrizione,
        TRUE,
        a.uom_id,
        um.codice,
        NULL::numeric,
        bsum.somma,
        bcomp.componenti
      FROM (
          SELECT DISTINCT lrc_p.articolo_padre_id
            FROM vendite.listini_righe_componenti lrc_p
           WHERE lrc_p.listino_versione_id = p_listino_versione_id
             AND lrc_p.attivo              = TRUE
             AND lrc_p.validita           @> (SELECT script.fn_data_operativa())
      ) padri
      JOIN catalogo.articoli a
        ON a.id           = padri.articolo_padre_id
       AND a.is_composito = TRUE
       AND a.attivo       = TRUE
      JOIN catalogo.unita_misura um ON um.id = a.uom_id
      CROSS JOIN LATERAL (
          SELECT SUM(lrc2.prezzo * ac2.coeff_qta) AS somma
            FROM vendite.listini_righe_componenti lrc2
            JOIN catalogo.articoli_componenti ac2
              ON ac2.id = lrc2.articolo_componente_id
           WHERE lrc2.listino_versione_id = p_listino_versione_id
             AND lrc2.articolo_padre_id   = a.id
             AND lrc2.attivo              = TRUE
             AND lrc2.validita           @> (SELECT script.fn_data_operativa())
      ) bsum
      CROSS JOIN LATERAL (
          SELECT jsonb_agg(jsonb_build_object(
              'articolo_componente_id', ac.id,
              'componente_id',          af.id,
              'componente_codice',      af.codice,
              'componente_descrizione', af.descrizione,
              'uom_id',                 af.uom_id,
              'uom_codice',             umf.codice,
              'coeff_qta',              ac.coeff_qta,
              'prezzo',                 lrc.prezzo,
              'obbligatorio',           ac.obbligatorio,
              'esposizione_in_fattura', ac.esposizione_in_fattura
          ) ORDER BY lrc.id) AS componenti
            FROM vendite.listini_righe_componenti lrc
            JOIN catalogo.articoli_componenti ac
              ON ac.id = lrc.articolo_componente_id
            JOIN catalogo.articoli af
              ON af.id = lrc.articolo_figlio_id
            JOIN catalogo.unita_misura umf
              ON umf.id = af.uom_id
           WHERE lrc.listino_versione_id = p_listino_versione_id
             AND lrc.articolo_padre_id   = a.id
             AND lrc.attivo              = TRUE
             AND lrc.validita           @> (SELECT script.fn_data_operativa())
      ) bcomp;
END;
$function$

COMMENT ON FUNCTION vendite.fn_espandi_listino_versione(p_listino_versione_id bigint, p_tipo_var character varying, p_valore_var numeric)
IS 'Core condiviso: espande una versione listino in righe piatte (standalone + bundle) con prezzo da-listino (variazione globale solo su standalone, come da contratti) e BoM in jsonb (incl. articolo_componente_id). Consumato da fn_contratto_righe_preview e fn_offerta_righe_espanse. Nessuna eccezione di dominio. rev 2026-10-01: nel jsonb componenti la chiave esposto_in_fattura diventa esposizione_in_fattura (NASCOSTO | DESCRITTIVO | VALORIZZATO) (brief-db-esposizione-componenti-kit-in-fattura).';
```

</div>

---
{% include-markdown "signature-core.md" %}
