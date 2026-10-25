-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): i resi dal builder dbops.fn_pgtap_crea_reso (quello sulla riga a mano con p_ddt_riga_id: la riga d'ordine resta NULL perche' non c'e' legame); resta scritto a mano il legame resi_righe_riconsegne verso la bolla in bozza (il caso del 7).
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; restano scritti a mano la riga aggiunta alla bolla in bozza (il caso del 4/5/11) e i resi (giro 2).
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: vendite.vw_partite_merce — la partita di merce
--       (brief-design-partita-merce-generalizzata, slice S2, changeSet 20260817-07).
--
-- Elenco test (plan 11):
--   1) la vista esiste
--   2) e' security_invoker=on (RLS su vendite.ddt e, via S1, commesse_attivita)
--   3) espone le colonne del contratto (21: + e_riconsegna, + sospetto_duplicato_ordine)
--   4) ⭐ una riga di DDT SENZA ordine a monte ha una partita, origine NESSUNA
--   5) ⭐ un reso su quella merce senza origine produce DA_ACCREDITARE
--   6) un DDT in BOZZA non ha partite (decisione D1)
--   7) `in_riconsegna`: la merce resa e gia' impegnata su un DDT non emesso
--      si legge, invece di sparire
--   8) causale NON fatturabile e nessun fatturato -> NON_FATTURABILE con
--      differenza NULL, non zero
--   9) causale NON fatturabile MA con fatturato -> il conto si applica lo stesso
--  10) ⭐ corsia ORD: la capienza dell'allocazione e' il CONSEGNATO, non i
--      tenuti — un reso NON riassorbe l'accredito
--  11) ⭐ `sospetto_duplicato_ordine`: la riga a mano con un articolo GIA'
--      nell'ordine e' segnalata; quella che l'ordine lo evade davvero no
--
-- Scopo:
--  - il 4) e il 5) sono il cantiere in due righe: fino a oggi la merce senza
--    riga d'ordine non compariva a conto zero, NON ESISTEVA, e un reso su di
--    essa si registrava senza produrre alcun accredito.
--  - il 10) presidia la decisione piu' facile da rovinare. Se la capienza
--    diventasse `tenuti`, un reso libererebbe capienza, l'accredito verrebbe
--    riassorbito e la coda accrediti resterebbe VUOTA — cioe' il difetto
--    contro cui mette in guardia il §2 del brief nota di credito. Il test
--    fallisce con `differenza = 0` invece di −4: un valore innocuo all'occhio,
--    ed e' proprio per questo che serve un test a dirlo.
--  - l' 8) e il 9) sono la stessa colonna letta nei due versi: la causale dice
--    cosa ci si aspetta dal VIAGGIO, non se la merce e' stata fatturata.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE. Senza, un fallimento a meta' lascia i dati di prova nel
--   database e rompe la corsa successiva, che vede un rosso non suo.
BEGIN;

-- ⚠️ 2. VINCOLI DIFFERITI. Scattano al COMMIT, e qui il COMMIT non arriva mai:
--   senza questa riga il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- ⚠️ 3. CONTESTO APPLICATIVO. Il test gira come `zeroerp_app` con la RLS
--   ATTIVA (vendite.ddt e vendite.ordini hanno policy sull'emittente).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(11);

SET LOCAL app.ruolo_applicativo = 'OPERATORE';
-- ⛔ rev 2026-10-13: niente app.current_user_id = '1' (in CI l'utente 1 non
--   esiste): l'operatore e' quello del contesto aperto qui sopra.

-- ============================================================
-- 1-3) Struttura della vista
-- ============================================================
SELECT has_view('vendite', 'vw_partite_merce', '1) la vista esiste');

-- ⚠️ SI LEGGE LA PROPRIETA', NON LA PAROLA (rev 2026-09-07). `security_invoker`
--   e' una reloption BOOLEANA: `on` e `true` sono lo stesso identico valore, e
--   PostgreSQL conserva quello che ha ricevuto. Un confronto sulla stringa
--   diventa rosso su una vista SANA riscritta con l'altra parola — successo il
--   2026-09-07 su due presidi gemelli, con due falsi allarmi e una bisezione fra
--   cantieri per scoprire che non era rotto niente. `::boolean` usa il parser di
--   PostgreSQL, quindi non c'e' nessun elenco di grafie da tenere allineato.
-- ⭐ Questa resta una PRECONDIZIONE del file, non un doppione: le asserzioni qui
--   sotto interrogano la vista dal contesto operatore, e senza il flag
--   verificherebbero un perimetro che non e' quello di nessuno. Il presidio
--   GLOBALE, su tutte le viste che toccano dati in RLS, e'
--   db/pgtap/rls/test-rls-viste-security-invoker.sql.
SELECT ok(
  (SELECT COALESCE(o.option_value::boolean, false)
     FROM pg_class c
     JOIN pg_namespace n ON n.oid = c.relnamespace
     LEFT JOIN LATERAL pg_options_to_table(c.reloptions) o
            ON o.option_name = 'security_invoker'
    WHERE n.nspname = 'vendite' AND c.relname = 'vw_partite_merce'),
  '2) vw_partite_merce gira col perimetro di chi legge (security_invoker)');

-- ⚠️ `columns_are` e' un contratto, non una fotografia: fallisce anche se una
--    colonna SPARISCE, che e' il motivo per cui esiste. Chi ne aggiunge una
--    aggiorna QUI, dichiarando cosa porta.
--    rev 2026-08-18 (brief-design-note-credito-resi N6/N7): due colonne nuove,
--    entrambe in coda perche' un CREATE OR REPLACE VIEW non ne inserisce in
--    mezzo — `rettificato` (quanto una nota di credito ha tolto al fatturato
--    della partita, negativo o zero) e `riconsegna_quota_nuova` (i pezzi
--    accreditati che hanno cambiato casa verso una spedizione di ri-consegna).
SELECT columns_are('vendite', 'vw_partite_merce',
  ARRAY['ddt_riga_id','ddt_id','ddt_uid','articolo_id','is_composito',
        'ordine_riga_id','ordine_id','origine','fatturabile','consegnato',
        'reso','in_riconsegna','tenuti','fatturato_merce','fatturato_da_ordine',
        'fatturato','misurabile','differenza','stato','e_riconsegna',
        'sospetto_duplicato_ordine','rettificato','riconsegna_quota_nuova'],
  '3) espone le 23 colonne del contratto della partita');

-- ============================================================
-- Riferimenti minimi
-- ============================================================
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti): cliente fatturabile legato all'azienda di chi agisce,
--   articolo merce non gestito a magazzino (il test non misura il magazzino).
--   Dal DB si legge solo il seed.
CREATE TEMP TABLE tmp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP partite merce');
CREATE TEMP TABLE tmp_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-PMV-V1', false) AS id;

CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT m.billing_account_id FROM tmp_mondo m)                         AS billing_account_id,
  (SELECT m.utility_id FROM tmp_mondo m)                                 AS utility_id,
  (SELECT m.istanza_utility_id FROM tmp_mondo m)                         AS istanza_utility_id,
  (SELECT t.id FROM tmp_art t)                                           AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA' AND s.attivo LIMIT 1)        AS sorgente_root_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id;

-- Le partite nascono dal builder della bolla da ordine, col cliente del mondo e
-- lo stesso articolo (l'11 confronta la riga a mano con quella dell'ordine);
-- trigger SPEDITO come gli ordini del file.
-- Helper: aggiunge una riga A MANO a un DDT esistente. Nessun fulfillment:
-- e' esattamente la riga che oggi non appartiene a nessuna partita.
-- ⚠️ Solo su una bolla in BOZZA (rev 2026-09-22): fuori bozza le righe non si
--   scrivono (trgfn_doc_righe_lock_fuori_bozza). Il P1 la chiede DRAFT e la
--   porta avanti dopo.
CREATE OR REPLACE FUNCTION pg_temp.mk_riga_manuale(p_ddt bigint, p_qta numeric)
RETURNS bigint AS $$
DECLARE r RECORD; v_id bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (p_ddt, 900, r.articolo_id, 'Riga aggiunta a mano', p_qta, p_qta, 25, r.iva_id,
          true, false, jsonb_build_object('test_scope','pgtap_partite'))
  RETURNING id INTO v_id;
  RETURN v_id;
END $$ LANGUAGE plpgsql;

-- Commessa + ROOT per gli AF.
CREATE TEMP TABLE tmp_com AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO', p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false, p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-08-01', p_competenza_al => DATE '2026-08-31',
  p_meta => jsonb_build_object('test_scope','pgtap_partite'), p_force_new => true
) AS commessa_id;
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_com),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs),
  p_sorgente_uid => (SELECT commessa_id FROM tmp_com)::text,
  p_sorgente_riga => 1, p_meta => '{}'::jsonb);

CREATE OR REPLACE FUNCTION pg_temp.mk_af(p_segment varchar, p_qta numeric)
RETURNS void AS $$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com),
    -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
    p_sorgente_uid => ((SELECT commessa_id FROM tmp_com))::text,
    p_segment_key => p_segment, p_articolo_id => r.articolo_id,
    p_istanza_utility_id => r.istanza_utility_id, p_data_attivita => DATE '2026-08-15',
    p_uom_id => r.uom_id, p_quantita => p_qta,
    p_competenza_mese => DATE '2026-08-01',
    p_competenza_dal => DATE '2026-08-01', p_competenza_al => DATE '2026-08-31',
    p_prezzo_snapshot => 10.0, p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
    p_tipo_variazione_applicata => NULL, p_valore_variazione_applicata => NULL,
    p_promo_id => NULL, p_contratto_id => NULL,
    p_categoria_cliente_id_snapshot => NULL, p_classe_utenza_id_snapshot => NULL,
    p_tipo_doc_fiscale_id => r.tipo_doc_fiscale_id,
    p_stato_approvazione => 'APPROVATA', p_stato_emissione => 'NON_EMESSA',
    p_tipo_movimento => 'NORMALE', p_meta => '{}'::jsonb,
    p_causale_onere_id => NULL);
END $$ LANGUAGE plpgsql;

-- ============================================================
-- Le partite del test
-- ============================================================

-- P1 — ordine 10, consegnato, fatturato sulla CORSIA ORD, poi reso 4.
--      Serve al 10): la capienza dell'allocazione.
CREATE TEMP TABLE tmp_p1 AS
SELECT b.*, NULL::bigint AS riga_manuale_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('partite P1', 'DRAFT',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs), p_quantita => 10,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'SPEDITO') b;

-- P2 — riga aggiunta A MANO sul DDT di P1 (spedizione mista), fatturata sulla
--      corsia DDT, poi resa 2. Serve al 4) e al 5). Entra in bozza, poi la
--      bolla va a CONSEGNATO.
UPDATE tmp_p1 SET riga_manuale_id = pg_temp.mk_riga_manuale(ddt_id, 6);
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT ddt_id FROM tmp_p1), 'CONSEGNATO');
CREATE TEMP TABLE tmp_p2 AS SELECT riga_manuale_id AS ddt_riga_id FROM tmp_p1;

-- P3 — ordine 5, DDT lasciato in BOZZA. Serve al 6) e, come destinazione della
--      ri-consegna, al 7).
CREATE TEMP TABLE tmp_p3 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('partite P3', 'DRAFT',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs), p_quantita => 5,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'SPEDITO');

-- P4 — causale NON fatturabile, nessun fatturato. Serve all' 8).
CREATE TEMP TABLE tmp_p4 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('partite P4',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs), p_quantita => 4,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'SPEDITO',
         p_causale_codice => 'CONTO_VISIONE');

-- P5 — causale NON fatturabile, ma l'ordine e' stato fatturato lo stesso
--      (corsia ORD). Serve al 9).
CREATE TEMP TABLE tmp_p5 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('partite P5',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs), p_quantita => 3,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'SPEDITO',
         p_causale_codice => 'CONTO_VISIONE');

-- Le attivita': P1 sulla corsia ORD, P2 sulla corsia DDT, P5 sulla corsia ORD.
SELECT pg_temp.mk_af(script.fn_segment_key('ORDINE_VENDITA', (SELECT ordine_uid FROM tmp_p1)::text, (SELECT ordine_riga_id FROM tmp_p1)), 10);
SELECT pg_temp.mk_af(script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_p1)::text, (SELECT ddt_riga_id FROM tmp_p2)), 6);
SELECT pg_temp.mk_af(script.fn_segment_key('ORDINE_VENDITA', (SELECT ordine_uid FROM tmp_p5)::text, (SELECT ordine_riga_id FROM tmp_p5)), 3);

SELECT vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_com), 'PRONTA_FATTURAZIONE');
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com));

-- I resi, confermati: 4 su P1 (a credito), 2 sulla riga manuale P2 (a
-- credito). La riga d'ordine il builder la ricava dal legame: sulla riga
-- manuale resta NULL, ed e' il punto.
CREATE TEMP TABLE tmp_reso_p1 AS
SELECT * FROM dbops.fn_pgtap_crea_reso('partite P1', (SELECT ddt_id FROM tmp_p1), 4,
         p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_p1));
CREATE TEMP TABLE tmp_reso_p2 AS
SELECT * FROM dbops.fn_pgtap_crea_reso('partite P2', (SELECT ddt_id FROM tmp_p1), 2,
         p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_p2));

-- ============================================================
-- 4-5) La merce senza origine: il buco che questo cantiere chiude
-- ============================================================
SELECT is(
  (SELECT origine::text FROM vendite.vw_partite_merce
    WHERE ddt_riga_id = (SELECT ddt_riga_id FROM tmp_p2)),
  'NESSUNA',
  '4) una riga di DDT aggiunta a mano HA una partita, con origine NESSUNA');

SELECT is(
  (SELECT differenza FROM vendite.vw_partite_merce
    WHERE ddt_riga_id = (SELECT ddt_riga_id FROM tmp_p2)),
  -2::numeric,
  '5) reso 2 su merce senza origine, fatturata 6 di 6: differenza −2 (accredito calcolabile)');

-- ============================================================
-- 6) La bozza non e' merce uscita (decisione D1)
-- ============================================================
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.vw_partite_merce
    WHERE ddt_id = (SELECT ddt_id FROM tmp_p3)),
  0,
  '6) un DDT in BOZZA non produce partite: la merce non e'' uscita dal magazzino');

-- ============================================================
-- 7) in_riconsegna: la merce impegnata su un DDT non emesso si LEGGE
--    Reso per ri-consegna su P4, agganciato alla riga del DDT in bozza di P3.
--    Senza questa colonna quei pezzi non sarebbero ne' dal cliente ne' in coda.
-- ============================================================
CREATE TEMP TABLE tmp_reso_p4 AS
SELECT * FROM dbops.fn_pgtap_crea_reso('partite P4', (SELECT ddt_id FROM tmp_p4), 2,
         'RESO_PER_RICONSEGNA');
-- Il legame a mano verso la bolla in BOZZA di P3: e' il caso del 7 (la madre
-- della ri-consegna farebbe una bolla sua).
INSERT INTO vendite.resi_righe_riconsegne (resi_riga_id, ddt_riga_id, qta, storicizza)
SELECT r.resi_riga_id, (SELECT ddt_riga_id FROM tmp_p3), 2, false
  FROM tmp_reso_p4 r;

SELECT is(
  (SELECT in_riconsegna FROM vendite.vw_partite_merce
    WHERE ddt_riga_id = (SELECT ddt_riga_id FROM tmp_p4)),
  2::numeric,
  '7) in_riconsegna = 2: merce resa e gia'' impegnata su un DDT non emesso');

-- ============================================================
-- 8-9) La causale non fatturabile, letta nei due versi
-- ============================================================
SELECT ok(
  (SELECT stato = 'NON_FATTURABILE' AND differenza IS NULL
     FROM vendite.vw_partite_merce WHERE ddt_riga_id = (SELECT ddt_riga_id FROM tmp_p4)),
  '8) causale non fatturabile e nessun fatturato: NON_FATTURABILE, differenza NULL (non 0)');

SELECT ok(
  (SELECT stato <> 'NON_FATTURABILE' AND differenza IS NOT NULL
     FROM vendite.vw_partite_merce WHERE ddt_riga_id = (SELECT ddt_riga_id FROM tmp_p5)),
  '9) causale non fatturabile MA fatturato dall''ordine: il conto si applica lo stesso');

-- ============================================================
-- 10) ⭐ La capienza dell'allocazione e' il CONSEGNATO, non i tenuti.
--     P1: consegnato 10, fatturato ORD 10, reso 4 -> tenuti 6, differenza −4.
--     Con capienza = tenuti si allocherebbe 6 e la differenza sarebbe 0:
--     l'accredito sparirebbe, e la coda accrediti resterebbe vuota.
-- ============================================================
SELECT is(
  (SELECT differenza FROM vendite.vw_partite_merce
    WHERE ddt_riga_id = (SELECT ddt_riga_id FROM tmp_p1)),
  -4::numeric,
  '10) capienza = consegnato: reso 4 su 10 fatturati -> differenza −4, l''accredito RESTA');

-- ============================================================
-- 11) ⭐ L'avviso sulla riga manuale sospetta (S6b).
--     P2 è una riga aggiunta a mano sul DDT di P1, con lo STESSO articolo che
--     l'ordine di P1 sta evadendo: è il caso che l'operatore non distingue da
--     una svista. P1 evade l'ordine davvero e non va segnalata.
--
--     ⚠️ È una LETTURA, non un divieto: la riga si è inserita senza ostacoli
--     (l'ha fatto la fixture). Il caso legittimo esiste — merce extra dello
--     stesso codice — e vietarlo costerebbe due documenti di trasporto per un
--     solo viaggio.
-- ============================================================
SELECT results_eq(
  $q$SELECT (SELECT sospetto_duplicato_ordine FROM vendite.vw_partite_merce
               WHERE ddt_riga_id = (SELECT ddt_riga_id FROM tmp_p2)),
            (SELECT sospetto_duplicato_ordine FROM vendite.vw_partite_merce
               WHERE ddt_riga_id = (SELECT ddt_riga_id FROM tmp_p1))$q$,
  $q$VALUES (true, false)$q$,
  '11) la riga a mano con articolo gia'' nell''ordine e'' segnalata, quella che lo evade no');

SELECT * FROM finish();
ROLLBACK;
