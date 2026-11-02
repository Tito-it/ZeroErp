-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: i test 4-6 e 12-14 scrivono su dbops.presidi e
--   dbops.presidi_testi — catalogo che a
--   runtime non scrive nessuno (lo popola il mirror CSV di 80_data) — per
--   provare che i due CHECK ci siano. E' la stessa situazione, con la stessa
--   motivazione, di test-catalogo-presidi-v1.sql. La lettura come applicazione
--   (test 7) si asserisce col catalogo dei privilegi, non con la connessione.
--
-- Test: il testo dei presidi per chi agisce, e chi lo spegne
-- Brief: brief-db-presidi-cosa-significa-cosa-fare.md §4.3-§4.4
--        brief-db-presidio-processi-testo-per-causa.md §3 B (test 8-14, rev 2026-10-09)
--
-- Elenco test (plan 19):
--  1) la misura non e' degradata: ci sono presidi che possono accendersi
--  2) ⭐ COMPLETEZZA — ogni presidio attivo, non obsoleto e non INVENTARIO ha
--     la riga `it` GENERICA, cioe' con variante NULL (il messaggio nomina le
--     viste scoperte)
--  3) ⭐ RITIRO — nessuna riga di testo punta a un presidio obsoleto
--  4) ⛔ chk_presidi_chi_agisce_se_allarma rifiuta un non-INVENTARIO senza
--     chi_agisce
--  5) ...e accetta un INVENTARIO senza chi_agisce
--  6) ⛔ chk_presidi_chi_agisce rifiuta un valore fuori dominio
--  7) zeroerp_app legge dbops.presidi_testi
--  8) ⛔ la colonna_variante dichiarata dal catalogo ESISTE nella sua vista
--  9) ⛔ nessuna causa (dbops.presidi_cause) su un presidio che non dichiara
--     colonna_variante — i testi di variante seguono, per FK (rev §5.5)
-- 10) ⭐ ogni testo (generico o variante) in una lingua ha la riga `it` DELLA
--     STESSA variante: il ripiego per lingua resta dentro la causa
-- 11) ⛔ la chiave (vista, lingua, variante) e' NULLS NOT DISTINCT — clausola
-- 12) ...e due testi generici dello stesso presidio e lingua sono rifiutati
-- 13) ⛔ una variante vuota e' rifiutata (non e' «nessuna variante»)
-- 14) ⛔ una colonna_variante vuota e' rifiutata
-- 15) ⛔ il dominio di chi_agisce e' lo STESSO su dbops.presidi e su
--     dbops.presidi_cause (vocabolario scritto in due posti)
-- 16) ⭐ ogni causa ha il suo testo italiano
-- 17) ⛔ ogni presidio che dichiara colonna_variante ha almeno una causa
-- 18) ⛔ la FK dei testi di variante verso le cause c'e', ed e' convalidata
-- 19) zeroerp_app legge dbops.presidi_cause
--
-- ⭐ I TEST 8-14 SONO IL MODELLO DELLE VARIANTI, non il presidio dei processi.
--   Che ogni CAUSA che una vista puo' produrre abbia il suo testo non si sa da
--   qui — bisogna sapere che cosa la vista produce: lo prova il pgTAP del
--   presidio (dbops/test-presidio-processi-testo-per-causa-v1). Qui si
--   presidia che la forma regga per qualsiasi presidio.
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

SELECT plan(19);

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
                              AND t.lingua = 'it'
                              -- ⚠️ rev 2026-10-09: il GENERICO. Una variante
                              --   non fa le veci del testo del presidio.
                              AND t.variante IS NULL)), ''),
    '',
    'test 2 — ogni presidio attivo, non obsoleto e non INVENTARIO ha significato e azione generici in italiano');

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

-- ============================================================
-- 8) ⛔ La colonna della variante esiste nella vista
-- ============================================================
-- ⚠️ Un CHECK non guarda un altro oggetto. Una colonna_variante che non esiste
--   (un refuso, o una vista rifatta senza) lascerebbe il lettore senza la
--   causa di ogni riga: e il testo giusto non si troverebbe mai.
SELECT is(
    coalesce((
        SELECT string_agg(p.vista || '.' || p.colonna_variante, ', ' ORDER BY p.vista)
          FROM dbops.presidi p
         WHERE p.colonna_variante IS NOT NULL
           AND NOT EXISTS (
               SELECT 1 FROM pg_attribute a
                WHERE a.attrelid = to_regclass(p.vista)
                  AND a.attname = p.colonna_variante
                  AND a.attnum > 0
                  AND NOT a.attisdropped)), ''),
    '',
    'test 8 — ogni colonna_variante dichiarata dal catalogo esiste nella sua vista');

-- ============================================================
-- 9) ⛔ Cause solo dove il catalogo le chiede
-- ============================================================
-- Una causa su un presidio senza colonna_variante non la sceglie nessuno: il
-- suo testo e il suo «chi agisce» non li leggera' mai nessuno, e chi li scrive
-- li crede letti. ⭐ Rev 2026-10-09 (§5.5): si guarda il catalogo delle cause,
-- perche' i testi di variante gli sono figli (fk_presidi_testi_presidi_cause).
SELECT is(
    coalesce((
        SELECT string_agg(c.vista || ' [' || c.causa || ']', ', ' ORDER BY c.vista, c.causa)
          FROM dbops.presidi_cause c
          JOIN dbops.presidi p ON p.vista = c.vista
         WHERE p.colonna_variante IS NULL), ''),
    '',
    'test 9 — nessuna causa su un presidio che non dichiara colonna_variante');

-- ============================================================
-- 10) ⭐ Il ripiego per lingua resta dentro la variante
-- ============================================================
-- Il lettore che non trova la sua lingua ripiega su `it` DELLA STESSA
-- variante, mai sul generico: quindi ogni testo deve avere il suo `it`.
SELECT is(
    coalesce((
        SELECT string_agg(t.vista || ' [' || coalesce(t.variante, 'generico') || '] ' || t.lingua,
                          ', ' ORDER BY t.vista, t.variante, t.lingua)
          FROM dbops.presidi_testi t
         WHERE NOT EXISTS (
               SELECT 1 FROM dbops.presidi_testi i
                WHERE i.vista = t.vista
                  AND i.lingua = 'it'
                  AND i.variante IS NOT DISTINCT FROM t.variante)), ''),
    '',
    'test 10 — ogni testo, generico o variante, ha la riga italiana della stessa variante');

-- ============================================================
-- 11) e 12) ⛔ La chiave e' NULLS NOT DISTINCT
-- ============================================================
-- ⚠️ Si asserisce la CLAUSOLA, non solo il nome: con l'indice di default due
--   testi generici dello stesso presidio convivrebbero (i NULL sono distinti
--   fra loro) e il lettore ne pescherebbe uno a caso.
SELECT ok(
    coalesce((
        SELECT i.indnullsnotdistinct
          FROM pg_constraint c
          JOIN pg_index i ON i.indexrelid = c.conindid
         WHERE c.conrelid = 'dbops.presidi_testi'::regclass
           AND c.conname = 'uq_presidi_testi_vista_lingua_variante'), false),
    'test 11 — uq_presidi_testi_vista_lingua_variante e'' NULLS NOT DISTINCT');

-- ⭐ E il comportamento, costruito: il presidio esiste di sicuro (test 2), la
--   seconda riga generica e' quella che la clausola deve rifiutare.
SELECT throws_like(
    $$INSERT INTO dbops.presidi_testi (vista, lingua, variante, significato, azione)
      SELECT t.vista, t.lingua, NULL, 'doppione', 'doppione'
        FROM dbops.presidi_testi t
       WHERE t.lingua = 'it' AND t.variante IS NULL
       ORDER BY t.vista
       LIMIT 1$$,
    '%uq_presidi_testi_vista_lingua_variante%',
    'test 12 — un secondo testo generico per lo stesso presidio e lingua e'' rifiutato');

-- ============================================================
-- 13) e 14) ⛔ Vuoto non e' «nessuno»
-- ============================================================
SELECT throws_like(
    $$INSERT INTO dbops.presidi_testi (vista, lingua, variante, significato, azione)
      SELECT t.vista, 'it', '  ', 'vuota', 'vuota'
        FROM dbops.presidi_testi t
       ORDER BY t.vista
       LIMIT 1$$,
    '%chk_presidi_testi_variante_non_vuota%',
    'test 13 — una variante vuota e'' rifiutata: «nessuna variante» si scrive NULL');

SELECT throws_like(
    $$INSERT INTO dbops.presidi (vista, natura, cadenza, perimetro, nota, chi_agisce,
                                 colonna_variante)
      VALUES ('pgtap_presidi_testi.vw_variante_vuota', 'ZERO', 'MAI', 'LIBERO',
              'fixture pgTAP: una colonna_variante vuota', 'SVILUPPO', '  ')$$,
    '%chk_presidi_colonna_variante_non_vuota%',
    'test 14 — una colonna_variante vuota e'' rifiutata dal database');

-- ============================================================
-- 15) ⛔ Il dominio di chi_agisce, scritto in due posti
-- ============================================================
-- Una tabella di vocabolario per tre valori sarebbe sproporzionata; allora la
-- seconda copia la tiene allineata QUESTO test. ⚠️ Si confrontano le
-- definizioni da pg_constraint: le colonne hanno lo stesso nome, quindi due
-- CHECK uguali si stampano uguali.
SELECT is(
    (SELECT pg_get_constraintdef(oid) FROM pg_constraint
      WHERE conrelid = 'dbops.presidi_cause'::regclass
        AND conname = 'chk_presidi_cause_chi_agisce'),
    (SELECT pg_get_constraintdef(oid) FROM pg_constraint
      WHERE conrelid = 'dbops.presidi'::regclass
        AND conname = 'chk_presidi_chi_agisce'),
    'test 15 — chi_agisce ha lo stesso dominio sul presidio e sulla causa');

-- ============================================================
-- 16) ⭐ Ogni causa ha il suo testo italiano
-- ============================================================
-- ⛔ Il generico non fa da ripiego: una causa senza testo darebbe il rimedio
--   sbagliato, in silenzio.
SELECT is(
    coalesce((
        SELECT string_agg(c.vista || ' [' || c.causa || ']', ', ' ORDER BY c.vista, c.causa)
          FROM dbops.presidi_cause c
         WHERE NOT EXISTS (
               SELECT 1 FROM dbops.presidi_testi t
                WHERE t.vista = c.vista
                  AND t.lingua = 'it'
                  AND t.variante = c.causa)), ''),
    '',
    'test 16 — ogni causa ha significato e azione in italiano');

-- ============================================================
-- 17) ⛔ Chi dichiara colonna_variante ha delle cause
-- ============================================================
-- Senza cause il lettore troverebbe la colonna e nessun testo per nessuna riga.
SELECT is(
    coalesce((
        SELECT string_agg(p.vista, ', ' ORDER BY p.vista)
          FROM dbops.presidi p
         WHERE p.colonna_variante IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM dbops.presidi_cause c
                            WHERE c.vista = p.vista)), ''),
    '',
    'test 17 — ogni presidio che dichiara colonna_variante ha almeno una causa a catalogo');

-- ============================================================
-- 18) ⛔ I testi di variante sono figli della causa
-- ============================================================
-- ⚠️ Convalidata, non solo presente: nasce NOT VALID (00_schema/20261009-36) e
--   la convalida 90_end/20261009-37. Una FK rimasta NOT VALID non garantirebbe
--   niente sulle righe gia' scritte.
SELECT is(
    (SELECT convalidated::text FROM pg_constraint
      WHERE conrelid = 'dbops.presidi_testi'::regclass
        AND conname = 'fk_presidi_testi_presidi_cause'
        AND confrelid = 'dbops.presidi_cause'::regclass),
    'true',
    'test 18 — fk_presidi_testi_presidi_cause esiste ed e'' convalidata');

-- ============================================================
-- 19) L'applicazione legge le cause
-- ============================================================
SELECT ok(
    has_table_privilege('zeroerp_app', 'dbops.presidi_cause', 'SELECT'),
    'test 19 — zeroerp_app ha SELECT su dbops.presidi_cause');

SELECT * FROM finish();
ROLLBACK;
