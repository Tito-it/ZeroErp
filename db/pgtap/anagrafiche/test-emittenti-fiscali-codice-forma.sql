-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture CREA emittenti fiscali, e nessun operatore ne
--   vede piu' di uno (config.user_emittenti_fiscali ha UNIQUE su auth_user_id).
--   Da dentro un perimetro la fixture non potrebbe nemmeno costruire il caso.
--   E' lo stesso marcatore, con la stessa ragione, di
--   db/pgtap/anagrafiche/test-soggetti-titoli-iva-due-emittenti.sql.
-- pgtap-contesto: escluso — discende dal marcatore qui sopra.
-- pgTAP test per Zero ERP
-- Test: C2-19 — la sigla dell'emittente ha una FORMA
--       anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma  (20260831-23)
--       chk_emittenti_fiscali_codice_forma                      (20260831-22)
--       Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, §5.4
-- ------------------------------------------------------------
-- Elenco test (plan 8):
-- 1) Il vincolo strutturale esiste
-- 2) Il guard e' montato BEFORE, su INSERT e su UPDATE
-- 3) ⛔ Sigla col TRATTINO: respinta (P0001)
-- 4) ⛔ Sigla di UN carattere: respinta
-- 5) ⛔ Sigla di UNDICI caratteri: respinta
-- 6) ⭐ Sigla conforme: passa
-- 7) ⭐ Sigla in MINUSCOLO: non respinta — alzata a maiuscolo
-- 8) ⭐ Il catalogo vivo e' conforme, e non e' vuoto
--
-- Scopo:
--   Dal 2026-08-31 la sigla dell'emittente sta DENTRO il codice commessa —
--   `CMM-<sigla>-<anno>-<9 cifre>` — che si legge separando sul trattino. Una
--   sigla che contiene un trattino produce cinque pezzi invece di quattro.
--
--   ⛔ E il difetto e' MUTO: `uq_commesse_codice` regge lo stesso, non nascono
--   duplicati e non si solleva niente. Cambia solo che quell'emittente ha
--   codici illeggibili PER SEMPRE, perche' il codice e' immutabile. Un difetto
--   muto non si scopre girando: si scopre solo se qualcuno scrive il test.
--
--   ⭐ IL 6) E IL 7) SERVONO QUANTO I TRE RIFIUTI, e non sono una formalita':
--   senza il gemello positivo, un guard che respingesse OGNI sigla passerebbe
--   il 3), il 4) e il 5) esattamente come quello giusto. E il 7) presidia la
--   meta' che si dimentica — il minuscolo si ALZA, non si rifiuta, perche' e'
--   una forma canonica e non una scelta di chi scrive.
--
--   ⚠️ I tre rifiuti girano PRIMA del 6), e l'ordine e' portante: usano lo
--   stesso ruolo, che `uq_emittenti_fiscali_ruolo` consente di occupare una
--   volta sola. Girando dopo, fallirebbero sulla UNIQUE invece che sulla forma
--   — passerebbero lo stesso, misurando un'altra cosa.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ anagrafiche.soggetti_ruoli porta trigger DEFERRABLE INITIALLY DEFERRED, e
--   qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- 0) Fixture: due soggetti liberi, e i loro ruoli di emittente
-- ============================================================
-- ⭐ Soggetti e ruoli si FABBRICANO (rev 2026-10-18): due persone giuridiche
--   complete e il loro ruolo EF, dai builder dbops.fn_pgtap_crea_soggetto_pg e
--   fn_pgtap_crea_soggetto_ruolo (gli stessi di dbops.fn_pgtap_crea_emittente,
--   che pero' scrive anche l'emittente: qui l'emittente lo scrivono i test).
--   Prima si pescavano due soggetti esistenti «che potevano diventare EF»: su un
--   database ricostruito da zero non ce n'e' nessuno, i test 3-7 scrivevano
--   zero righe e l'8 trovava il catalogo vuoto.
CREATE TEMP TABLE tmp_ecf_ruoli AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(
           dbops.fn_pgtap_crea_soggetto_pg('pgTAP sigla emittente ' || g.n), 'EF') AS soggetto_ruolo_id,
       g.n
  FROM generate_series(1, 2) AS g(n);

SET CONSTRAINTS ALL IMMEDIATE;

-- ============================================================
-- 1) Il vincolo strutturale esiste
-- ============================================================
-- ⭐ Si asserisce il CHECK e non solo il guard: il guard e' la frase, il
--   vincolo e' la rete che nessuno aggira — nemmeno uno script di manutenzione
--   che accende il bypass del lock sulle colonne.
SELECT is(
    (SELECT count(*)::int
       FROM pg_constraint c
       JOIN pg_class     t ON t.oid = c.conrelid
       JOIN pg_namespace n ON n.oid = t.relnamespace
      WHERE n.nspname = 'anagrafiche'
        AND t.relname = 'emittenti_fiscali'
        AND c.conname = 'chk_emittenti_fiscali_codice_forma'
        AND c.convalidated),
    1,
    '1) chk_emittenti_fiscali_codice_forma esiste ed e'' VALIDATO');

-- ============================================================
-- 2) Il guard e' montato BEFORE, su INSERT e su UPDATE
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger t
       JOIN pg_class     c ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE NOT t.tgisinternal
        AND n.nspname = 'anagrafiche'
        AND c.relname = 'emittenti_fiscali'
        AND t.tgname  = 'trg_emittenti_fiscali_a05_guard_codice_forma_ins_upd'
        -- 2 = BEFORE, 4 = INSERT, 16 = UPDATE  (pg_trigger.tgtype)
        AND (t.tgtype & 2)  = 2
        AND (t.tgtype & 4)  = 4
        AND (t.tgtype & 16) = 16),
    1,
    '2) Il guard e'' montato BEFORE su INSERT e UPDATE');

-- ============================================================
-- 3/4/5) ⛔ I TRE RIFIUTI — tutti sul ruolo 1, che e' ancora libero
-- ============================================================
PREPARE ecf_trattino AS
INSERT INTO anagrafiche.emittenti_fiscali (soggetto_ruolo_id, codice)
SELECT r.soggetto_ruolo_id, 'AC-ME' FROM tmp_ecf_ruoli r WHERE r.n = 1;

SELECT throws_ok(
    'EXECUTE ecf_trattino',
    'P0001',
    NULL,
    '3) Una sigla col TRATTINO e'' respinta: e'' il separatore del codice commessa');

PREPARE ecf_troppo_corta AS
INSERT INTO anagrafiche.emittenti_fiscali (soggetto_ruolo_id, codice)
SELECT r.soggetto_ruolo_id, 'A' FROM tmp_ecf_ruoli r WHERE r.n = 1;

SELECT throws_ok(
    'EXECUTE ecf_troppo_corta',
    'P0001',
    NULL,
    '4) Una sigla di un solo carattere e'' respinta');

PREPARE ecf_troppo_lunga AS
INSERT INTO anagrafiche.emittenti_fiscali (soggetto_ruolo_id, codice)
SELECT r.soggetto_ruolo_id, 'ABCDEFGHIJK' FROM tmp_ecf_ruoli r WHERE r.n = 1;

SELECT throws_ok(
    'EXECUTE ecf_troppo_lunga',
    'P0001',
    NULL,
    '5) Una sigla di undici caratteri e'' respinta: il tetto e'' dieci');

-- ============================================================
-- 6) ⭐ IL GEMELLO POSITIVO — senza, un guard che respinge tutto passerebbe
-- ============================================================
SELECT lives_ok(
    $q$INSERT INTO anagrafiche.emittenti_fiscali (soggetto_ruolo_id, codice)
       SELECT r.soggetto_ruolo_id, 'ACME01' FROM tmp_ecf_ruoli r WHERE r.n = 1$q$,
    '6) Una sigla conforme passa');

-- ============================================================
-- 7) ⭐ IL MINUSCOLO SI ALZA, NON SI RIFIUTA
-- ============================================================
-- E' la meta' che si dimentica: il maiuscolo e' una forma CANONICA, non un
-- requisito che l'utente debba conoscere. ⚠️ Si scrive su un ruolo diverso,
-- perche' il primo e' stato occupato dal 6).
INSERT INTO anagrafiche.emittenti_fiscali (soggetto_ruolo_id, codice)
SELECT r.soggetto_ruolo_id, '  acme02  ' FROM tmp_ecf_ruoli r WHERE r.n = 2;

SELECT is(
    (SELECT e.codice::text
       FROM anagrafiche.emittenti_fiscali e
       JOIN tmp_ecf_ruoli r ON r.soggetto_ruolo_id = e.soggetto_ruolo_id
      WHERE r.n = 2),
    'ACME02',
    '7) Il minuscolo (e gli spazi) vengono normalizzati, non respinti');

-- ============================================================
-- 8) ⭐ Il catalogo vivo attraversa il vincolo scritto dopo di lui
-- ============================================================
-- ⛔ Due condizioni in una: «nessuna sigla e' fuori forma» E «di sigle ce ne
--   sono». Un test che conta i soli cattivi diventa MUTO il giorno in cui la
--   tabella si svuota.
-- ⚠️ E' la prova che la bonifica del 20260831-22 ha fatto il suo lavoro: prima
--   di quel changeSet qui c'erano EMI-TEST e PGTAP-EF-20260126172242554.
SELECT ok(
    (SELECT count(*) FROM anagrafiche.emittenti_fiscali) > 0
    AND NOT EXISTS (SELECT 1 FROM anagrafiche.emittenti_fiscali e
                     WHERE e.codice !~ '^[A-Z0-9]{2,10}$'),
    '8) Nessuna sigla in circolazione e'' fuori forma, e di sigle ce ne sono');

SELECT * FROM finish();
ROLLBACK;
