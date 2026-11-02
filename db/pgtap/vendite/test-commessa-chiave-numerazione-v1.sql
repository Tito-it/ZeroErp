-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la COMMESSA porta gli assi del contatore nelle sue colonne
--       vendite.commesse.registro_id / .anno        (20260902-07)
--       vendite.fn_get_or_create_commessa           (20260902-08)
--       Piano: brief-be-fe-crud-registri-di-numerazione, sezione 12.6
-- ------------------------------------------------------------
-- Elenco test (plan 6):
-- 1) ⭐ Le due colonne esistono, e la FK punta ai registri
-- 2) ⭐ Il backfill non ha lasciato indietro nessuna commessa
-- 3) ⭐⭐ DERIVATO: il codice PORTA gli assi che le colonne dichiarano
-- 4) ⭐ La madre le scrive: l'INSERT le nomina
-- 5) ⭐ L'identita' resta il codice, e resta unica da sola
-- 6) ⭐ L'indice sugli assi esiste e NON e' unico
--
-- Scopo:
--   ⭐ IL TEST CHE CONTA E' IL 3, ed e' il motivo per cui le due colonne
--   esistono. Il codice della commessa e' `CMM-<sigla>-<anno>-<9 cifre>`:
--   gli assi del contatore ci sono gia' DENTRO, ma per convenzione di chi
--   compone la stringa. Finche' non erano colonne, quella convenzione non si
--   poteva verificare — si poteva solo rileggere la funzione e fidarsi.
--   ⇒ Adesso si confronta il codice con gli assi dichiarati, e se un domani
--   qualcuno cambia la composizione senza toccare le colonne (o viceversa),
--   il test lo dice.
--
--   ⛔ COSA NON PROVA, e va saputo: che gli assi siano TUTTI nella stringa.
--   Prova che ci siano quelli che oggi la chiave del contatore ha —
--   (registro, anno) — perche' la serie sulla commessa e' vietata da un guard
--   suo. Il giorno che un asse nuovo entrasse nel contatore, questo test
--   resterebbe verde: a intercettarlo e' il test 5 di
--   test-chiave-contatore-assi-dichiarati-v1, che deriva gli assi dal
--   catalogo delle famiglie.
--
-- ⚠️ Le colonne sono NULLABLE di proposito: una decina di file pgTAP inserisce
--   in vendite.commesse senza passare dalla madre, e un NOT NULL li farebbe
--   rossi insieme. Il test 2 guarda il parco reale, non impone il vincolo.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- 1) La struttura
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM pg_constraint
      WHERE conname = 'fk_commesse_registro'
        AND conrelid = 'vendite.commesse'::regclass
        AND confrelid = 'vendite.registri_fatturazione'::regclass),
    1,
    '1) La commessa ha registro_id, e la FK punta ai registri di numerazione');

-- ============================================================
-- 2) Il backfill
-- ============================================================
-- ⚠️ Guarda il parco reale: se una commessa non avesse registro sarebbe una
--   riga che il backfill non ha saputo risolvere, e va vista.
SELECT is(
    (SELECT count(*)::int FROM vendite.commesse WHERE registro_id IS NULL),
    0,
    '2) Nessuna commessa e'' rimasta senza registro');

-- ============================================================
-- 3) ⭐⭐ DERIVATO — il codice porta gli assi che le colonne dichiarano
-- ============================================================
-- ⭐ Nessun elenco a mano: la sigla si legge dall'emittente DEL REGISTRO
--   dichiarato sulla riga, l'anno dalla colonna. Se il codice non li contiene,
--   la stringa e le colonne raccontano due cose diverse.
-- ⚠️ Solo sui codici del formato nuovo: quelli anteriori al 2026-08-31 erano
--   `CMM-<timestamp>-<md5>` e non portano nessun asse — sono storia, e
--   pretendere che la rispettino sarebbe chiedere al passato di essere il
--   presente.
SELECT is(
    (SELECT count(*)::int
       FROM vendite.commesse c
       JOIN vendite.registri_fatturazione r  ON r.id = c.registro_id
       JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = r.emittente_soggetto_ruolo_id
      WHERE c.codice ~ '^CMM-[A-Za-z0-9]+-[0-9]{4}-[0-9]{9}$'
        AND (c.codice NOT LIKE '%' || ef.codice || '%'
             OR c.codice NOT LIKE '%' || c.anno::text || '%')),
    0,
    '3) Il codice porta la sigla dell''emittente e l''anno che le colonne dichiarano');

-- ============================================================
-- 4) La madre le scrive
-- ============================================================
-- ⚠️ Si guarda l'INSERT nel corpo della funzione e non il risultato di una
--   chiamata: creare una commessa qui vorrebbe dire fabbricare un billing
--   account, un'utility e un emittente per provare una riga di INSERT.
--   ⛔ E' un presidio strutturale, non un collaudo: se qualcuno riscrivesse la
--   madre dimenticando le due colonne, le commesse nuove nascerebbero senza
--   assi e nessun vincolo lo direbbe.
SELECT matches(
    (SELECT pg_get_functiondef(p.oid)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite' AND p.proname = 'fn_get_or_create_commessa'),
    -- ⚠️ Backslash SINGOLI: in un letterale SQL `\\(` sono due caratteri, e la
    --   regex ci legge un backslash seguito da una parentesi aperta — «parentesi
    --   non bilanciate». Si e' visto eseguendo, non rileggendo.
    'INSERT INTO vendite\.commesse \(codice, registro_id, anno,',
    '4) La madre della commessa scrive registro_id e anno');

-- ============================================================
-- 5/6) L'identita' non e' cambiata
-- ============================================================
-- ⭐ Il codice resta unico DA SOLO, ed e' piu' stretto delle sorelle: porta la
--   sigla dell'emittente, quindi non collide fra registri diversi.
SELECT is(
    (SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'uq_commesse_codice'),
    'UNIQUE (codice)',
    '5) L''identita'' resta il codice, e resta unica da sola');

-- ⚠️ L'indice sugli assi NON deve essere unico: l'unicita' ce l'ha gia' il
--   codice, e in forma piu' stretta. Se qualcuno lo rendesse unico
--   aggiungerebbe un vincolo che non serve e che un domani rifiuterebbe una
--   riga per la ragione sbagliata.
SELECT is(
    (SELECT x.indisunique
       FROM pg_index x JOIN pg_class i ON i.oid = x.indexrelid
      WHERE i.relname = 'ix_commesse_registro_anno'),
    false,
    '6) L''indice sugli assi esiste e NON e'' unico');

SELECT * FROM finish();
ROLLBACK;
