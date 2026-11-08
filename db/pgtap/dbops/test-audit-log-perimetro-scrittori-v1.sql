-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test — CANCELLO: dbops.audit_log resta un registro TECNICO
--   dbops.vw_audit_log_scrittori_fuori_perimetro
--
-- Brief: brief-db-rls-storico-scope-congelato.md §8.3 (decisione «No», 2026-09-11)
-- ChangeSet: 20_code/dbops/20260911-32 · 90_end/20260911-33 · catalogo dbops.presidi
--            20_code/dbops/20261104-21 (il corpo da dbops.fn_corpo_funzione)
--            20_code/dbops/20261104-45 (il prefiltro prima del building block)
--
-- ⭐ IL REGISTRO DELLE ESECUZIONI NON DEVE CONTENERE DATI DI DOMINIO. Non si
--   ripara con una policy di perimetro sul log: si impedisce alla FONTE che una
--   funzione di vendite, anagrafiche, pagamenti ci scriva. La vista elenca chi
--   scrive nel registro da fuori il perimetro dichiarato (dbops, maintenance),
--   e questo file la pretende vuota — in CI, a ogni build.
--
-- ⭐ E SI PROVA CHE LA LENTE VEDA: una vista vuota potrebbe essere vuota perché
--   non guarda. Il test 4 costruisce un caso — una funzione TEMPORANEA, quindi
--   in uno schema fuori perimetro, che chiama fn_audit_log_once — e pretende che
--   la vista la elenchi. Poi il ROLLBACK la porta via.
--
-- ⭐ rev 20261104-21: la vista legge il corpo dal building block. I test 7 e
--   8 provano le due cose che prima sfuggivano: uno scrittore SQL BEGIN ATOMIC
--   (prosrc vuoto) e una chiamata rimasta in un commento a blocco (che contava).
--
-- ⭐ rev 20261104-45: la vista chiede il corpo al building block solo per chi
--   nomina audit_log nel testo grezzo, piu' le BEGIN ATOMIC. I test 7 e 8
--   restano la prova che il prefiltro non perde i due casi difficili.
--
-- Elenco test (plan 8):
--   1  : ⛔ la vista è VUOTA: nessuna funzione di dominio scrive nel registro
--   2  : gemello «esiste»: dentro il perimetro ci sono scrittori (la regex prende)
--   3  : il perimetro dichiarato nella vista è {dbops, maintenance} — il contratto
--   4  : ⭐ una funzione costruita fuori perimetro che scrive → la vista la vede
--   5  : … e la classifica VIA_FN_AUDIT (chiama la porta, non il DML)
--   6  : la vista è a catalogo in dbops.presidi come CANCELLO, presidiata da questo file
--   7  : ⭐ uno scrittore SQL BEGIN ATOMIC fuori perimetro → la vista lo vede, DML_DIRETTO
--   8  : ⭐ una chiamata alla porta dentro un commento a blocco non è uno scrittore
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

SELECT is((SELECT count(*) FROM dbops.vw_audit_log_scrittori_fuori_perimetro),
          0::bigint,
          '1. nessuna funzione fuori da dbops/maintenance scrive in dbops.audit_log: il registro resta tecnico');

-- Gemello «esiste», calcolato SENZA passare dalla vista: la stessa regex sul
-- catalogo, dentro il perimetro. Se fosse zero, la vista vuota non direbbe niente.
SELECT cmp_ok((SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname IN ('dbops', 'maintenance')
                  AND p.proname <> 'fn_audit_log_once'
                  AND dbops.fn_corpo_funzione(p.oid) ~ '\mfn_audit_log_once\s*\('),
              '>', 0::bigint,
              '2. gemello «esiste»: dentro il perimetro ci sono scrittori del registro — la regex prende');

-- Il perimetro è il contratto e vive nella definizione della vista.
SELECT ok(pg_get_viewdef('dbops.vw_audit_log_scrittori_fuori_perimetro'::regclass) LIKE '%''dbops''%'
          AND pg_get_viewdef('dbops.vw_audit_log_scrittori_fuori_perimetro'::regclass) LIKE '%''maintenance''%'
          AND pg_get_viewdef('dbops.vw_audit_log_scrittori_fuori_perimetro'::regclass) NOT LIKE '%''vendite''%',
          '3. il perimetro dichiarato è {dbops, maintenance}: allargarlo è un changeSet firmato, non una svista');

-- Il caso costruito: una funzione nello schema temporaneo (fuori perimetro per
-- costruzione) che chiama la porta di scrittura. Non viene eseguita: basta che
-- esista, il cancello guarda il sorgente.
CREATE FUNCTION pg_temp.fn_pgtap_scrive_audit_da_fuori()
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    PERFORM dbops.fn_audit_log_once('pgtap.fuori_perimetro', 'OK');
END
$f$;

SELECT is((SELECT count(*) FROM dbops.vw_audit_log_scrittori_fuori_perimetro
            WHERE funzione LIKE '%.fn_pgtap_scrive_audit_da_fuori'),
          1::bigint,
          '4. una funzione costruita fuori perimetro che scrive nel registro: la vista la vede');

SELECT is((SELECT come_scrive FROM dbops.vw_audit_log_scrittori_fuori_perimetro
            WHERE funzione LIKE '%.fn_pgtap_scrive_audit_da_fuori'),
          'VIA_FN_AUDIT',
          '5. e la classifica come chiamata alla porta, non come DML diretto');

SELECT ok((SELECT natura = 'CANCELLO'
                  AND presidiato_da = 'db/pgtap/dbops/test-audit-log-perimetro-scrittori-v1.sql'
                  AND attivo AND obsoleto_dal IS NULL
             FROM dbops.presidi WHERE vista = 'dbops.vw_audit_log_scrittori_fuori_perimetro'),
          '6. la vista è a catalogo come CANCELLO, attiva, presidiata da questo file');

-- 7. Lo scrittore SQL BEGIN ATOMIC: prosrc è VUOTO, il corpo sta in
--    prosqlbody. Prima di 20261104-21 il cancello non lo vedeva.
CREATE FUNCTION pg_temp.fn_pgtap_scrive_audit_atomic()
RETURNS void LANGUAGE sql
BEGIN ATOMIC
    INSERT INTO dbops.audit_log (function_name, status) VALUES ('pgtap.fuori_perimetro', 'OK');
END;

SELECT is((SELECT come_scrive FROM dbops.vw_audit_log_scrittori_fuori_perimetro
            WHERE funzione LIKE '%.fn_pgtap_scrive_audit_atomic'),
          'DML_DIRETTO',
          '7. uno scrittore SQL BEGIN ATOMIC fuori perimetro: la vista lo vede, come DML diretto');

-- 8. La chiamata sta in un commento a BLOCCO: la copia di prima toglieva solo
--    i commenti di riga, e la contava.
CREATE FUNCTION pg_temp.fn_pgtap_nomina_audit_in_commento()
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    /* un giorno: PERFORM dbops.fn_audit_log_once('pgtap.fuori_perimetro', 'OK'); */
    NULL;
END
$f$;

SELECT is((SELECT count(*) FROM dbops.vw_audit_log_scrittori_fuori_perimetro
            WHERE funzione LIKE '%.fn_pgtap_nomina_audit_in_commento'),
          0::bigint,
          '8. una chiamata alla porta dentro un commento a blocco non è uno scrittore');

SELECT * FROM finish();
ROLLBACK;
