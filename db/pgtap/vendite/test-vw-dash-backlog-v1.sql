-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d/2e): l'area della dashboard e' il codice della sorgente; le chiavi del push col prefisso lungo.
-- pgTAP test per Zero ERP
--
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima le
--   offerte nascevano gia' EMESSA e ACCETTATA, i contratti gia' ANNULLATO e
--   ATTIVO). Il contratto ATTIVO prende il listino della fixture: senza, non si
--   attiva (trgfn_contratti_freeze_listino_versione). Il figlio ANNULLATO si
--   annulla col verbo vendite.fn_annulla_contratto (conferma del legame con
--   l'offerta).
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): il mondo si
--   COSTRUISCE (emittente A col suo operatore, cliente, articoli merce e
--   servizio con la natura nel builder, listino) invece di pescare «il primo BA
--   / articolo / emittente / operatore per id»; i due contratti nascono da
--   dbops.fn_pgtap_crea_contratto: il figlio ANNULLATO dalla push dell'offerta
--   ACCETTATA, l'ATTIVO sul cliente del test.
-- rev 2026-10-24 (brief-modello-documento-vendita R-9): azienda, operatore,
--   contesto e cliente nascono da dbops.fn_pgtap_crea_mondo_cliente, che da'
--   anche la whitelist su A: tolta la riscrittura a mano di
--   config.user_emittenti_fiscali e il set_config. La commessa nasce da
--   dbops.fn_pgtap_crea_commessa in BOZZA (prima: INSERT a mano nel «primo
--   stato per id»); le attivita' restano del test.
-- rev 2026-10-24 (brief-modello-documento-vendita §4-octies): le due attivita'
--   della commessa le scrive dbops.fn_pgtap_crea_commessa_attivita: l'EMESSA
--   con la sorgente (chiave dal dominio), la ferma senza (sorgente COMMESSA:
--   prima una riga PREVENTIVO con una chiave inventata); uom e tipo documento
--   non si pescano piu'.
--
-- Test: Lente 2 Backlog (20260706-01..02 lookup+seed, -03..08 colonna
--       data_riferimento su resolver/union, -12..13 viste backlog):
--       config.motivi_fermo (10 codici, 4 classi), vw_dash_backlog_documenti
--       (fermi non-verdi con classe fail-visible e anzianita'),
--       vw_dash_backlog_riepilogo (contatori per classe x area).
--       Brief: brief-db-fatturazione-due-lenti §3 e §5.
--       Fixture: preventivo ACCETTATO con residuo (RIGA_RESIDUA); ordine
--       DRAFT->CONFERMATO (DOC_BOZZA fuori, PUSH_NON_ESEGUITO dentro);
--       offerte BOZZA/EMESSA/ACCETTATA con figlio abortito; contratto ATTIVO
--       senza canone (fuori); commessa con attivita' ferma.
--
-- Indice test (0..13):
--   0)  Precondizioni (refs: BA, articoli, stati incl. offerta EMESSA)
--   1)  Le 2 viste backlog + la lookup config.motivi_fermo esistono
--   2)  Seed lookup: 10 codici attivi, tutte le classi valide, mappatura DL-6
--   3)  Setup: operatore OPERATORE non-super trovato + GUC scope
--   4)  Coerenza vocabolario: motivi emessi dalla union tutti in lookup
--   5)  RIGA_RESIDUA in backlog: classe RECUPERABILE, valore fermo 30,
--       data_riferimento = data documento, anzianita' coerente
--   6)  Ordine DRAFT (DOC_BOZZA, verde): FUORI dal backlog
--   7)  Ordine CONFERMATO senza push: PUSH_NON_ESEGUITO, RECUPERABILE
--   8)  Offerta BOZZA fuori; offerta EMESSA: IN_ATTESA_ACCETTAZIONE (blu)
--   9)  Offerta con figlio ANNULLATO: FIGLIO_ABORTITO, ANOMALIA (rossa)
--   10) Contratto ATTIVO senza canone (verde): area CONTRATTI assente
--   11) Commessa ferma: ATTIVITA_NON_APPROVATA, data_riferimento = competenza
--   12) FAIL-VISIBLE: motivo con lookup disattivata -> classe ANOMALIA,
--       riga NON persa
--   13) Riepilogo: contatori RECUPERABILE = somma del dettaglio
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. Questo file scrive su NOVE tabelle che
--   ne hanno. IMMEDIATE li riporta a scattare a fine di ogni istruzione.
--   In testa e non in coda: in coda scatterebbero dopo il cleanup, su righe
--   ormai cancellate. Brief: brief-db-pgtap-runner-rls-baseline §17 e §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⭐ rev 2026-10-24 (Q-4): l'azienda A e il suo operatore si costruiscono
--   PRIMA del contesto, e il contesto si apre su di lui: il cliente che nasce
--   dopo il trigger z90 lo lega ad A.
-- rev 2026-10-24 (R-9): il mondo del builder fa i tre passi nell'ordine giusto.
CREATE TEMP TABLE tmp_bl_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('dash backlog');

-- Il contesto l'ha gia' aperto il mondo sul suo operatore: la riga lo rende
-- esplicito (ed e' cio' che legge scripts/guardrail_pgtap_preambolo.py).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_bl_mondo)); END $ctx$;

SELECT plan(14);

CREATE TEMP TABLE tmp_bl_cli AS
SELECT billing_account_id, istanza_utility_id, utility_id FROM tmp_bl_mondo;

-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo): si
--   COSTRUISCE con l'operatore di A in sessione, quindi il builder gli da'
--   l'emittente A, sulla utility del cliente.
CREATE TEMP TABLE tmp_bl_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_bl_cli), 'dash backlog');

-- ============================================================
-- 0) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_bl_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_bl_cli) AS billing_account_id,
  (SELECT utility_id FROM tmp_bl_cli) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_bl_cli) AS istanza_utility_id,
  -- Gli articoli si costruiscono con la natura che il caso pretende (rev
  --   2026-10-24): prima si pescavano i primi due per id e se ne cambiava la
  --   natura con un UPDATE.
  dbops.fn_pgtap_crea_articolo('PGT-BL-MERCE', true,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE')) AS art_merce_id,
  dbops.fn_pgtap_crea_articolo('PGT-BL-SERV', false,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita WHERE codice_interno = 'SERVIZIO_UNA_TANTUM')) AS art_serv_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1) AS prev_accettato_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE) AS prev_bozza_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno = 'CONFERMATO' AND s.attivo IS TRUE LIMIT 1) AS ord_confermato_id,
  (SELECT s.id FROM config.stati_doc_offerte s
    WHERE s.codice_interno = 'BOZZA' AND s.attivo IS TRUE LIMIT 1) AS off_bozza_id,
  (SELECT s.id FROM config.stati_doc_offerte s
    WHERE s.codice_interno = 'EMESSA' AND s.attivo IS TRUE LIMIT 1) AS off_emessa_id,
  (SELECT s.id FROM config.stati_doc_offerte s
    WHERE s.codice_interno = 'ACCETTATA' AND s.attivo IS TRUE LIMIT 1) AS off_accettata_id,
  (SELECT s.id FROM config.stati_doc_contratti s
    WHERE s.codice_interno = 'ATTIVO' AND s.attivo IS TRUE LIMIT 1) AS contr_attivo_id,
  (SELECT s.id FROM config.stati_doc_contratti s
    WHERE s.codice_interno = 'ANNULLATO' AND s.attivo IS TRUE LIMIT 1) AS contr_annullato_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT emittente_fiscale_id FROM tmp_bl_mondo) AS emittente_fiscale_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT listino_id FROM tmp_bl_listino) AS listino_id,
  (SELECT listino_versione_id FROM tmp_bl_listino) AS listino_versione_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE') AS natura_merce_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'SERVIZIO_UNA_TANTUM') AS natura_serv_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND art_merce_id IS NOT NULL
      AND art_serv_id IS NOT NULL AND prev_accettato_id IS NOT NULL
      AND ord_confermato_id IS NOT NULL AND off_bozza_id IS NOT NULL
      AND off_emessa_id IS NOT NULL AND off_accettata_id IS NOT NULL
      AND contr_attivo_id IS NOT NULL AND contr_annullato_id IS NOT NULL
      AND listino_id IS NOT NULL AND listino_versione_id IS NOT NULL
      AND natura_merce_id IS NOT NULL AND natura_serv_id IS NOT NULL
     FROM tmp_bl_refs),
  '0. Precondizioni soddisfatte'
);

-- ============================================================
-- 1) Viste backlog + lookup esistono
-- ============================================================
SELECT ok(
  (SELECT count(*) = 2 FROM pg_views
    WHERE schemaname = 'vendite'
      AND viewname IN ('vw_dash_backlog_documenti', 'vw_dash_backlog_riepilogo'))
  AND EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'config' AND table_name = 'motivi_fermo'),
  '1. Le 2 viste backlog e la lookup config.motivi_fermo esistono'
);

-- ============================================================
-- 2) Seed lookup: 10 codici, classi DL-6
-- ============================================================
SELECT ok(
  (SELECT count(*) = 10
      AND count(*) FILTER (WHERE classe = 'RECUPERABILE') = 5
      AND count(*) FILTER (WHERE classe = 'ANOMALIA') = 1
      AND count(*) FILTER (WHERE classe = 'SOLLECITO_CLIENTE') = 1
      AND count(*) FILTER (WHERE classe = 'FISIOLOGICO') = 3
      AND bool_and(attivo)
     FROM config.motivi_fermo
    WHERE codice_interno IN ('RIGA_RESIDUA','PUSH_NON_ESEGUITO','PUSH_PARZIALE',
                             'ATTIVITA_NON_APPROVATA','ATTIVITA_NON_EMESSA',
                             'FIGLIO_ABORTITO','IN_ATTESA_ACCETTAZIONE',
                             'DOC_BOZZA','CANONE_NON_GENERATO','SENZA_FIGLIO')),
  '2. Seed lookup: 10 codici attivi con la mappatura classi DL-6 (5 arancio, 1 rosso, 1 blu, 3 verdi)'
);

-- ============================================================
-- 3) Setup scope operatore (il ramo commesse della union e' fail-closed)
-- ============================================================
-- L'operatore e' quello costruito con l'azienda A (rev 2026-10-24): prima si
-- pescava il primo OPERATORE non super per id.
-- rev 2026-10-24 (R-9): la whitelist su A e il contesto li da' il mondo; la
-- riscrittura a mano e il set_config sono usciti.
CREATE TEMP TABLE tmp_bl_op AS
SELECT id.auth_user_id AS user_id
  FROM anagrafiche.identita_digitali id
 WHERE id.auth_user_id = (SELECT auth_user_id FROM tmp_bl_mondo)
   AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND id.attivo = true
   AND NOT EXISTS (
       SELECT 1 FROM config.profili_accesso_bindings pab
       JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
       WHERE pab.identita_digitale_id = id.id
         AND pab.attivo = true
         AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso);

SELECT ok(
  (SELECT user_id IS NOT NULL FROM tmp_bl_op),
  '3. Trovato un operatore OPERATORE non-super per lo scope'
);

-- ============================================================
-- Fixture PREVENTIVO ACCETTATO misto (pattern test-vw-dash-fatturazione):
-- merce 1x50 a ordine, servizio 2x30 emesso in commessa, servizio 3x10
-- residuo -> RIGA_RESIDUA con valore fermo 30. data documento 2080-01-01.
-- ============================================================
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT, prende le tre righe, poi passa ad ACCETTATO con dbops.fn_pgtap_porta_a_stato prima del push — fuori bozza le righe non si scrivono piu' (20261008-91).
CREATE TEMP TABLE tmp_bl_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-BL-PREV', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.prev_bozza_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_backlog'), r.emittente_fiscale_id
    FROM tmp_bl_refs r
  RETURNING id, uid)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_bl_riga_merce AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_merce_id, 1.000000, 50.000000, r.iva_id, true
    FROM tmp_bl_prev p, tmp_bl_refs r
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_bl_riga_serv_emessa AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 2.000000, 30.000000, r.iva_id, true
    FROM tmp_bl_prev p, tmp_bl_refs r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.art_serv_id, 3.000000, 10.000000, r.iva_id, true
  FROM tmp_bl_prev p, tmp_bl_refs r;
DO $porta$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_bl_prev), 'ACCETTATO'); END $porta$;

-- Push del ramo merce: ordine DRAFT reale.
SELECT vendite.fn_push_preventivo_a_ordine((SELECT id FROM tmp_bl_prev));

-- Commessa (emittente A) + attivita' EMESSA per il servizio 2x30 + una ferma
-- BOZZA/NON_EMESSA (per il motivo ATTIVITA_NON_APPROVATA in backlog).
-- rev 2026-10-24: la commessa nasce dalla madre via dbops.fn_pgtap_crea_commessa,
--   in BOZZA; le due attivita' dal builder (rev §4-octies, sotto).
CREATE TEMP TABLE tmp_bl_cmd AS
SELECT * FROM dbops.fn_pgtap_crea_commessa(
                 'dash backlog', 'BOZZA', (SELECT billing_account_id FROM tmp_bl_refs));

CREATE TEMP TABLE tmp_bl_commessa AS
SELECT commessa_id AS id FROM tmp_bl_cmd;

-- rev 2026-10-24 (§4-octies): le due attivita' le scrive il builder.
--   L'EMESSA del servizio porta la sorgente (la riga del preventivo): la
--   chiave la compone il dominio. La ferma era una riga PREVENTIVO con una
--   chiave inventata, che nessuna riga del preventivo produce: ora e' una
--   riga della commessa (sorgente COMMESSA, chiave del builder), cio' che il
--   caso 11 legge (il motivo della commessa) non cambia. Tipo documento
--   fiscale e valuta li deriva la madre, l'unita' di misura l'articolo.
CREATE TEMP TABLE tmp_bl_att_emessa AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_bl_commessa),
    p_prezzo_snapshot    => 30.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_bl_refs),
    p_sorgente_codice    => 'PREVENTIVO',
    p_sorgente_uid       => (SELECT uid::text FROM tmp_bl_prev),
    p_sorgente_riga_id   => (SELECT id FROM tmp_bl_riga_serv_emessa),
    p_quantita           => 2,
    p_stato_approvazione => 'BOZZA',
    p_stato_emissione    => 'EMESSA',
    p_competenza_dal     => DATE '2080-01-01',
    p_competenza_al      => DATE '2080-12-31');

CREATE TEMP TABLE tmp_bl_att_ferma AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_bl_commessa),
    p_prezzo_snapshot    => 10.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_bl_refs),
    p_quantita           => 3,
    p_stato_approvazione => 'BOZZA',
    p_stato_emissione    => 'NON_EMESSA',
    p_competenza_dal     => DATE '2080-01-01',
    p_competenza_al      => DATE '2080-12-31');

-- Le due righe scritte davvero (controllo, non test).
DO $chk$ BEGIN
  IF (SELECT count(*) FROM vendite.commesse_attivita ca
       WHERE ca.commessa_id = (SELECT id FROM tmp_bl_commessa)
         AND ((ca.id = (SELECT attivita_id FROM tmp_bl_att_emessa) AND ca.stato_emissione = 'EMESSA'
               AND ca.segment_key = script.fn_segment_key('PREVENTIVO', (SELECT uid::text FROM tmp_bl_prev),
                                                          (SELECT id FROM tmp_bl_riga_serv_emessa)))
           OR (ca.id = (SELECT attivita_id FROM tmp_bl_att_ferma)
               AND ca.stato_approvazione = 'BOZZA' AND ca.stato_emissione = 'NON_EMESSA'))) <> 2 THEN
    RAISE EXCEPTION 'fixture: attese 2 attivita'' dal builder';
  END IF;
END $chk$;

-- Fixture OFFERTE: BOZZA (verde, fuori), EMESSA (blu), ACCETTATA con figlio
-- ANNULLATO (rossa). validita_dal 2080-03-01.
CREATE TEMP TABLE tmp_bl_offerte (slot text, offerta_id bigint);

WITH ins AS (
  INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id)
  SELECT r.emittente_fiscale_id, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         r.listino_id, r.listino_versione_id, DATE '2080-03-01', r.off_bozza_id
    FROM tmp_bl_refs r
  RETURNING id)
INSERT INTO tmp_bl_offerte SELECT 'BOZZA', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id)
  SELECT r.emittente_fiscale_id, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         r.listino_id, r.listino_versione_id, DATE '2080-03-01', r.off_bozza_id
    FROM tmp_bl_refs r
  RETURNING id)
INSERT INTO tmp_bl_offerte SELECT 'EMESSA', id FROM ins;

-- rev 2026-10-24: nata in BOZZA, emessa per la matrice.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', o.offerta_id, 'EMESSA')
  FROM tmp_bl_offerte o
 WHERE o.slot = 'EMESSA';

WITH ins AS (
  INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id)
  SELECT r.emittente_fiscale_id, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         r.listino_id, r.listino_versione_id, DATE '2080-03-01', r.off_bozza_id
    FROM tmp_bl_refs r
  RETURNING id)
INSERT INTO tmp_bl_offerte SELECT 'ACC_FIGLIO_ABORTITO', id FROM ins;

-- rev 2026-10-24: nata in BOZZA, accettata per la matrice (BOZZA -> EMESSA -> ACCETTATA).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', o.offerta_id, 'ACCETTATA')
  FROM tmp_bl_offerte o
 WHERE o.slot = 'ACC_FIGLIO_ABORTITO';

-- Il figlio ANNULLATO (rev 2026-10-24, Q-2): nasce dalla PUSH dell'offerta
--   ACCETTATA, come in produzione, e il builder lo annulla col verbo
--   vendite.fn_annulla_contratto dichiarando il legame con l'offerta.
CREATE TEMP TABLE tmp_bl_k_annullato AS
SELECT * FROM dbops.fn_pgtap_crea_contratto(
                 'dash backlog figlio', 'ANNULLATO', NULL,
                 (SELECT offerta_id FROM tmp_bl_offerte WHERE slot = 'ACC_FIGLIO_ABORTITO'));

CREATE TEMP TABLE tmp_bl_contratto_annullato AS
SELECT contratto_id AS id FROM tmp_bl_k_annullato;

-- Fixture CONTRATTO ATTIVO senza canone (fisiologico, fuori dal backlog).
-- ⚠️ Il motivo e' NULL, non CANONE_NON_GENERATO: dal 20260707-03 (vista dei
--   contratti «de-esplosa») i contratti non hanno un motivo di fermo finche' non
--   esiste il push ricorrente dei canoni. Il codice resta nel seed di
--   config.motivi_fermo apposta, per la riaccensione (vedi la doc della vista).
--   rev 2026-10-24: il commento diceva ancora CANONE_NON_GENERATO.
-- rev 2026-10-24 (Q-2): dal builder, sul cliente del test, attivato sul
--   listino che il builder gli costruisce (dell'azienda di chi agisce).
CREATE TEMP TABLE tmp_bl_k_attivo AS
SELECT * FROM dbops.fn_pgtap_crea_contratto(
                 'dash backlog', 'ATTIVO', (SELECT billing_account_id FROM tmp_bl_refs));

CREATE TEMP TABLE tmp_bl_contratto AS
SELECT contratto_id AS id FROM tmp_bl_k_attivo;

-- ============================================================
-- 4) Coerenza vocabolario: ogni motivo emesso dalla union e' in lookup.
--    (Sentinella anti-drift: se una vista introduce un codice nuovo senza
--    seed, questo test diventa rosso.)
-- ============================================================
SELECT is(
  (SELECT count(*)::integer
     FROM (SELECT DISTINCT d.motivo_fermo
             FROM vendite.vw_dash_fatturazione_documenti d
            WHERE d.motivo_fermo IS NOT NULL) m
    WHERE NOT EXISTS (SELECT 1 FROM config.motivi_fermo mf
                       WHERE mf.codice_interno = m.motivo_fermo)),
  0,
  '4. Coerenza vocabolario: nessun motivo_fermo emesso dalla union fuori dalla lookup'
);

-- ============================================================
-- 5) RIGA_RESIDUA in backlog (arancio)
-- ============================================================
SELECT ok(
  (SELECT b.classe = 'RECUPERABILE'
      AND b.azione IS NOT NULL
      AND b.valore_fermo = 30
      AND b.data_riferimento = DATE '2080-01-01'
      AND b.anzianita_giorni = (script.fn_data_operativa() - DATE '2080-01-01')
     FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area = 'PREVENTIVO'
      AND b.documento_id = (SELECT id FROM tmp_bl_prev)
      AND b.motivo_fermo = 'RIGA_RESIDUA'),
  '5. RIGA_RESIDUA in backlog: RECUPERABILE, valore fermo 30, data_riferimento = data documento, anzianita'' coerente'
);

-- ============================================================
-- 6-7) Ordine: DOC_BOZZA fuori (verde), PUSH_NON_ESEGUITO dentro (arancio)
-- ============================================================
CREATE TEMP TABLE tmp_bl_ordine AS
SELECT o.id
  FROM vendite.ordini o
  JOIN vendite.ordini_righe orr ON orr.ordine_id = o.id
 WHERE orr.preventivo_riga_id = (SELECT id FROM tmp_bl_riga_merce);

SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area = 'ORDINE_VENDITA' AND b.documento_id = (SELECT id FROM tmp_bl_ordine)),
  0,
  '6. Ordine DRAFT (DOC_BOZZA, fisiologico): FUORI dal backlog'
);

UPDATE vendite.ordini
   SET stato_doc_ordine_id = (SELECT ord_confermato_id FROM tmp_bl_refs)
 WHERE id = (SELECT id FROM tmp_bl_ordine);

SELECT ok(
  (SELECT b.motivo_fermo = 'PUSH_NON_ESEGUITO' AND b.classe = 'RECUPERABILE'
      AND b.data_riferimento IS NOT NULL
     FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area = 'ORDINE_VENDITA' AND b.documento_id = (SELECT id FROM tmp_bl_ordine)),
  '7. Ordine CONFERMATO senza push: PUSH_NON_ESEGUITO in backlog, RECUPERABILE'
);

-- ============================================================
-- 8-9) Offerte: BOZZA fuori; EMESSA -> blu; figlio abortito -> rossa
-- ============================================================
SELECT ok(
  (SELECT count(*) = 0 FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area = 'OFFERTA_COMMERCIALE'
      AND b.documento_id = (SELECT offerta_id FROM tmp_bl_offerte WHERE slot = 'BOZZA'))
  AND
  (SELECT b.motivo_fermo = 'IN_ATTESA_ACCETTAZIONE' AND b.classe = 'SOLLECITO_CLIENTE'
     FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area = 'OFFERTA_COMMERCIALE'
      AND b.documento_id = (SELECT offerta_id FROM tmp_bl_offerte WHERE slot = 'EMESSA')),
  '8. Offerta BOZZA fuori dal backlog; offerta EMESSA dentro come SOLLECITO_CLIENTE (blu)'
);

SELECT ok(
  (SELECT b.motivo_fermo = 'FIGLIO_ABORTITO' AND b.classe = 'ANOMALIA'
     FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area = 'OFFERTA_COMMERCIALE'
      AND b.documento_id = (SELECT offerta_id FROM tmp_bl_offerte WHERE slot = 'ACC_FIGLIO_ABORTITO')),
  '9. Offerta con figlio ANNULLATO: FIGLIO_ABORTITO in backlog, ANOMALIA (rossa)'
);

-- ============================================================
-- 10) Contratti tutti verdi: area assente dal backlog
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area = 'CONTRATTO'
      AND b.documento_id = (SELECT id FROM tmp_bl_contratto)),
  0,
  '10. Contratto ATTIVO senza canone (motivo NULL dal 20260707-03, fisiologico): FUORI dal backlog'
);

-- ============================================================
-- 11) Commessa ferma in backlog (arancio), anzianita' dalla competenza
-- ============================================================
SELECT ok(
  (SELECT b.motivo_fermo = 'ATTIVITA_NON_APPROVATA' AND b.classe = 'RECUPERABILE'
      AND b.data_riferimento = DATE '2080-01-01'
      AND b.competenza_mese = DATE '2080-01-01'
     FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area = 'COMMESSA'
      AND b.documento_id = (SELECT id FROM tmp_bl_commessa)),
  '11. Commessa ferma: ATTIVITA_NON_APPROVATA in backlog, data_riferimento = competenza'
);

-- ============================================================
-- 12) FAIL-VISIBLE: lookup disattivata -> classe ANOMALIA, riga NON persa
-- ============================================================
UPDATE config.motivi_fermo SET attivo = false
 WHERE codice_interno = 'RIGA_RESIDUA';

SELECT ok(
  (SELECT b.classe = 'ANOMALIA' AND b.azione IS NULL
     FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area = 'PREVENTIVO'
      AND b.documento_id = (SELECT id FROM tmp_bl_prev)
      AND b.motivo_fermo = 'RIGA_RESIDUA'),
  '12. Fail-visible: motivo senza lookup attiva -> classe ANOMALIA, riga NON persa in silenzio'
);

UPDATE config.motivi_fermo SET attivo = true
 WHERE codice_interno = 'RIGA_RESIDUA';

-- ============================================================
-- 13) Riepilogo coerente col dettaglio (classe RECUPERABILE)
-- ============================================================
SELECT ok(
  (SELECT COALESCE(SUM(r.n_documenti), 0) =
          (SELECT count(*) FROM vendite.vw_dash_backlog_documenti b
            WHERE b.classe = 'RECUPERABILE')
     FROM vendite.vw_dash_backlog_riepilogo r
    WHERE r.classe = 'RECUPERABILE'),
  '13. Riepilogo: somma n_documenti RECUPERABILE = conteggio del dettaglio'
);

SELECT * FROM finish();
ROLLBACK;
