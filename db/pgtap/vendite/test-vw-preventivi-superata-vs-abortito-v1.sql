-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.vw_preventivi / vendite.vw_preventivi_lista — le DUE domande
--       che `is_attiva` teneva insieme sono ora colonne distinte
--       (changeSet 20260828-08 / 20260828-09, brief-db-revisione-attiva-due-domande).
--
--       L'invariante in prova non e' «is_attiva e' giusta» — quella non cambia,
--       e il self-term del 20260708-07 resta. E' che a valle si possa chiedere
--       «e' l'ultima revisione?» (`is_superata IS FALSE`) SENZA chiedere anche
--       «e non e' annullato». Prima non si poteva, e il filtro di stato
--       «Annullato» della lista era vuoto per costruzione.
--
--       ⭐ Il test COSTRUISCE i tre casi che distinguono i predicati: non li
--       cerca fra i dati esistenti. Su un DB ricostruito da zero verifica le
--       stesse cose.
--
--       Fixture (rev 2026-10-24, R-6: preventivi del builder, numero dal
--       dominio, rev 1 da vendite.fn_crea_revisione_preventivo):
--         A) numero A: rev0 EMESSO + rev1 ANNULLATO
--            -> rev1 e' l'ULTIMA revisione e non e' superata da nessuno, ma e'
--               abortita: is_superata=F, is_abortito=T, is_attiva=F.
--               rev0 e' la viva: is_superata=F (l'abortita non rimpiazza),
--               is_abortito=F, has_next_revisione=T, is_attiva=T.
--         B) numero B: rev0 ANNULLATO, revisione unica
--            -> e' il caso del collaudo (PRV0000133): is_superata=F —
--               «e' l'ultima revisione» e' VERO — ma is_attiva=F. Con il solo
--               is_attiva il documento non era raggiungibile da nessun filtro.
--         C) numero C: rev0 EMESSO + rev1 EMESSO
--            -> superamento vero: rev0 is_superata=T, rev1 is_superata=F.
--
-- Indice test (0..11):
--   0)  Precondizioni: refs minimi (BA, emittente, valuta, stati)
--   1)  Struttura: vw_preventivi espone is_superata, is_abortito, has_next_revisione
--   2)  Scope operatore: quello del contesto vede l'emittente dei fixture
--   3)  A rev0: viva e non superata, ma con una revisione successiva abortita
--   4)  A rev1: ultima revisione (non superata) E abortita -> is_attiva=F
--   5)  B rev0: annullato a revisione unica -> is_superata=F, is_attiva=F
--   6)  C rev0: superata da una rev viva -> is_superata=T, is_attiva=F
--   7)  C rev1: la viva del numero -> is_superata=F, is_attiva=T
--   8)  Invariante di composizione: is_attiva = NOT is_abortito AND NOT is_superata
--   9)  Unicita' invariata: al piu' una rev is_attiva per numero
--   10) ⭐ I due predicati NON coincidono: «solo l'ultima revisione» rende 4
--       righe, is_attiva ne rende 2 — e le 2 che mancano sono gli annullati
--   11) Propagazione: vw_preventivi_lista espone le tre colonne, riga per riga
--       uguali a vw_preventivi
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima le
--   revisioni nascevano gia' EMESSO/ANNULLATO).
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
--   diretti in vendite.preventivi con numero e rev fissati (PGTAP-SUPABO-*).
--   Le asserzioni sul numero letterale (3..11) leggono ora il numero
--   COSTRUITO (tmp_sa_numeri, da vendite.preventivi): provano le stesse cose
--   (superata vs abortita), con le stesse attese.
-- rev 2026-10-25 (brief-modello-documento-vendita §8, giro 6): le rev 0 EMESSO
--   (A, C) vengono da dbops.fn_pgtap_crea_preventivo_con_righe. Lo stato ora
--   passa dal verbo sotto la porta e l'emissione chiede almeno una riga
--   attiva: senza righe la fixture si fermava su E_PREV_NESSUNA_RIGA_ATTIVA.
--   La rev 1 di C copia la riga dalla rev 0 e si emette con quella. B
--   (ANNULLATO dalla bozza) resta senza righe. Il builder con le righe non
--   restituisce la valuta: i riferimenti la leggono dalla testata. Le
--   asserzioni contano revisioni, non righe: invariate.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Le viste sono security_invoker=on:
-- senza contesto, non si esercita nulla di cio' che l'applicazione vede.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- ============================================================
-- 0) Riferimenti minimi
-- ============================================================
-- ⭐ rev 2026-10-24 (Q-4): il cliente e l'emittente si COSTRUISCONO. Prima
--   erano «il primo billing account» e «il primo emittente attivo» del
--   database: su uno ricostruito da zero non c'erano e il file moriva al primo
--   INSERT. dbops.fn_pgtap_crea_mondo_cliente, col contesto gia' aperto, riusa
--   l'azienda di chi agisce e le lega un cliente nuovo: emittente e BA vanno
--   d'accordo per costruzione. ⛔ Cio' che il builder scrive si legge in
--   un'istruzione SEPARATA.
-- ⭐ rev 2026-10-24 (R-6): ogni numero e' un preventivo del builder, con
--   la rev 0 gia' nello stato del caso (per la matrice).
-- ⚠️ rev 2026-10-25 (giro 6): l'emissione pretende una riga attiva (guard di
--   transizione): le rev 0 EMESSO vengono dal builder con le righe. B esce
--   dalla bozza verso ANNULLATO, che righe non ne chiede.
CREATE TEMP TABLE tmp_sa_a AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo_con_righe('superata vs abortito A', 'EMESSO');
CREATE TEMP TABLE tmp_sa_b AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('superata vs abortito B', 'ANNULLATO');
CREATE TEMP TABLE tmp_sa_c AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo_con_righe('superata vs abortito C', 'EMESSO');

CREATE TEMP TABLE tmp_sa_refs AS
SELECT
  a.billing_account_id,
  -- rev 2026-10-25: il builder con le righe non restituisce la valuta; si
  --   legge dalla testata che ha costruito.
  (SELECT p.valuta_id FROM vendite.preventivi p WHERE p.id = a.preventivo_id) AS valuta_id,
  a.emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'EMESSO' AND s.attivo IS TRUE) AS st_emesso_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ANNULLATO' AND s.attivo IS TRUE) AS st_annullato_id
FROM tmp_sa_a a;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND emittente_fiscale_id IS NOT NULL
      AND valuta_id IS NOT NULL AND st_emesso_id IS NOT NULL
      AND st_annullato_id IS NOT NULL
     FROM tmp_sa_refs),
  '0. Precondizioni: refs minimi presenti (BA, emittente, valuta, stati EMESSO/ANNULLATO)'
);

-- ============================================================
-- 1) Struttura: le tre colonne esistono
--    ⚠️ Si verifica PRIMA di qualunque asserzione sui valori: se mancano, il
--    resto fallirebbe con un errore di colonna inesistente e il messaggio non
--    direbbe che il changeSet non e' applicato.
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name   = 'vw_preventivi'
      AND c.column_name IN ('is_attiva', 'is_superata', 'is_abortito', 'has_next_revisione')),
  4,
  '1. vw_preventivi espone is_attiva + le due componenti (is_superata, is_abortito) + has_next_revisione'
);

-- ============================================================
-- 2) Setup scope operatore: le viste sono security_invoker, l'emittente dei
--    fixture deve essere nello scope o la RLS le rende invisibili (e un
--    conteggio a zero passerebbe per «non c'e'» invece che per «non lo vedo»).
-- ⭐ rev 2026-10-24 (Q-4): l'operatore e' quello del CONTESTO, la cui azienda
--   e' l'emittente del mondo costruito: e' gia' nel suo scope. Prima si
--   pescava «il primo OPERATORE non super admin» delle identita' e gli si
--   riscriveva config.user_emittenti_fiscali sul primo emittente del
--   database: su un database ricostruito non c'era nessuno dei due.
-- ============================================================
CREATE TEMP TABLE tmp_sa_op AS
SELECT nullif(current_setting('app.current_user_id', true), '')::integer AS user_id;

SELECT ok(
  (SELECT o.user_id IS NOT NULL
      AND script.fn_has_identita_attiva(o.user_id, 'OPERATORE'::config.ruolo_applicativo)
      AND NOT script.fn_is_super_admin(o.user_id)
      AND (SELECT bool_and(x.emittente_fiscale_id = script.fn_pgtap_emittente_operatore())
             FROM (SELECT emittente_fiscale_id FROM tmp_sa_a
                   UNION ALL SELECT emittente_fiscale_id FROM tmp_sa_b
                   UNION ALL SELECT emittente_fiscale_id FROM tmp_sa_c) x)
     FROM tmp_sa_op o),
  '2. L''operatore del contesto e'' un OPERATORE non-super con l''emittente dei fixture nello scope'
);

-- ============================================================
-- Fixture: tre numeri, cinque revisioni
-- ⚠️ rev 2026-10-24 (R-6, la strada del dominio): le rev 0 sono i preventivi
--   del builder, gia' nello stato del caso. La rev 1 di A e di C nasce da
--   vendite.fn_crea_revisione_preventivo sulla rev 0 EMESSO (stesso numero,
--   rev 1, in bozza) e si porta allo stato del caso per la matrice, sotto i
--   guard veri. ANNULLATO esce direttamente dalla bozza (DRAFT -> ANNULLATO).
--   A) rev0 EMESSO + rev1 ANNULLATO
--   B) rev0 ANNULLATO, revisione unica
--   C) rev0 EMESSO + rev1 EMESSO
-- ============================================================
CREATE TEMP TABLE tmp_sa_a_rev1 AS
SELECT nuovo_preventivo_id AS id
  FROM vendite.fn_crea_revisione_preventivo((SELECT preventivo_id FROM tmp_sa_a), 'pgtap');
CREATE TEMP TABLE tmp_sa_c_rev1 AS
SELECT nuovo_preventivo_id AS id
  FROM vendite.fn_crea_revisione_preventivo((SELECT preventivo_id FROM tmp_sa_c), 'pgtap');

DO $porta$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_sa_a_rev1), 'ANNULLATO');
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_sa_c_rev1), 'EMESSO');
END $porta$;

-- Il numero di ogni caso, COSTRUITO dal dominio e letto da vendite.preventivi.
--   Prima era il letterale PGTAP-SUPABO-<caso>.
CREATE TEMP TABLE tmp_sa_numeri AS
SELECT 'A'::text AS caso, p.numero FROM vendite.preventivi p WHERE p.id = (SELECT preventivo_id FROM tmp_sa_a)
UNION ALL
SELECT 'B', p.numero FROM vendite.preventivi p WHERE p.id = (SELECT preventivo_id FROM tmp_sa_b)
UNION ALL
SELECT 'C', p.numero FROM vendite.preventivi p WHERE p.id = (SELECT preventivo_id FROM tmp_sa_c);

-- ============================================================
-- 3) A rev0 — la viva. Ha una revisione successiva, ma abortita: non la
--    rimpiazza (is_superata=F) pur essendo has_next_revisione=T. E' proprio
--    la coppia che un flag solo non sa dire.
-- ============================================================
SELECT is(
  (SELECT ROW(v.is_attiva, v.is_superata, v.is_abortito, v.has_next_revisione)::text
     FROM vendite.vw_preventivi v
    WHERE v.numero = (SELECT numero FROM tmp_sa_numeri WHERE caso = 'A') AND v.rev = 0),
  ROW(true, false, false, true)::text,
  '3. A rev0 (EMESSO, con rev1 ANNULLATO sopra): attiva=T, superata=F, abortito=F, has_next=T'
);

-- ============================================================
-- 4) A rev1 — l'annullata in cima. Nessuno l'ha rimpiazzata: is_superata=F.
--    is_attiva=F dipende SOLO dall'annullamento.
-- ============================================================
SELECT is(
  (SELECT ROW(v.is_attiva, v.is_superata, v.is_abortito, v.has_next_revisione)::text
     FROM vendite.vw_preventivi v
    WHERE v.numero = (SELECT numero FROM tmp_sa_numeri WHERE caso = 'A') AND v.rev = 1),
  ROW(false, false, true, false)::text,
  '4. A rev1 (ANNULLATO in cima): attiva=F ma superata=F — non-attiva per annullamento, non per superamento'
);

-- ============================================================
-- 5) B rev0 — il caso del collaudo (PRV0000133): annullato a revisione unica.
--    «E' l'ultima revisione?» -> SI'. «E' attiva?» -> NO.
-- ============================================================
SELECT is(
  (SELECT ROW(v.is_attiva, v.is_superata, v.is_abortito, v.has_next_revisione)::text
     FROM vendite.vw_preventivi v
    WHERE v.numero = (SELECT numero FROM tmp_sa_numeri WHERE caso = 'B') AND v.rev = 0),
  ROW(false, false, true, false)::text,
  '5. B rev0 (ANNULLATO, revisione unica): superata=F (e'' l''ultima revisione) e attiva=F (annullato)'
);

-- ============================================================
-- 6) C rev0 — superamento vero: sopra c'e' una rev viva.
-- ============================================================
SELECT is(
  (SELECT ROW(v.is_attiva, v.is_superata, v.is_abortito, v.has_next_revisione)::text
     FROM vendite.vw_preventivi v
    WHERE v.numero = (SELECT numero FROM tmp_sa_numeri WHERE caso = 'C') AND v.rev = 0),
  ROW(false, true, false, true)::text,
  '6. C rev0 (EMESSO, rimpiazzato da rev1 EMESSO): superata=T, abortito=F, attiva=F'
);

-- ============================================================
-- 7) C rev1 — la viva del numero.
-- ============================================================
SELECT is(
  (SELECT ROW(v.is_attiva, v.is_superata, v.is_abortito, v.has_next_revisione)::text
     FROM vendite.vw_preventivi v
    WHERE v.numero = (SELECT numero FROM tmp_sa_numeri WHERE caso = 'C') AND v.rev = 1),
  ROW(true, false, false, false)::text,
  '7. C rev1 (EMESSO in cima): attiva=T, superata=F, abortito=F, has_next=F'
);

-- ============================================================
-- 8) Invariante di composizione. is_attiva NON e' una terza cosa: e' l'AND
--    delle due negazioni. Se un giorno drifta, questo test lo dice.
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM vendite.vw_preventivi v
    WHERE v.numero IN (SELECT numero FROM tmp_sa_numeri)
      AND v.is_attiva IS DISTINCT FROM (NOT v.is_abortito AND NOT v.is_superata)),
  0,
  '8. Invariante: is_attiva = NOT is_abortito AND NOT is_superata su tutte le revisioni fixture'
);

-- ============================================================
-- 9) Unicita' invariata (garanzia del self-term 20260708-07): al piu' una rev
--    attiva per numero. Il cantiere non la tocca, e questo lo presidia.
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM (SELECT v.numero
             FROM vendite.vw_preventivi v
            WHERE v.numero IN (SELECT numero FROM tmp_sa_numeri) AND v.is_attiva
            GROUP BY v.numero
           HAVING count(*) > 1) x),
  0,
  '9. Unicita'' preservata: nessun numero fixture ha piu'' di una revisione is_attiva'
);

-- ============================================================
-- 10) ⭐ Il punto del cantiere: i due predicati NON selezionano lo stesso
--     insieme. «Solo l'ultima revisione» (is_superata IS FALSE) tiene A rev0,
--     A rev1, B rev0 e C rev1 = 4 righe; is_attiva ne tiene 2 (A rev0, C rev1).
--     Le due che mancano sono esattamente gli ANNULLATO — cioe' quelli che
--     nessun filtro di stato riusciva a mostrare.
-- ============================================================
SELECT is(
  (SELECT ROW(
            count(*) FILTER (WHERE NOT v.is_superata),
            count(*) FILTER (WHERE v.is_attiva),
            count(*) FILTER (WHERE NOT v.is_superata AND v.is_abortito)
          )::text
     FROM vendite.vw_preventivi v
    WHERE v.numero IN (SELECT numero FROM tmp_sa_numeri)),
  ROW(4::bigint, 2::bigint, 2::bigint)::text,
  '10. «Solo ultima revisione» = 4 righe, is_attiva = 2: le 2 di scarto sono gli annullati non superati'
);

-- ============================================================
-- 11) Propagazione alla vista di lista: stesse colonne, stessi valori riga per
--     riga. E' la vista che la lista legge davvero.
-- ============================================================
--     ⚠️ Si asserisce ANCHE quante righe sono state confrontate: un conteggio
--     di scarti a zero su zero righe sarebbe verde per sottrazione.
SELECT is(
  (SELECT ROW(count(*), count(*) FILTER (WHERE
              (l.is_attiva, l.is_superata, l.is_abortito, l.has_next_revisione)
              IS DISTINCT FROM
              (v.is_attiva, v.is_superata, v.is_abortito, v.has_next_revisione)))::text
     FROM vendite.vw_preventivi_lista l
     JOIN vendite.vw_preventivi v ON v.id = l.id
    WHERE l.numero IN (SELECT numero FROM tmp_sa_numeri)),
  ROW(5::bigint, 0::bigint)::text,
  '11. vw_preventivi_lista: 5 righe fixture confrontate, zero scarti sulle quattro colonne'
);

SELECT * FROM finish();
ROLLBACK;
