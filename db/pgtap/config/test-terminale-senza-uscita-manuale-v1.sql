-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: da uno stato terminale non esce nessun passaggio a mano.
--   ChangeSet: 20261113-43 (il COMMENT di terminale), -45
--   (script.fn_doc_terminali_con_uscita_manuale), -46 (il building block
--   script.trgfn_doc_terminale_senza_uscita_manuale e i suoi montaggi).
--   Brief: brief-db-stati-documento-dal-vocabolario, giro 3 (④, S-1 = A, S-4).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - una riga attiva della matrice con meta.manuale = true che esce da uno
--     stato terminale e' rifiutata (E_DOC_TERMINALE_CON_USCITA_MANUALE), qualunque
--     sia l'ordine delle scritture: si giudica a fine transazione;
--   - la stessa riga di processo (manuale = false), o spenta, e' ammessa;
--   - terminale = true su uno stato con un'uscita a mano attiva e' rifiutato;
--   - implicazione, non equivalenza: uno stato senza uscite a mano puo' non
--     essere terminale;
--   - terminale si legge, non si copia: un'offerta SUPERATA e' terminale, e
--     torna EMESSA (non terminale) quando la sua revisione si annulla.
--
-- ⭐ I CASI SI COSTRUISCONO sulla matrice vera del reso, in transazione:
--   ANNULLATO e' terminale e non ha uscite; CONFERMATO non e' terminale (S-5) e
--   ha l'annullo a mano. Nessun builder per i test 1-6: si scrive la
--   configurazione. ⚠️ SET CONSTRAINTS ALL IMMEDIATE: il trigger e' differito,
--   e qui il COMMIT non arriva mai.
--
-- Elenco test (plan 10):
--   1) una riga a mano attiva ANNULLATO -> DRAFT del reso: rifiutata
--   2) la stessa riga di processo (manuale = false): ammessa
--   3) ... diventare a mano (UPDATE di meta, da sola): rifiutata
--   4) ... spenta (attivo = false), poi a mano: ammessa
--   5) ... riaccesa (UPDATE di attivo, da solo): rifiutata
--   6) terminale = true sul reso CONFERMATO, che ha l'annullo a mano: rifiutato
--   7) implicazione: la configurazione di oggi non ha stati terminali con
--      uscite a mano, sui sette documenti (una configurazione, non una
--      popolazione: e' il seed di catalogo)
--   8) forma: i quattordici montaggi, differiti, con la testata come argomento
--   9) una testata il cui vocabolario non ha terminale (la fattura):
--      E_SCRIPT_CHIAMATA_NON_VALIDA
--  10) il lettore rilegge: l'offerta SUPERATA e' terminale; annullata la
--      revisione, torna EMESSA e non lo e' piu'
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- Gli id degli stati del reso, per codice: la configurazione che si scrive.
CREATE TEMP TABLE _st AS
SELECT s.codice_interno::text AS codice, s.id
  FROM config.stati_doc_reso s;

CREATE FUNCTION pg_temp.st(p text) RETURNS bigint
LANGUAGE sql STABLE AS $f$ SELECT id FROM _st WHERE codice = p $f$;

-- ============================================================
-- 1-5) La matrice: una riga che esce da uno stato terminale
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$INSERT INTO config.transizioni_stati_reso (stato_da_id, stato_a_id, attivo, meta)
          VALUES (%s, %s, true, '{"manuale": true, "action_key": "riapri", "label_key": "pgtap.riapri"}')$$,
        pg_temp.st('ANNULLATO'), pg_temp.st('DRAFT'))),
    'E_DOC_TERMINALE_CON_USCITA_MANUALE',
    '1. una riga a mano attiva che esce dallo stato terminale ANNULLATO e'' rifiutata'
);

SELECT is(
    COALESCE(dbops.fn_pgtap_codice_errore(format(
        $$INSERT INTO config.transizioni_stati_reso (stato_da_id, stato_a_id, attivo, meta)
          VALUES (%s, %s, true, '{"manuale": false}')$$,
        pg_temp.st('ANNULLATO'), pg_temp.st('DRAFT'))), 'PASSA'),
    'PASSA',
    '2. la stessa riga di processo (manuale = false) e'' ammessa'
);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$UPDATE config.transizioni_stati_reso
             SET meta = '{"manuale": true, "action_key": "riapri", "label_key": "pgtap.riapri"}'
           WHERE stato_da_id = %s AND stato_a_id = %s$$,
        pg_temp.st('ANNULLATO'), pg_temp.st('DRAFT'))),
    'E_DOC_TERMINALE_CON_USCITA_MANUALE',
    '3. diventare a mano (un UPDATE di meta, da solo) e'' rifiutato'
);

SELECT is(
    COALESCE(dbops.fn_pgtap_codice_errore(format(
        $$UPDATE config.transizioni_stati_reso
             SET attivo = false,
                 meta = '{"manuale": true, "action_key": "riapri", "label_key": "pgtap.riapri"}'
           WHERE stato_da_id = %s AND stato_a_id = %s$$,
        pg_temp.st('ANNULLATO'), pg_temp.st('DRAFT'))), 'PASSA'),
    'PASSA',
    '4. spenta, la riga a mano non e'' un''uscita: ammessa'
);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$UPDATE config.transizioni_stati_reso SET attivo = true
           WHERE stato_da_id = %s AND stato_a_id = %s$$,
        pg_temp.st('ANNULLATO'), pg_temp.st('DRAFT'))),
    'E_DOC_TERMINALE_CON_USCITA_MANUALE',
    '5. riaccenderla (un UPDATE di attivo, da solo) e'' rifiutato'
);

-- ============================================================
-- 6) Il vocabolario: terminale su uno stato con un'uscita a mano
-- ============================================================
-- CONFERMATO ha fase CHIUSO (il CHECK terminale -> CHIUSO passerebbe) e
-- l'annullo a mano: parla il building block.
SELECT is(
    dbops.fn_pgtap_codice_errore(
        $$UPDATE config.stati_doc_reso SET terminale = true WHERE codice_interno = 'CONFERMATO'$$),
    'E_DOC_TERMINALE_CON_USCITA_MANUALE',
    '6. terminale = true sul reso CONFERMATO, che ha l''annullo a mano attivo, e'' rifiutato'
);

-- ============================================================
-- 7-9) La configurazione, la forma, la chiamata sbagliata
-- ============================================================
-- ⚠️ Legge il seed di catalogo (la configurazione), non una popolazione: e'
--   lo stesso su ogni database ricostruito.
SELECT is(
    ARRAY(SELECT t || ':' || x.stato || '->' || x.uscita
            FROM unnest(ARRAY['vendite.preventivi', 'vendite.offerte_commerciali', 'vendite.contratti',
                              'vendite.ordini', 'vendite.ddt', 'vendite.resi',
                              'vendite.listini_versioni']) AS t,
                 script.fn_doc_terminali_con_uscita_manuale(t::regclass) AS x
           ORDER BY 1),
    ARRAY[]::text[],
    '7. la configurazione dei sette documenti: nessuno stato terminale con un''uscita a mano'
);

-- ⚠️ Presidio sulla FORMA: i montaggi si cercano per funzione e argomento,
--   non per nome (linee-guida-trigger).
SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger tg
       JOIN pg_constraint c ON c.oid = tg.tgconstraint
      WHERE tg.tgfoid = 'script.trgfn_doc_terminale_senza_uscita_manuale()'::regprocedure
        AND c.condeferrable AND c.condeferred
        AND (dbops.fn_trigger_argomenti(tg.tgargs))[1]::regclass = ANY (
              ARRAY['vendite.preventivi', 'vendite.offerte_commerciali', 'vendite.contratti',
                    'vendite.ordini', 'vendite.ddt', 'vendite.resi', 'vendite.listini_versioni']::regclass[])),
    14,
    '8. forma: quattordici montaggi differiti (vocabolario e matrice di sette documenti), con la testata come argomento'
);

SELECT is(
    dbops.fn_pgtap_codice_errore(
        $$SELECT * FROM script.fn_doc_terminali_con_uscita_manuale('vendite.fatture'::regclass)$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '9. una testata il cui vocabolario non ha terminale (la fattura) e'' una chiamata sbagliata'
);

-- ============================================================
-- 10) Il lettore rilegge: SUPERATA e' terminale, e torna EMESSA
-- ============================================================
CREATE TEMP TABLE _off AS
SELECT * FROM dbops.fn_pgtap_crea_offerta('terminale senza uscita manuale', 'EMESSA');

CREATE TEMP TABLE _rev AS
SELECT vendite.fn_crea_revisione_offerta((SELECT o.offerta_id FROM _off o), 'pgtap') AS revisione_id;

CREATE TEMP TABLE _prima AS
SELECT v.stato_codice_interno::text AS stato, v.terminale
  FROM vendite.vw_stato_sorgente_offerta v
  JOIN vendite.offerte_commerciali o ON o.uid::text = v.sorgente_uid
 WHERE o.id = (SELECT x.offerta_id FROM _off x);

-- L'annullo conferma i legami della revisione (il padre superato, di
-- provenienza): si contano, non si scrivono a mano.
SELECT vendite.fn_annulla_offerta(
    (SELECT r.revisione_id FROM _rev r), 'pgtap: la revisione si annulla',
    (SELECT count(*)::int FROM vendite.fn_documento_legami('OFFERTA_COMMERCIALE', (SELECT r.revisione_id FROM _rev r))));

SELECT is(
    (SELECT p.stato || ' ' || p.terminale FROM _prima p)
    || ' | ' ||
    (SELECT v.stato_codice_interno || ' ' || v.terminale
       FROM vendite.vw_stato_sorgente_offerta v
       JOIN vendite.offerte_commerciali o ON o.uid::text = v.sorgente_uid
      WHERE o.id = (SELECT x.offerta_id FROM _off x)),
    'SUPERATA true | EMESSA false',
    '10. l''offerta SUPERATA e'' terminale; annullata la revisione torna EMESSA e non lo e'' piu'' (si rilegge, non si copia)'
);

SELECT * FROM finish();
ROLLBACK;
