-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- SQL una tantum per Zero ERP — NON e' un changeSet
--
-- L2b-2 (brief-db-grammatica-unica-documenti §12.10.3, decisione (c) di Tid,
-- 2026-10-20): le copie del modello d'ordine degli EMITTENTI passano alla forma
-- dei dati 3, come lo standard (20261020-25).
--
-- QUANDO: subito DOPO il riavvio del backend che porta l'ordine a
--   CONTEXT_VERSION = 3 (giro BE del §12.10.4). Prima, le versioni in forma 3
--   non stamperebbero (409 E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA).
-- DOVE: i database di sviluppo (dbdev). Non c'e' produzione. Sono dati
--   dell'applicazione: per questo non e' un changeSet (brief dei modelli
--   standard, §4.1 Q-5).
-- COME:  psql -X -v ON_ERROR_STOP=1 -f <questo file>   (come owner: titodb)
--
-- COSA FA, per ogni modello d'ordine di un emittente (non standard, attivo)
--   la cui versione stampata oggi dichiara la forma 2 e legge
--   `ordine.origine.tipo`:
--   * copia quella versione in una BOZZA, con `ordine.origine.tipo` ->
--     `ordine.origine.etichetta` (esattamente 2 occorrenze, o si ferma tutto);
--   * la bozza dichiara la forma 3 e si pubblica dalla data operativa con
--     documenti.fn_pubblica_template_documento_versione: la versione di prima
--     diventa OBSOLETA (le ristampe dei documenti gia' generati non cambiano).
--   Criterio, non id: rilanciato non trova piu' niente e non fa niente.
--   Si ferma (e annulla tutto) se un modello ha gia' una BOZZA attiva: e' un
--   lavoro in corso di qualcuno, da guardare prima.
--   Alla fine stampa il riepilogo. Il COMMIT e' in fondo.
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE l2b2_riepilogo (
    template_id  bigint,
    emittente_id bigint,
    codice       text,
    da_versione  integer,
    a_versione   integer,
    versione_id  bigint,
    valido_dal   date,
    obsolete     integer
) ON COMMIT DROP;

DO $l2b2$
DECLARE
    c_vecchia CONSTANT text := 'ordine.origine.tipo';
    c_nuova   CONSTANT text := 'ordine.origine.etichetta';
    c_forma   CONSTANT documenti.template_documenti_versioni.versione_contesto%TYPE := 3;
    v_oggi    CONSTANT date := script.fn_data_operativa();
    r         record;
    v_html    documenti.template_documenti_versioni.html_template%TYPE;
    v_conta   integer;
    v_nuova   documenti.template_documenti_versioni.id%TYPE;
    v_numero  documenti.template_documenti_versioni.versione%TYPE;
    v_esito   record;
BEGIN
    FOR r IN
        SELECT DISTINCT ON (t.id)
               t.id AS template_id, t.emittente_fiscale_id, t.codice_interno, v.*
          FROM documenti.template_documenti t
          JOIN config.sorgenti s ON s.id = t.sorgente_tipo_id
          JOIN documenti.template_documenti_versioni v ON v.template_documento_id = t.id
         WHERE NOT t.standard
           AND t.attivo
           AND s.codice_interno = 'ORDINE_VENDITA'
           AND v.stato = 'PUBBLICATA'
           AND v.attivo
           AND v.validita @> v_oggi
         ORDER BY t.id, v.versione DESC, v.id DESC
    LOOP
        -- Solo le copie ancora in forma 2 che leggono il codice.
        CONTINUE WHEN r.versione_contesto <> 2 OR strpos(r.html_template, c_vecchia) = 0;

        IF EXISTS (SELECT 1 FROM documenti.template_documenti_versioni b
                    WHERE b.template_documento_id = r.template_id
                      AND b.stato = 'BOZZA' AND b.attivo) THEN
            RAISE EXCEPTION 'Modello % (%, emittente %): c''e'' gia'' una BOZZA attiva. Guardarla prima; niente e'' stato scritto.',
                r.template_id, r.codice_interno, r.emittente_fiscale_id;
        END IF;

        v_conta := (length(r.html_template) - length(replace(r.html_template, c_vecchia, ''))) / length(c_vecchia);
        IF v_conta <> 2 THEN
            RAISE EXCEPTION 'Modello % (%, emittente %), versione %: % trovato % volte invece di 2. Niente e'' stato scritto.',
                r.template_id, r.codice_interno, r.emittente_fiscale_id, r.versione, c_vecchia, v_conta;
        END IF;

        v_html := replace(r.html_template, c_vecchia, c_nuova);
        IF strpos(v_html, 'origine.tipo') > 0 THEN
            RAISE EXCEPTION 'Modello %: nell''HTML risultante resta origine.tipo.', r.template_id;
        END IF;

        INSERT INTO documenti.template_documenti_versioni (
            template_documento_id, versione, stato, titolo,
            formato_template, html_template, css_template,
            markdown_template, render_engine_id, page_format,
            page_orientation, margin_top_mm, margin_right_mm,
            margin_bottom_mm, margin_left_mm, context_schema,
            storicizza, versione_contesto, derivata_da_versione_id, meta)
        SELECT r.template_id,
               (SELECT max(v2.versione) + 1 FROM documenti.template_documenti_versioni v2
                 WHERE v2.template_documento_id = r.template_id),
               'BOZZA', r.titolo,
               r.formato_template, v_html, r.css_template,
               r.markdown_template, r.render_engine_id, r.page_format,
               r.page_orientation, r.margin_top_mm, r.margin_right_mm,
               r.margin_bottom_mm, r.margin_left_mm, r.context_schema,
               r.storicizza, c_forma, r.derivata_da_versione_id,
               r.meta || jsonb_build_object(
                   'brief',               'brief-db-grammatica-unica-documenti',
                   'origine',             'L2b-2 (c), SQL una tantum',
                   'origine_versione_id', r.id,
                   'motivo',              'forma 3: la provenienza si stampa con origine.etichetta')
        RETURNING id, versione INTO v_nuova, v_numero;

        SELECT * INTO v_esito
          FROM documenti.fn_pubblica_template_documento_versione(v_nuova, v_oggi, c_forma, NULL);

        INSERT INTO l2b2_riepilogo
        VALUES (r.template_id, r.emittente_fiscale_id, r.codice_interno, r.versione, v_numero,
                v_nuova, v_oggi, v_esito.versioni_obsolete);
    END LOOP;
END
$l2b2$;

\echo 'Modelli d''ordine degli emittenti portati alla forma 3:'
SELECT * FROM l2b2_riepilogo ORDER BY template_id;

\echo 'Che cosa stampa l''ordine oggi (ogni riga deve avere forma 3 e legge_codice f):'
SELECT t.id AS template_id, t.standard, t.emittente_fiscale_id, v.versione,
       v.versione_contesto AS forma, strpos(v.html_template, 'origine.tipo') > 0 AS legge_codice
  FROM documenti.template_documenti t
  JOIN config.sorgenti s ON s.id = t.sorgente_tipo_id AND s.codice_interno = 'ORDINE_VENDITA'
  JOIN documenti.template_documenti_versioni v
    ON v.template_documento_id = t.id AND v.stato = 'PUBBLICATA' AND v.attivo
   AND v.validita @> script.fn_data_operativa()
 WHERE t.attivo
 ORDER BY t.standard DESC, t.id;

COMMIT;
