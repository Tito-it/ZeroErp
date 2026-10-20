-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la proprieta' sotto esame e' la SEPARAZIONE fra due
--   emittenti, e nessun operatore ne vede due: config.user_emittenti_fiscali ha
--   UNIQUE su auth_user_id — «un operatore, un emittente». La fixture deve
--   COSTRUIRE due emittenti e i loro registri, e da dentro un perimetro non
--   potrebbe nemmeno crearli. E' lo stesso marcatore, con la stessa ragione, di
--   db/pgtap/vendite/test-fatture-guard-registro-emittente.sql.
-- pgtap-contesto: escluso — discende dal marcatore qui sopra.
-- pgTAP test per Zero ERP
-- Test: P-1 / P-3 / P-7 — il MOTORE dopo il trasloco
--       vendite.fn_get_next_progressivo        (20260831-06)
--       vendite.fn_lookup_registro_documento   (20260831-01)
--       vendite.fn_get_registro_documento      (20260831-02)
--       Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, §3.6 e §2.3
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2c/2d): la famiglia della bolla e' DDT_VENDITA.
-- ------------------------------------------------------------
-- Elenco test (plan 9):
-- 1) Fixture: due emittenti, un registro DDT per ciascuno
-- 2) ⭐⭐ DUE EMITTENTI, STESSO ANNO: entrambi ripartono da 1
-- 3) ⭐ ...e non e' un caso: il secondo numero di ciascuno e' 2, indipendente
-- 4) ⭐ IL RESET DI CAPODANNO: seminato il contatore dell'anno prima a 99,
--       l'anno dopo riparte da 1
-- 5) ⚠️ ...e l'anno prima NON e' stato toccato: resta a 99
-- 6) Il lettore su un emittente SENZA registro risponde vuoto (non solleva)
-- 7) ⛔ L'involucro invece SOLLEVA: il fail-closed dev'essere rumoroso
-- 8) ⛔ L'involucro RIFIUTA la famiglia FATTURA
-- 9) ⭐ Il lettore preferisce il registro della UTILITY a quello generale
--
-- Scopo:
--   ⭐⭐ IL TEST 2 E' LA RAGIONE PER CUI IL CANTIERE ESISTE. Prima del trasloco
--   DDT, ordini, resi e commesse pescavano da UNA sequenza globale: due
--   partite IVA condividevano la progressione, e nessuna delle due aveva una
--   numerazione propria. ⛔ Il difetto era MUTO — il contatore e' uno solo,
--   quindi nessun numero duplicato e nessun errore: saltava l'ATTRIBUZIONE,
--   non l'unicita'. Un difetto muto non lo trova la baseline verde: lo trova
--   solo un test che va a guardare il numero.
--
--   ⭐ IL TEST 4 PROVA UNA COSA CHE NON ERA MAI ESISTITA. Il vecchio contatore
--   era una sequenza di database, e una sequenza non sa cosa sia un anno: il
--   reset di Capodanno era dichiarato dalla chiave (`anno` nella UNIQUE) e non
--   implementato da nessuna parte. ⚠️ Il tempo non si simula — si SEMINA il
--   contatore dell'anno prima e si guarda cosa fa quello dopo.
--
--   ⭐ I TEST 6 e 7 SONO UNA COPPIA e vanno letti insieme: il lettore che tace
--   e l'involucro che grida sono le due meta' della stessa decisione. Provare
--   solo il secondo non distinguerebbe «l'involucro solleva» da «solleva
--   qualunque cosa in questo percorso».
--
-- ⚠️ COSA QUESTO FILE NON PUO' PROVARE, scritto qui invece di essere scoperto
--   da chi verra' dopo: che il contatore stia SOTTO il lock, cioe' che due
--   sessioni concorrenti non prendano lo stesso numero. pgTAP e' mono-sessione.
--   Si presidia in review sul changeSet, come gia' dichiarato al §3.6 del piano.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ anagrafiche.soggetti_ruoli porta trigger DEFERRABLE INITIALLY DEFERRED, e
--   qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- 1) Fixture: due emittenti, un registro DDT per ciascuno
-- ============================================================
CREATE TEMP TABLE tmp_mot_costanti AS
SELECT 'pgtap_motore_trasloco'::text AS test_scope,
       -- ⚠️ Anni FISSI e lontani da quelli veri: il test semina un contatore, e
       --   seminarlo sull'anno corrente lo mescolerebbe ai documenti veri.
       2101::smallint AS anno_a,
       2102::smallint AS anno_b;

-- ⭐ Gli emittenti si FABBRICANO (rev 2026-10-18): soggetto, ruolo EF e
--   emittente dal builder dbops.fn_pgtap_crea_emittente, che scrive l'emittente
--   col verbo anagrafiche.fn_crea_emittente_fiscale — il percorso reale, quello
--   che fa nascere anche i registri. Prima si pescavano tre soggetti esistenti
--   «che potevano diventare EF»: su un database ricostruito da zero non ce n'e'
--   nessuno, e la fixture moriva su fn_get_next_progressivo(NULL).
-- ⚠️ TRE emittenti e non due: il terzo serve al 6)/7), che hanno bisogno di un
--   emittente SENZA registro — e un emittente a cui il provisioning ha gia'
--   dato i registri non serve a niente li'.
-- ⚠️ Le sigle rispettano chk_emittenti_fiscali_codice_forma (maiuscole e cifre,
--   2..10): dal 2026-08-31 una sigla col trattino non si scrive piu'.
CREATE TEMP TABLE tmp_mot_emittenti AS
SELECT e.soggetto_ruolo_id, e.emittente_codice AS codice, g.n
  FROM generate_series(1, 3) AS g(n)
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_emittente(('PGTMOT' || g.n)::varchar) AS e;

SET CONSTRAINTS ALL IMMEDIATE;

-- ⭐ I REGISTRI NON SI CREANO A MANO: si usano quelli che
--   vendite.fn_provision_registri_emittente ha appena fatto nascere insieme
--   all'emittente. E' il percorso reale, e in piu' evita un difetto che il
--   primo tentativo aveva preso in pieno:
--   ⛔ `uq_registri_fatturazione_famiglia_emittente_utility` NON filtra su
--   `attivo`, quindi un registro SPENTO continua a occupare lo slot
--   (famiglia, emittente, utility): «spegni e rifai» non e' una strada, e un
--   INSERT accanto a quello provisionato sbatte sulla UNIQUE.
--   ⭐ Il vincolo ha ragione: se lo slot si liberasse spegnendo, resterebbero
--   due registri storici della stessa famiglia e nessuno saprebbe piu' quale
--   ha numerato cosa.
CREATE TEMP TABLE tmp_mot_registri AS
SELECT r.id AS registro_id, r.emittente_soggetto_ruolo_id, e.n
  FROM tmp_mot_emittenti e
  JOIN vendite.registri_fatturazione r
    ON r.emittente_soggetto_ruolo_id = e.soggetto_ruolo_id
   AND r.famiglia_documento          = 'DDT_VENDITA'
   AND r.utility_id IS NULL
   AND r.attivo
 WHERE e.n IN (1, 2);

-- ⚠️ Il TERZO emittente deve restare senza registro DDT VISIBILE: qui si spegne
--   e non si cancella, e va bene — il lettore filtra gia' su `attivo`, e lo
--   slot occupato non da' fastidio perche' qui non si inserisce niente.
-- ⚠️ Rev 2026-10-18 (R-BE-14, 20261019-08): SOLO il registro DDT, quello che il
--   6)/7) chiedono. Dal provisioning del registro delle fatture standard
--   l'emittente nasce anche col registro FAT-, collegato alle coppie (tipo
--   documento, natura), e un registro con collegamenti non si spegne
--   (dbops.trgfn_prevent_deactivate_if_children): spegnere «tutto» fermava la
--   fixture su un registro che il test non guarda.
UPDATE vendite.registri_fatturazione r
   SET attivo = false
  FROM tmp_mot_emittenti e
 WHERE e.n = 3
   AND r.emittente_soggetto_ruolo_id = e.soggetto_ruolo_id
   AND r.famiglia_documento = 'DDT_VENDITA';

SELECT is(
    (SELECT count(*)::int FROM tmp_mot_registri),
    2,
    '1) Fixture: due emittenti distinti con un registro DDT ciascuno');

-- ============================================================
-- 2) ⭐⭐ DUE EMITTENTI, STESSO ANNO: entrambi ripartono da 1
-- ============================================================
-- E' la proprieta' che il cantiere esiste per ottenere. Prima del trasloco i
-- due avrebbero pescato dalla stessa sequenza globale: 1 e 2, non 1 e 1.
CREATE TEMP TABLE tmp_mot_primo AS
SELECT r.n,
       vendite.fn_get_next_progressivo(
           r.registro_id,
           make_date((SELECT anno_a FROM tmp_mot_costanti)::int, 3, 15),
           NULL, '', NULL, 'DDT_VENDITA') AS numero
  FROM tmp_mot_registri r
 ORDER BY r.n;

SELECT is(
    (SELECT string_agg(p.numero::text, '|' ORDER BY p.n) FROM tmp_mot_primo p),
    '1|1',
    '2) Due emittenti nello stesso anno ripartono ENTRAMBI da 1');

-- ============================================================
-- 3) ⭐ E i due contatori proseguono indipendenti
-- ============================================================
-- ⚠️ Senza questo, il 2) sarebbe compatibile con un contatore che torna sempre
--   1 — cioe' con un motore rotto in modo diverso.
CREATE TEMP TABLE tmp_mot_secondo AS
SELECT r.n,
       vendite.fn_get_next_progressivo(
           r.registro_id,
           make_date((SELECT anno_a FROM tmp_mot_costanti)::int, 4, 20),
           NULL, '', NULL, 'DDT_VENDITA') AS numero
  FROM tmp_mot_registri r
 ORDER BY r.n;

SELECT is(
    (SELECT string_agg(p.numero::text, '|' ORDER BY p.n) FROM tmp_mot_secondo p),
    '2|2',
    '3) I due contatori proseguono indipendenti: 2 e 2, non 3 e 4');

-- ============================================================
-- 4/5) ⭐ IL RESET DI CAPODANNO
-- ============================================================
-- ⚠️ Il tempo non si simula: si SEMINA il contatore dell'anno prima a 99 e si
--   guarda cosa fa l'anno dopo. E' il caso che una sequenza di database non
--   sapeva fare — il vecchio motore non aveva nessuna nozione di anno.
UPDATE vendite.registri_fatturazione_progressivi p
   SET last_numero = 99
 WHERE p.registro_id = (SELECT registro_id FROM tmp_mot_registri WHERE n = 1)
   AND p.anno = (SELECT anno_a FROM tmp_mot_costanti);

-- ⚠️ Il verbo in un'istruzione SEPARATA dall'asserzione: fn_get_next_progressivo
--   SCRIVE (incrementa il contatore), e chiamarla dentro la is() la
--   mescolerebbe alla snapshot dell'asserzione.
CREATE TEMP TABLE tmp_mot_capodanno AS
SELECT vendite.fn_get_next_progressivo(
           (SELECT registro_id FROM tmp_mot_registri WHERE n = 1),
           make_date((SELECT anno_b FROM tmp_mot_costanti)::int, 1, 2),
           NULL, '', NULL, 'DDT_VENDITA') AS numero;

SELECT is(
    (SELECT numero FROM tmp_mot_capodanno),
    1::bigint,
    '4) L''anno nuovo riparte da 1, anche se il precedente era arrivato a 99');

-- ⚠️ Il gemello che si dimentica: un reset che azzerasse ANCHE l'anno prima
--   passerebbe il 4) e distruggerebbe la storia.
SELECT is(
    (SELECT p.last_numero
       FROM vendite.registri_fatturazione_progressivi p
      WHERE p.registro_id = (SELECT registro_id FROM tmp_mot_registri WHERE n = 1)
        AND p.anno = (SELECT anno_a FROM tmp_mot_costanti)),
    99::bigint,
    '5) ...e il contatore dell''anno precedente resta intatto a 99');

-- ============================================================
-- 6/7) ⭐ IL LETTORE TACE, L'INVOLUCRO GRIDA
-- ============================================================
-- Sono le due meta' della stessa decisione, e vanno lette insieme: chi deve
-- solo SAPERE accetta un «non c'e'», chi sta per SCRIVERE no.
SELECT is(
    (SELECT k.registro_id
       FROM vendite.fn_lookup_registro_documento(
                'DDT_VENDITA',
                (SELECT soggetto_ruolo_id FROM tmp_mot_emittenti WHERE n = 3),
                NULL) k),
    NULL::bigint,
    '6) Il lettore su un emittente senza registro risponde vuoto, e non solleva');

PREPARE mot_involucro_muto AS
SELECT k.registro_id
  FROM vendite.fn_get_registro_documento(
           'DDT_VENDITA',
           (SELECT soggetto_ruolo_id FROM tmp_mot_emittenti WHERE n = 3),
           NULL) k;

SELECT throws_ok(
    'EXECUTE mot_involucro_muto',
    'P0001',
    NULL,
    '7) L''involucro invece SOLLEVA: il fail-closed e'' rumoroso');

-- ============================================================
-- 8) ⛔ L'involucro rifiuta la famiglia FATTURA
-- ============================================================
-- Rispondere darebbe il PRIMO registro di fatturazione dell'emittente:
-- plausibile, e per una nota di credito il sezionale sbagliato, in silenzio.
PREPARE mot_involucro_fattura AS
SELECT k.registro_id
  FROM vendite.fn_get_registro_documento(
           'FATTURA',
           (SELECT emittente_soggetto_ruolo_id FROM tmp_mot_registri WHERE n = 1),
           NULL) k;

SELECT throws_ok(
    'EXECUTE mot_involucro_fattura',
    'P0001',
    NULL,
    '8) L''involucro rifiuta la famiglia FATTURA, che ha una strada sua');

-- ============================================================
-- 9) ⭐ Il piu' specifico vince: utility prima del generale
-- ============================================================
-- ⚠️ Provato sul PERCORSO: si aggiunge un secondo registro DDT legato a una
--   utility e si chiede il registro passando quella utility. Senza questo test
--   la regola di priorita' resterebbe dichiarata e non verificata.
INSERT INTO vendite.registri_fatturazione (
    codice, descrizione, emittente_soggetto_ruolo_id,
    famiglia_documento, reset_policy, attivo, utility_id)
SELECT 'MOTU1', 'Registro DDT utility', r.emittente_soggetto_ruolo_id,
       'DDT_VENDITA', 'ANNUALE', true,
       (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1)
  FROM tmp_mot_registri r
 WHERE r.n = 1;

SELECT is(
    (SELECT reg.codice::text
       FROM vendite.fn_lookup_registro_documento(
                'DDT_VENDITA',
                (SELECT emittente_soggetto_ruolo_id FROM tmp_mot_registri WHERE n = 1),
                (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1)) k
       JOIN vendite.registri_fatturazione reg ON reg.id = k.registro_id),
    'MOTU1',
    '9) Con una utility vince il registro dedicato, non quello generale');

SELECT * FROM finish();
ROLLBACK;
