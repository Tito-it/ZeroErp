-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- Test: la lineage per CHIAVE DEL NODO —
--       vendite.fn_documento_lineage_nodi(p_tipo_ids, p_uids)  (20261011-63)
--       vendite.fn_documento_lineage_archi(p_tipo_ids, p_uids) (20261011-64)
--       e le due viste che ne sono la proiezione (20261011-65/-66).
--       Brief: brief-db-lineage-seminata-per-chiave §8.2, giro 1.
--
-- Elenco test (plan 22):
--   1) le due funzioni esistono con la firma (bigint[], text[])
--   2) nodi: BEGIN ATOMIC, STABLE, INVOKER
--   3) archi: BEGIN ATOMIC, STABLE, INVOKER
--   4) vw_documento_lineage_nodi.fase resta varchar(20) (typmod ricastato)
--   5) vw_documento_lineage_nodi.tipo_codice_interno resta varchar(50)
--   6) vw_documento_lineage_archi.to_fase resta varchar(20)
--   7) seme NULL: fn_documento_lineage_nodi = la vista (EXCEPT ALL, due versi)
--   8) seme NULL: fn_documento_lineage_archi = la vista grezza (idem)
--   9) gemello «esiste» del 10-12: il grafo COSTRUITO porta esattamente gli
--      archi A, B, E, H, U (senza, i test seguenti passerebbero a vuoto)
--  10) ⭐ ogni nodo del grafo costruito, da solo come seme, da' gli archi
--      della vista incidenti a lui — uscenti ed entranti, nei due versi
--  11) ⭐ seme misto (i cinque nodi, quattro tipi): gli archi incidenti, ciascuno
--      UNA volta anche quando i due capi stanno entrambi nel seme
--  12) nodi col seme misto = le righe della vista per quei cinque nodi
--  13) seme vuoto: zero nodi e zero archi
--  14) un tipo ignoto, una chiave inesistente o una coppia monca non
--      seminano niente
--  15) le lettere che questo file NON costruisce (C, D, F, G, N, R, S, T): un
--      arco vivo per lettera, e i suoi due capi come seme danno gli archi della
--      vista — skip() se nessuna c'e' (database da zero, CI)
--  16) il nodo senza archi (il secondo preventivo) da' zero archi
--  17) ⭐ il pannello (fn_documento_lineage, per livelli dal 20261011-93), in
--      avanti dal preventivo del grafo costruito: 1A, 1B, 2E, 2H, 3U
--  18) ⭐ e indietro dalla commessa: 1B, 1E, 1U, 2A, 2H, 3A — l'ordine arriva
--      per due strade (A diretto al livello 2, e A dal DDT al livello 3): i
--      percorsi sono due, e la guardia dei cicli e' sul percorso
--  19) ⭐ la sintesi (fn_documento_lineage_sintesi) dei cinque nodi costruiti:
--      discendenti, frontiera, sorgenti e radice attesi dal grafo (dal giro B
--      la vista vw_documento_lineage non c'e' piu': i valori vengono dal grafo)
--  20) ⭐ ogni nodo chiesto da solo da' la stessa riga che da' nel seme misto
--  21) la commessa costruita ha tre sorgenti (B, E, U) e la radice e' il
--      preventivo, che e' la sorgente ROOT
--  22) la sintesi senza seme solleva (si chiede per le chiavi dei documenti)
--
-- ── PERCHE' QUESTO FILE ─────────────────────────────────────────────
--   La funzione degli archi scrive ogni ramo DUE volte: una per la lettura
--   intera (la vista) e una per il seme, uscente ed entrante. Un ramo nuovo
--   aggiunto in un modo solo, o un'esclusione delle entranti sbagliata, fa
--   divergere il seme dalla vista SENZA che la vista cambi: i pgTAP della
--   lineage che leggono le viste resterebbero verdi. Qui si confrontano i
--   due modi su un grafo costruito.
--
-- ── ⚠️ IL LIMITE, DICHIARATO ────────────────────────────────────────
--   Il grafo costruito copre cinque lettere su tredici (A, B, E, H, U: le
--   sole che le fixture sanno fare con scritture dirette). Le altre otto
--   chiedono fatture, resi e accrediti veri: il test 15 le prova sui dati
--   vivi, una per lettera, ed e' uno skip() su un database che non le ha.
--   Su dbdev, al 2026-10-11, le tredici ci sono tutte; la prova di
--   equivalenza completa (ogni nodo, ogni coppia di capi) e' nel brief §8.2.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(22);

-- ============================================================
-- Il grafo costruito: due preventivi, un ordine, una commessa, un DDT.
--   A  preventivo → ordine          (ordini.documento_origine_*)
--   B  preventivo → commessa        (commesse_sorgenti, chiave uid)
--   E  ordine     → commessa        (commesse_sorgenti, chiave id)
--   H  ordine     → DDT             (ddt.sorgente_*)
--   U  DDT        → commessa        (commesse_sorgenti, chiave id)
--   Il secondo preventivo non ha archi.
-- ============================================================
CREATE TEMP TABLE g_prev  AS SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgtap_lin_sem',  'DRAFT');
CREATE TEMP TABLE g_prev2 AS SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgtap_lin_sem2', 'DRAFT');
CREATE TEMP TABLE g_ord   AS SELECT * FROM dbops.fn_pgtap_crea_ordine('pgtap_lin_sem', 'DRAFT');
CREATE TEMP TABLE g_com   AS SELECT * FROM dbops.fn_pgtap_crea_commessa('pgtap_lin_sem');
CREATE TEMP TABLE g_ddt   AS
SELECT dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM g_ord),
                               (SELECT cliente_soggetto_ruolo_id FROM g_ord),
                               'VENDITA') AS ddt_id;

UPDATE vendite.ordini o
   SET documento_origine_tipo = 'PREVENTIVO',
       documento_origine_id   = (SELECT preventivo_id FROM g_prev)
 WHERE o.id = (SELECT ordine_id FROM g_ord);

UPDATE vendite.ddt d
   SET sorgente_tipo_id = (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA'),
       sorgente_uid     = (SELECT ordine_uid FROM g_ord)
 WHERE d.id = (SELECT ddt_id FROM g_ddt);

INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
SELECT (SELECT commessa_id FROM g_com), s.id, k.uid, k.ruolo
  FROM (VALUES ('PREVENTIVO',     (SELECT preventivo_uid::text FROM g_prev), 'ROOT'),
               ('ORDINE_VENDITA', (SELECT ordine_id::text      FROM g_ord),  'COLLEGATO'),
               ('DDT_VENDITA',    (SELECT ddt_id::text         FROM g_ddt),  'COLLEGATO')) AS k(codice, uid, ruolo)
  JOIN config.sorgenti s ON s.codice_interno = k.codice;

-- ⚠️ rev 2026-10-13 (20261013-69…-71, D-15 di Tid): ogni legame del grafo PORTA
--   qualcosa. Dal 20261013-71 la sintesi non attraversa un arco il cui legame e'
--   ritirato (vendite.fn_documento_lineage_legami), e un link senza righe e' un
--   legame che non porta niente. Nel modello non nasce cosi': il link
--   documento -> commessa lo scrive la madre delle righe insieme alla riga
--   (vendite.fn_upsert_commessa_attivita -> fn_link_commessa_sorgente), l'ordine
--   da preventivo nasce con le righe del preventivo, la bolla da ordine con le
--   evasioni. Prima la fixture scriveva solo i link di testata: qui le righe.
--   Chiave delle righe di commessa: <testata>.uid::text (vendite.fn_documento_legami).
DO $leg$
DECLARE
  v_art uuid; v_iva bigint; v_pr bigint; v_or bigint; v_dr bigint; v_ca bigint; k record;
BEGIN
  v_art := dbops.fn_pgtap_crea_articolo('PGT-LINSEM-' || substr(md5(random()::text), 1, 8), false);
  SELECT i.id INTO v_iva FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1;

  -- A: la riga d'ordine viene da una riga del preventivo.
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id)
  VALUES ((SELECT preventivo_id FROM g_prev), v_art, 1, 10, v_iva)
  RETURNING id INTO v_pr;
  -- rev 2026-11-06 (brief-db-sorgente-documento-e-riga lotto R, 20261106-57): la
  --   provenienza nel modello, come la scrive vendite.fn_push_preventivo_a_ordine:
  --   PREVENTIVO + l'uid del preventivo + la riga, accanto a preventivo_riga_id.
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione, qta_operativa,
                                    prezzo_unitario, iva_id, preventivo_riga_id,
                                    sorgente_tipo_id, sorgente_uid, sorgente_riga)
  VALUES ((SELECT ordine_id FROM g_ord), 1, v_art, 'Riga pgTAP lineage seminata', 1, 10, v_iva, v_pr,
          (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO'),
          (SELECT p.uid FROM vendite.preventivi p WHERE p.id = (SELECT preventivo_id FROM g_prev)), v_pr)
  RETURNING id INTO v_or;

  -- H: la riga della bolla evade la riga d'ordine.
  INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, storicizza)
  VALUES ((SELECT ddt_id FROM g_ddt), 1, v_art, 'Riga pgTAP lineage seminata', 1, false)
  RETURNING id INTO v_dr;
  INSERT INTO vendite.ordini_righe_fulfillment (ordine_riga_id, ddt_riga_id, qta_evasa, storicizza)
  VALUES (v_or, v_dr, 1, false);

  -- B, E, U: una riga di commessa NON_EMESSA per ciascuna sorgente.
  FOR k IN
    SELECT s.id AS tipo_id, x.uid
      FROM (VALUES ('PREVENTIVO',     (SELECT preventivo_uid::text FROM g_prev)),
                   ('ORDINE_VENDITA', (SELECT ordine_uid::text     FROM g_ord)),
                   ('DDT_VENDITA',    (SELECT d.uid::text FROM vendite.ddt d
                                        WHERE d.id = (SELECT ddt_id FROM g_ddt)))) AS x(codice, uid)
      JOIN config.sorgenti s ON s.codice_interno = x.codice
  LOOP
    SELECT a.attivita_id INTO v_ca
      FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM g_com)) a;
    UPDATE vendite.commesse_attivita
       SET sorgente_tipo_id = k.tipo_id, sorgente_uid = k.uid
     WHERE id = v_ca;
  END LOOP;
END $leg$;

-- I cinque nodi, con la chiave del modello (tipo_id, uid::text).
CREATE TEMP TABLE g_nodi AS
SELECT s.id AS tipo_id, k.uid
  FROM (VALUES ('PREVENTIVO',     (SELECT preventivo_uid::text FROM g_prev)),
               ('PREVENTIVO',     (SELECT preventivo_uid::text FROM g_prev2)),
               ('ORDINE_VENDITA', (SELECT ordine_id::text      FROM g_ord)),
               ('COMMESSA',       (SELECT commessa_id::text    FROM g_com)),
               ('DDT_VENDITA',    (SELECT ddt_id::text         FROM g_ddt))) AS k(codice, uid)
  JOIN config.sorgenti s ON s.codice_interno = k.codice;

-- Gli archi della vista, grezzi (le colonne della funzione).
CREATE TEMP TABLE g_vista AS
SELECT from_tipo_id, from_uid, to_tipo_id, to_uid, ruolo, arco, is_ramo_inverso, rango_origine
  FROM vendite.vw_documento_lineage_archi;

-- ============================================================
-- 1-3. Forma
-- ============================================================
SELECT ok(
    to_regprocedure('vendite.fn_documento_lineage_nodi(bigint[], text[])') IS NOT NULL
    AND to_regprocedure('vendite.fn_documento_lineage_archi(bigint[], text[])') IS NOT NULL,
    '1) fn_documento_lineage_nodi e fn_documento_lineage_archi esistono con la firma (bigint[], text[])');

SELECT ok(
    (SELECT p.prosqlbody IS NOT NULL AND p.provolatile = 's' AND NOT p.prosecdef
       FROM pg_proc p WHERE p.oid = 'vendite.fn_documento_lineage_nodi(bigint[], text[])'::regprocedure),
    '2) fn_documento_lineage_nodi: BEGIN ATOMIC (dipendenze in pg_depend), STABLE, INVOKER');

SELECT ok(
    (SELECT p.prosqlbody IS NOT NULL AND p.provolatile = 's' AND NOT p.prosecdef
       FROM pg_proc p WHERE p.oid = 'vendite.fn_documento_lineage_archi(bigint[], text[])'::regprocedure),
    '3) fn_documento_lineage_archi: BEGIN ATOMIC (dipendenze in pg_depend), STABLE, INVOKER');

-- ============================================================
-- 4-6. I typmod delle viste: la funzione li perde, la proiezione li ricasta
-- ============================================================
SELECT col_type_is('vendite', 'vw_documento_lineage_nodi', 'fase', 'character varying(20)',
    '4) vw_documento_lineage_nodi.fase resta varchar(20)');
SELECT col_type_is('vendite', 'vw_documento_lineage_nodi', 'tipo_codice_interno', 'character varying(50)',
    '5) vw_documento_lineage_nodi.tipo_codice_interno resta varchar(50)');
SELECT col_type_is('vendite', 'vw_documento_lineage_archi', 'to_fase', 'character varying(20)',
    '6) vw_documento_lineage_archi.to_fase resta varchar(20)');

-- ============================================================
-- 7-8. Seme NULL = la vista
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM (
        SELECT * FROM vendite.fn_documento_lineage_nodi(NULL::bigint[], NULL::text[])
        EXCEPT ALL SELECT * FROM vendite.vw_documento_lineage_nodi) x)
  + (SELECT count(*)::int FROM (
        SELECT * FROM vendite.vw_documento_lineage_nodi
        EXCEPT ALL SELECT * FROM vendite.fn_documento_lineage_nodi(NULL::bigint[], NULL::text[])) y),
    0,
    '7) seme NULL: fn_documento_lineage_nodi e'' la vista, riga per riga');

SELECT is(
    (SELECT count(*)::int FROM (
        SELECT * FROM vendite.fn_documento_lineage_archi(NULL::bigint[], NULL::text[])
        EXCEPT ALL SELECT * FROM g_vista) x)
  + (SELECT count(*)::int FROM (
        SELECT * FROM g_vista
        EXCEPT ALL SELECT * FROM vendite.fn_documento_lineage_archi(NULL::bigint[], NULL::text[])) y),
    0,
    '8) seme NULL: fn_documento_lineage_archi e'' la vista grezza, riga per riga');

-- ============================================================
-- 9. Il grafo costruito esiste davvero
-- ============================================================
SELECT is(
    (SELECT string_agg(DISTINCT v.arco, ',' ORDER BY v.arco)
       FROM g_vista v
       JOIN g_nodi n ON (n.tipo_id = v.from_tipo_id AND n.uid = v.from_uid)
                     OR (n.tipo_id = v.to_tipo_id   AND n.uid = v.to_uid)),
    'A,B,E,H,U',
    '9) il grafo costruito porta esattamente gli archi A, B, E, H, U (gemello «esiste» dei test 10-12)');

-- ============================================================
-- 10. Ogni nodo da solo
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM g_nodi n
      WHERE (SELECT count(*) FROM (
                SELECT * FROM vendite.fn_documento_lineage_archi(ARRAY[n.tipo_id], ARRAY[n.uid])
                EXCEPT ALL
                SELECT * FROM g_vista v
                 WHERE (v.from_tipo_id = n.tipo_id AND v.from_uid = n.uid)
                    OR (v.to_tipo_id   = n.tipo_id AND v.to_uid   = n.uid)) a)
          + (SELECT count(*) FROM (
                SELECT * FROM g_vista v
                 WHERE (v.from_tipo_id = n.tipo_id AND v.from_uid = n.uid)
                    OR (v.to_tipo_id   = n.tipo_id AND v.to_uid   = n.uid)
                EXCEPT ALL
                SELECT * FROM vendite.fn_documento_lineage_archi(ARRAY[n.tipo_id], ARRAY[n.uid])) b) <> 0),
    0,
    '10) ogni nodo del grafo costruito, come seme, da'' gli archi della vista incidenti a lui (uscenti ed entranti)');

-- ============================================================
-- 11-12. Seme misto: i cinque nodi insieme
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM (
        SELECT * FROM vendite.fn_documento_lineage_archi(
                   (SELECT array_agg(tipo_id) FROM g_nodi), (SELECT array_agg(uid) FROM g_nodi))
        EXCEPT ALL
        SELECT v.* FROM g_vista v
         WHERE EXISTS (SELECT 1 FROM g_nodi n
                        WHERE (n.tipo_id = v.from_tipo_id AND n.uid = v.from_uid)
                           OR (n.tipo_id = v.to_tipo_id   AND n.uid = v.to_uid))) a)
  + (SELECT count(*)::int FROM (
        SELECT v.* FROM g_vista v
         WHERE EXISTS (SELECT 1 FROM g_nodi n
                        WHERE (n.tipo_id = v.from_tipo_id AND n.uid = v.from_uid)
                           OR (n.tipo_id = v.to_tipo_id   AND n.uid = v.to_uid))
        EXCEPT ALL
        SELECT * FROM vendite.fn_documento_lineage_archi(
                   (SELECT array_agg(tipo_id) FROM g_nodi), (SELECT array_agg(uid) FROM g_nodi))) b),
    0,
    '11) seme misto: gli archi incidenti, ciascuno UNA volta anche con i due capi nel seme');

SELECT is(
    (SELECT count(*)::int FROM (
        SELECT * FROM vendite.fn_documento_lineage_nodi(
                   (SELECT array_agg(tipo_id) FROM g_nodi), (SELECT array_agg(uid) FROM g_nodi))
        EXCEPT ALL
        SELECT v.* FROM vendite.vw_documento_lineage_nodi v
          JOIN g_nodi n ON n.tipo_id = v.tipo_id AND n.uid = v.uid) a)
  + (SELECT count(*)::int FROM (
        SELECT v.* FROM vendite.vw_documento_lineage_nodi v
          JOIN g_nodi n ON n.tipo_id = v.tipo_id AND n.uid = v.uid
        EXCEPT ALL
        SELECT * FROM vendite.fn_documento_lineage_nodi(
                   (SELECT array_agg(tipo_id) FROM g_nodi), (SELECT array_agg(uid) FROM g_nodi))) b)
  + abs((SELECT count(*)::int FROM g_nodi) - 5),
    0,
    '12) nodi col seme misto = le righe della vista per quei nodi (cinque, uno per riga del seme)');

-- ============================================================
-- 13-14. Semi che non seminano
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM vendite.fn_documento_lineage_nodi('{}'::bigint[], '{}'::text[]))
  + (SELECT count(*)::int FROM vendite.fn_documento_lineage_archi('{}'::bigint[], '{}'::text[])),
    0,
    '13) seme vuoto: zero nodi e zero archi (un array vuoto non e'' «tutti»)');

SELECT is(
    (SELECT count(*)::int FROM vendite.fn_documento_lineage_archi(ARRAY[-1]::bigint[], ARRAY['1']))
  + (SELECT count(*)::int FROM vendite.fn_documento_lineage_archi(
         ARRAY[(SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA')], ARRAY['-1']))
  + (SELECT count(*)::int FROM vendite.fn_documento_lineage_archi(
         ARRAY[(SELECT tipo_id FROM g_nodi WHERE uid = (SELECT ordine_id::text FROM g_ord))], ARRAY[NULL::text]))
  + (SELECT count(*)::int FROM vendite.fn_documento_lineage_nodi(ARRAY[-1]::bigint[], ARRAY['1'])),
    0,
    '14) un tipo ignoto, una chiave inesistente o una coppia monca non seminano niente');

-- ============================================================
-- 15. Le lettere non costruite qui: un arco vivo per lettera
-- ============================================================
CREATE TEMP TABLE g_campioni AS
SELECT DISTINCT ON (v.arco) v.arco, v.from_tipo_id, v.from_uid, v.to_tipo_id, v.to_uid
  FROM g_vista v
 WHERE v.arco IN ('C', 'D', 'F', 'G', 'N', 'R', 'S', 'T')
 ORDER BY v.arco, v.from_tipo_id, v.from_uid, v.to_tipo_id, v.to_uid;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM g_campioni)
    THEN skip('15) nessun arco C, D, F, G, N, R, S, T su questo database (da zero): la prova sui dati vivi non si applica', 1)
    ELSE is(
        (SELECT count(*)::int FROM g_campioni c
          WHERE (SELECT count(*) FROM (
                    SELECT * FROM vendite.fn_documento_lineage_archi(
                               ARRAY[c.from_tipo_id, c.to_tipo_id], ARRAY[c.from_uid, c.to_uid])
                    EXCEPT ALL
                    SELECT * FROM g_vista v
                     WHERE (v.from_tipo_id, v.from_uid) IN ((c.from_tipo_id, c.from_uid), (c.to_tipo_id, c.to_uid))
                        OR (v.to_tipo_id,   v.to_uid)   IN ((c.from_tipo_id, c.from_uid), (c.to_tipo_id, c.to_uid))) a)
              + (SELECT count(*) FROM (
                    SELECT * FROM g_vista v
                     WHERE (v.from_tipo_id, v.from_uid) IN ((c.from_tipo_id, c.from_uid), (c.to_tipo_id, c.to_uid))
                        OR (v.to_tipo_id,   v.to_uid)   IN ((c.from_tipo_id, c.from_uid), (c.to_tipo_id, c.to_uid))
                    EXCEPT ALL
                    SELECT * FROM vendite.fn_documento_lineage_archi(
                               ARRAY[c.from_tipo_id, c.to_tipo_id], ARRAY[c.from_uid, c.to_uid])) b) <> 0),
        0,
        format('15) lettere non costruite qui, un arco vivo ciascuna (%s): i due capi come seme danno gli archi della vista',
               (SELECT string_agg(arco, ',' ORDER BY arco) FROM g_campioni)))
END;

-- ============================================================
-- 16. Il nodo senza archi
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM vendite.fn_documento_lineage_archi(
         ARRAY[(SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')],
         ARRAY[(SELECT preventivo_uid::text FROM g_prev2)])),
    0,
    '16) il preventivo senza archi, come seme, non ne da'' nessuno');

-- ============================================================
-- 17-18. Il pannello, sul grafo costruito
-- ============================================================
-- Le catene attese sono ricavate dal grafo, e verificate contro la forma di
-- prima (vista intera + ricorsione, 20261010-44) il 2026-10-11.
SELECT is(
    (SELECT string_agg(l.livello || l.arco, ',' ORDER BY l.livello, l.arco)
       FROM vendite.fn_documento_lineage(
                (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO'),
                (SELECT preventivo_uid::text FROM g_prev), 'avanti') l),
    '1A,1B,2E,2H,3U',
    '17) pannello, avanti dal preventivo: A e B, poi E e H dall''ordine, poi U dal DDT');

SELECT is(
    (SELECT string_agg(l.livello || l.arco, ',' ORDER BY l.livello, l.arco)
       FROM vendite.fn_documento_lineage(
                (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
                (SELECT commessa_id::text FROM g_com), 'indietro') l),
    '1B,1E,1U,2A,2H,3A',
    '18) pannello, indietro dalla commessa: l''ordine si raggiunge per due strade, e A compare a due livelli');

-- ============================================================
-- 19-22. La sintesi
-- ============================================================
-- ⭐ rev giro B (2026-10-11): vw_documento_lineage e' ritirata (20261011-98), e
--   la sintesi e' la sede unica della regola. I valori attesi si ricavano dal
--   grafo costruito (tutti i documenti in fase APERTO): la frontiera e' il nodo
--   piu' a valle — la commessa, raggiunta al livello 3 dal preventivo via
--   ordine e DDT; le sorgenti sono gli archi entranti non di ritorno, la radice
--   e' la sorgente ROOT. Verificati contro la vista prima del ritiro.
CREATE TEMP TABLE g_sint AS
SELECT CASE
         WHEN s.tipo_codice_interno = 'PREVENTIVO' AND s.uid = (SELECT preventivo_uid::text FROM g_prev)  THEN 'prev'
         WHEN s.tipo_codice_interno = 'PREVENTIVO' AND s.uid = (SELECT preventivo_uid::text FROM g_prev2) THEN 'prev2'
         WHEN s.tipo_codice_interno = 'ORDINE_VENDITA' THEN 'ord'
         WHEN s.tipo_codice_interno = 'COMMESSA'       THEN 'com'
         WHEN s.tipo_codice_interno = 'DDT_VENDITA'    THEN 'ddt'
       END AS nodo, s.*
  FROM vendite.fn_documento_lineage_sintesi(
           (SELECT array_agg(tipo_id) FROM g_nodi), (SELECT array_agg(uid) FROM g_nodi)) s;

SELECT is(
    (SELECT string_agg(g.nodo || ':' || g.n_discendenti_diretti || '/' || g.n_discendenti_attivi
                       || '/' || g.frontiera_tipo_codice_interno || '/' || g.n_sorgenti
                       || '/' || coalesce(so.codice_interno, '-') || '/' || g.is_transitato::text,
                       ',' ORDER BY g.nodo)
       FROM g_sint g
       LEFT JOIN config.sorgenti so ON so.id = g.root_tipo_id),
    'com:0/0/COMMESSA/3/PREVENTIVO/false,ddt:1/1/COMMESSA/1/ORDINE_VENDITA/true,'
    'ord:2/2/COMMESSA/1/PREVENTIVO/true,prev:2/2/COMMESSA/0/-/true,prev2:0/0/PREVENTIVO/0/-/false',
    '19) sintesi dei cinque nodi costruiti: discendenti, frontiera, sorgenti e radice attesi dal grafo');

SELECT is(
    (SELECT count(*)::int FROM g_nodi n
      WHERE (SELECT count(*) FROM (
                SELECT * FROM vendite.fn_documento_lineage_sintesi(ARRAY[n.tipo_id], ARRAY[n.uid])
                EXCEPT ALL
                SELECT tipo_id, uid, codice, stato_codice_interno, stato_codice, stato_descrizione, fase,
                       is_abortito, pratica_id, pratica_numero, n_pratiche, frontiera_tipo_id, frontiera_uid,
                       frontiera_codice, frontiera_stato_codice_interno, frontiera_fase, n_discendenti_diretti,
                       n_discendenti_attivi, is_transitato, n_sorgenti, root_tipo_id, root_uid, root_codice,
                       natura_doc_codice_interno, natura_doc_descrizione, frontiera_natura_doc_codice_interno,
                       tipo_codice_interno, frontiera_tipo_codice_interno
                  FROM g_sint g WHERE g.tipo_id = n.tipo_id AND g.uid = n.uid) a) <> 0),
    0,
    '20) ogni nodo chiesto da solo da'' la stessa riga che da'' nel seme misto');

SELECT is(
    (SELECT s.n_sorgenti || '|' || (s.root_uid = (SELECT preventivo_uid::text FROM g_prev))::text
       FROM vendite.fn_documento_lineage_sintesi(
                ARRAY[(SELECT s2.id FROM config.sorgenti s2 WHERE s2.codice_interno = 'COMMESSA')],
                ARRAY[(SELECT commessa_id::text FROM g_com)]) s),
    '3|true',
    '21) la commessa costruita ha tre sorgenti (B, E, U) e la radice e'' il preventivo ROOT');

SELECT throws_ok(
    $q$ SELECT * FROM vendite.fn_documento_lineage_sintesi(NULL::bigint[], NULL::text[]) $q$,
    NULL,
    '22) la sintesi senza seme solleva: si chiede per le chiavi dei documenti');

SELECT * FROM finish();
ROLLBACK;
