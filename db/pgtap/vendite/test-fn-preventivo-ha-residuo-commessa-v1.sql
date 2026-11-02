-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2e): le chiavi del push col codice della sorgente (PREVENTIVO:, DDT_VENDITA:, ORDINE_VENDITA:, CONTRATTO:, ATTIVITA_CONSUMI:), stessa forma di script.fn_segment_key carattere per carattere.
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato; il preventivo
--   senza BA del test 3 nasce DRAFT (prima ACCETTATO: il trigger della nascita
--   avrebbe parlato prima del NOT NULL, coprendo il 23502 che il test chiede).
-- rev 2026-10-24 (brief-modello-documento-vendita R-6/Q-4): il mondo si
--   costruisce. Cliente ed emittente da dbops.fn_pgtap_crea_mondo_cliente,
--   i due articoli da dbops.fn_pgtap_crea_articolo con la natura del caso
--   (MERCE, SERVIZIO_UNA_TANTUM), la commessa dei casi 8-12 da
--   dbops.fn_pgtap_crea_commessa sul cliente del mondo. Prima si pescavano il
--   primo billing account, il primo emittente, «i primi due articoli per id»
--   (riscrivendone la natura: il primo e' un articolo-onere e il file moriva
--   li'), la prima unita' di misura e il primo stato commessa. Numero e stato
--   delle testate non si scrivono piu': li assegnano il dominio e il trigger
--   della nascita (l'INSERT del test 3, che non deve nascere, resta com'era).
-- rev 2026-10-24 (brief-modello-documento-vendita §4-octies): le attivita' dei casi 8, 10 e 12 le scrive dbops.fn_pgtap_crea_commessa_attivita con la sorgente (chiave dal dominio, stato di emissione dichiarato) invece degli INSERT con la chiave composta a mano; il caso 11 (#CMP) resta a mano, con la base della chiave da script.fn_segment_key.
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_preventivo_ha_residuo_commessa (20260612-03) +
--       capability can_push_commessa simmetrica con reason
--       (script.fn_available_actions_preventivo, 20260612-04).
--       Brief: brief-db-smistamento-preventivi.md, Richiesta A.
--
-- Indice test (0..9):
--   0) Precondizioni (refs + nature)
--   1) Preventivo MISTO (servizio+merce, BA ok) -> residuo = true
--   2) Preventivo SOLO MERCE -> residuo = false
--   3) Un preventivo SENZA billing account non nasce (23502) — rev 2026-10-08,
--      brief-db-istanza-nasce-col-ba R-2: fino a quel giorno il caso esisteva e
--      il test diceva «residuo = false (testata incompleta)»
--   4) Guard: id invalido -> throws
--   5) available_actions MISTO: can_push_commessa = true, reason NULL
--   6) available_actions SOLO MERCE: can_push=false, reason PREVENTIVO_NESSUNA_RIGA_COMMESSA
--   7) (ritirato il 2026-10-08: «available_actions SENZA BA» — il preventivo
--      senza BA non si puo' piu' costruire, vedi 3)
--   8) Post-push (riga servizio EMESSA in commessa): residuo MISTO = false
--      (la merce residua non conta sul ramo commessa)
--   9) available_actions DRAFT: reason PREVENTIVO_NON_ACCETTATO
--  10) Post-push NON_EMESSA -> residuo = false (fix gate EVASO: la riga e'
--      esclusa appena instradata, non solo dopo fatturazione)
--  11) Post-push componente BoM (segment_key #CMP, NON_EMESSA) -> residuo = false
--      (match a prefisso §4: una riga composita viene esclusa)
--  12) Attivita ANNULLATA -> residuo = true: una riga ritirata non occupa, la
--      riga torna da mandare in commessa (rev 2026-10-12, 20261012-08/-09,
--      brief-db-annullo-a-valle-riapre-a-monte D-5 di Tid). Fino a quel giorno
--      il test fissava la decisione del 2026-06-28 «riga instradata, non
--      ri-pushabile; non riapre il preventivo», che D-5 sostituisce.
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

SELECT plan(12);

-- ============================================================
-- 0) Riferimenti minimi + classificazione nature
-- ============================================================
-- ⭐ rev 2026-10-24 (Q-4): il cliente e l'emittente da
--   dbops.fn_pgtap_crea_mondo_cliente (col contesto aperto riusa l'azienda di
--   chi agisce: emittente e BA d'accordo per costruzione); gli articoli
--   nascono con la natura del caso: merce -> MERCE (ORDINE), servizio ->
--   SERVIZIO_UNA_TANTUM (COMMESSA). ⛔ Cio' che il builder scrive si legge in
--   un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_rc_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('residuo commessa');

CREATE TEMP TABLE tmp_rc_art AS
SELECT
  dbops.fn_pgtap_crea_articolo('PGT-RC-MERCE',
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                               WHERE codice_interno = 'MERCE')) AS art_merce_id,
  dbops.fn_pgtap_crea_articolo('PGT-RC-SERV', false,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                               WHERE codice_interno = 'SERVIZIO_UNA_TANTUM')) AS art_serv_id;

CREATE TEMP TABLE tmp_rc_refs AS
SELECT
  m.billing_account_id,
  m.utility_id,
  m.istanza_utility_id,
  x.art_merce_id,
  x.art_serv_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ACCETTATO' AND s.attivo IS TRUE) AS stato_accettato_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE) AS stato_draft_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  -- L'unita' di misura e' quella dell'articolo del servizio: le attivita'
  --   dei casi 8-12 sono sue. Prima era la prima del catalogo per id.
  (SELECT a.uom_id FROM catalogo.articoli a WHERE a.id = x.art_serv_id) AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE
    ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  m.emittente_fiscale_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE') AS natura_merce_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'SERVIZIO_UNA_TANTUM') AS natura_serv_id,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO' AND s.attivo IS TRUE) AS sorgente_preventivo_id
FROM tmp_rc_mondo m, tmp_rc_art x;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND art_merce_id IS NOT NULL
      AND art_serv_id IS NOT NULL AND stato_accettato_id IS NOT NULL
      AND natura_merce_id IS NOT NULL AND natura_serv_id IS NOT NULL
     FROM tmp_rc_refs),
  '0. Precondizioni soddisfatte'
);

-- Preventivo MISTO ACCETTATO (BA ok): 1 riga servizio + 1 riga merce.
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): i
--   preventivi ACCETTATO di questo file (misto, solo merce, i tre dei casi
--   10-12) nascono DRAFT, prendono le righe, poi passano ad ACCETTATO con
--   dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu'
--   (20261008-91).
CREATE TEMP TABLE tmp_rc_misto AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_residuo_commessa'), r.emittente_fiscale_id
    FROM tmp_rc_refs r
  RETURNING id, uid)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_rc_riga_serv AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 2.000000, 30.000000, r.iva_id, true
    FROM tmp_rc_misto p, tmp_rc_refs r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.art_merce_id, 1.000000, 50.000000, r.iva_id, true
  FROM tmp_rc_misto p, tmp_rc_refs r;

DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_rc_misto), 'ACCETTATO');
END $x$;

-- Preventivo SOLO MERCE ACCETTATO (BA ok).
CREATE TEMP TABLE tmp_rc_merce AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_residuo_commessa_merce'), r.emittente_fiscale_id
    FROM tmp_rc_refs r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.art_merce_id, 1.000000, 50.000000, r.iva_id, true
  FROM tmp_rc_merce p, tmp_rc_refs r;

DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_rc_merce), 'ACCETTATO');
END $x$;

-- Preventivo DRAFT con riga servizio (per reason non_accettato).
CREATE TEMP TABLE tmp_rc_draft AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_residuo_commessa_draft'), r.emittente_fiscale_id
    FROM tmp_rc_refs r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.art_serv_id, 1.000000, 20.000000, r.iva_id, true
  FROM tmp_rc_draft p, tmp_rc_refs r;

-- ============================================================
-- 1) MISTO -> residuo = true
-- ============================================================
SELECT is(
  vendite.fn_preventivo_ha_residuo_commessa((SELECT id FROM tmp_rc_misto)),
  true,
  '1. Preventivo misto: residuo commessa = true'
);

-- ============================================================
-- 2) SOLO MERCE -> residuo = false
-- ============================================================
SELECT is(
  vendite.fn_preventivo_ha_residuo_commessa((SELECT id FROM tmp_rc_merce)),
  false,
  '2. Preventivo solo merce: residuo commessa = false'
);

-- ============================================================
-- 3) Un preventivo SENZA billing account non nasce
--    ⚠️ rev 2026-10-08 (brief-db-istanza-nasce-col-ba, R-2): fino a quel
--    giorno il caso esisteva, e il test chiedeva «residuo = false, testata
--    incompleta». Ora billing_account_id e' NOT NULL: il guard dell'emittente
--    lascia parlare il vincolo (23502), che e' la regola.
--    ⚠️ rev 2026-10-24: nello stato iniziale (DRAFT). Con uno stato avanti il
--    trigger della nascita (a05, BEFORE INSERT) solleverebbe
--    E_DOC_STATO_INIZIALE_NON_VALIDO prima del vincolo, e il test smetterebbe
--    di parlare del billing account.
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO vendite.preventivi (
      numero, rev, istanza_utility_id, utility_id,
      validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
      fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
    SELECT 'PGTAP-RC-NOBA', 0, r.istanza_utility_id, r.utility_id,
           DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_draft_id,
           DATE '2080-01-01', false, false,
           jsonb_build_object('test_scope','pgtap_residuo_commessa_noba'), r.emittente_fiscale_id
      FROM tmp_rc_refs r$$,
  '23502',
  NULL,
  '3. Un preventivo senza billing account non nasce (23502)'
);

-- ============================================================
-- 4) Guard: id invalido -> throws
-- ============================================================
SELECT throws_ok(
  'SELECT vendite.fn_preventivo_ha_residuo_commessa(-1)',
  NULL, NULL,
  '4. Guard: p_preventivo_id invalido rifiutato'
);

-- ============================================================
-- 5) available_actions MISTO: can_push = true, reason NULL
-- ============================================================
SELECT ok(
  (SELECT (j->>'can_push_commessa')::boolean IS TRUE
      AND (j->>'can_push_commessa_reason') IS NULL
     FROM (SELECT script.fn_available_actions_preventivo((SELECT id FROM tmp_rc_misto)) AS j) s),
  '5. Misto ACCETTATO: can_push_commessa=true, reason NULL'
);

-- ============================================================
-- 6) available_actions SOLO MERCE: reason NESSUNA_RIGA_COMMESSA
-- ============================================================
SELECT ok(
  (SELECT (j->>'can_push_commessa')::boolean IS FALSE
      AND (j->>'can_push_commessa_reason') = 'PREVENTIVO_NESSUNA_RIGA_COMMESSA'
      -- rev 2026-10-08: la chiave porta il prefisso vendite. dal 2026-07-19
      -- (radici i18n uniformi); il test era rimasto alla forma vecchia.
      AND (j->>'can_push_commessa_reason_key') = 'vendite.preventivi.push_commessa_reason.nessuna_riga'
     FROM (SELECT script.fn_available_actions_preventivo((SELECT id FROM tmp_rc_merce)) AS j) s),
  '6. Solo merce ACCETTATO: can_push=false, reason PREVENTIVO_NESSUNA_RIGA_COMMESSA'
);

-- ============================================================
-- 8) Post-push: riga servizio EMESSA in commessa -> residuo false
--    (la merce residua non conta sul ramo commessa)
-- ============================================================
-- ⭐ rev 2026-10-24 (Q-4): la commessa nasce dalla madre del dominio
--   (dbops.fn_pgtap_crea_commessa), sul cliente del mondo, nello stato
--   iniziale: emittente e whitelist d'accordo per costruzione. Prima era un
--   INSERT diretto col primo stato commessa per id. Le attivita' dei casi
--   8, 10 e 12 le scrive il builder (rev §4-octies); l'11 resta qui.
CREATE TEMP TABLE tmp_rc_commessa AS
SELECT c.commessa_id AS id
  FROM dbops.fn_pgtap_crea_commessa('residuo commessa', NULL,
         (SELECT billing_account_id FROM tmp_rc_refs)) c;

-- rev 2026-10-24 (§4-octies): l'attivita' EMESSA della riga di servizio la
--   scrive il builder con la sorgente; la chiave la compone il dominio.
CREATE TEMP TABLE tmp_rc_att8 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_rc_commessa),
    p_prezzo_snapshot    => 30.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_rc_refs),
    p_sorgente_codice    => 'PREVENTIVO',
    p_sorgente_uid       => (SELECT uid::text FROM tmp_rc_misto),
    p_sorgente_riga_id   => (SELECT id FROM tmp_rc_riga_serv),
    p_quantita           => 2,
    p_stato_approvazione => 'BOZZA',
    p_stato_emissione    => 'EMESSA',
    p_competenza_dal     => DATE '2080-01-01',
    p_competenza_al      => DATE '2080-12-31');

SELECT is(
  vendite.fn_preventivo_ha_residuo_commessa((SELECT id FROM tmp_rc_misto)),
  false,
  '8. Post-push (servizio EMESSO): residuo commessa = false anche con merce residua'
);

-- ============================================================
-- 9) available_actions DRAFT: reason PREVENTIVO_NON_ACCETTATO
-- ============================================================
SELECT ok(
  (SELECT (j->>'can_push_commessa')::boolean IS FALSE
      AND (j->>'can_push_commessa_reason') = 'PREVENTIVO_NON_ACCETTATO'
     FROM (SELECT script.fn_available_actions_preventivo((SELECT id FROM tmp_rc_draft)) AS j) s),
  '9. DRAFT: can_push=false, reason PREVENTIVO_NON_ACCETTATO'
);

-- ============================================================
-- Setup casi 10-12: tre preventivi servizio (BA ok), riusano la
-- commessa del caso 8 (tmp_rc_commessa) con segment_key distinti.
-- Helper inline: crea preventivo+riga servizio, ritorna id/uid/riga_id.
-- ============================================================
-- ⛔ TESTATA E RIGA IN DUE STATEMENT, e non e' uno stile.
--   Fino al 2026-09-09 questi tre blocchi erano una CTE sola
--   (`WITH p AS (INSERT INTO preventivi …), rg AS (INSERT INTO
--   preventivi_righe …)`). Da quando `vendite.preventivi_righe` ha la sua
--   policy (slice 20260909-27..30) quella forma NON PUO' funzionare: le CTE che
--   scrivono condividono la stessa snapshot, quindi il preventivo appena
--   inserito NON e' visibile al ramo che inserisce la riga. La policy della
--   riga risolve il perimetro passando dalla testata
--   (`fn_scope_ef_whitelist_via_preventivo`), non la trova, e il `WITH CHECK`
--   nega — fail-closed, che e' il comportamento giusto.
--   ⚠️ Il sintomo mente: l'errore parla della RIGA e sembra un problema di
--   whitelist. E' visibilita' dentro lo statement. ⛔ Non si corregge la policy:
--   nel percorso applicativo la testata nasce in uno step e le righe in quello
--   dopo. ⭐ In `LANGUAGE sql` non c'e' modo di concatenare due scritture se non
--   con una CTE: serve plpgsql con due INSERT e una variabile in mezzo.
CREATE TEMP TABLE tmp_rc_nonemessa (prev_id bigint, prev_uid uuid, riga_id bigint);
CREATE TEMP TABLE tmp_rc_bom       (prev_id bigint, prev_uid uuid, riga_id bigint);
CREATE TEMP TABLE tmp_rc_annull    (prev_id bigint, prev_uid uuid, riga_id bigint);

DO $servizio$
DECLARE
    r          record;
    caso       record;
    v_prev_id  vendite.preventivi.id%TYPE;
    v_prev_uid vendite.preventivi.uid%TYPE;
    v_riga_id  vendite.preventivi_righe.id%TYPE;
BEGIN
    SELECT * INTO r FROM tmp_rc_refs;

    FOR caso IN
        SELECT * FROM (VALUES
            ('tmp_rc_nonemessa', 'pgtap_residuo_nonemessa'),
            ('tmp_rc_bom',       'pgtap_residuo_bom'),
            ('tmp_rc_annull',    'pgtap_residuo_annull')
        ) AS v(tabella, scope)
    LOOP
        -- 1) La testata.
        INSERT INTO vendite.preventivi (
            billing_account_id, istanza_utility_id, utility_id,
            validita_dal, validita_al, valuta_id, data,
            fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
        VALUES (
            r.billing_account_id, r.istanza_utility_id, r.utility_id,
            DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
            DATE '2080-01-01', false, false,
            jsonb_build_object('test_scope', caso.scope), r.emittente_fiscale_id)
        RETURNING id, uid INTO v_prev_id, v_prev_uid;

        -- 2) La riga: statement SUO, cosi' la policy vede la testata.
        INSERT INTO vendite.preventivi_righe
            (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
        VALUES (v_prev_id, r.art_serv_id, 1.000000, 25.000000, r.iva_id, true)
        RETURNING id INTO v_riga_id;

        -- 3) Poi la transizione: in bozza la riga, fuori bozza piu' niente.
        PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', v_prev_id, 'ACCETTATO');

        EXECUTE format('INSERT INTO %I VALUES ($1, $2, $3)', caso.tabella)
          USING v_prev_id, v_prev_uid, v_riga_id;
    END LOOP;
END
$servizio$;

-- Attivita NON_EMESSA con la chiave esatta della riga (caso 10): dal builder.
CREATE TEMP TABLE tmp_rc_att10 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_rc_commessa),
    p_prezzo_snapshot    => 25.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_rc_refs),
    p_sorgente_codice    => 'PREVENTIVO',
    p_sorgente_uid       => (SELECT prev_uid::text FROM tmp_rc_nonemessa),
    p_sorgente_riga_id   => (SELECT riga_id FROM tmp_rc_nonemessa),
    p_quantita           => 1,
    p_stato_approvazione => 'BOZZA',
    p_stato_emissione    => 'NON_EMESSA',
    p_competenza_dal     => DATE '2080-01-01',
    p_competenza_al      => DATE '2080-12-31');

-- Attivita NON_EMESSA con segment_key componente BoM '#CMP:<id>' (caso 11)
-- ⚠️ rev 2026-10-24 (§4-octies): resta scritta a mano, perche' la chiave col
--   suffisso #CMP e' il caso (il match a prefisso) e il builder non la scrive;
--   la base <sorgente>:<uid>:R:<riga> la compone pero' script.fn_segment_key
--   (il suffisso lo aggiunge chi scrive la riga, come nel dominio).
INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al, tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
SELECT (SELECT id FROM tmp_rc_commessa),
  script.fn_segment_key('PREVENTIVO', (SELECT prev_uid FROM tmp_rc_bom)::text, (SELECT riga_id FROM tmp_rc_bom)) || '#CMP:999',
  r.art_serv_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 1,
  DATE '2080-01-01', DATE '2080-01-01', DATE '2080-12-31', r.tipo_doc_fiscale_id, r.valuta_id, 25.000000,
  'FIXED', 'BOZZA', 'NON_EMESSA',
  r.sorgente_preventivo_id,
  (SELECT prev_uid FROM tmp_rc_bom)::text
FROM tmp_rc_refs r;

-- Attivita ANNULLATA con la chiave esatta della riga (caso 12): dal builder.
CREATE TEMP TABLE tmp_rc_att12 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_rc_commessa),
    p_prezzo_snapshot    => 25.000000,
    p_articolo_id        => (SELECT art_serv_id FROM tmp_rc_refs),
    p_sorgente_codice    => 'PREVENTIVO',
    p_sorgente_uid       => (SELECT prev_uid::text FROM tmp_rc_annull),
    p_sorgente_riga_id   => (SELECT riga_id FROM tmp_rc_annull),
    p_quantita           => 1,
    p_stato_approvazione => 'BOZZA',
    p_stato_emissione    => 'ANNULLATA',
    p_competenza_dal     => DATE '2080-01-01',
    p_competenza_al      => DATE '2080-12-31');

-- Le righe scritte davvero, ciascuna sulla chiave della sua riga e nello
-- stato del caso (controllo, non test: niente verde per sottrazione).
DO $chk$ BEGIN
  IF (SELECT count(*) FROM vendite.commesse_attivita ca
        JOIN (SELECT attivita_id, 'EMESSA' AS st,
                     script.fn_segment_key('PREVENTIVO', (SELECT uid::text FROM tmp_rc_misto),
                                           (SELECT id FROM tmp_rc_riga_serv)) AS k FROM tmp_rc_att8
              UNION ALL
              SELECT attivita_id, 'NON_EMESSA',
                     script.fn_segment_key('PREVENTIVO', (SELECT prev_uid::text FROM tmp_rc_nonemessa),
                                           (SELECT riga_id FROM tmp_rc_nonemessa)) FROM tmp_rc_att10
              UNION ALL
              SELECT attivita_id, 'ANNULLATA',
                     script.fn_segment_key('PREVENTIVO', (SELECT prev_uid::text FROM tmp_rc_annull),
                                           (SELECT riga_id FROM tmp_rc_annull)) FROM tmp_rc_att12) t
          ON t.attivita_id = ca.id AND ca.segment_key = t.k AND ca.stato_emissione = t.st) <> 3 THEN
    RAISE EXCEPTION 'fixture: attese 3 attivita'' dal builder (casi 8, 10, 12)';
  END IF;
END $chk$;

-- ============================================================
-- 10) NON_EMESSA -> residuo = false (IL FIX: esclusa appena instradata)
-- ============================================================
SELECT is(
  vendite.fn_preventivo_ha_residuo_commessa((SELECT prev_id FROM tmp_rc_nonemessa)),
  false,
  '10. Post-push NON_EMESSA: residuo commessa = false (fix gate EVASO)'
);

-- ============================================================
-- 11) Componente BoM (#CMP) NON_EMESSA -> residuo = false (match a prefisso)
-- ============================================================
SELECT is(
  vendite.fn_preventivo_ha_residuo_commessa((SELECT prev_id FROM tmp_rc_bom)),
  false,
  '11. Post-push componente BoM (#CMP): residuo commessa = false (match prefisso §4)'
);

-- ============================================================
-- 12) Attivita ANNULLATA -> residuo = true (D-5: la riga ritirata non occupa)
-- ============================================================
SELECT is(
  vendite.fn_preventivo_ha_residuo_commessa((SELECT prev_id FROM tmp_rc_annull)),
  true,
  '12. Attivita ANNULLATA: residuo commessa = true (D-5: una riga ritirata non occupa, la riga torna da mandare)'
);

SELECT * FROM finish();
ROLLBACK;
