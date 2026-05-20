{% include-markdown "it/dbzero/vendite/manual/fn_contratto_righe_preview.md" %}
# ⚙️ Funzione `fn_contratto_righe_preview`

```sql
CREATE FUNCTION fn_contratto_righe_preview(p_contratto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_contratto_righe_preview(p_contratto_id bigint)
 RETURNS TABLE(articolo_id uuid, articolo_codice character varying, articolo_descrizione character varying, is_composito boolean, uom_id bigint, uom_codice character varying, prezzo_listino numeric, tipo_variazione character varying, valore_variazione numeric, override_riga_id bigint, override_prezzo numeric, tipo_eccezione vendite.tipo_eccezione_contratto, origine character varying, prezzo_finale numeric, componenti jsonb, quantita numeric, qta_operativa numeric, tipo_erogazione character varying, fonte_quantita_attesa character varying)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: restituisce tutte le righe del drawer ContrattoRigheDrawer.
-- Parte 1 (con listino): standalone + bundle da listini_righe/_componenti.
-- Parte 2 (AGGIUNTA): standalone e bundle da contratti_righe/_componenti.
-- prezzo_finale aggregato in DB; componenti JSONB uniforme per bundle.
-- Versione operativa: usa snapshot se ATTIVO, altrimenti lookup
--   stato IN ('ATTIVA','CHIUSA') per escludere BOZZA (Bug A fix).
-- quantita/qta_operativa/tipo_erogazione/fonte_quantita_attesa:
--   da cr.* via LEFT JOIN (NULL per DA_LISTINO) o JOIN diretto (Parte 2).
DECLARE
    v_listino_id          vendite.contratti.listino_id%TYPE;
    v_listino_versione_id vendite.contratti.listino_versione_id%TYPE;
    v_tipo_var            vendite.contratti.tipo_variazione_globale%TYPE;
    v_valore_var          vendite.contratti.valore_variazione_globale%TYPE;
BEGIN
    SELECT c.listino_id,
           c.listino_versione_id,
           c.tipo_variazione_globale,
           c.valore_variazione_globale
      INTO v_listino_id,
           v_listino_versione_id,
           v_tipo_var,
           v_valore_var
      FROM vendite.contratti c
     WHERE c.id = p_contratto_id;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Risolvi versione operativa per contratti DRAFT senza snapshot.
    -- stato IN ('ATTIVA','CHIUSA'): BOZZA esclusa (Bug A fix).
    IF v_listino_id IS NOT NULL AND v_listino_versione_id IS NULL THEN
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

    -- PARTE 1: articoli dal listino (versione operativa trovata).
    IF v_listino_versione_id IS NOT NULL THEN

        -- 1a: standalone (is_composito=FALSE) + overlay eccezioni.
        -- cr.* via LEFT JOIN: NULL per DA_LISTINO, valorizzato per OVERRIDE/ESCLUSIONE.
        RETURN QUERY
        SELECT
            a.id,
            a.codice,
            a.descrizione,
            FALSE,
            lr.uom_id,
            um.codice,
            lr.prezzo,
            v_tipo_var,
            v_valore_var,
            cr.id,
            cr.prezzo_unitario,
            cr.tipo_eccezione,
            CASE
                WHEN cr.tipo_eccezione = 'OVERRIDE'   THEN 'OVERRIDE'
                WHEN cr.tipo_eccezione = 'ESCLUSIONE' THEN 'ESCLUSIONE'
                ELSE                                       'DA_LISTINO'
            END::varchar,
            CASE
                WHEN cr.tipo_eccezione = 'OVERRIDE'   THEN cr.prezzo_unitario
                WHEN cr.tipo_eccezione = 'ESCLUSIONE' THEN NULL
                WHEN v_tipo_var = 'PERCENTUALE'        THEN lr.prezzo * (1 + v_valore_var / 100.0)
                WHEN v_tipo_var = 'VALORE_FISSO'       THEN lr.prezzo + v_valore_var
                ELSE                                        lr.prezzo
            END,
            NULL::jsonb,
            cr.quantita,
            cr.qta_operativa,
            cr.tipo_erogazione,
            cr.fonte_quantita_attesa
          FROM vendite.listini_righe lr
          JOIN catalogo.articoli a
            ON a.id           = lr.articolo_id
           AND a.is_composito = FALSE
           AND a.attivo       = TRUE
          JOIN catalogo.unita_misura um ON um.id = lr.uom_id
          LEFT JOIN vendite.contratti_righe cr
                 ON cr.contratto_id           = p_contratto_id
                AND cr.articolo_id            = lr.articolo_id
                AND cr.tipo_eccezione         IN (
                        'OVERRIDE'::vendite.tipo_eccezione_contratto,
                        'ESCLUSIONE'::vendite.tipo_eccezione_contratto
                    )
                AND COALESCE(cr.attivo, TRUE) = TRUE
         WHERE lr.listino_versione_id = v_listino_versione_id
           AND lr.attivo              = TRUE;

        -- 1b: bundle (padri compositi in listini_righe_componenti)
        -- + overlay OVERRIDE/ESCLUSIONE sulla riga padre.
        -- componenti: jsonb_agg figli da listini_righe_componenti.
        -- prezzo_finale bundle (DA_LISTINO): SUM(lrc.prezzo * ac.coeff_qta).
        -- cr.* via LEFT JOIN: NULL per DA_LISTINO, valorizzato per OVERRIDE/ESCLUSIONE.
        RETURN QUERY
        SELECT
            a.id,
            a.codice,
            a.descrizione,
            TRUE,
            a.uom_id,
            um.codice,
            NULL::numeric,
            v_tipo_var,
            v_valore_var,
            cr.id,
            cr.prezzo_unitario,
            cr.tipo_eccezione,
            CASE
                WHEN cr.tipo_eccezione = 'OVERRIDE'   THEN 'OVERRIDE'
                WHEN cr.tipo_eccezione = 'ESCLUSIONE' THEN 'ESCLUSIONE'
                ELSE                                       'DA_LISTINO'
            END::varchar,
            CASE
                WHEN cr.tipo_eccezione = 'OVERRIDE'   THEN cr.prezzo_unitario
                WHEN cr.tipo_eccezione = 'ESCLUSIONE' THEN NULL
                ELSE (
                    SELECT SUM(lrc2.prezzo * ac2.coeff_qta)
                      FROM vendite.listini_righe_componenti lrc2
                      JOIN catalogo.articoli_componenti ac2
                        ON ac2.id = lrc2.articolo_componente_id
                     WHERE lrc2.listino_versione_id = v_listino_versione_id
                       AND lrc2.articolo_padre_id   = a.id
                       AND lrc2.attivo              = TRUE
                       AND lrc2.validita           @> CURRENT_DATE
                )
            END,
            (
                SELECT jsonb_agg(jsonb_build_object(
                    'componente_id',          af.id,
                    'componente_codice',      af.codice,
                    'componente_descrizione', af.descrizione,
                    'uom_id',                 af.uom_id,
                    'uom_codice',             umf.codice,
                    'coeff_qta',              ac.coeff_qta,
                    'prezzo',                 lrc.prezzo,
                    'obbligatorio',           ac.obbligatorio,
                    'esposto_in_fattura',     ac.esposto_in_fattura
                ) ORDER BY lrc.id)
                  FROM vendite.listini_righe_componenti lrc
                  JOIN catalogo.articoli_componenti ac
                    ON ac.id = lrc.articolo_componente_id
                  JOIN catalogo.articoli af
                    ON af.id = lrc.articolo_figlio_id
                  JOIN catalogo.unita_misura umf
                    ON umf.id = af.uom_id
                 WHERE lrc.listino_versione_id = v_listino_versione_id
                   AND lrc.articolo_padre_id   = a.id
                   AND lrc.attivo              = TRUE
                   AND lrc.validita           @> CURRENT_DATE
            ),
            cr.quantita,
            cr.qta_operativa,
            cr.tipo_erogazione,
            cr.fonte_quantita_attesa
          FROM (
              SELECT DISTINCT lrc_p.articolo_padre_id
                FROM vendite.listini_righe_componenti lrc_p
               WHERE lrc_p.listino_versione_id = v_listino_versione_id
                 AND lrc_p.attivo              = TRUE
                 AND lrc_p.validita           @> CURRENT_DATE
          ) padri
          JOIN catalogo.articoli a
            ON a.id           = padri.articolo_padre_id
           AND a.is_composito = TRUE
           AND a.attivo       = TRUE
          JOIN catalogo.unita_misura um ON um.id = a.uom_id
          LEFT JOIN vendite.contratti_righe cr
                 ON cr.contratto_id           = p_contratto_id
                AND cr.articolo_id            = a.id
                AND cr.tipo_eccezione         IN (
                        'OVERRIDE'::vendite.tipo_eccezione_contratto,
                        'ESCLUSIONE'::vendite.tipo_eccezione_contratto
                    )
                AND COALESCE(cr.attivo, TRUE) = TRUE;

    END IF;

    -- PARTE 2a: AGGIUNTA standalone (is_composito=FALSE, non in listino).
    -- cr.* sempre valorizzati (JOIN diretto).
    RETURN QUERY
    SELECT
        a.id,
        a.codice,
        a.descrizione,
        FALSE,
        a.uom_id,
        um.codice,
        NULL::numeric,
        NULL::varchar,
        NULL::numeric,
        cr.id,
        cr.prezzo_unitario,
        cr.tipo_eccezione,
        'AGGIUNTA'::varchar,
        cr.prezzo_unitario,
        NULL::jsonb,
        cr.quantita,
        cr.qta_operativa,
        cr.tipo_erogazione,
        cr.fonte_quantita_attesa
      FROM vendite.contratti_righe cr
      JOIN catalogo.articoli a
        ON a.id           = cr.articolo_id
       AND a.is_composito = FALSE
       AND a.attivo       = TRUE
      JOIN catalogo.unita_misura um ON um.id = a.uom_id
     WHERE cr.contratto_id          = p_contratto_id
       AND cr.tipo_eccezione        = 'AGGIUNTA'::vendite.tipo_eccezione_contratto
       AND COALESCE(cr.attivo, TRUE) = TRUE;

    -- PARTE 2b: AGGIUNTA bundle (is_composito=TRUE, non in listino).
    -- componenti: jsonb_agg da contratti_righe_componenti (figli persistiti).
    -- prezzo_finale padre: prezzo_unitario aggiornato da trgfn_ricalcola_padre.
    -- cr.* sempre valorizzati (JOIN diretto).
    RETURN QUERY
    SELECT
        a.id,
        a.codice,
        a.descrizione,
        TRUE,
        a.uom_id,
        um.codice,
        NULL::numeric,
        NULL::varchar,
        NULL::numeric,
        cr.id,
        cr.prezzo_unitario,
        cr.tipo_eccezione,
        'AGGIUNTA'::varchar,
        cr.prezzo_unitario,
        (
            SELECT jsonb_agg(jsonb_build_object(
                'componente_id',          af.id,
                'componente_codice',      af.codice,
                'componente_descrizione', af.descrizione,
                'uom_id',                 af.uom_id,
                'uom_codice',             umf.codice,
                'coeff_qta',              crc.coeff_qta_snapshot,
                'prezzo',                 crc.prezzo_unitario,
                'obbligatorio',           ac.obbligatorio,
                'esposto_in_fattura',     ac.esposto_in_fattura
            ) ORDER BY crc.ordine, crc.id)
              FROM vendite.contratti_righe_componenti crc
              JOIN catalogo.articoli af
                ON af.id = crc.componente_id
              JOIN catalogo.unita_misura umf
                ON umf.id = af.uom_id
              JOIN catalogo.articoli_componenti ac
                ON ac.id = crc.articolo_componente_id
             WHERE crc.riga_contratto_id = cr.id
               AND crc.attivo            = TRUE
        ),
        cr.quantita,
        cr.qta_operativa,
        cr.tipo_erogazione,
        cr.fonte_quantita_attesa
      FROM vendite.contratti_righe cr
      JOIN catalogo.articoli a
        ON a.id           = cr.articolo_id
       AND a.is_composito = TRUE
       AND a.attivo       = TRUE
      JOIN catalogo.unita_misura um ON um.id = a.uom_id
     WHERE cr.contratto_id          = p_contratto_id
       AND cr.tipo_eccezione        = 'AGGIUNTA'::vendite.tipo_eccezione_contratto
       AND COALESCE(cr.attivo, TRUE) = TRUE;

END;
$function$

COMMENT ON FUNCTION vendite.fn_contratto_righe_preview(p_contratto_id bigint)
IS 'Preview righe drawer ContrattoRigheDrawer. 4 parti: 1a standalone listino + overlay, 1b bundle listino + overlay, 2a AGGIUNTA standalone, 2b AGGIUNTA bundle. Versione listino: snapshot (ATTIVO) o lookup operativo ATTIVA/CHIUSA (DRAFT, Bug A). prezzo_finale aggregato in DB. componenti JSONB uniforme per 1b e 2b. quantita/qta_operativa/tipo_erogazione/fonte_quantita_attesa: da cr.* (NULL per DA_LISTINO via LEFT JOIN; valorizzati per eccezioni e AGGIUNTA).';
```

---
{% include-markdown "signature-core.md" %}
