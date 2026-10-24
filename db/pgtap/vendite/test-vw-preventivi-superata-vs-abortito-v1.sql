-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
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
--       Fixture (numeri multi-rev inseriti diretti, nati DRAFT e portati
--       allo stato scelto con dbops.fn_pgtap_porta_a_stato — rev 2026-10-24):
--         A) PGTAP-SUPABO-A: rev0 EMESSO + rev1 ANNULLATO
--            -> rev1 e' l'ULTIMA revisione e non e' superata da nessuno, ma e'
--               abortita: is_superata=F, is_abortito=T, is_attiva=F.
--               rev0 e' la viva: is_superata=F (l'abortita non rimpiazza),
--               is_abortito=F, has_next_revisione=T, is_attiva=T.
--         B) PGTAP-SUPABO-B: rev0 ANNULLATO, revisione unica
--            -> e' il caso del collaudo (PRV0000133): is_superata=F —
--               «e' l'ultima revisione» e' VERO — ma is_attiva=F. Con il solo
--               is_attiva il documento non era raggiungibile da nessun filtro.
--         C) PGTAP-SUPABO-C: rev0 EMESSO + rev1 EMESSO
--            -> superamento vero: rev0 is_superata=T, rev1 is_superata=F.
--
-- Indice test (0..11):
--   0)  Precondizioni: refs minimi (BA, emittente, valuta, stati)
--   1)  Struttura: vw_preventivi espone is_superata, is_abortito, has_next_revisione
--   2)  Setup scope operatore (le viste sono security_invoker: serve la GUC)
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
CREATE TEMP TABLE tmp_sa_refs AS
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
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'EMESSO' AND s.attivo IS TRUE LIMIT 1) AS st_emesso_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ANNULLATO' AND s.attivo IS TRUE LIMIT 1) AS st_annullato_id;

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
-- ============================================================
CREATE TEMP TABLE tmp_sa_op AS
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
  (SELECT user_id IS NOT NULL FROM tmp_sa_op),
  '2. Trovato un operatore OPERATORE non-super per lo scope'
);

SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_sa_op);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id, meta)
SELECT o.user_id, r.emittente_fiscale_id,
       '{"test_scope":"pgtap_superata_vs_abortito"}'::jsonb
  FROM tmp_sa_op o, tmp_sa_refs r
 WHERE o.user_id IS NOT NULL;

SELECT set_config('app.current_user_id',
    (SELECT user_id::text FROM tmp_sa_op), true);

-- ============================================================
-- Fixture: tre numeri, cinque revisioni
-- ⚠️ rev 2026-10-24 (brief-modello-documento-vendita N-1): le revisioni
--   nascono DRAFT (lo stato non si scrive: lo mette il trigger della nascita)
--   e si portano allo stato del caso per la matrice, sotto i guard veri
--   (senza righe non hanno motivi da sollevare). Lo stato voluto sta in
--   tmp_sa_fix, letta due volte: dall'INSERT e dal cammino.
-- ============================================================
CREATE TEMP TABLE tmp_sa_fix (numero, rev, stato) AS
VALUES
  ('PGTAP-SUPABO-A'::text, 0, 'EMESSO'::text),
  ('PGTAP-SUPABO-A', 1, 'ANNULLATO'),
  ('PGTAP-SUPABO-B', 0, 'ANNULLATO'),
  ('PGTAP-SUPABO-C', 0, 'EMESSO'),
  ('PGTAP-SUPABO-C', 1, 'EMESSO');

INSERT INTO vendite.preventivi (
  numero, rev, billing_account_id, istanza_utility_id, utility_id,
  validita_dal, validita_al, valuta_id, data,
  fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
SELECT f.numero, f.rev, r.billing_account_id, r.istanza_utility_id, r.utility_id,
       DATE '2081-01-01', DATE '2081-12-31', r.valuta_id,
       DATE '2081-01-01', false, false,
       jsonb_build_object('test_scope','pgtap_superata_vs_abortito'), r.emittente_fiscale_id
  FROM tmp_sa_refs r, tmp_sa_fix f;

-- Prima la rev 0, poi la rev 1, come nel flusso vero. ANNULLATO esce
--   direttamente dalla bozza (DRAFT -> ANNULLATO).
DO $porta$
DECLARE
  r record;
BEGIN
  FOR r IN
    SELECT p.id, f.stato
      FROM tmp_sa_fix f
      JOIN vendite.preventivi p ON p.numero = f.numero AND p.rev = f.rev
     ORDER BY f.numero, f.rev
  LOOP
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', r.id, r.stato);
  END LOOP;
END
$porta$;

-- ============================================================
-- 3) A rev0 — la viva. Ha una revisione successiva, ma abortita: non la
--    rimpiazza (is_superata=F) pur essendo has_next_revisione=T. E' proprio
--    la coppia che un flag solo non sa dire.
-- ============================================================
SELECT is(
  (SELECT ROW(v.is_attiva, v.is_superata, v.is_abortito, v.has_next_revisione)::text
     FROM vendite.vw_preventivi v
    WHERE v.numero = 'PGTAP-SUPABO-A' AND v.rev = 0),
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
    WHERE v.numero = 'PGTAP-SUPABO-A' AND v.rev = 1),
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
    WHERE v.numero = 'PGTAP-SUPABO-B' AND v.rev = 0),
  ROW(false, false, true, false)::text,
  '5. B rev0 (ANNULLATO, revisione unica): superata=F (e'' l''ultima revisione) e attiva=F (annullato)'
);

-- ============================================================
-- 6) C rev0 — superamento vero: sopra c'e' una rev viva.
-- ============================================================
SELECT is(
  (SELECT ROW(v.is_attiva, v.is_superata, v.is_abortito, v.has_next_revisione)::text
     FROM vendite.vw_preventivi v
    WHERE v.numero = 'PGTAP-SUPABO-C' AND v.rev = 0),
  ROW(false, true, false, true)::text,
  '6. C rev0 (EMESSO, rimpiazzato da rev1 EMESSO): superata=T, abortito=F, attiva=F'
);

-- ============================================================
-- 7) C rev1 — la viva del numero.
-- ============================================================
SELECT is(
  (SELECT ROW(v.is_attiva, v.is_superata, v.is_abortito, v.has_next_revisione)::text
     FROM vendite.vw_preventivi v
    WHERE v.numero = 'PGTAP-SUPABO-C' AND v.rev = 1),
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
    WHERE v.numero LIKE 'PGTAP-SUPABO-%'
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
            WHERE v.numero LIKE 'PGTAP-SUPABO-%' AND v.is_attiva
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
    WHERE v.numero LIKE 'PGTAP-SUPABO-%'),
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
    WHERE l.numero LIKE 'PGTAP-SUPABO-%'),
  ROW(5::bigint, 0::bigint)::text,
  '11. vw_preventivi_lista: 5 righe fixture confrontate, zero scarti sulle quattro colonne'
);

SELECT * FROM finish();
ROLLBACK;
