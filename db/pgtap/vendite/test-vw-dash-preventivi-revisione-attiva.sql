-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d): l'area della dashboard e' il codice della sorgente.
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima le
--   revisioni nascevano gia' EMESSO/RIFIUTATO/ANNULLATO).
-- rev 2026-10-24 (brief-modello-documento-vendita Q-4): cliente ed emittente
--   dal mondo costruito (dbops.fn_pgtap_crea_mondo_cliente), l'operatore e'
--   quello del contesto: prima si pescavano dal database il primo billing
--   account, il primo emittente e il primo operatore, che su un database
--   ricostruito non ci sono.
-- rev 2026-10-24 (brief-modello-documento-vendita R-6/Q-4): le revisioni
--   nascono per la strada del dominio. Ogni numero e' un preventivo di
--   dbops.fn_pgtap_crea_preventivo (numero assegnato dal dominio), portato
--   allo stato dal builder; la rev 1 nasce da vendite.fn_crea_revisione_preventivo
--   sulla rev 0 EMESSO e poi si porta allo stato del caso. Prima erano INSERT
--   diretti in vendite.preventivi con numero e rev fissati (PGTAP-REVATT-*).
--   Le asserzioni sul numero letterale (4, 8, 10, 11, 12) leggono ora il
--   numero COSTRUITO (tmp_ra_numeri, da vendite.preventivi): provano le stesse
--   cose (sola revisione attiva nei cruscotti).
-- pgTAP test per Zero ERP
--
-- Test: regressione bug di vista "la vecchia revisione EMESSO riemerge come
--       documento aperto nei cruscotti" (brief-db-preventivi-revisione-attiva-
--       dashboard, fix 20260708-06 Opzione A).
--
--       Invariante: i resolver/union dashboard preventivi devono esporre SOLO
--       la revisione attiva del numero (derivazione canonica
--       vw_preventivi.is_attiva), MAI le revisioni superate rimaste in EMESSO.
--
--       Il fix cambia la SORGENTE di vw_dash_fatturazione_preventivi da
--       vendite.preventivi grezzo a vendite.vw_preventivi WHERE is_attiva.
--       Non introduce lo stato SUPERATO -> preserva il flusso voluto
--       "revisione annullata rifluisce al predecessore" (gestione-preventivi
--       §4.3), testato dallo scenario B.
--
--       Fixture (rev 2026-10-24, R-6: preventivi del builder, numero dal
--       dominio, rev 1 da vendite.fn_crea_revisione_preventivo):
--         A) numero A: rev0 EMESSO + rev1 RIFIUTATO
--            -> attiva = rev1 (negativa) -> 0 righe backlog/aperto, 1 sola riga
--               (RIFIUTATO) nella union; la rev0 EMESSO NON deve comparire.
--         B) numero B: rev0 EMESSO + rev1 ANNULLATO
--            -> ANNULLATO e' abortito -> attiva = rev0 EMESSO (revert-on-abandon)
--               -> 1 riga = rev0 EMESSO; la rev1 ANNULLATO NON deve comparire.
--         C) numero C: rev0 EMESSO singola -> compare 1 volta (no regressione).
--
-- Indice test (0..11):
--   0)  Precondizioni: refs minimi (BA, emittente, valuta, stati)
--   1)  Vista vw_dash_fatturazione_preventivi + derivazione vw_preventivi.is_attiva
--   2)  Scope operatore: quello del contesto vede l'emittente dei fixture
--   3)  A: vw_preventivi.is_attiva canonico (rev1 attiva, rev0 no)
--   4)  A: union espone SOLO la rev attiva (1 riga, stato RIFIUTATO, no EMESSO)
--   5)  A: backlog = 0 righe per il numero
--   6)  A: situazione aperta = 0 righe per il numero
--   7)  B: is_attiva unico e allineato a §4.3 (rev0 attiva, rev1 ANNULLATO no)
--   8)  B: union espone SOLO rev0 EMESSO (1 riga, no ANNULLATO)
--   9)  B: backlog espone rev0 EMESSO come IN_ATTESA_ACCETTAZIONE
--   10) C: preventivo singola-rev EMESSO compare 1 volta (no regressione)
--   11) D: preventivo singola-rev ANNULLATO -> is_attiva=FALSE e assente dalla
--       union (nuovo comportamento voluto dal self-term 20260708-07)
--   12) Invariante generale: nessun documento_id area PREVENTIVI non-attivo
--       nella union (per i fixture del test)
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

SELECT plan(13);

-- ============================================================
-- 0) Riferimenti minimi
-- ============================================================
-- ⭐ rev 2026-10-24 (Q-4, R-6): il cliente e l'emittente si COSTRUISCONO,
--   e con loro i preventivi. Ogni numero del test e' un preventivo di
--   dbops.fn_pgtap_crea_preventivo, che col contesto gia' aperto riusa
--   l'azienda di chi agisce e le lega un cliente nuovo: emittente e BA vanno
--   d'accordo per costruzione. Il builder porta la rev 0 allo stato del caso
--   (EMESSO, o ANNULLATO per D) per la matrice: l'emissione oggi non pretende
--   righe, e il test non ne ha bisogno. ⛔ Cio' che il builder scrive si legge
--   in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_ra_a AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('dash revisione attiva A', 'EMESSO');
CREATE TEMP TABLE tmp_ra_b AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('dash revisione attiva B', 'EMESSO');
CREATE TEMP TABLE tmp_ra_c AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('dash revisione attiva C', 'EMESSO');
CREATE TEMP TABLE tmp_ra_d AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('dash revisione attiva D', 'ANNULLATO');

CREATE TEMP TABLE tmp_ra_refs AS
SELECT
  a.billing_account_id,
  a.valuta_id,
  a.emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'EMESSO' AND s.attivo IS TRUE) AS st_emesso_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'RIFIUTATO' AND s.attivo IS TRUE) AS st_rifiutato_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ANNULLATO' AND s.attivo IS TRUE) AS st_annullato_id
FROM tmp_ra_a a;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND emittente_fiscale_id IS NOT NULL
      AND valuta_id IS NOT NULL AND st_emesso_id IS NOT NULL
      AND st_rifiutato_id IS NOT NULL AND st_annullato_id IS NOT NULL
     FROM tmp_ra_refs),
  '0. Precondizioni: refs minimi presenti (BA, emittente, valuta, stati EMESSO/RIFIUTATO/ANNULLATO)'
);

-- ============================================================
-- 1) Vista union sorgente + derivazione canonica esistono
-- ============================================================
SELECT ok(
  EXISTS (SELECT 1 FROM pg_views
           WHERE schemaname = 'vendite'
             AND viewname   = 'vw_dash_fatturazione_preventivi')
  AND EXISTS (SELECT 1 FROM information_schema.columns c
               WHERE c.table_schema = 'vendite'
                 AND c.table_name   = 'vw_preventivi'
                 AND c.column_name  = 'is_attiva'),
  '1. vw_dash_fatturazione_preventivi esiste e vw_preventivi espone is_attiva (derivazione canonica)'
);

-- ============================================================
-- 2) Setup scope operatore: la union include il ramo commesse che scopa per
--    current_setting(app.current_user_id) -> serve una GUC valida.
-- ⭐ rev 2026-10-24 (Q-4): l'operatore e' quello del CONTESTO, la cui azienda
--   e' l'emittente del mondo costruito: e' gia' nel suo scope. Prima si
--   pescava «il primo OPERATORE non super admin» delle identita' e gli si
--   riscriveva config.user_emittenti_fiscali sul primo emittente del
--   database: su un database ricostruito non c'era nessuno dei due.
-- ============================================================
CREATE TEMP TABLE tmp_ra_op AS
SELECT nullif(current_setting('app.current_user_id', true), '')::integer AS user_id;

SELECT ok(
  (SELECT o.user_id IS NOT NULL
      AND script.fn_has_identita_attiva(o.user_id, 'OPERATORE'::config.ruolo_applicativo)
      AND NOT script.fn_is_super_admin(o.user_id)
      AND (SELECT bool_and(x.emittente_fiscale_id = script.fn_pgtap_emittente_operatore())
             FROM (SELECT emittente_fiscale_id FROM tmp_ra_a
                   UNION ALL SELECT emittente_fiscale_id FROM tmp_ra_b
                   UNION ALL SELECT emittente_fiscale_id FROM tmp_ra_c
                   UNION ALL SELECT emittente_fiscale_id FROM tmp_ra_d) x)
     FROM tmp_ra_op o),
  '2. L''operatore del contesto e'' un OPERATORE non-super con l''emittente dei fixture nello scope'
);

-- ============================================================
-- Fixture (rev 2026-10-24, R-6: la strada del dominio). Le rev 0 sono i
--   preventivi del builder, gia' nello stato del caso. La rev 1 di A e di B
--   nasce da vendite.fn_crea_revisione_preventivo sulla rev 0 EMESSO (stesso
--   numero, rev 1, in bozza) e si porta allo stato del caso per la matrice:
--   RIFIUTATO passa da EMESSO; ANNULLATO esce direttamente dalla bozza.
--   A) rev0 EMESSO + rev1 RIFIUTATO (attiva = rev1)
--   B) rev0 EMESSO + rev1 ANNULLATO (attiva = rev0)
--   C) rev0 EMESSO singola (no regressione)
--   D) rev0 ANNULLATO singola (annullato = non attivo, fuori dai cruscotti)
-- ============================================================
CREATE TEMP TABLE tmp_ra_a_rev0 AS SELECT preventivo_id AS id FROM tmp_ra_a;
CREATE TEMP TABLE tmp_ra_b_rev0 AS SELECT preventivo_id AS id FROM tmp_ra_b;
CREATE TEMP TABLE tmp_ra_c_rev0 AS SELECT preventivo_id AS id FROM tmp_ra_c;
CREATE TEMP TABLE tmp_ra_d_rev0 AS SELECT preventivo_id AS id FROM tmp_ra_d;

CREATE TEMP TABLE tmp_ra_a_rev1 AS
SELECT nuovo_preventivo_id AS id
  FROM vendite.fn_crea_revisione_preventivo((SELECT id FROM tmp_ra_a_rev0), 'pgtap');
CREATE TEMP TABLE tmp_ra_b_rev1 AS
SELECT nuovo_preventivo_id AS id
  FROM vendite.fn_crea_revisione_preventivo((SELECT id FROM tmp_ra_b_rev0), 'pgtap');

DO $porta$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_ra_a_rev1), 'RIFIUTATO');
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_ra_b_rev1), 'ANNULLATO');
END $porta$;

-- Il numero di ogni caso, COSTRUITO dal dominio e letto da vendite.preventivi:
--   e' cio' che la union espone come codice. Prima era il letterale
--   PGTAP-REVATT-<caso>.
CREATE TEMP TABLE tmp_ra_numeri AS
SELECT 'A'::text AS caso, p.numero FROM vendite.preventivi p WHERE p.id = (SELECT id FROM tmp_ra_a_rev0)
UNION ALL
SELECT 'B', p.numero FROM vendite.preventivi p WHERE p.id = (SELECT id FROM tmp_ra_b_rev0)
UNION ALL
SELECT 'C', p.numero FROM vendite.preventivi p WHERE p.id = (SELECT id FROM tmp_ra_c_rev0)
UNION ALL
SELECT 'D', p.numero FROM vendite.preventivi p WHERE p.id = (SELECT id FROM tmp_ra_d_rev0);

-- ============================================================
-- 3) A: derivazione canonica corretta (rev1 attiva, rev0 no)
-- ============================================================
SELECT ok(
  (SELECT is_attiva FROM vendite.vw_preventivi WHERE id = (SELECT id FROM tmp_ra_a_rev1)) IS TRUE
  AND
  (SELECT is_attiva FROM vendite.vw_preventivi WHERE id = (SELECT id FROM tmp_ra_a_rev0)) IS FALSE,
  '3. A: vw_preventivi.is_attiva = rev1 RIFIUTATO attiva, rev0 EMESSO non attiva'
);

-- ============================================================
-- 4) A: union espone SOLO la revisione attiva (1 riga, RIFIUTATO, no EMESSO)
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1
      AND bool_and(d.stato_codice_interno = 'RIFIUTATO')
      AND count(*) FILTER (WHERE d.stato_codice_interno = 'EMESSO') = 0
     FROM vendite.vw_dash_fatturazione_documenti d
    WHERE d.area = 'PREVENTIVO' AND d.codice = (SELECT numero FROM tmp_ra_numeri WHERE caso = 'A')),
  '4. A: la union mostra 1 sola riga = rev attiva RIFIUTATO; la rev0 EMESSO superata NON compare (no fantasma)'
);

-- ============================================================
-- 5) A: backlog = 0 righe (rev attiva negativa -> esclusa; nessun fantasma)
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area = 'PREVENTIVO'
      AND b.documento_id IN ((SELECT id FROM tmp_ra_a_rev0), (SELECT id FROM tmp_ra_a_rev1))),
  0,
  '5. A: Backlog = 0 righe per il numero (rev attiva RIFIUTATA esclusa, rev0 EMESSO non piu'' fantasma)'
);

-- ============================================================
-- 6) A: situazione aperta = 0 righe
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_aperto_documenti a
    WHERE a.area = 'PREVENTIVO'
      AND a.documento_id IN ((SELECT id FROM tmp_ra_a_rev0), (SELECT id FROM tmp_ra_a_rev1))),
  0,
  '6. A: Situazione aperta = 0 righe per il numero (nessuna riga fantasma)'
);

-- ============================================================
-- 7) B: is_attiva unico e allineato alla spec (gestione-preventivi §4.3) dopo
--    il self-term (20260708-07): rev0 EMESSO attiva (revert-on-abandon: il
--    predecessore torna il documento vivo), rev1 ANNULLATO NON attiva (il suo
--    stato e' abortito, non si auto-dichiara piu' attiva stando in cima).
-- ============================================================
SELECT ok(
  (SELECT is_attiva FROM vendite.vw_preventivi WHERE id = (SELECT id FROM tmp_ra_b_rev0)) IS TRUE
  AND
  (SELECT is_attiva FROM vendite.vw_preventivi WHERE id = (SELECT id FROM tmp_ra_b_rev1)) IS FALSE,
  '7. B: vw_preventivi.is_attiva = rev0 EMESSO attiva (revert-on-abandon), rev1 ANNULLATO non attiva'
);

-- ============================================================
-- 8) B: union espone SOLO rev0 EMESSO (1 riga); la rev1 ANNULLATO, ora
--    is_attiva=FALSE, e' filtrata dal predicato WHERE is_attiva del resolver.
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1
      AND bool_and(d.stato_codice_interno = 'EMESSO')
      AND bool_and(d.documento_id = (SELECT id FROM tmp_ra_b_rev0))
     FROM vendite.vw_dash_fatturazione_documenti d
    WHERE d.area = 'PREVENTIVO' AND d.codice = (SELECT numero FROM tmp_ra_numeri WHERE caso = 'B')),
  '8. B: la union mostra 1 sola riga = rev0 EMESSO (predecessore vivo); la rev1 ANNULLATO NON compare'
);

-- ============================================================
-- 9) B: backlog espone rev0 EMESSO come IN_ATTESA_ACCETTAZIONE
-- ============================================================
SELECT ok(
  (SELECT b.motivo_fermo = 'IN_ATTESA_ACCETTAZIONE'
     FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area = 'PREVENTIVO'
      AND b.documento_id = (SELECT id FROM tmp_ra_b_rev0))
  AND NOT EXISTS (
    SELECT 1 FROM vendite.vw_dash_backlog_documenti b
     WHERE b.area = 'PREVENTIVO'
       AND b.documento_id = (SELECT id FROM tmp_ra_b_rev1)),
  '9. B: Backlog espone rev0 EMESSO (IN_ATTESA_ACCETTAZIONE); la rev1 ANNULLATO assente'
);

-- ============================================================
-- 10) C: preventivo singola-rev EMESSO compare 1 volta (no regressione)
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_fatturazione_documenti d
    WHERE d.area = 'PREVENTIVO' AND d.codice = (SELECT numero FROM tmp_ra_numeri WHERE caso = 'C')),
  1,
  '10. C: preventivo singola-rev EMESSO compare esattamente 1 volta (nessuna regressione sul caso normale)'
);

-- ============================================================
-- 11) D: preventivo ANNULLATO singola-rev -> is_attiva=FALSE (self-term) e
--     assente dalla union (il resolver filtra WHERE is_attiva).
-- ============================================================
SELECT ok(
  (SELECT is_attiva FROM vendite.vw_preventivi
    WHERE id = (SELECT id FROM tmp_ra_d_rev0)) IS FALSE
  AND
  (SELECT count(*)::integer FROM vendite.vw_dash_fatturazione_documenti d
    WHERE d.area = 'PREVENTIVO' AND d.codice = (SELECT numero FROM tmp_ra_numeri WHERE caso = 'D')) = 0,
  '11. D: annullato singola-rev is_attiva=FALSE e fuori dalla union (annullato = non attivo)'
);

-- ============================================================
-- 12) Invariante generale: ogni documento_id (area PREVENTIVI) esposto dalla
--     union per i fixture del test e' la revisione attiva secondo vw_preventivi.
-- ============================================================
SELECT is(
  (SELECT count(*)::integer
     FROM vendite.vw_dash_fatturazione_documenti d
     JOIN vendite.vw_preventivi p ON p.id = d.documento_id
    WHERE d.area = 'PREVENTIVO'
      AND d.codice IN (SELECT numero FROM tmp_ra_numeri)
      AND p.is_attiva IS FALSE),
  0,
  '12. Invariante: nessuna revisione non-attiva compare nella union dashboard'
);

SELECT * FROM finish();
ROLLBACK;
