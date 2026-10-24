-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2e): le chiavi del push col codice della sorgente (PREVENTIVO:, DDT_VENDITA:, ORDINE_VENDITA:, CONTRATTO:, ATTIVITA_CONSUMI:), stessa forma di script.fn_segment_key carattere per carattere.
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2b, 20261019-87 … -99):
--   la destinazione della merce e' ORDINE_VENDITA, il codice della sorgente (era ORDINE).
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): preventivo e cliente dal builder dbops.fn_pgtap_crea_preventivo, la commessa da dbops.fn_pgtap_crea_commessa sul cliente del preventivo; prima billing account ed emittente erano «i primi per id» del database, che su uno scratch ricostruito non ci sono.
-- rev 2026-10-24 (brief-modello-documento-vendita §4-octies): le due attivita' (EMESSA della riga servizio, NON_EMESSA della residua) le scrive dbops.fn_pgtap_crea_commessa_attivita con la sorgente, invece degli INSERT con la chiave composta a mano; il ritiro del 6b la trova per id, non per la chiave riscritta; uom, tipo documento e valuta non si pescano piu' (articolo e madre).
-- pgTAP test per Zero ERP
--
-- Test: viste smistamento preventivi (20260612-05):
--       vw_preventivi_smistamento_righe (stato_smistamento autorevole,
--       natura/destinazione, ramo ordine) + vw_preventivi_smistamento
--       (contatori per ramo). Brief: brief-db-smistamento-preventivi.md B.
--       Fixture: preventivo misto ACCETTATO con 4 righe:
--         merce (push reale a ordine), servizio EMESSO in commessa,
--         servizio residuo, natura NULL (pregresso -> COMMESSA).
--
-- Indice test (0..8):
--   0) Precondizioni (refs + nature)
--   1) Vista righe: 4 righe per il preventivo
--   2) Riga merce -> A_ORDINE, destinazione ORDINE, ordine_id/numero valorizzati
--   3) Riga servizio EMESSA -> IN_COMMESSA
--   4) Riga servizio residua -> RESIDUA
--   5) Riga natura NULL -> destinazione COMMESSA (pregresso), RESIDUA
--   6) Allineamento predicato col classificatore unico (rev 2026-10-12,
--      20261012-11, brief-db-annullo-a-valle-riapre-a-monte D-5): una ca
--      NON_EMESSA porta la riga IN_COMMESSA (6a); ritirata (ANNULLATA) la
--      riga torna RESIDUA (6b). Prima il test fissava «NON_EMESSA non conta»,
--      cioe' l'allineamento a un predicato che la vista smistabili non ha piu'
--      dal 2026-06-28.
--   7) Aggregata: contatori per ramo corretti
--   8) Aggregata: righe_residue = 2 (progress X/Y -> EVASO)
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- ============================================================
-- 0) Riferimenti minimi + classificazione nature
-- ============================================================
-- ⭐ rev 2026-10-24 (Q-2/Q-4): il preventivo nasce qui, in bozza, dal builder
--   (azienda dell'operatore, cliente e testata costruiti); i riferimenti ne
--   leggono il cliente. ⛔ Cio' che il builder scrive si legge in
--   un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_vs_b AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('vw smistamento');

CREATE TEMP TABLE tmp_vs_refs AS
SELECT
  b.billing_account_id,
  b.utility_id,
  b.istanza_utility_id,
  -- ⛔ rev 2026-10-13: i due articoli si COSTRUISCONO. Prima erano «i primi
  --   due per id» del catalogo, e la natura gli veniva cambiata qui sotto:
  --   se il primo e' un onere, dal 20261013-05 il guard
  --   E_ARTICOLO_ONERE_NATURA_MERCE (giustamente) rifiuta la MERCE e il file
  --   muore nella fixture. Un articolo costruito ha solo le proprieta' che il
  --   test gli da', e la natura la riceve alla nascita.
  dbops.fn_pgtap_crea_articolo('PGT-VS-MERCE', true,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                               WHERE codice_interno = 'MERCE'))               AS art_merce_id,
  dbops.fn_pgtap_crea_articolo('PGT-VS-SERV', false,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                               WHERE codice_interno = 'SERVIZIO_UNA_TANTUM')) AS art_serv_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1) AS stato_accettato_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE) AS stato_bozza_id,
  b.emittente_fiscale_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE') AS natura_merce_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'SERVIZIO_UNA_TANTUM') AS natura_serv_id
FROM tmp_vs_b b;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND art_merce_id IS NOT NULL
      AND art_serv_id IS NOT NULL AND stato_accettato_id IS NOT NULL
      AND natura_merce_id IS NOT NULL AND natura_serv_id IS NOT NULL
     FROM tmp_vs_refs),
  '0. Precondizioni soddisfatte'
);

-- Preventivo MISTO ACCETTATO: merce + servizio (da emettere) + servizio
-- residuo + riga natura NULL (pregresso).
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT, prende le quattro righe (e la natura NULL), poi passa ad ACCETTATO con dbops.fn_pgtap_porta_a_stato prima del push — fuori bozza le righe non si scrivono piu' (20261008-91).
CREATE TEMP TABLE tmp_vs_prev AS
SELECT b.preventivo_id AS id, b.preventivo_uid AS uid FROM tmp_vs_b b;

CREATE TEMP TABLE tmp_vs_riga_merce AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_merce_id, 1.000000, 50.000000, r.iva_id, true
    FROM tmp_vs_prev p, tmp_vs_refs r
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_vs_riga_serv_emessa AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 2.000000, 30.000000, r.iva_id, true
    FROM tmp_vs_prev p, tmp_vs_refs r
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_vs_riga_serv_residua AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 3.000000, 10.000000, r.iva_id, true
    FROM tmp_vs_prev p, tmp_vs_refs r
  RETURNING id)
SELECT * FROM ins;

-- Riga "legacy" a natura NULL (serve l'override del lock di colonna, vedi sotto).
CREATE TEMP TABLE tmp_vs_riga_null AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 1.000000, 15.000000, r.iva_id, true
    FROM tmp_vs_prev p, tmp_vs_refs r
  RETURNING id)
SELECT * FROM ins;
-- ⚠️ La natura NON si azzera piu' con un UPDATE diretto: dal 2026-08-21
--   `natura_vendita_id` e' protetta dal lock di colonna
--   `trg_preventivi_righe_a10_lock_columns_upd`
--   (E_PREV_RIGA_NATURA_IMMUTABILE), perche' scriverla a mano staccava la riga
--   dalla classificazione dell'articolo e aggirava il guard MODALITA' A.
--
--   La riga a natura NULL resta pero' uno stato REALE e da verificare: sono le
--   righe legacy nate prima del trigger di ereditarieta' (45 su 197 nel DB di
--   sviluppo al 2026-08-21). Non e' piu' riproducibile passando dall'articolo,
--   perche' `catalogo.articoli.natura_vendita_id` e' NOT NULL: nessun articolo
--   puo' avere natura nulla da cui ereditarla.
--
--   Si usa quindi la porta di manutenzione che `script.trgfn_lock_columns`
--   prevede apposta, e la si RICHIUDE subito: lasciarla aperta renderebbe
--   verdi per sottrazione tutte le asserzioni successive che toccano colonne
--   lockate.
SET LOCAL zeroerp.allow_lock_columns_override = 'on';
UPDATE vendite.preventivi_righe SET natura_vendita_id = NULL
 WHERE id = (SELECT id FROM tmp_vs_riga_null);
SET LOCAL zeroerp.allow_lock_columns_override = 'off';
DO $porta$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_vs_prev), 'ACCETTATO'); END $porta$;

-- Push reale del ramo merce: crea ordine + riga ordine (A_ORDINE).
SELECT vendite.fn_push_preventivo_a_ordine((SELECT id FROM tmp_vs_prev));

-- Ramo commessa: servizio "emesso" (commessa + attivita EMESSA).
-- ⭐ rev 2026-10-24 (Q-2): la commessa dal builder, sul cliente del preventivo
--   e nello stato iniziale (la madre del dominio la apre); l'emittente e'
--   quello dell'azienda del mondo. Le attivita' sono il caso del test: le
--   scrive il builder con la sorgente (rev §4-octies), lo stato lo dichiara.
CREATE TEMP TABLE tmp_vs_commessa AS
SELECT c.commessa_id AS id
  FROM dbops.fn_pgtap_crea_commessa('vw smistamento', NULL,
                                    (SELECT billing_account_id FROM tmp_vs_refs)) c;

CREATE TEMP TABLE tmp_vs_att_emessa AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_vs_commessa),
    p_prezzo_snapshot    => 30.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_vs_refs),
    p_sorgente_codice    => 'PREVENTIVO',
    p_sorgente_uid       => (SELECT uid::text FROM tmp_vs_prev),
    p_sorgente_riga_id   => (SELECT id FROM tmp_vs_riga_serv_emessa),
    p_quantita           => 2,
    p_stato_approvazione => 'BOZZA',
    p_stato_emissione    => 'EMESSA',
    p_competenza_dal     => DATE '2080-01-01',
    p_competenza_al      => DATE '2080-12-31');

-- ============================================================
-- 1) Vista righe: 4 righe per il preventivo
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_preventivi_smistamento_righe v
    WHERE v.preventivo_id = (SELECT id FROM tmp_vs_prev)),
  4,
  '1. Vista righe: 4 righe attive esposte'
);

-- ============================================================
-- 2) Riga merce -> A_ORDINE con riferimenti ordine
-- ============================================================
SELECT ok(
  (SELECT v.stato_smistamento = 'A_ORDINE'
      AND v.destinazione_tipo = 'ORDINE_VENDITA'
      AND v.ordine_riga_id IS NOT NULL
      AND v.ordine_id IS NOT NULL
     FROM vendite.vw_preventivi_smistamento_righe v
    WHERE v.riga_id = (SELECT id FROM tmp_vs_riga_merce)),
  '2. Riga merce: A_ORDINE, destinazione ORDINE, riferimenti ordine valorizzati'
);

-- ============================================================
-- 3) Riga servizio EMESSA -> IN_COMMESSA
-- ============================================================
SELECT is(
  (SELECT v.stato_smistamento FROM vendite.vw_preventivi_smistamento_righe v
    WHERE v.riga_id = (SELECT id FROM tmp_vs_riga_serv_emessa)),
  'IN_COMMESSA',
  '3. Riga servizio emessa: IN_COMMESSA'
);

-- ============================================================
-- 4) Riga servizio residua -> RESIDUA
-- ============================================================
SELECT is(
  (SELECT v.stato_smistamento FROM vendite.vw_preventivi_smistamento_righe v
    WHERE v.riga_id = (SELECT id FROM tmp_vs_riga_serv_residua)),
  'RESIDUA',
  '4. Riga servizio non smistata: RESIDUA'
);

-- ============================================================
-- 5) Riga natura NULL -> destinazione COMMESSA (pregresso), RESIDUA
-- ============================================================
SELECT ok(
  (SELECT v.destinazione_tipo = 'COMMESSA'
      AND v.natura_vendita_id IS NULL
      AND v.stato_smistamento = 'RESIDUA'
     FROM vendite.vw_preventivi_smistamento_righe v
    WHERE v.riga_id = (SELECT id FROM tmp_vs_riga_null)),
  '5. Riga natura NULL: destinazione effettiva COMMESSA (pregresso), RESIDUA'
);

-- ============================================================
-- 6) Allineamento predicato col classificatore unico (D-5)
-- ============================================================
CREATE TEMP TABLE tmp_vs_att_residua AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_vs_commessa),
    p_prezzo_snapshot    => 10.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_vs_refs),
    p_sorgente_codice    => 'PREVENTIVO',
    p_sorgente_uid       => (SELECT uid::text FROM tmp_vs_prev),
    p_sorgente_riga_id   => (SELECT id FROM tmp_vs_riga_serv_residua),
    p_quantita           => 3,
    p_stato_approvazione => 'BOZZA',
    p_stato_emissione    => 'NON_EMESSA',
    p_competenza_dal     => DATE '2080-01-01',
    p_competenza_al      => DATE '2080-12-31');

-- La riga scritta davvero, sulla chiave della riga residua (controllo, non test).
DO $chk$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM vendite.commesse_attivita ca
                   JOIN tmp_vs_att_residua t ON t.attivita_id = ca.id
                  WHERE ca.stato_emissione = 'NON_EMESSA'
                    AND ca.segment_key = script.fn_segment_key('PREVENTIVO', (SELECT uid::text FROM tmp_vs_prev),
                                                               (SELECT id FROM tmp_vs_riga_serv_residua))) THEN
    RAISE EXCEPTION 'fixture: manca l''attivita'' NON_EMESSA della riga residua';
  END IF;
END $chk$;

SELECT is(
  (SELECT v.stato_smistamento FROM vendite.vw_preventivi_smistamento_righe v
    WHERE v.riga_id = (SELECT id FROM tmp_vs_riga_serv_residua)),
  'IN_COMMESSA',
  '6a. Attivita NON_EMESSA: la riga e'' IN_COMMESSA (stessa domanda del push: gia'' mandata)'
);

-- La riga si ritira (come all'annullo della commessa): non occupa piu'.
UPDATE vendite.commesse_attivita
   SET stato_emissione = 'ANNULLATA'
 WHERE id = (SELECT attivita_id FROM tmp_vs_att_residua);

SELECT is(
  (SELECT v.stato_smistamento FROM vendite.vw_preventivi_smistamento_righe v
    WHERE v.riga_id = (SELECT id FROM tmp_vs_riga_serv_residua)),
  'RESIDUA',
  '6b. Attivita ritirata (ANNULLATA): la riga torna RESIDUA'
);

-- ============================================================
-- 7) Aggregata: contatori per ramo
-- ============================================================
SELECT ok(
  (SELECT a.righe_totali = 4
      AND a.righe_merce = 1
      AND a.righe_servizi = 3
      AND a.righe_a_ordine = 1
      AND a.righe_in_commessa = 1
     FROM vendite.vw_preventivi_smistamento a
    WHERE a.preventivo_id = (SELECT id FROM tmp_vs_prev)),
  '7. Aggregata: totali=4, merce=1, servizi=3 (incl. pregresso NULL), a_ordine=1, in_commessa=1'
);

-- ============================================================
-- 8) Aggregata: righe_residue = 2 (progress X/Y -> EVASO)
-- ============================================================
SELECT is(
  (SELECT a.righe_residue::integer FROM vendite.vw_preventivi_smistamento a
    WHERE a.preventivo_id = (SELECT id FROM tmp_vs_prev)),
  2,
  '8. Aggregata: righe_residue=2 (servizio residuo + pregresso NULL)'
);

SELECT * FROM finish();
ROLLBACK;
