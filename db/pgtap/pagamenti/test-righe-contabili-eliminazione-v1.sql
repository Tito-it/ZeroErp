-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la riga di una bozza manuale si ELIMINA, e sotto VALIDATA il contenuto
--       si CONGELA — script.fn_check_riga_contabile_eliminabile +
--       pagamenti.trgfn_vendite_contabili_righe_guard_contenuto
--
-- Elenco test (plan 35):
--  1) la check esiste con la firma dichiarata
--  2) il guard e' montato: BEFORE INSERT / UPDATE OF fatti / DELETE
--  3) manuale in BOZZA: la check risponde [] — si puo' eliminare
--  4) sotto una GENERATA: motivo 2, DISTINTA_NON_MANUALE, ed e' l'UNICO
--  5) ...e la disattivazione e' rifiutata con quel messaggio
--  6) la manuale si valida (400 dichiarati, 400 di righe)
--  7) sotto la VALIDATA: motivo 3, DISTINTA_VALIDATA
--  8) ...e la disattivazione e' rifiutata (porta 1)
--  9) ⭐ D18: una riga NUOVA sotto la validata e' rifiutata (porta 2)
-- 10) ⭐ D18: cambiare l'IMPORTO di una riga sotto la validata e' rifiutato
-- 11) ⭐ D18: SPOSTARE una riga dentro la validata e' rifiutato
-- 12) ⭐ D18: ABBINARE (una decisione) sotto la validata PASSA
-- 13) un UPDATE OF a valore invariato passa: il backend scrive piu' colonne
-- 14) la manuale si riapre in BOZZA
-- 15) in bozza la riga nuova entra
-- 16) il saldo contabile «in lavorazione» conta anche la riga nuova (+400)
-- 17) ⚠️ «scartare» la riga sbagliata NON e' un'eliminazione: la quadratura si rompe
-- 18) ⭐ D17: la riga sbagliata si ELIMINA (attivo = false) in bozza
-- 19) ...ed esce dal saldo «in lavorazione» (torna al valore di prima)
-- 20) ⭐ lo scenario di §2.2: eliminata la sbagliata, la distinta si valida
-- 21) riattivare in bozza e' ammesso (guard_distinta_finale non parla)
-- 22) il DELETE fisico in bozza passa: stesso perimetro della disattivazione
-- 23) sotto una CHIUSA: motivo 1, DISTINTA_FINALE — il codice RIUSATO
-- 24) ...la disattivazione della riga registrata e' rifiutata da QUESTO guard
-- 25) ...e il DELETE parla PRIMA della FK del movimento, col messaggio giusto
-- 26) il DELETE sotto una GENERATA e' rifiutato: la porta e' chiusa
-- 27) ⭐ ...ma la madre del giro la apre con la GUC, e passa
-- 28) ...e richiusa la GUC, la porta e' di nuovo chiusa
-- 29) una riga che non si legge: E_RIGA_CONTABILE_NON_TROVATA, non []
-- 30) un id non valido: chiamata non valida (TECNICO)
-- 31) la meta' su distinta esiste, con la riga della testata come parametro
-- 32) ⭐ le due strade danno la stessa risposta, sulle tre distinte della fixture
-- 33) ⭐ la meta' giudica la distinta RICEVUTA, non la rilegge (nessun perimetro)
-- 34) una distinta senza id: chiamata non valida (TECNICO)
-- 35) ⭐ il guard del contenuto eredita ancora i quattro codici attraverso la delega
--
-- Scopo:
--  - D17 (§2.2): la riga digitata male su una manuale in bozza non e' un
--    fatto — non e' denaro arrivato, e' un errore di battitura — e si elimina
--    con `attivo = false`. «Scarta» racconta il contrario e CONTA nella
--    quadratura (test 17): senza l'eliminazione, un errore di digitazione su
--    una manuale con totale dichiarato non aveva via d'uscita (test 20);
--  - D18 (§2.3, confermata da Tid il 2026-09-14): sotto una MANUALE validata il
--    CONTENUTO e' fermo (righe nuove, fatti, spostamenti, eliminazioni: test
--    8-11) e le DECISIONI restano libere (test 12) — l'abbinamento non tocca
--    la quadratura, e il posting muove lo stato a distinta ancora validata;
--  - ⭐ i test 7 e 9-10 LEGANO le due porte: la condizione «MANUALE non piu'
--    in BOZZA» sta scritta nella check (motivo 3) e nel guard (porta 2),
--    perche' sull'INSERT non c'e' una riga da passare — e qui si pretende lo
--    stesso codice da entrambe;
--  - ⭐ il DELETE fisico (D12-d, «tre porte»): chiuso con la stessa check
--    (test 22, 25, 26), aperto SOLO a chi dichiara di essere il giro dei fondi
--    con la GUC transazionale (test 27) e richiuso subito dopo (test 28) —
--    vendite.fn_cancella_fondo_fattura e' l'unico che la imposta;
--  - ⭐ LETTURA E GIUDIZIO IN DUE META' (rev 2026-10-21, 20261021-62/-63): i
--    motivi stanno in fn_check_riga_contabile_eliminabile_su_distinta, che le
--    liste chiamano con la testata gia' letta; la firma per id legge sotto RLS e
--    delega. I test 32-35 tengono la promessa: stessa risposta per le due
--    strade (32), nessuna rilettura nella meta' (33), i codici che il guard
--    eredita non si perdono nella delega (35);
--  - ⚠️ la fixture SI COSTRUISCE: un'azienda con il suo operatore, un cliente
--    fatturabile, una fattura. Su un database ricostruito dai changelog non
--    c'e' niente di tutto questo, e un test che lo pescasse resterebbe
--    collaudato solo su dbdev. Le distinte si INSERISCONO dirette (non con
--    fn_get_or_create_vendite_contabile): la chiave di riuso di quella
--    funzione potrebbe restituire una distinta gia' esistente della stessa
--    giornata, e il conteggio delle righe cambierebbe con la macchina.
--
-- Piano: brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga §4 P-4 + P-5
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione, con la RLS.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(35);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_righe_eliminazione'::text AS test_scope;

-- Il cliente fatturabile, nel contesto dell'operatore: il legame BA -> emittente
-- lo scrive il trigger z90 verso l'emittente di chi agisce.
CREATE TEMP TABLE tmp_cli AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('eliminazione riga') c;

CREATE TEMP TABLE tmp_refs AS
SELECT (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA'
         ORDER BY c.id LIMIT 1)                                                  AS centro_banca_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'ABBINATA'    ORDER BY s.id LIMIT 1)           AS st_abbinata,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'SOSPESA'     ORDER BY s.id LIMIT 1)           AS st_sospesa,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'SCARTATA'    ORDER BY s.id LIMIT 1)           AS st_scartata,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'BOZZA'       ORDER BY s.id LIMIT 1)           AS d_bozza,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'VALIDATA'    ORDER BY s.id LIMIT 1)           AS d_validata,
       (SELECT soggetto_ruolo_id FROM _mondo)                                    AS emittente_sr_id,
       (SELECT billing_account_id FROM tmp_cli)                                  AS billing_account_id;

-- La fattura dell'azienda, scritta come la scriverebbe l'applicazione.
CREATE TEMP TABLE tmp_fattura AS
WITH f AS (
    INSERT INTO vendite.fatture
        (registro_id, emittente_soggetto_ruolo_id, billing_account_id, meta)
    SELECT script.fn_pgtap_registro_fattura(r.emittente_sr_id), r.emittente_sr_id,
           r.billing_account_id,
           jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
      FROM tmp_refs r
    RETURNING id
)
SELECT id AS fattura_id FROM f;

-- Tre distinte, INSERITE dirette (vedi Scopo):
--   D1  MANUALE  in BOZZA, dichiara 400   — il lotto di lavoro dell'operatore
--   D2  GENERATA in VALIDATA              — com'e' quella del sync dei fondi
--   D3  MANUALE  in BOZZA                 — destinata a essere REGISTRATA (CHIUSA)
CREATE TEMP TABLE tmp_distinte AS
WITH ins AS (
    INSERT INTO pagamenti.vendite_contabili
        (centro_riscossione_id, data_contabile, data_registrazione,
         stato_id, origine, importo_dichiarato, meta)
    SELECT r.centro_banca_id, script.fn_data_operativa(), script.fn_data_operativa(),
           CASE v.et WHEN 'D2' THEN r.d_validata ELSE r.d_bozza END,
           v.origine, v.dichiarato,
           jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'et', v.et)
      FROM tmp_refs r
      CROSS JOIN (VALUES ('D1', 'MANUALE',  400.00::numeric),
                         ('D2', 'GENERATA', NULL::numeric),
                         ('D3', 'MANUALE',  NULL::numeric)) AS v(et, origine, dichiarato)
    RETURNING id, meta ->> 'et' AS et
)
SELECT * FROM ins;

-- Le righe: A sotto D1, C sotto D2, E sotto D3. Tutte ABBINATE alla fattura
-- (senza rata: e' facoltativa, e la capienza non entra in gioco).
CREATE TEMP TABLE tmp_righe AS
WITH ins AS (
    INSERT INTO pagamenti.vendite_contabili_righe
        (contabile_id, riferimento_ente, data_pagamento, importo,
         fattura_id, billing_account_id, stato_id, meta)
    SELECT d.id, 'PGTAP_ELIM_' || v.et, script.fn_data_operativa(), v.importo,
           (SELECT fattura_id FROM tmp_fattura), r.billing_account_id, r.st_abbinata,
           jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'et', v.et)
      FROM tmp_refs r
      CROSS JOIN (VALUES ('A', 'D1', 400.00::numeric),
                         ('C', 'D2',  10.00::numeric),
                         ('E', 'D3',  50.00::numeric)) AS v(et, dist, importo)
      JOIN tmp_distinte d ON d.et = v.dist
    RETURNING id, meta ->> 'et' AS et
)
SELECT * FROM ins;

-- ============================================================
-- 1-2) Gli oggetti ci sono
-- ============================================================
SELECT has_function(
    'script', 'fn_check_riga_contabile_eliminabile', ARRAY['bigint'],
    '1) script.fn_check_riga_contabile_eliminabile esiste con la firma dichiarata');

-- ⚠️ Si asserisce l'EVENTO, non solo il nome: un trigger montato senza il
--    DELETE, o senza l'UPDATE OF sui fatti, avrebbe lo stesso nome e la meta'
--    delle porte. pg_trigger.tgtype: bit 0 = ROW, 1 = BEFORE, 2 = INSERT,
--    3 = DELETE, 4 = UPDATE; tgattr = le colonne dell'UPDATE OF.
SELECT ok(
    EXISTS (SELECT 1
              FROM pg_trigger tg
             WHERE tg.tgrelid = 'pagamenti.vendite_contabili_righe'::regclass
               AND tg.tgname  = 'trg_vendite_contabili_righe_a10_guard_contenuto_ins_upd_dlt'
               AND (tg.tgtype & 2) <> 0     -- BEFORE
               AND (tg.tgtype & 4) <> 0     -- INSERT
               AND (tg.tgtype & 8) <> 0     -- DELETE
               AND (tg.tgtype & 16) <> 0    -- UPDATE
               AND (SELECT array_agg(a.attname::text ORDER BY a.attname)
                      FROM unnest(tg.tgattr::smallint[]) AS n(attnum)
                      JOIN pg_attribute a ON a.attrelid = tg.tgrelid AND a.attnum = n.attnum)
                   = ARRAY['attivo', 'contabile_id', 'data_operazione', 'data_pagamento',
                           'data_valuta', 'importo', 'riferimento_ente']),
    '2) il guard e'' montato BEFORE INSERT OR UPDATE OF <fatti, attivo, contabile_id> OR DELETE');

-- ============================================================
-- 3) In bozza si puo'
-- ============================================================
SELECT is(
    script.fn_check_riga_contabile_eliminabile((SELECT id FROM tmp_righe WHERE et = 'A')),
    '[]'::jsonb,
    '3) su una MANUALE in BOZZA la check risponde []: la riga si puo'' eliminare');

-- ============================================================
-- 4-5) Sotto una GENERATA: il motivo 2, e solo quello
-- ============================================================
CREATE TEMP TABLE tmp_check_c AS
SELECT script.fn_check_riga_contabile_eliminabile((SELECT id FROM tmp_righe WHERE et = 'C')) AS m;

SELECT ok(
    (SELECT m -> 0 ->> 'reason' = 'DISTINTA_NON_MANUALE'
        AND m -> 0 ->> 'codice' = 'E_RIGA_CONTABILE_DISTINTA_NON_MANUALE'
        AND m -> 0 ->> 'reason_key' = 'pagamenti.righe.elimina_reason.distinta_non_manuale'
        AND jsonb_array_length(m) = 1
       FROM tmp_check_c),
    '4) sotto una GENERATA: DISTINTA_NON_MANUALE, ed e'' l''UNICO motivo (il 3 non parla: «torna in bozza» non e'' un rimedio per una generata)');

-- ⚠️ throws_like e non throws_ok: qui la posta e' PROPRIO quale frase esce.
SELECT throws_like(
    format($q$UPDATE pagamenti.vendite_contabili_righe SET attivo = false WHERE id = %s$q$,
           (SELECT id FROM tmp_righe WHERE et = 'C')),
    '%non e'' compilata a mano%',
    '5) disattivare una riga di una GENERATA e'' rifiutato con il messaggio del motivo 2');

-- ============================================================
-- 6-8) La validata: motivo 3, porta 1
-- ============================================================
SELECT lives_ok(
    format($q$UPDATE pagamenti.vendite_contabili SET stato_id = %s WHERE id = %s$q$,
           (SELECT d_validata FROM tmp_refs),
           (SELECT id FROM tmp_distinte WHERE et = 'D1')),
    '6) la manuale si valida: 400 dichiarati, 400 di righe');

SELECT ok(
    (SELECT m -> 0 ->> 'reason' = 'DISTINTA_VALIDATA'
        AND m -> 0 ->> 'codice' = 'E_RIGA_CONTABILE_DISTINTA_VALIDATA'
        AND m -> 0 ->> 'reason_key' = 'pagamenti.righe.elimina_reason.distinta_validata'
       FROM script.fn_check_riga_contabile_eliminabile((SELECT id FROM tmp_righe WHERE et = 'A')) AS m),
    '7) sotto la VALIDATA: DISTINTA_VALIDATA, codice E_RIGA_CONTABILE_DISTINTA_VALIDATA');

SELECT throws_like(
    format($q$UPDATE pagamenti.vendite_contabili_righe SET attivo = false WHERE id = %s$q$,
           (SELECT id FROM tmp_righe WHERE et = 'A')),
    '%non si eliminano finche%',
    '8) disattivare sotto la validata e'' rifiutato (porta 1, dal motivo 3 della check)');

-- ============================================================
-- 9-11) ⭐ D18 — il contenuto e' fermo (porta 2)
-- ============================================================
-- ⭐ Stesso codice, stessa frase della porta 1: e' cio' che LEGA le due porte.
SELECT throws_like(
    format($q$INSERT INTO pagamenti.vendite_contabili_righe
                 (contabile_id, riferimento_ente, data_pagamento, importo,
                  fattura_id, billing_account_id, stato_id)
              VALUES (%s, 'PGTAP_ELIM_NUOVA', script.fn_data_operativa(), 1.00, %s, %s, %s)$q$,
           (SELECT id FROM tmp_distinte WHERE et = 'D1'),
           (SELECT fattura_id FROM tmp_fattura),
           (SELECT billing_account_id FROM tmp_refs),
           (SELECT st_abbinata FROM tmp_refs)),
    '%non si aggiungono%',
    '9) D18: una riga nuova sotto la validata e'' rifiutata (porta 2, stesso codice)');

SELECT throws_like(
    format($q$UPDATE pagamenti.vendite_contabili_righe SET importo = 401.00 WHERE id = %s$q$,
           (SELECT id FROM tmp_righe WHERE et = 'A')),
    '%non si modificano%',
    '10) D18: cambiare l''importo sotto la validata e'' rifiutato');

-- Spostare una riga DENTRO la validata: la testata di ARRIVO e' quella che decide.
SELECT throws_like(
    format($q$UPDATE pagamenti.vendite_contabili_righe SET contabile_id = %s WHERE id = %s$q$,
           (SELECT id FROM tmp_distinte WHERE et = 'D1'),
           (SELECT id FROM tmp_righe WHERE et = 'C')),
    '%non si aggiungono%',
    '11) D18: spostare una riga dentro la validata e'' rifiutato');

-- ============================================================
-- 12-13) ...e le decisioni no
-- ============================================================
-- ⭐ La forma e' quella del backend (`abbina_riga`): abbinamento e stato in UN
--    UPDATE. Nessuno dei fatti cambia: il trigger non scatta nemmeno.
SELECT lives_ok(
    format($q$UPDATE pagamenti.vendite_contabili_righe r
                 SET fattura_id = %s, billing_account_id = %s, scadenza_id = NULL,
                     forzata = false, motivo_forzatura = NULL, stato_id = %s
               WHERE r.id = %s$q$,
           (SELECT fattura_id FROM tmp_fattura),
           (SELECT billing_account_id FROM tmp_refs),
           (SELECT st_abbinata FROM tmp_refs),
           (SELECT id FROM tmp_righe WHERE et = 'A')),
    '12) D18: ABBINARE sotto la validata PASSA — e'' una decisione, non contenuto');

-- ⚠️ Un UPDATE OF scatta anche a valore invariato: il backend scrive piu'
--    colonne in una SET, e «importo = importo» non deve fermare nessuno.
SELECT lives_ok(
    format($q$UPDATE pagamenti.vendite_contabili_righe
                 SET importo = importo, riferimento_ente = riferimento_ente, meta = meta
               WHERE id = %s$q$,
           (SELECT id FROM tmp_righe WHERE et = 'A')),
    '13) un UPDATE OF a valore invariato passa: nessun contenuto si muove');

-- ============================================================
-- 14-22) ⭐ Lo scenario di §2.2 — «scarta» non e' «elimina»
-- ============================================================
SELECT lives_ok(
    format($q$UPDATE pagamenti.vendite_contabili SET stato_id = %s WHERE id = %s$q$,
           (SELECT d_bozza FROM tmp_refs),
           (SELECT id FROM tmp_distinte WHERE et = 'D1')),
    '14) la manuale si riapre in BOZZA');

-- Il saldo «in lavorazione» PRIMA della riga sbagliata: la fattura ha gia'
-- righe pronte sotto altre distinte non finali (C sotto D2, E sotto D3), e
-- il numero assoluto direbbe la fotografia della fixture, non la regola.
-- Si asserisce il DELTA: la riga entra, la riga esce.
CREATE TEMP TABLE tmp_saldo_base AS
SELECT saldo_contabile AS base
  FROM pagamenti.fn_get_saldo_fattura_contabili((SELECT fattura_id FROM tmp_fattura));

-- La riga «sbagliata»: stessi 400, digitati due volte.
SELECT lives_ok(
    format($q$INSERT INTO pagamenti.vendite_contabili_righe
                 (contabile_id, riferimento_ente, data_pagamento, importo,
                  fattura_id, billing_account_id, stato_id, meta)
              VALUES (%s, 'PGTAP_ELIM_B', script.fn_data_operativa(), 400.00, %s, %s, %s,
                      jsonb_build_object('test_scope', %L, 'et', 'B'))$q$,
           (SELECT id FROM tmp_distinte WHERE et = 'D1'),
           (SELECT fattura_id FROM tmp_fattura),
           (SELECT billing_account_id FROM tmp_refs),
           (SELECT st_abbinata FROM tmp_refs),
           (SELECT test_scope FROM tmp_costanti)),
    '15) in bozza la riga nuova entra');

INSERT INTO tmp_righe (id, et)
SELECT cr.id, 'B'
  FROM pagamenti.vendite_contabili_righe cr
 WHERE cr.riferimento_ente = 'PGTAP_ELIM_B'
   AND cr.meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti);

SELECT is(
    (SELECT saldo_contabile FROM pagamenti.fn_get_saldo_fattura_contabili((SELECT fattura_id FROM tmp_fattura))),
    (SELECT base + 400.00 FROM tmp_saldo_base),
    '16) il saldo contabile «in lavorazione» conta anche la riga nuova: +400');

-- «Scarto» la sbagliata: ABBINATA -> SOSPESA -> SCARTATA (la matrice non ha la
-- via diretta — e' il «vincolo troppo stretto» visto al collaudo).
UPDATE pagamenti.vendite_contabili_righe SET stato_id = (SELECT st_sospesa  FROM tmp_refs)
 WHERE id = (SELECT id FROM tmp_righe WHERE et = 'B');
UPDATE pagamenti.vendite_contabili_righe SET stato_id = (SELECT st_scartata FROM tmp_refs)
 WHERE id = (SELECT id FROM tmp_righe WHERE et = 'B');

-- ⚠️ La quadratura conta ANCHE le scartate (D12-e): 800 <> 400.
SELECT throws_like(
    format($q$UPDATE pagamenti.vendite_contabili SET stato_id = %s WHERE id = %s$q$,
           (SELECT d_validata FROM tmp_refs),
           (SELECT id FROM tmp_distinte WHERE et = 'D1')),
    '%dichiara%',
    '17) «scartare» la sbagliata NON e'' un''eliminazione: la distinta non si valida piu'' (800 <> 400)');

-- ⭐ D17: l'eliminazione.
SELECT lives_ok(
    format($q$UPDATE pagamenti.vendite_contabili_righe SET attivo = false WHERE id = %s$q$,
           (SELECT id FROM tmp_righe WHERE et = 'B')),
    '18) D17: la riga sbagliata si ELIMINA (attivo = false) su una manuale in bozza');

SELECT is(
    (SELECT saldo_contabile FROM pagamenti.fn_get_saldo_fattura_contabili((SELECT fattura_id FROM tmp_fattura))),
    (SELECT base FROM tmp_saldo_base),
    '19) la riga eliminata esce dal saldo «in lavorazione»: torna al valore di prima');

SELECT lives_ok(
    format($q$UPDATE pagamenti.vendite_contabili SET stato_id = %s WHERE id = %s$q$,
           (SELECT d_validata FROM tmp_refs),
           (SELECT id FROM tmp_distinte WHERE et = 'D1')),
    '20) eliminata la sbagliata, la distinta si valida: 400 = 400');

UPDATE pagamenti.vendite_contabili SET stato_id = (SELECT d_bozza FROM tmp_refs)
 WHERE id = (SELECT id FROM tmp_distinte WHERE et = 'D1');

SELECT lives_ok(
    format($q$UPDATE pagamenti.vendite_contabili_righe SET attivo = true WHERE id = %s$q$,
           (SELECT id FROM tmp_righe WHERE et = 'B')),
    '21) riattivare in bozza e'' ammesso: guard_distinta_finale non parla, e la porta 2 vede BOZZA');

SELECT lives_ok(
    format($q$DELETE FROM pagamenti.vendite_contabili_righe WHERE id = %s$q$,
           (SELECT id FROM tmp_righe WHERE et = 'B')),
    '22) il DELETE fisico in bozza passa: stesso perimetro della disattivazione');

-- ============================================================
-- 23-25) Sotto una CHIUSA: il codice riusato, e la riga registrata
-- ============================================================
UPDATE pagamenti.vendite_contabili SET stato_id = (SELECT d_validata FROM tmp_refs)
 WHERE id = (SELECT id FROM tmp_distinte WHERE et = 'D3');

CREATE TEMP TABLE tmp_esito AS
SELECT * FROM pagamenti.fn_posta_contabile((SELECT id FROM tmp_distinte WHERE et = 'D3'));

SELECT ok(
    (SELECT m -> 0 ->> 'reason' = 'DISTINTA_FINALE'
        AND m -> 0 ->> 'codice' = 'E_RIGA_CONTABILE_DISTINTA_FINALE'
        AND m -> 0 ->> 'reason_key' = 'pagamenti.righe.elimina_reason.distinta_finale'
       FROM script.fn_check_riga_contabile_eliminabile((SELECT id FROM tmp_righe WHERE et = 'E')) AS m),
    '23) sotto una CHIUSA: DISTINTA_FINALE, con il codice RIUSATO del guard d''ingresso');

-- ⚠️ La frase e' la posta: a parlare dev'essere QUESTO guard e non
--    prevent_deactivate_if_children («ci sono ancora righe collegate»), che
--    verrebbe dopo in ordine alfabetico.
SELECT throws_like(
    format($q$UPDATE pagamenti.vendite_contabili_righe SET attivo = false WHERE id = %s$q$,
           (SELECT id FROM tmp_righe WHERE et = 'E')),
    '%non si lavorano%',
    '24) disattivare la riga REGISTRATA e'' rifiutato da questo guard, col messaggio della distinta finale');

-- ⚠️ Prima la FK NO ACTION del movimento diceva 23503 e basta: adesso il
--    messaggio arriva PRIMA, ed e' quello giusto.
SELECT throws_like(
    format($q$DELETE FROM pagamenti.vendite_contabili_righe WHERE id = %s$q$,
           (SELECT id FROM tmp_righe WHERE et = 'E')),
    '%non si lavorano%',
    '25) il DELETE della riga registrata parla PRIMA della FK, col messaggio giusto');

-- ============================================================
-- 26-28) La porta del DELETE: chiusa, aperta dalla madre, richiusa
-- ============================================================
SELECT throws_like(
    format($q$DELETE FROM pagamenti.vendite_contabili_righe WHERE id = %s$q$,
           (SELECT id FROM tmp_righe WHERE et = 'C')),
    '%non e'' compilata a mano%',
    '26) il DELETE sotto una GENERATA e'' rifiutato: la porta e'' chiusa');

-- ⭐ E' cio' che fa vendite.fn_cancella_fondo_fattura attorno al SUO DELETE.
SELECT set_config('zeroerp.allow_contabile_riga_delete_override', 'on', true);

SELECT lives_ok(
    format($q$DELETE FROM pagamenti.vendite_contabili_righe WHERE id = %s$q$,
           (SELECT id FROM tmp_righe WHERE et = 'C')),
    '27) ...ma la madre del giro la apre con la GUC, e il suo DELETE passa');

SELECT set_config('zeroerp.allow_contabile_riga_delete_override', '', true);

-- Una seconda riga sotto la stessa GENERATA: la GUC e' richiusa, la porta anche.
INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, data_pagamento, importo,
     fattura_id, billing_account_id, stato_id, meta)
SELECT d.id, 'PGTAP_ELIM_C2', script.fn_data_operativa(), 10.00,
       (SELECT fattura_id FROM tmp_fattura), r.billing_account_id, r.st_abbinata,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'et', 'C2')
  FROM tmp_refs r, tmp_distinte d
 WHERE d.et = 'D2';

SELECT throws_like(
    $q$DELETE FROM pagamenti.vendite_contabili_righe WHERE riferimento_ente = 'PGTAP_ELIM_C2'$q$,
    '%non e'' compilata a mano%',
    '28) richiusa la GUC, la porta e'' di nuovo chiusa: non e'' un permesso, e'' un passaggio');

-- ============================================================
-- 29-30) I due guard di chiamata
-- ============================================================
-- ⚠️ Un id che non esiste non risponde []: sarebbe «si puo' eliminare» detto
--    di una cosa che non si vede. Stessa risposta per una riga di un altro.
SELECT throws_like(
    format($q$SELECT script.fn_check_riga_contabile_eliminabile(%s)$q$,
           (SELECT COALESCE(max(id), 0) + 1000000 FROM pagamenti.vendite_contabili_righe)),
    '%non trovata%',
    '29) una riga che non si legge: E_RIGA_CONTABILE_NON_TROVATA, non []');

SELECT throws_like(
    $q$SELECT script.fn_check_riga_contabile_eliminabile(0)$q$,
    '%Chiamata non valida%',
    '30) un id non valido e'' un chiamante rotto: E_PAGAMENTI_CHIAMATA_NON_VALIDA');

-- ============================================================
-- 31-35) Lettura e giudizio in due meta' (rev 2026-10-21)
-- ============================================================
SELECT has_function(
    'script', 'fn_check_riga_contabile_eliminabile_su_distinta',
    ARRAY['pagamenti.vendite_contabili'],
    '31) script.fn_check_riga_contabile_eliminabile_su_distinta esiste, con la riga della testata come parametro');

-- ⭐ Le due strade, sulle righe della fixture: a questo punto D1 e' VALIDATA
--    (test 20), D2 e' la GENERATA, D3 e' CHIUSA (test 23). ⛔ Non verde per
--    sottrazione: si pretendono le TRE distinte e TRE risposte diverse, cosi'
--    un'uguaglianza su un insieme vuoto, o su risposte tutte uguali, e' rossa.
SELECT ok(
    (SELECT count(DISTINCT c.id) = 3
        AND count(DISTINCT script.fn_check_riga_contabile_eliminabile_su_distinta(c)) = 3
        AND bool_and(script.fn_check_riga_contabile_eliminabile(r.id)
                     = script.fn_check_riga_contabile_eliminabile_su_distinta(c))
       FROM pagamenti.vendite_contabili_righe r
       JOIN pagamenti.vendite_contabili c ON c.id = r.contabile_id
      WHERE c.id IN (SELECT id FROM tmp_distinte)),
    '32) per id o su distinta, la risposta e'' la stessa — su tre distinte e tre risposte diverse');

-- ⭐ La meta' giudica il VALORE che riceve: una copia di D1 portata in
--    ANNULLATA risponde DISTINTA_ANNULLATA, mentre la D1 scritta e' VALIDATA.
--    Se la meta' rileggesse la testata (e con lei il perimetro) risponderebbe
--    DISTINTA_VALIDATA. ⚠️ La copia ha le colonne della tabella nello stesso
--    ordine (CREATE TABLE AS SELECT *), quindi il cast della riga regge.
CREATE TEMP TABLE tmp_d1_annullata AS
SELECT c.* FROM pagamenti.vendite_contabili c
 WHERE c.id = (SELECT id FROM tmp_distinte WHERE et = 'D1');

UPDATE tmp_d1_annullata
   SET stato_id = (SELECT s.id FROM pagamenti.vendite_contabili_stati s
                    WHERE s.codice_interno = 'ANNULLATA' ORDER BY s.id LIMIT 1);

SELECT is(
    (SELECT script.fn_check_riga_contabile_eliminabile_su_distinta(
                ROW(t.*)::pagamenti.vendite_contabili) -> 0 ->> 'reason'
       FROM tmp_d1_annullata t),
    'DISTINTA_ANNULLATA',
    '33) la meta'' giudica la distinta ricevuta e non la rilegge: nessun perimetro per riga');

SELECT throws_like(
    $q$SELECT script.fn_check_riga_contabile_eliminabile_su_distinta(NULL::pagamenti.vendite_contabili)$q$,
    '%Chiamata non valida%',
    '34) una distinta senza id (un LEFT JOIN che non ha trovato la testata): E_PAGAMENTI_CHIAMATA_NON_VALIDA');

-- ⭐ La forma `v_motivi := script.fn_check_…(` della firma per id e' cio' che fa
--    arrivare i codici della meta' al guard che la chiama: senza, il guard
--    perderebbe i suoi quattro codici in dbops.vw_funzioni_check_codici.
SELECT set_eq(
    $q$SELECT codice FROM dbops.vw_funzioni_check_codici
        WHERE funzione = 'pagamenti.trgfn_vendite_contabili_righe_guard_contenuto'$q$,
    ARRAY['E_RIGA_CONTABILE_DISTINTA_ANNULLATA', 'E_RIGA_CONTABILE_DISTINTA_FINALE',
          'E_RIGA_CONTABILE_DISTINTA_NON_MANUALE', 'E_RIGA_CONTABILE_DISTINTA_VALIDATA'],
    '35) il guard del contenuto eredita ancora i quattro codici attraverso la delega');

-- ⚠️ Niente cleanup: ci pensa il ROLLBACK.
SELECT * FROM finish();
ROLLBACK;
