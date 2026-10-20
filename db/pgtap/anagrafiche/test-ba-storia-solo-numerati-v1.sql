-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: P-6 — la «storia» del billing account conta i documenti NUMERATI,
--       e conta anche il DDT
-- Oggetti:
--   anagrafiche.fn_ba_ha_storia_emittente()    (20260831-17)
--   anagrafiche.fn_get_storia_emittente_ba()   (20260831-17)
--   script.fn_check_ba_cambio_emittente()      (20260831-19)
--   anagrafiche.fn_guard_ba_cambio_emittente()
--   Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, §3.6 e §3.7
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2c/2d): la famiglia della bolla e' DDT_VENDITA, il codice della sorgente.
-- ------------------------------------------------------------
-- Elenco test (plan 7):
-- 1) Fixture: un billing account NUOVO, quindi senza storia
-- 2) ⭐ IL GEMELLO CHE DISTINGUE: un DDT in BOZZA non fa storia
-- 3) ⭐ ...e infatti il cambio di emittente PASSA ancora
-- 4) Il DDT emesso prende un numero dal registro del suo emittente
-- 5) ⭐⭐ ORA la storia lo conta, e lo conta SOTTO LA SUA FAMIGLIA
-- 6) ⛔ ...e il cambio di emittente e' respinto (P0001)
-- 7) ⭐ La frase nomina la SPECIE del documento che blocca
--
-- Scopo:
--   Fino al 2026-08-30 «storia» erano fatture e commesse, e ordini e DDT
--   restavano fuori con una motivazione precisa: il loro emittente non e' una
--   copia che invecchia, perche' un guard lo riallinea al cliente a ogni
--   scrittura. ⛔ Quella motivazione E' CADUTA quando il DDT ha cominciato a
--   prendere il NUMERO dal registro di quell'emittente: il numero, quello,
--   nessuno lo riallinea.
--
--   ⭐⭐ I TEST 2 E 5 SONO GEMELLI, E VANNO LETTI INSIEME. Senza il 2, il 5 non
--   distingue «blocca il documento NUMERATO» da «blocca qualunque documento» —
--   e la differenza e' esattamente la decisione presa il 2026-08-31: una bozza
--   non ha congelato niente, ed e' il caso per cui la finestra di correzione
--   esiste. Un test che provasse solo il blocco passerebbe anche su un
--   presidio troppo severo, che chiuderebbe la finestra al primo documento
--   aperto.
--
--   ⚠️ Il caso si FABBRICA: un billing account nuovo, un DDT sopra, e la
--   transizione a EMESSO. Cercarlo fra i dati esistenti passerebbe a vuoto in
--   CI, dove il database e' ricostruito da zero.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- =========================================================
-- 0) Il mondo si COSTRUISCE — i cataloghi si scelgono, col loro ORDER BY
-- =========================================================
-- ⛔ 2026-09-23: soggetto, ruolo e utility venivano PESCATI da «un billing
--   account esistente», e l'articolo da «l'ultimo articolo attivo». Su un
--   database ricostruito dai changelog i billing account sono zero: la fixture
--   moriva sul NOT NULL di `istanze_utilities.soggetto_id`.
-- ⭐ Il cliente del mondo e' gia' il caso del test (punto 1): un BA appena
--   nato, legato dal trigger z90 all'emittente di chi agisce. Il contesto e'
--   aperto dalla riga sopra, quindi il BB riusa l'azienda dell'operatore.
CREATE TEMP TABLE tmp_bsd_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('BA storia DDT');

CREATE TEMP TABLE tmp_bsd_refs AS
SELECT
    m.cliente_soggetto_ruolo_id                              AS soggetto_ruolo_id,
    m.emittente_fiscale_id,
    m.emittente_soggetto_ruolo_id                            AS emittente_sr_ok,
    -- ⭐ L'«altro» emittente e' un emittente VERO, costruito: prima era «un
    --   soggetto_ruolo qualunque diverso da quello dell'operatore».
    (SELECT e.soggetto_ruolo_id
       FROM dbops.fn_pgtap_crea_emittente() e)               AS emittente_sr_altro,
    -- ⚠️ `gestito_a_magazzino = false`: il caso del file e' la NUMERAZIONE del
    --   DDT, non il suo movimento. Un articolo gestito porterebbe dentro il
    --   magazzino — disponibilita', ubicazioni — che qui non e' in esame.
    dbops.fn_pgtap_crea_articolo('PGTAP-BSD-' || m.billing_account_id,
                                 p_gestito := false)          AS articolo_id,
    (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)              AS valuta_id,
    (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
    (SELECT s.id FROM config.stati_doc_ddt s
      WHERE s.codice_interno = 'DRAFT'  ORDER BY s.id LIMIT 1) AS stato_ddt_draft_id,
    (SELECT s.id FROM config.stati_doc_ddt s
      WHERE s.codice_interno = 'EMESSO' ORDER BY s.id LIMIT 1) AS stato_ddt_emesso_id,
    -- ⚠️ Qui l'aggancio e' su `codice` e NON su `codice_interno`, e non per
    --   scelta: config.causali_trasporto la colonna `codice_interno` non ce
    --   l'ha proprio. Resta quindi un aggancio FRAGILE — `codice` e'
    --   modificabile dall'utente, e un rename lo sgancia in silenzio — ed e'
    --   dichiarato qui invece di essere scoperto da chi vedra' il test
    --   diventare rosso senza capire perche'.
    (SELECT c.id FROM config.causali_trasporto c
      WHERE c.codice = 'VENDITA' ORDER BY c.id LIMIT 1)                   AS causale_vendita_id,
    (SELECT ti.id FROM config.tipi_indirizzi ti
      WHERE ti.codice_interno = 'CON' ORDER BY ti.id LIMIT 1)             AS tipo_ind_con_id
  FROM tmp_bsd_mondo m;

-- =========================================================
-- 1) Fixture: un billing account NUOVO, quindi senza storia
-- =========================================================
CREATE TEMP TABLE tmp_bsd_ids AS
SELECT m.billing_account_id FROM tmp_bsd_mondo m;

SELECT is(
    (SELECT anagrafiche.fn_ba_ha_storia_emittente(t.billing_account_id)
       FROM tmp_bsd_ids t),
    false,
    '1) Un billing account appena nato non ha storia');

-- =========================================================
-- 2) ⭐ IL GEMELLO CHE DISTINGUE: un DDT in BOZZA non fa storia
-- =========================================================
-- ⛔ Senza questa riga, il 5) non distinguerebbe «blocca il documento
--   NUMERATO» da «blocca qualunque documento», e un presidio troppo severo
--   passerebbe il test chiudendo la finestra di correzione al primo documento
--   aperto.
CREATE TEMP TABLE tmp_bsd_ddt (ddt_id bigint);

DO $$
DECLARE
    v_ddt bigint;
    r     record;
    t     record;
BEGIN
    SELECT * INTO r FROM tmp_bsd_refs;
    SELECT * INTO t FROM tmp_bsd_ids;

    INSERT INTO vendite.ddt (
        destinatario_soggetto_ruolo_id, stato_doc_ddt_id, data,
        billing_account_id, valuta_id, causale_trasporto_id,
        emittente_fiscale_id, storicizza, meta)
    VALUES (r.soggetto_ruolo_id, r.stato_ddt_draft_id, script.fn_data_operativa(),
            t.billing_account_id, r.valuta_id, r.causale_vendita_id,
            r.emittente_fiscale_id, false,
            jsonb_build_object('test_scope', 'pgtap_ba_storia_ddt'))
    RETURNING id INTO v_ddt;

    INSERT INTO vendite.ddt_righe (
        ddt_id, riga_nr, articolo_id, descrizione,
        qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
    VALUES (v_ddt, 1, r.articolo_id, 'Riga storia BA', 5, 5, 10, r.iva_id, true, false,
            jsonb_build_object('test_scope', 'pgtap_ba_storia_ddt'));

    -- L'indirizzo di consegna serve all'EMISSIONE, non alla creazione.
    INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
    VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb)
    ON CONFLICT DO NOTHING;

    INSERT INTO tmp_bsd_ddt VALUES (v_ddt);
END;
$$;

SELECT is(
    (SELECT anagrafiche.fn_ba_ha_storia_emittente(t.billing_account_id)
       FROM tmp_bsd_ids t),
    false,
    '2) Un DDT in BOZZA non fa storia: senza numero non ha congelato niente');

-- =========================================================
-- 3) ⭐ E infatti la finestra di correzione e' ancora aperta
-- =========================================================
SELECT lives_ok(
    format(
        $q$SELECT anagrafiche.fn_guard_ba_cambio_emittente(%s, %s, %s)$q$,
        (SELECT billing_account_id FROM tmp_bsd_ids),
        (SELECT emittente_sr_ok    FROM tmp_bsd_refs),
        (SELECT emittente_sr_altro FROM tmp_bsd_refs)),
    '3) Con il solo DDT in bozza, il cambio di emittente passa ancora');

-- =========================================================
-- 4) Il DDT emesso prende il numero dal registro
-- =========================================================
-- ⚠️ Il verbo in un'istruzione SEPARATA dall'asserzione: la transizione SCRIVE
--   (numero, anno, registro), e mescolarla alla is() la leggerebbe nella
--   snapshot sbagliata.
UPDATE vendite.ddt d
   SET stato_doc_ddt_id = (SELECT stato_ddt_emesso_id FROM tmp_bsd_refs)
 WHERE d.id = (SELECT ddt_id FROM tmp_bsd_ddt);

SELECT ok(
    (SELECT d.numero IS NOT NULL
        AND d.registro_id IS NOT NULL
        AND d.anno = EXTRACT(YEAR FROM d.data)::smallint
       FROM vendite.ddt d
      WHERE d.id = (SELECT ddt_id FROM tmp_bsd_ddt)),
    '4) Il DDT emesso ha numero, registro e anno preso dalla DATA DOCUMENTO');

-- =========================================================
-- 5) ⭐⭐ Ora la storia lo conta, sotto la SUA famiglia
-- =========================================================
-- ⚠️ Si cerca per FAMIGLIA e non per posizione: l'ordine e' quello del
--   catalogo, e un test che pescasse «la prima riga» misurerebbe
--   l'ordinamento invece del conteggio.
SELECT is(
    (SELECT s.n_documenti
       FROM tmp_bsd_ids t,
            LATERAL anagrafiche.fn_get_storia_emittente_ba(t.billing_account_id) s
      WHERE s.famiglia_documento = 'DDT_VENDITA'),
    1::bigint,
    '5) Il DDT NUMERATO entra nella storia, sotto la famiglia DDT');

-- =========================================================
-- 6) ⛔ E ora il cambio di emittente e' respinto
-- =========================================================
SELECT throws_ok(
    format(
        $q$SELECT anagrafiche.fn_guard_ba_cambio_emittente(%s, %s, %s)$q$,
        (SELECT billing_account_id FROM tmp_bsd_ids),
        (SELECT emittente_sr_ok    FROM tmp_bsd_refs),
        (SELECT emittente_sr_altro FROM tmp_bsd_refs)),
    'P0001',
    NULL,
    '6) Con un DDT numerato a carico, il cambio di emittente e'' respinto');

-- =========================================================
-- 7) ⭐ La frase nomina la SPECIE del documento che blocca
-- =========================================================
-- Con cinque famiglie in gioco, un «non si puo'» che non dice QUALE manda a
-- cercare a mano in cinque tabelle. Le parole vengono dal catalogo.
SELECT throws_like(
    format(
        $q$SELECT anagrafiche.fn_guard_ba_cambio_emittente(%s, %s, %s)$q$,
        (SELECT billing_account_id FROM tmp_bsd_ids),
        (SELECT emittente_sr_ok    FROM tmp_bsd_refs),
        (SELECT emittente_sr_altro FROM tmp_bsd_refs)),
    '%Documento di trasporto: 1%',
    '7) La frase nomina la specie che blocca, con le parole del catalogo');

SELECT * FROM finish();
ROLLBACK;
