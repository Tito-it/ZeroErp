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
-- rev 2026-10-25 (brief-modello-documento-vendita §7, giro 5): l'emissione del DDT (test 4) con dbops.fn_pgtap_porta_a_stato, non piu' con l'UPDATE diretto dello stato che la porta ora rifiuta.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): la bolla in bozza dal builder dbops.fn_pgtap_crea_ddt_senza_ordine ('DRAFT', 5 a 10); l'emissione del test 4 resta col verbo, perche' e' il caso.
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
    m.emittente_soggetto_ruolo_id                            AS emittente_sr_ok,
    -- ⭐ L'«altro» emittente e' un emittente VERO, costruito: prima era «un
    --   soggetto_ruolo qualunque diverso da quello dell'operatore».
    (SELECT e.soggetto_ruolo_id
       FROM dbops.fn_pgtap_crea_emittente() e)               AS emittente_sr_altro
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
-- La bolla in bozza dal builder della bolla senza ordine: causale VENDITA,
-- indirizzi, una riga 5 a 10 su un articolo merce NON gestito (il caso del file
-- e' la NUMERAZIONE del DDT, non il suo movimento).
CREATE TEMP TABLE tmp_bsd_ddt AS
SELECT b.ddt_id
  FROM dbops.fn_pgtap_crea_ddt_senza_ordine('BA storia DDT', 'DRAFT',
           p_billing_account_id => (SELECT billing_account_id FROM tmp_bsd_mondo),
           p_quantita           => 5,
           p_prezzo             => 10) b;

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
-- ⭐ 2026-10-25: l'emissione passa dal verbo (porta sullo stato), non da un
--   UPDATE diretto della colonna.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', t.ddt_id, 'EMESSO')
  FROM tmp_bsd_ddt t;

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
