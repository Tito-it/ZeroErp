-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.vw_dash_competenza_gruppi — `riferimento` e `documento_id`
--       risolti da vendite.fn_get_sorgente_documento_ref
-- Brief: brief-db-riferimento-gruppi-lateral-costosa §6
-- Changeset coperti: 20260901-04
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima il
--   preventivo nasceva gia' EMESSO).
-- rev 2026-10-25 (brief-modello-documento-vendita §8, giro 6): la rev 0 si
--   emette con una riga (merce, 1 x 10) da
--   dbops.fn_pgtap_crea_preventivo_con_righe (p_preventivo_id): l'emissione
--   senza righe e' rifiutata. Le attese leggono la vista dei gruppi della
--   commessa, non le righe del preventivo: non cambiano.
-- rev 2026-10-24 (brief-modello-documento-vendita Q-4): il mondo si COSTRUISCE
--   (azienda A col suo operatore, contesto su di lui, cliente, articolo
--   servizio) invece di pescare «il primo BA / articolo / emittente per id».
-- rev 2026-10-24 (brief-modello-documento-vendita R-9): azienda, operatore,
--   contesto e cliente nascono in una chiamata da
--   dbops.fn_pgtap_crea_mondo_cliente, al posto dei tre builder atomici.
-- ------------------------------------------------------------
-- Indice test (1..6):
--  1) controllo: PRIMA della revisione riferimento = numero e documento_id = rev spinta
--  2) il caso e' stato davvero prodotto: rev 0 superata e non attiva, rev 1 esiste
--  3) ⭐ con la rev 0 SUPERATA il riferimento resta il NUMERO, non la gruppo_key
--  4) ⭐ D-1: documento_id punta alla revisione SPINTA, non alla corrente
--  5) invariante BE: riferimento e documento_id descrivono lo STESSO documento
--  6) grana: una riga sola per il gruppo, senza il LIMIT 1 a difenderla
-- ------------------------------------------------------------
-- ⭐ PERCHE' QUESTO FILE SI FABBRICA IL CASO, E NON LO CERCA.
--    Misurato il 2026-09-01 su competenza giugno (48 gruppi): le righe nel
--    caso rotto sono ZERO — nessun preventivo superato con attivita' spinte,
--    nessun DDT con causale cambiata dopo il push. Un test che confrontasse
--    la popolazione esistente sarebbe verde per SOTTRAZIONE: passerebbe
--    smettendo di verificare, e in CI — dove il database e' ricostruito da
--    zero — passerebbe a vuoto sempre.
--    ⛔ Zero occorrenze non significa che il caso non esista: significa che
--    non c'e' ancora un controesempio. Il modello lo ammette, ed e' verificato:
--    fn_crea_revisione_preventivo NON tocca commesse_attivita, e le righe di
--    commessa si ritirano solo annullando il documento (rev 2026-10-11: dal
--    verbo di annullo, dopo la conferma; prima dal ritiro automatico _z90_).
--    Quindi le attivita' spinte dalla rev 0 restano sulla rev 0.
--
-- ⭐ IL TEST 2 E' IL GEMELLO «ESISTE» dei test 3 e 4. Senza, se un giorno
--    fn_crea_revisione_preventivo smettesse di produrre la revisione, i test 3
--    e 4 resterebbero VERDI — verificherebbero un preventivo mai superato,
--    cioe' il caso facile. Un test che conta i cattivi e' muto quando il dato
--    rotto esce dal join: qui il 2 dichiara che il dato rotto c'e'.
--
-- ⚠️ IL TEST 3 ERA ROSSO PRIMA DEL 20260901-04, ed e' il motivo del cantiere.
--    La LATERAL passava da vw_dash_fatturazione_preventivi, che filtra
--    `WHERE p.is_attiva` (= NOT is_abortito AND NOT is_superata): una rev
--    superata cadeva fuori e `riferimento` ripiegava.
--    ⚠️ E ripiegava sul CODICE COMMESSA, non sulla gruppo_key: commesse.codice
--    e' NOT NULL e commesse_attivita.commessa_id pure, quindi il primo ramo del
--    COALESCE c'e' sempre e la gruppo_key e' irraggiungibile. E' la forma
--    PEGGIORE del difetto — una chiave grezza si vede che e' rotta, un codice
--    commessa sembra un valore legittimo, e la riga NOMINA UN OGGETTO DIVERSO
--    da quello di cui parla. Verificato: risoluzione vecchia su questa stessa
--    fixture -> riferimento = CMM-…, documento_id = NULL (quindi niente
--    azione «apri», e la ricerca per numero non trova la riga).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⭐ rev 2026-10-24 (Q-4): l'azienda e il suo operatore si costruiscono PRIMA
--   del contesto, e il contesto si apre su di lui: la vista legge nel suo
--   perimetro, e il cliente che nasce dopo il trigger z90 lo lega a lei.
-- rev 2026-10-24 (R-9): il mondo del builder fa i tre passi nell'ordine giusto.
CREATE TEMP TABLE tmp_rif_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('vista gruppi riferimento');

-- Il contesto l'ha gia' aperto il mondo sul suo operatore: la riga lo rende
-- esplicito (ed e' cio' che legge scripts/guardrail_pgtap_preambolo.py).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_rif_mondo)); END $ctx$;

SELECT plan(6);

CREATE TEMP TABLE tmp_rif_cli AS
SELECT billing_account_id, istanza_utility_id, utility_id FROM tmp_rif_mondo;

-- ============================================================
-- Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_rif_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_rif_cli)      AS billing_account_id,
  (SELECT utility_id FROM tmp_rif_cli)              AS utility_id,
  (SELECT istanza_utility_id FROM tmp_rif_cli)      AS istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGT-VGRIF-SERV', false,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                               WHERE codice_interno = 'SERVIZIO_UNA_TANTUM')) AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT emittente_fiscale_id FROM tmp_rif_mondo) AS emittente_fiscale_id,
  -- ⚠️ EMESSO e non ACCETTATO: fn_crea_revisione_preventivo ammette la
  --   revisione SOLO da EMESSO (E_PREV_REVISIONE_STATO_NON_AMMESSO). Il
  --   preventivo si porta nello stato da cui si revisiona (rev 2026-10-24:
  --   nasce in bozza e ci arriva con dbops.fn_pgtap_porta_a_stato).
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'EMESSO' AND s.attivo IS TRUE LIMIT 1) AS stato_prev_emesso_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
      AND EXISTS (SELECT 1 FROM vendite.tipi_doc_fiscale_registri m WHERE m.tipo_doc_fiscale_id = t.id)
    ORDER BY t.id LIMIT 1)                          AS tipo_doc_fiscale_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO' LIMIT 1) AS src_preventivo_id;

-- ---------- la revisione 0: quella da cui si spinge ----------
CREATE TEMP TABLE tmp_rif_prev0 AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-VGRIF', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2082-01-01', DATE '2082-12-31', r.valuta_id,
         DATE '2082-01-01', false, false,
         jsonb_build_object('test_scope', 'pgtap_vgrif'), r.emittente_fiscale_id
  FROM tmp_rif_refs r
  RETURNING id, uid, numero)
SELECT * FROM ins;

-- ⚠️ rev 2026-10-24: nato in bozza, va a EMESSO sotto i guard veri.
-- ⚠️ rev 2026-10-25 (§8, giro 6): con una riga (merce, 1 x 10) scritta in
--   bozza da dbops.fn_pgtap_crea_preventivo_con_righe, che poi porta lo stato:
--   senza righe l'emissione e' rifiutata (E_PREV_NESSUNA_RIGA_ATTIVA).
DO $porta$ BEGIN
  PERFORM dbops.fn_pgtap_crea_preventivo_con_righe('vgrif', 'EMESSO',
            p_preventivo_id => (SELECT id FROM tmp_rif_prev0));
END $porta$;

CREATE TEMP TABLE tmp_rif_comm AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_rif_refs),
  p_utility_id => (SELECT utility_id FROM tmp_rif_refs),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2082-01-01',
  p_competenza_al => DATE '2082-01-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_vgrif'),
  p_force_new => true
) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_id FROM tmp_rif_comm),
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_rif_refs),
  p_sorgente_uid     => (SELECT uid::text FROM tmp_rif_prev0),
  p_meta             => jsonb_build_object('test_scope', 'pgtap_vgrif')
);

-- ---------- il push: l'attivita' porta l'uid della REV 0 ----------
CREATE TEMP TABLE tmp_rif_att AS
SELECT * FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_rif_comm),
  p_segment_key => 'SEG-VGRIF-1'::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_rif_refs),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_rif_refs),
  p_data_attivita => DATE '2082-01-15',
  p_uom_id => (SELECT uom_id FROM tmp_rif_refs),
  p_quantita => 1.000000,
  p_competenza_mese => DATE '2082-01-01',
  p_competenza_dal => DATE '2082-01-01',
  p_competenza_al => DATE '2082-01-31',
  p_prezzo_snapshot => 100.00,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_rif_refs),
  p_valuta_id => (SELECT valuta_id FROM tmp_rif_refs),
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_rif_refs),
  p_sorgente_uid => (SELECT uid::text FROM tmp_rif_prev0),
  p_tipo_movimento => 'NORMALE',
  p_meta => jsonb_build_object('test_scope', 'pgtap_vgrif')
);

-- ============================================================
-- TEST 1 — controllo, PRIMA della revisione.
--   Serve a non far passare i test 3 e 4 «perche' funziona sempre»: se gia'
--   qui il riferimento fosse sbagliato, il caso della revisione non
--   proverebbe niente.
-- ============================================================
SELECT is(
  (SELECT ARRAY[g.riferimento::text, g.documento_id::text]
     FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.commessa_id = (SELECT commessa_id FROM tmp_rif_comm)
      AND g.tipo_gruppo = 'PREVENTIVO'),
  ARRAY[(SELECT numero::text FROM tmp_rif_prev0),
        (SELECT id::text     FROM tmp_rif_prev0)],
  '1) controllo: prima della revisione riferimento = numero e documento_id = rev spinta'
);

-- ---------- si crea la revisione: la rev 0 diventa SUPERATA ----------
CREATE TEMP TABLE tmp_rif_prev1 AS
SELECT * FROM vendite.fn_crea_revisione_preventivo(
  (SELECT id FROM tmp_rif_prev0), 'pgtap: revisione dopo il push');

-- ============================================================
-- TEST 2 — il gemello «esiste»: il caso rotto e' stato prodotto davvero.
--   ⛔ Senza questo, i test 3 e 4 sarebbero verdi anche se la revisione non
--      fosse mai avvenuta — verificherebbero il caso facile.
-- ============================================================
SELECT is(
  (SELECT ARRAY[v.is_superata::text, v.is_attiva::text,
                (SELECT (nuovo_preventivo_id <> (SELECT id FROM tmp_rif_prev0))::text
                   FROM tmp_rif_prev1)]
     FROM vendite.vw_preventivi v
    WHERE v.id = (SELECT id FROM tmp_rif_prev0)),
  ARRAY['true', 'false', 'true'],
  '2) il caso e prodotto: rev 0 superata e non attiva, rev 1 e un documento diverso'
);

-- ============================================================
-- TEST 3 ⭐ — IL DIFETTO. Con la rev 0 superata, il riferimento deve restare
--   il NUMERO del documento. Prima del 20260901-04 qui usciva il CODICE
--   COMMESSA, perche' vw_dash_fatturazione_preventivi filtra `WHERE p.is_attiva`
--   e la rev superata cadeva fuori dalla LATERAL.
--   ⚠️ L'asserzione e' sul numero ATTESO e non su «diverso dalla gruppo_key»:
--   un test scritto in negativo sarebbe passato anche col codice commessa.
-- ============================================================
SELECT is(
  (SELECT g.riferimento::text
     FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.commessa_id = (SELECT commessa_id FROM tmp_rif_comm)
      AND g.tipo_gruppo = 'PREVENTIVO'),
  (SELECT numero::text FROM tmp_rif_prev0),
  '3) rev superata: riferimento resta il numero del documento, non il codice commessa'
);

-- ============================================================
-- TEST 4 ⭐ — DECISIONE D-1. `documento_id` punta alla revisione SPINTA, non
--   alla corrente: e' quella da cui vengono quantita' e prezzi che si stanno
--   per fatturare, e aprire la corrente mostrerebbe righe diverse da quelle
--   che finiranno in fattura senza dirlo.
--   ⚠️ Il NUMERO non distingue le revisioni (label_selector = `numero`, che e'
--      condiviso): senza questo test la scelta non sarebbe presidiata da
--      nessuna parte, perche' il test 3 passerebbe con entrambe.
-- ============================================================
SELECT is(
  (SELECT g.documento_id
     FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.commessa_id = (SELECT commessa_id FROM tmp_rif_comm)
      AND g.tipo_gruppo = 'PREVENTIVO'),
  (SELECT id FROM tmp_rif_prev0),
  '4) D-1: documento_id e la revisione SPINTA (rev 0), non la corrente (rev 1)'
);

-- ============================================================
-- TEST 5 — l'invariante che il BE dichiara: «codice e id non possono
--   descrivere documenti diversi». Si verifica dal PERCORSO: si rilegge il
--   numero DAL documento puntato da documento_id, e deve coincidere con
--   riferimento.
-- ============================================================
SELECT is(
  (SELECT p.numero::text
     FROM vendite.vw_dash_competenza_gruppi g
     JOIN vendite.preventivi p ON p.id = g.documento_id
    WHERE g.commessa_id = (SELECT commessa_id FROM tmp_rif_comm)
      AND g.tipo_gruppo = 'PREVENTIVO'),
  (SELECT g.riferimento::text
     FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.commessa_id = (SELECT commessa_id FROM tmp_rif_comm)
      AND g.tipo_gruppo = 'PREVENTIVO'),
  '5) riferimento e documento_id descrivono lo STESSO documento'
);

-- ============================================================
-- TEST 6 — la grana, senza il LIMIT 1 a difenderla.
--   La LATERAL vecchia aveva `ORDER BY … LIMIT 1` perche'
--   vw_dash_fatturazione_documenti NON e' unica per documento: era
--   de-duplicazione forzata. Tolto il LIMIT, la riga unica deve venire dalla
--   COSTRUZIONE — un solo documento per (sorgente_tipo, sorgente_uid).
--   ⚠️ Un fan-out qui moltiplicherebbe conteggio e totali, e il «seleziona
--      tutto» manderebbe doppioni a fatturare.
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.commessa_id = (SELECT commessa_id FROM tmp_rif_comm)
      AND g.tipo_gruppo = 'PREVENTIVO'),
  1,
  '6) una riga sola per il gruppo: la grana non dipende piu da un LIMIT 1'
);

SELECT * FROM finish();
ROLLBACK;
