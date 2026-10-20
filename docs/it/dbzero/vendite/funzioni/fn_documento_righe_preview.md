{% include-markdown "it/dbzero/vendite/manual/fn_documento_righe_preview.md" %}
# ⚙️ Funzione `fn_documento_righe_preview`

```sql
CREATE FUNCTION fn_documento_righe_preview(p_documento character varying, p_documento_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_documento_righe_preview(p_documento character varying, p_documento_id bigint)
 RETURNS TABLE(articolo_id uuid, articolo_codice character varying, articolo_descrizione character varying, is_composito boolean, uom_id bigint, uom_codice character varying, prezzo_listino numeric, tipo_variazione character varying, valore_variazione numeric, override_riga_id bigint, override_prezzo numeric, tipo_eccezione vendite.tipo_eccezione_contratto, origine character varying, prezzo_finale numeric, componenti jsonb, quantita numeric, qta_operativa numeric, tipo_erogazione character varying, fonte_quantita_attesa character varying, riga_key text, azioni text[], escludi_blocco_codice text, ordine smallint, uom_operativa_id bigint)
 LANGUAGE plpgsql
 STABLE
AS $function$

-- Scopo: le righe di un contratto o di un'offerta per il drawer
--   (p_documento = CONTRATTO | OFFERTA_COMMERCIALE), sorgente delle due liste.
-- Parte 1: righe del listino (core fn_espandi_listino_versione,
--   standalone e bundle) con l'overlay OVERRIDE/ESCLUSIONE.
-- Parte 2: AGGIUNTA standalone (2a) e bundle (2b).
-- Versione operativa: vendite.fn_documento_listino_operativo
--   (fissata, o in vigore oggi; nessun listino = solo la parte 2).
-- Colonne in coda: riga_key ('L:<articolo>:<uom>' dal listino,
--   'A:<id>' per le AGGIUNTA), azioni (i verbi dell'origine),
--   escludi_blocco_codice (il reason del PRIMO motivo di
--   script.fn_check_esclusione_articolo_documento, NULL = ammesso:
--   lo stesso predicato del guard), ordine e uom_operativa_id della
--   riga eccezione (NULL sulle righe DA_LISTINO).
-- L'UdM di una AGGIUNTA e' quella della RIGA; NULL = la base
--   dell'articolo (lo stesso ripiego di script.trgfn_qta_from_operativa).
-- ⚠️ Il blocco «fuori bozza» NON e' qui: e' di documento.
-- ⚠️ p_documento ancorato a config.sorgenti.codice_interno (grammatica
--   unica, lotto 1); p_documento_id nudo DICHIARATO (id polimorfo);
--   nude anche le colonne calcolate.
-- Nasce il 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende,
--   R4) dal corpo di vendite.fn_contratto_righe_preview (20261004-14),
--   che ora la chiama; la chiama anche vendite.fn_offerta_righe_preview.
DECLARE
    v_trovato             boolean := false;
    v_listino_versione_id vendite.listini_versioni.id%TYPE;
    v_tipo_var            vendite.contratti.tipo_variazione_globale%TYPE;
    v_valore_var          vendite.contratti.valore_variazione_globale%TYPE;
BEGIN
    SELECT true, lo.listino_versione_id,
           lo.tipo_variazione_globale, lo.valore_variazione_globale
      INTO v_trovato, v_listino_versione_id, v_tipo_var, v_valore_var
      FROM vendite.fn_documento_listino_operativo(p_documento, p_documento_id) lo;

    -- Documento assente (o fuori perimetro): nessuna riga.
    IF NOT COALESCE(v_trovato, false) THEN
        RETURN;
    END IF;

    -- PARTE 1: righe dal listino (core) + overlay OVERRIDE/ESCLUSIONE.
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
            e.id,
            e.prezzo_unitario,
            e.tipo_eccezione,
            CASE
                WHEN e.tipo_eccezione = 'OVERRIDE'   THEN 'OVERRIDE'
                WHEN e.tipo_eccezione = 'ESCLUSIONE' THEN 'ESCLUSIONE'
                ELSE                                      'DA_LISTINO'
            END::varchar,
            CASE
                WHEN e.tipo_eccezione = 'OVERRIDE'   THEN e.prezzo_unitario
                WHEN e.tipo_eccezione = 'ESCLUSIONE' THEN NULL
                ELSE                                      base.prezzo_da_listino
            END,
            base.componenti,
            e.quantita,
            e.qta_operativa,
            e.tipo_erogazione,
            e.fonte_quantita_attesa,
            ('L:' || base.articolo_id::text || ':' || base.uom_id::text),
            CASE
                WHEN e.tipo_eccezione = 'OVERRIDE'
                    THEN ARRAY['MODIFICA', 'RIPRISTINA_LISTINO']
                -- Un'esclusione si crea e si cancella, non si modifica
                -- (guard _a05_ sulla riga, sui due documenti).
                WHEN e.tipo_eccezione = 'ESCLUSIONE'
                    THEN ARRAY['RIPRISTINA_ARTICOLO']
                ELSE ARRAY['SOVRASCRIVI_PREZZO', 'ESCLUDI']
            END,
            -- Solo dove «Escludi» e' un'azione della riga (dal listino).
            CASE
                WHEN e.tipo_eccezione IS NULL
                    THEN script.fn_check_esclusione_articolo_documento(
                             p_documento, p_documento_id, base.articolo_id)
                         -> 0 ->> 'reason'
            END,
            e.ordine,
            e.uom_operativa_id
          FROM vendite.fn_espandi_listino_versione(
                   v_listino_versione_id, v_tipo_var, v_valore_var
               ) base
          LEFT JOIN vendite.fn_documento_righe_eccezione(p_documento, p_documento_id) e
                 ON e.articolo_id            = base.articolo_id
                AND e.tipo_eccezione         IN (
                        'OVERRIDE'::vendite.tipo_eccezione_contratto,
                        'ESCLUSIONE'::vendite.tipo_eccezione_contratto
                    )
                AND COALESCE(e.attivo, TRUE) = TRUE;
    END IF;

    -- PARTE 2a: AGGIUNTA standalone (non in listino).
    RETURN QUERY
    SELECT
        a.id, a.codice, a.descrizione, FALSE,
        COALESCE(e.uom_operativa_id, a.uom_id), um.codice,
        NULL::numeric, NULL::varchar, NULL::numeric,
        e.id, e.prezzo_unitario, e.tipo_eccezione,
        'AGGIUNTA'::varchar, e.prezzo_unitario, NULL::jsonb,
        e.quantita, e.qta_operativa, e.tipo_erogazione, e.fonte_quantita_attesa,
        ('A:' || e.id::text), ARRAY['MODIFICA', 'RIMUOVI'], NULL::text,
        e.ordine, e.uom_operativa_id
      FROM vendite.fn_documento_righe_eccezione(p_documento, p_documento_id) e
      JOIN catalogo.articoli a
        ON a.id = e.articolo_id AND a.is_composito = FALSE AND a.attivo = TRUE
      -- L'UdM della riga; NULL = la base dell'articolo.
      JOIN catalogo.unita_misura um ON um.id = COALESCE(e.uom_operativa_id, a.uom_id)
     WHERE e.tipo_eccezione         = 'AGGIUNTA'::vendite.tipo_eccezione_contratto
       AND COALESCE(e.attivo, TRUE) = TRUE;

    -- PARTE 2b: AGGIUNTA bundle (non in listino), coi componenti della
    -- tabella dei componenti del documento.
    RETURN QUERY
    SELECT
        a.id, a.codice, a.descrizione, TRUE,
        COALESCE(e.uom_operativa_id, a.uom_id), um.codice,
        NULL::numeric, NULL::varchar, NULL::numeric,
        e.id, e.prezzo_unitario, e.tipo_eccezione,
        'AGGIUNTA'::varchar, e.prezzo_unitario,
        (
            SELECT jsonb_agg(jsonb_build_object(
                'articolo_componente_id', ac.id,
                'componente_id',          af.id,
                'componente_codice',      af.codice,
                'componente_descrizione', af.descrizione,
                'uom_id',                 c.uom_operativa_id,
                'uom_codice',             umf.codice,
                'coeff_qta',              c.coeff_qta_snapshot,
                'prezzo',                 c.prezzo_unitario,
                'obbligatorio',           ac.obbligatorio,
                'esposizione_in_fattura', ac.esposizione_in_fattura
            ) ORDER BY c.ordine, c.id)
              FROM (
                  SELECT crc.id, crc.articolo_componente_id, crc.componente_id,
                         crc.uom_operativa_id, crc.coeff_qta_snapshot,
                         crc.prezzo_unitario, crc.ordine
                    FROM vendite.contratti_righe_componenti crc
                   WHERE p_documento           = 'CONTRATTO'
                     AND crc.riga_contratto_id = e.id
                     AND crc.attivo            = TRUE
                  UNION ALL
                  SELECT occ.id, occ.articolo_componente_id, occ.componente_id,
                         occ.uom_operativa_id, occ.coeff_qta_snapshot,
                         occ.prezzo_unitario, occ.ordine
                    FROM vendite.offerte_commerciali_eccezioni_componenti occ
                   WHERE p_documento              = 'OFFERTA_COMMERCIALE'
                     AND occ.eccezione_offerta_id = e.id
                     AND occ.attivo               = TRUE
              ) c
              JOIN catalogo.articoli af ON af.id = c.componente_id
              -- Il prezzo del componente e' quotato nella SUA UdM operativa.
              JOIN catalogo.unita_misura umf ON umf.id = c.uom_operativa_id
              JOIN catalogo.articoli_componenti ac ON ac.id = c.articolo_componente_id
        ),
        e.quantita, e.qta_operativa, e.tipo_erogazione, e.fonte_quantita_attesa,
        ('A:' || e.id::text), ARRAY['MODIFICA', 'RIMUOVI'], NULL::text,
        e.ordine, e.uom_operativa_id
      FROM vendite.fn_documento_righe_eccezione(p_documento, p_documento_id) e
      JOIN catalogo.articoli a
        ON a.id = e.articolo_id AND a.is_composito = TRUE AND a.attivo = TRUE
      -- L'UdM della riga; NULL = la base dell'articolo.
      JOIN catalogo.unita_misura um ON um.id = COALESCE(e.uom_operativa_id, a.uom_id)
     WHERE e.tipo_eccezione         = 'AGGIUNTA'::vendite.tipo_eccezione_contratto
       AND COALESCE(e.attivo, TRUE) = TRUE;
END;
$function$

COMMENT ON FUNCTION vendite.fn_documento_righe_preview(p_documento character varying, p_documento_id bigint)
IS 'Le righe di un contratto o di un''offerta come le vede il drawer (p_documento = CONTRATTO | OFFERTA): righe della versione operativa del listino (vendite.fn_documento_listino_operativo) con l''overlay OVERRIDE/ESCLUSIONE, piu'' le AGGIUNTA standalone e bundle (eccezioni da vendite.fn_documento_righe_eccezione). Colonne in coda: riga_key, azioni (DA_LISTINO -> SOVRASCRIVI_PREZZO, ESCLUDI; OVERRIDE -> MODIFICA, RIPRISTINA_LISTINO; ESCLUSIONE -> RIPRISTINA_ARTICOLO; AGGIUNTA -> MODIFICA, RIMUOVI), escludi_blocco_codice (primo motivo di script.fn_check_esclusione_articolo_documento, lo stesso predicato del guard), ordine e uom_operativa_id della riga eccezione. Il blocco «fuori bozza» non e'' qui: e'' di documento. Documento assente o fuori perimetro (INVOKER): nessuna riga. Sorgente unica (regola del 2) di vendite.fn_contratto_righe_preview e vendite.fn_offerta_righe_preview, involucri di una riga. Nasce il 2026-10-04 dal corpo di fn_contratto_righe_preview (20261004-14), brief-db-righe-esclusione-solo-non-si-vende (R4). ⭐ rev 2026-10-19 (20261019-23, brief-db-grammatica-unica-documenti lotto 1, G-1 di Tid): il documento si nomina col codice della sorgente, CONTRATTO | OFFERTA_COMMERCIALE (era OFFERTA); dove sopra si legge OFFERTA come selettore, oggi e'' OFFERTA_COMMERCIALE. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato).';
```

</div>

---
{% include-markdown "signature-core.md" %}
