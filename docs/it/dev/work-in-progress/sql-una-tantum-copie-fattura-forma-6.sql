-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- SQL una tantum per Zero ERP — NON e' un changeSet
--
-- K-S2 (brief-modello-documento-vendita §15.16.1 R-S2, §15.17; D-S1 = forma
-- 6, Tid 2026-10-27): le copie del modello della fattura degli EMITTENTI
-- passano alla forma dei dati 6, come lo standard (20261028-01).
--
-- QUANDO: subito DOPO il riavvio del backend che porta la fattura a
--   CONTEXT_VERSION = 6 (giro BE, §15.16.3 punto 3). Prima, le versioni in
--   forma 6 non stamperebbero (409 E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA).
-- DOVE: i database di sviluppo (dbdev). Non c'e' produzione. Sono dati
--   dell'applicazione: per questo non e' un changeSet (brief dei modelli
--   standard, §4.1 Q-5).
-- COME:  psql -X -v ON_ERROR_STOP=1 -f <questo file>   (come owner: titodb)
--
-- COSA FA, per ogni modello della fattura di un emittente (non standard,
--   attivo) la cui versione stampata oggi dichiara la forma 5 e legge
--   `fattura.origine.`:
--   * copia quella versione in una BOZZA, col riquadro «Origine documento»
--     sostituito da «Documenti di origine» (l'elenco fattura.origini): lo
--     stesso blocco del 20261028-01, testo esatto, 1 occorrenza, o si ferma
--     tutto; sul risultato zero `fattura.origine.`;
--   * la bozza dichiara la forma 6 e si pubblica dalla data operativa con
--     documenti.fn_pubblica_template_documento_versione: la versione di prima
--     diventa OBSOLETA (le ristampe dei documenti gia' generati non cambiano).
--   Criterio, non id: rilanciato non trova piu' niente e non fa niente.
--   Si ferma (e annulla tutto) se un modello ha gia' una BOZZA attiva: e' un
--   lavoro in corso di qualcuno, da guardare prima.
--   Alla fine stampa il riepilogo. Il COMMIT e' in fondo.
-- ⚠️ I due blocchi sono gli stessi del 20261028-01 (non e' una copia da
--   estrarre: questo file si cancella all'archiviazione del brief).
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE ks2_riepilogo (
    template_id  bigint,
    emittente_id bigint,
    codice       text,
    da_versione  integer,
    a_versione   integer,
    versione_id  bigint,
    valido_dal   date,
    obsolete     integer
) ON COMMIT DROP;

DO $ks2$
DECLARE
    -- Pezzi di html_template.
    c_vecchio CONSTANT documenti.template_documenti_versioni.html_template%TYPE := array_to_string(ARRAY[
        '{% if fattura.origine.tipo or fattura.origine.codice %}',
        '      <section class="section">',
        '        <div class="label">Origine documento</div>',
        '        <div class="box">',
        '          <strong>{{ fattura.origine.tipo or "Documento origine" }}</strong>',
        '          {% if fattura.origine.codice %}',
        '            <span class="muted"> - {{ fattura.origine.codice }}</span>',
        '          {% endif %}',
        '        </div>',
        '      </section>',
        '    {% endif %}'], E'\n');
    c_nuovo   CONSTANT documenti.template_documenti_versioni.html_template%TYPE := array_to_string(ARRAY[
        '{% if fattura.origini %}',
        '      <section class="section">',
        '        <div class="label">Documenti di origine</div>',
        '        <div class="box">',
        '          {% for o in fattura.origini %}',
        '            <div><strong>{{ o.etichetta }}</strong>{% if o.codice %}<span class="muted"> - {{ o.codice }}</span>{% endif %}</div>',
        '          {% endfor %}',
        '        </div>',
        '      </section>',
        '    {% endif %}'], E'\n');
    c_chiave_vecchia CONSTANT documenti.template_documenti_versioni.html_template%TYPE := 'fattura.origine.';
    c_forma_da CONSTANT documenti.template_documenti_versioni.versione_contesto%TYPE := 5;
    c_forma    CONSTANT documenti.template_documenti_versioni.versione_contesto%TYPE := 6;
    v_oggi    CONSTANT documenti.template_documenti_versioni.valido_dal%TYPE := script.fn_data_operativa();
    r         record;
    v_html    documenti.template_documenti_versioni.html_template%TYPE;
    -- un conteggio di sottostringhe: nessuna colonna di cui sia il riflesso
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
          JOIN documenti.tipi_documento_output o ON o.id = t.tipo_documento_output_id
          JOIN documenti.template_documenti_versioni v ON v.template_documento_id = t.id
         WHERE NOT t.standard
           AND t.attivo
           AND s.codice_interno = 'FATTURA'
           AND o.codice_interno = 'FATTURA_VENDITA'
           AND v.stato = 'PUBBLICATA'
           AND v.attivo
           AND v.validita @> v_oggi
         ORDER BY t.id, v.versione DESC, v.id DESC
    LOOP
        -- Solo le copie ancora in forma 5 che leggono la chiave tolta.
        CONTINUE WHEN r.versione_contesto <> c_forma_da OR strpos(r.html_template, c_chiave_vecchia) = 0;

        IF EXISTS (SELECT 1 FROM documenti.template_documenti_versioni b
                    WHERE b.template_documento_id = r.template_id
                      AND b.stato = 'BOZZA' AND b.attivo) THEN
            RAISE EXCEPTION 'Modello % (%, emittente %): c''e'' gia'' una BOZZA attiva. Guardarla prima; niente e'' stato scritto.',
                r.template_id, r.codice_interno, r.emittente_fiscale_id;
        END IF;

        v_conta := (length(r.html_template) - length(replace(r.html_template, c_vecchio, ''))) / length(c_vecchio);
        IF v_conta <> 1 THEN
            RAISE EXCEPTION 'Modello % (%, emittente %), versione %: riquadro «Origine documento» trovato % volte invece di 1 (ritoccato?). Niente e'' stato scritto.',
                r.template_id, r.codice_interno, r.emittente_fiscale_id, r.versione, v_conta;
        END IF;

        v_html := replace(r.html_template, c_vecchio, c_nuovo);
        IF strpos(v_html, c_chiave_vecchia) > 0 THEN
            RAISE EXCEPTION 'Modello % (%, emittente %): nell''HTML risultante resta %, fuori dal riquadro. Niente e'' stato scritto.',
                r.template_id, r.codice_interno, r.emittente_fiscale_id, c_chiave_vecchia;
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
                   'brief',               'brief-modello-documento-vendita',
                   'origine',             'K-S2, SQL una tantum',
                   'origine_versione_id', r.id,
                   'motivo',              'forma 6: la fattura stampa i documenti di origine (fattura.origini)')
        RETURNING id, versione INTO v_nuova, v_numero;

        SELECT * INTO v_esito
          FROM documenti.fn_pubblica_template_documento_versione(v_nuova, v_oggi, c_forma, NULL);

        INSERT INTO ks2_riepilogo
        VALUES (r.template_id, r.emittente_fiscale_id, r.codice_interno, r.versione, v_numero,
                v_nuova, v_oggi, v_esito.versioni_obsolete);
    END LOOP;
END
$ks2$;

\echo 'Modelli della fattura degli emittenti portati alla forma 6:'
SELECT * FROM ks2_riepilogo ORDER BY template_id;

\echo 'Che cosa stampa la fattura oggi (ogni riga deve avere forma 6 e legge_origine f):'
SELECT t.id AS template_id, t.standard, t.emittente_fiscale_id, v.versione,
       v.versione_contesto AS forma, strpos(v.html_template, 'fattura.origine.') > 0 AS legge_origine
  FROM documenti.template_documenti t
  JOIN config.sorgenti s ON s.id = t.sorgente_tipo_id AND s.codice_interno = 'FATTURA'
  JOIN documenti.tipi_documento_output o ON o.id = t.tipo_documento_output_id
   AND o.codice_interno = 'FATTURA_VENDITA'
  JOIN documenti.template_documenti_versioni v
    ON v.template_documento_id = t.id AND v.stato = 'PUBBLICATA' AND v.attivo
   AND v.validita @> script.fn_data_operativa()
 WHERE t.attivo
 ORDER BY t.standard DESC, t.id;

COMMIT;
