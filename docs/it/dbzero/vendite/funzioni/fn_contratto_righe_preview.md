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
-- Scopo: righe drawer ContrattoRigheDrawer (output invariato).
-- Parte 1: core fn_espandi_listino_versione (standalone+bundle) +
--   overlay OVERRIDE/ESCLUSIONE via LEFT JOIN contratti_righe.
-- Parte 2: AGGIUNTA standalone+bundle da contratti_righe/_componenti.
-- Versione operativa: snapshot se ATTIVO, altrimenti lookup ATTIVA/CHIUSA.
DECLARE
    v_listino_id          vendite.contratti.listino_id%TYPE;
    v_listino_versione_id vendite.contratti.listino_versione_id%TYPE;
    v_tipo_var            vendite.contratti.tipo_variazione_globale%TYPE;
    v_valore_var          vendite.contratti.valore_variazione_globale%TYPE;
BEGIN
    SELECT c.listino_id, c.listino_versione_id,
           c.tipo_variazione_globale, c.valore_variazione_globale
      INTO v_listino_id, v_listino_versione_id, v_tipo_var, v_valore_var
      FROM vendite.contratti c
     WHERE c.id = p_contratto_id;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Versione operativa per contratti DRAFT senza snapshot (BOZZA esclusa).
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

    -- PARTE 1: righe dal listino (core) + overlay eccezioni OVERRIDE/ESCLUSIONE.
    IF v_listino_versione_id IS NOT NULL THEN
        RETURN QUERY
        SELECT
            base.articolo_id,
            base.articolo_codice,
            base.articolo_descrizione,
            base.is_composito,
            base.uom_id,
            base.uom_codice,
            base.prezzo_listino,
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
                ELSE                                       base.prezzo_da_listino
            END,
            base.componenti,
            cr.quantita,
            cr.qta_operativa,
            cr.tipo_erogazione,
            cr.fonte_quantita_attesa
          FROM vendite.fn_espandi_listino_versione(
                   v_listino_versione_id, v_tipo_var, v_valore_var
               ) base
          LEFT JOIN vendite.contratti_righe cr
                 ON cr.contratto_id           = p_contratto_id
                AND cr.articolo_id            = base.articolo_id
                AND cr.tipo_eccezione         IN (
                        'OVERRIDE'::vendite.tipo_eccezione_contratto,
                        'ESCLUSIONE'::vendite.tipo_eccezione_contratto
                    )
                AND COALESCE(cr.attivo, TRUE) = TRUE;
    END IF;

    -- PARTE 2a: AGGIUNTA standalone (non in listino). JOIN diretto.
    RETURN QUERY
    SELECT
        a.id, a.codice, a.descrizione, FALSE,
        a.uom_id, um.codice,
        NULL::numeric, NULL::varchar, NULL::numeric,
        cr.id, cr.prezzo_unitario, cr.tipo_eccezione,
        'AGGIUNTA'::varchar, cr.prezzo_unitario, NULL::jsonb,
        cr.quantita, cr.qta_operativa, cr.tipo_erogazione, cr.fonte_quantita_attesa
      FROM vendite.contratti_righe cr
      JOIN catalogo.articoli a
        ON a.id = cr.articolo_id AND a.is_composito = FALSE AND a.attivo = TRUE
      JOIN catalogo.unita_misura um ON um.id = a.uom_id
     WHERE cr.contratto_id          = p_contratto_id
       AND cr.tipo_eccezione        = 'AGGIUNTA'::vendite.tipo_eccezione_contratto
       AND COALESCE(cr.attivo, TRUE) = TRUE;

    -- PARTE 2b: AGGIUNTA bundle (non in listino). Componenti da contratti_righe_componenti.
    RETURN QUERY
    SELECT
        a.id, a.codice, a.descrizione, TRUE,
        a.uom_id, um.codice,
        NULL::numeric, NULL::varchar, NULL::numeric,
        cr.id, cr.prezzo_unitario, cr.tipo_eccezione,
        'AGGIUNTA'::varchar, cr.prezzo_unitario,
        (
            SELECT jsonb_agg(jsonb_build_object(
                'articolo_componente_id', ac.id,
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
              JOIN catalogo.articoli af ON af.id = crc.componente_id
              JOIN catalogo.unita_misura umf ON umf.id = af.uom_id
              JOIN catalogo.articoli_componenti ac ON ac.id = crc.articolo_componente_id
             WHERE crc.riga_contratto_id = cr.id
               AND crc.attivo            = TRUE
        ),
        cr.quantita, cr.qta_operativa, cr.tipo_erogazione, cr.fonte_quantita_attesa
      FROM vendite.contratti_righe cr
      JOIN catalogo.articoli a
        ON a.id = cr.articolo_id AND a.is_composito = TRUE AND a.attivo = TRUE
      JOIN catalogo.unita_misura um ON um.id = a.uom_id
     WHERE cr.contratto_id          = p_contratto_id
       AND cr.tipo_eccezione        = 'AGGIUNTA'::vendite.tipo_eccezione_contratto
       AND COALESCE(cr.attivo, TRUE) = TRUE;
END;
$function$

COMMENT ON FUNCTION vendite.fn_contratto_righe_preview(p_contratto_id bigint)
IS 'Preview righe drawer ContrattoRigheDrawer. Parte 1 dal core fn_espandi_listino_versione (standalone+bundle) + overlay OVERRIDE/ESCLUSIONE; Parte 2 AGGIUNTA standalone+bundle da contratti_righe/_componenti. Output invariato (19 colonne). componenti jsonb ora include articolo_componente_id.';
```

---
{% include-markdown "signature-core.md" %}
