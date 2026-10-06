-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: i test 4-6 scrivono su dbops.presidi — catalogo che a
--   runtime non scrive nessuno (lo popola il mirror CSV di 80_data) — per
--   provare che i due CHECK ci siano. E' la stessa situazione, con la stessa
--   motivazione, di test-catalogo-presidi-v1.sql. La lettura come applicazione
--   (test 7) si asserisce col catalogo dei privilegi, non con la connessione.
--
-- Test: il testo dei presidi per chi agisce, e chi lo spegne
-- Brief: brief-db-presidi-cosa-significa-cosa-fare.md §4.3-§4.4
--
-- Elenco test (plan 7):
--  1) la misura non e' degradata: ci sono presidi che possono accendersi
--  2) ⭐ COMPLETEZZA — ogni presidio attivo, non obsoleto e non INVENTARIO ha
--     la riga `it` (il messaggio nomina le viste scoperte)
--  3) ⭐ RITIRO — nessuna riga di testo punta a un presidio obsoleto
--  4) ⛔ chk_presidi_chi_agisce_se_allarma rifiuta un non-INVENTARIO senza
--     chi_agisce
--  5) ...e accetta un INVENTARIO senza chi_agisce
--  6) ⛔ chk_presidi_chi_agisce rifiuta un valore fuori dominio
--  7) zeroerp_app legge dbops.presidi_testi
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ I test 2 e 3 sono i due versi dello stesso legame, come i test 2 e 3 di
--   test-catalogo-presidi-v1. Il 2 e' quello che conta: un CHECK non guarda
--   un'altra tabella, quindi e' QUESTO il vincolo per cui la prossima vista di
--   presidio non entra a catalogo senza le sue due frasi — e l'errore sta
--   nella build, non a video. Il 3 impedisce ai testi di sopravvivere al
--   presidio che spiegavano: una frase che nessuno legge piu'.
--
-- ⚠️ Il test 2 itera sul catalogo, ma il catalogo e' CONTRATTO (seed di
--   80_data), non popolazione: su un database ricostruito da zero e' pieno
--   uguale. Il test 1 c'e' perche' un catalogo vuoto lo farebbe passare a vuoto.
--
-- ⚠️ I test 4 e 6 si leggono dal NOME del vincolo (throws_like), non dal solo
--   SQLSTATE: dbops.presidi ha nove CHECK, e un 23514 di un altro vincolo
--   farebbe passare il test per il motivo sbagliato. Il nome sta nel messaggio
--   in ogni lingua del server.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- 1) La misura non e' degradata
-- ============================================================
-- ⚠️ «Non vuoto» e non un numero: un numero scritto qui invecchierebbe alla
--   prossima vista di presidio, cioe' proprio all'evento che il test 2 presidia.
SELECT cmp_ok(
    (SELECT count(*) FROM dbops.presidi
      WHERE attivo AND obsoleto_dal IS NULL AND natura <> 'INVENTARIO')::bigint,
    '>', 0::bigint,
    'test 1 — ci sono presidi che possono accendersi (misura non degradata)');

-- ============================================================
-- 2) Completezza: ogni presidio che si accende ha la riga `it`
-- ============================================================
SELECT is(
    coalesce((
        SELECT string_agg(p.vista, ', ' ORDER BY p.vista)
          FROM dbops.presidi p
         WHERE p.attivo
           AND p.obsoleto_dal IS NULL
           AND p.natura <> 'INVENTARIO'
           AND NOT EXISTS (SELECT 1 FROM dbops.presidi_testi t
                            WHERE t.vista = p.vista
                              AND t.lingua = 'it')), ''),
    '',
    'test 2 — ogni presidio attivo, non obsoleto e non INVENTARIO ha significato e azione in italiano');

-- ============================================================
-- 3) Ritiro: nessun testo su un presidio obsoleto
-- ============================================================
SELECT is(
    coalesce((
        SELECT string_agg(DISTINCT t.vista, ', ' ORDER BY t.vista)
          FROM dbops.presidi_testi t
          JOIN dbops.presidi p ON p.vista = t.vista
         WHERE p.obsoleto_dal IS NOT NULL), ''),
    '',
    'test 3 — nessuna riga di dbops.presidi_testi punta a un presidio obsoleto');

-- ============================================================
-- 4) e 5) chi_agisce obbligatoria, tranne su INVENTARIO
-- ============================================================
SELECT throws_like(
    $$INSERT INTO dbops.presidi (vista, natura, cadenza, perimetro, nota, chi_agisce)
      VALUES ('pgtap_presidi_testi.vw_senza_chi', 'ZERO', 'MAI', 'LIBERO',
              'fixture pgTAP: un presidio che si accende senza dire a chi tocca', NULL)$$,
    '%chk_presidi_chi_agisce_se_allarma%',
    'test 4 — un presidio non INVENTARIO senza chi_agisce e'' rifiutato dal database');

SELECT lives_ok(
    $$INSERT INTO dbops.presidi (vista, natura, cadenza, perimetro, nota, chi_agisce)
      VALUES ('pgtap_presidi_testi.vw_inventario', 'INVENTARIO', 'MAI', 'LIBERO',
              'fixture pgTAP: un inventario non si accende', NULL)$$,
    'test 5 — un INVENTARIO senza chi_agisce e'' accettato');

-- ============================================================
-- 6) Il dominio di chi_agisce
-- ============================================================
SELECT throws_like(
    $$INSERT INTO dbops.presidi (vista, natura, cadenza, perimetro, nota, chi_agisce)
      VALUES ('pgtap_presidi_testi.vw_chi_ignoto', 'ZERO', 'MAI', 'LIBERO',
              'fixture pgTAP: un valore fuori dominio', 'OPERATORE')$$,
    '%chk_presidi_chi_agisce"%',
    'test 6 — chi_agisce fuori dai tre valori e'' rifiutato dal database');

-- ============================================================
-- 7) L'applicazione legge i testi
-- ============================================================
-- ⭐ has_table_privilege e non information_schema.role_table_grants, che
--   mostra solo i grant del ruolo connesso (linee-guida-sql §11.8).
SELECT ok(
    has_table_privilege('zeroerp_app', 'dbops.presidi_testi', 'SELECT'),
    'test 7 — zeroerp_app ha SELECT su dbops.presidi_testi');

SELECT * FROM finish();
ROLLBACK;
