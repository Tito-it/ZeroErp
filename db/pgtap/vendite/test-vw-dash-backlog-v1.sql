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
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

-- ============================================================
-- 0) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_bl_refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS billing_account_id,
  (SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS utility_id,
  (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1 OFFSET 0) AS art_merce_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1 OFFSET 1) AS art_serv_id,
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
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1) AS sorg_preventivo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE
    ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.codice_interno <> 'ANNULLATA'
    ORDER BY sc.id LIMIT 1) AS stato_commessa_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
  (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1) AS ef_a_sr,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT l.id FROM vendite.listini l WHERE l.attivo IS TRUE ORDER BY l.id LIMIT 1) AS listino_id,
  (SELECT lv.id FROM vendite.listini_versioni lv WHERE lv.stato = 'ATTIVA'
    ORDER BY lv.id LIMIT 1) AS listino_versione_id,
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
CREATE TEMP TABLE tmp_bl_op AS
SELECT id.auth_user_id AS user_id
  FROM anagrafiche.identita_digitali id
 WHERE id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND id.attivo = true
   AND NOT EXISTS (
       SELECT 1 FROM config.profili_accesso_bindings pab
       JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
       WHERE pab.identita_digitale_id = id.id
         AND pab.attivo = true
         AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso)
 ORDER BY id.id LIMIT 1;

SELECT ok(
  (SELECT user_id IS NOT NULL FROM tmp_bl_op),
  '3. Trovato un operatore OPERATORE non-super per lo scope'
);

SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_bl_op);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id, meta)
SELECT o.user_id, r.emittente_fiscale_id,
       '{"test_scope":"pgtap_dash_backlog"}'::jsonb
  FROM tmp_bl_op o, tmp_bl_refs r
 WHERE o.user_id IS NOT NULL;

SELECT set_config('app.current_user_id',
    (SELECT user_id::text FROM tmp_bl_op), true);

-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo). Le offerte
--   del fixture sono dell'emittente A e del primo BA dei dati: il listino si
--   COSTRUISCE qui, dopo il passaggio all'operatore whitelistato su A, quindi il
--   builder gli da' l'emittente A, sulla utility del BA. Prima era il primo listino
--   per id, di qualunque utility ed emittente.
--   ⚠️ Prima stesura dello stesso giorno: si cercava fra i dati un listino di A
--   sulla utility del BA, e su dbdev non c'era (offerta con listino NULL).
CREATE TEMP TABLE tmp_bl_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_bl_refs), 'dash backlog');
UPDATE tmp_bl_refs r
   SET listino_id          = (SELECT listino_id FROM tmp_bl_listino),
       listino_versione_id = (SELECT listino_versione_id FROM tmp_bl_listino);

-- ============================================================
-- Fixture PREVENTIVO ACCETTATO misto (pattern test-vw-dash-fatturazione):
-- merce 1x50 a ordine, servizio 2x30 emesso in commessa, servizio 3x10
-- residuo -> RIGA_RESIDUA con valore fermo 30. data documento 2080-01-01.
-- ============================================================
UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_merce_id FROM tmp_bl_refs)
 WHERE id = (SELECT art_merce_id FROM tmp_bl_refs);
UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_serv_id FROM tmp_bl_refs)
 WHERE id = (SELECT art_serv_id FROM tmp_bl_refs);

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
CREATE TEMP TABLE tmp_bl_commessa AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                emittente_soggetto_ruolo_id, stato_commessa_id)
  SELECT 'PGTAP-BL-CMD-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id, r.ef_a_sr, r.stato_commessa_id
    FROM tmp_bl_refs r
  RETURNING id)
SELECT id FROM ins;

INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key,
  articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione,
  sorgente_tipo_id, sorgente_uid)
SELECT
  (SELECT id FROM tmp_bl_commessa),
  'PREVENTIVO:' || (SELECT uid FROM tmp_bl_prev)::text || ':R:' || (SELECT id FROM tmp_bl_riga_serv_emessa)::text,
  r.art_serv_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 2,
  DATE '2080-01-01', DATE '2080-01-01', DATE '2080-12-31',
  r.tipo_doc_fiscale_id, r.valuta_id, 30.000000,
  'FIXED', 'BOZZA', 'EMESSA',
  r.sorg_preventivo_id, (SELECT uid FROM tmp_bl_prev)::text
FROM tmp_bl_refs r;

INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key,
  articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione,
  sorgente_tipo_id, sorgente_uid)
SELECT
  (SELECT id FROM tmp_bl_commessa),
  'PGTAP-BL-NE-' || substr(md5(clock_timestamp()::text), 1, 8),
  r.art_serv_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 3,
  DATE '2080-01-01', DATE '2080-01-01', DATE '2080-12-31',
  r.tipo_doc_fiscale_id, r.valuta_id, 10.000000,
  'FIXED', 'BOZZA', 'NON_EMESSA',
  r.sorg_preventivo_id, (SELECT uid FROM tmp_bl_prev)::text
FROM tmp_bl_refs r;

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

-- Il figlio ANNULLATO: nasce DRAFT e si annulla col verbo (rev 2026-10-24).
-- ⚠️ Non con fn_pgtap_porta_a_stato: annullare un contratto nato da
--   un'offerta riapre un legame (l'offerta da cui nasce), e il guard
--   trg_contratti_m10_guard_annullo_con_legami_upd vuole la conferma. Il verbo
--   vendite.fn_annulla_contratto la riceve come conteggio: 1, l'offerta.
CREATE TEMP TABLE tmp_bl_contratto_annullato AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al, data, offerta_id,
    emittente_fiscale_id, meta)
  SELECT 'PGTAP-BL-CA-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.istanza_utility_id, r.utility_id,
         script.fn_data_operativa(), NULL, script.fn_data_operativa(),
         (SELECT offerta_id FROM tmp_bl_offerte WHERE slot = 'ACC_FIGLIO_ABORTITO'),
         COALESCE(anagrafiche.fn_get_emittente_fiscale_pk(r.billing_account_id),
                  r.emittente_fiscale_id),
         jsonb_build_object('test_scope','pgtap_dash_backlog')
    FROM tmp_bl_refs r
  RETURNING id)
SELECT * FROM ins;

SELECT vendite.fn_annulla_contratto(c.id, 1)
  FROM tmp_bl_contratto_annullato c;

-- Fixture CONTRATTO ATTIVO senza canone (verde: CANONE_NON_GENERATO).
-- rev 2026-10-24: nasce DRAFT sul listino della fixture e si attiva per la matrice.
CREATE TEMP TABLE tmp_bl_contratto AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al, data, listino_id,
    emittente_fiscale_id, meta)
  SELECT 'PGTAP-BL-CT-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.istanza_utility_id, r.utility_id,
         date_trunc('month', script.fn_data_operativa())::date, NULL,
         date_trunc('month', script.fn_data_operativa())::date, r.listino_id,
         COALESCE(anagrafiche.fn_get_emittente_fiscale_pk(r.billing_account_id),
                  r.emittente_fiscale_id),
         jsonb_build_object('test_scope','pgtap_dash_backlog')
    FROM tmp_bl_refs r
  RETURNING id)
SELECT * FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti', c.id, 'ATTIVO')
  FROM tmp_bl_contratto c;

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
  '10. Contratto ATTIVO senza canone (CANONE_NON_GENERATO, fisiologico): FUORI dal backlog'
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
