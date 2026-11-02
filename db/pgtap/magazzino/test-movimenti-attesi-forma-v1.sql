-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto sono i VINCOLI e i guard di magazzino.movimenti_attesi,
--   che dal 2026-09-28 l'app non scrive piu': la tabella e' in sola lettura e i blocchi
--   li aprono e li liberano i verbi fn_apri_blocco / fn_libera_blocco
--   (brief-db-magazzino-lotto-3-scarico-da-ddt, D-L3-j). Scrivere righe che i verbi non
--   producono (attesi con sorgente, in entrata, stati fuori vocabolario) per provare i
--   CHECK e' cosa che solo uno scrittore privilegiato puo' fare: forma 3 del criterio
--   del runner, come i test del ledger. Il contesto operatore resta impostato: i guard
--   lo leggono.
--
-- Test: magazzino.movimenti_attesi nella forma decisa dal Lotto 1 — la
--   rinomina di reservations e' completa e le regole della tabella reggono
--   (brief-db-magazzino-lotto-1-terreno-vuoto, sezioni 4.5 e 7;
--   analisi carico e scarico, sezione 7-bis; D-L1-b).
--
-- ⚠️ I test 1 e 2 valgono A ci_apply AVVENUTO (stampo: test 3 di
--   pagamenti/test-sistemazioni-registro): audit e tx_id sono stati rinominati
--   dal 20260915-06, i require_attivo e lo storico li rigenera il framework col
--   nome nuovo. Su dbdev fra il migrate e il pgagent delle 21:00 il test 2
--   vede meno trigger di quelli attesi: non e' un rosso del lotto, e' il
--   momento sbagliato — la CI esegue i pgTAP dopo ci_apply.
-- ⚠️ Fixture COSTRUITA (regola zero): azienda + operatore e INDIRIZZO dagli helper
--   (indirizzi_dettaglio e' dato di macchina: su un DB da zero non ce n'e'), un
--   magazzino con quell'emittente, un inventario con una riga come sorgente.
--
-- Elenco test (plan 15):
--   La rinomina e' di tutto:
--    1) nessun vincolo, indice, sequenza o trigger della tabella — ne' trigger
--       sui padri — nomina piu' `reservations`
--    2) i generati col nome nuovo ci sono: audit, tx_id, storico, i sette require_attivo
--       verso articoli/magazzini/ubicazioni/causali/sorgenti/lotti/assets
--       (⚠️ non verso soggetti_ruoli: quella tabella non ha `attivo`, il framework non genera)
--   Il verso (M-1):
--    3) qta = 0 -> P0001 dal guard del verso
--    4) verso incoerente (SCARICO_VEN con qta positiva) -> la frase del catalogo
--   Per chi e' (7-bis):
--    5) senza sorgente, senza soggetto e con nota di soli spazi -> 23514 per_chi (la riga muta)
--    6) col soggetto -> passa, nasce APERTA
--   La sorgente (D-6, nullable):
--    7) sorgente_riga senza tipo -> 23514 sorgente_chiave
--    8) con documento e data_prevista -> 23514 data_solo_senza_documento
--    9) con documento, senza data -> passa (e il guard tipizzato ha verificato il record)
--   Il ciclo (D-L1-b):
--   10) CHIUSA senza data_chiusura -> 23514 chiusura
--   11) APERTA con data_chiusura -> 23514 chiusura
--   12) liberare = CHIUSA con data -> passa
--   13) stato fuori vocabolario -> 23514 stato
--   L'ancora (M-6):
--   14) magazzino_id NOT NULL, dal catalogo (⚠️ non per INSERT: sotto RLS la
--       policy scatta prima del vincolo e uscirebbe 42501, non 23502)
--   Il lettore (rev 2026-09-28, dal test 3 di test-vw-disponibilita-v1):
--   15) un atteso in ENTRATA aperto non e' un blocco: vw_disponibilita non lo conta
--       (il caso lo ammette la tabella e non lo produce nessun verbo: si costruisce qui)
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- 1..2 La rinomina
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM (
        SELECT conname AS n FROM pg_constraint WHERE conrelid = 'magazzino.movimenti_attesi'::regclass
        UNION ALL SELECT indexname FROM pg_indexes WHERE schemaname = 'magazzino' AND tablename = 'movimenti_attesi'
        UNION ALL SELECT tgname FROM pg_trigger WHERE tgrelid = 'magazzino.movimenti_attesi'::regclass AND NOT tgisinternal
        UNION ALL SELECT relname FROM pg_class WHERE relkind = 'S' AND relnamespace = 'magazzino'::regnamespace
        UNION ALL SELECT tgname FROM pg_trigger WHERE NOT tgisinternal AND pg_get_triggerdef(oid) ~ '''reservations'''
        UNION ALL SELECT relname FROM pg_class WHERE relname = 'reservations' AND relnamespace IN ('magazzino'::regnamespace, 'storico'::regnamespace)
    -- ⚠️ anche `mag_res_`: e' l'abbreviazione del 2025 (ix_mag_res_articolo, chk_mag_res_stato…).
    --   Su un DB da zero i tre indici FK del 2025 sopravvivevano alla rinomina, perche' la
    --   policy FK copre solo una FK scoperta — trovato il 15-09 su zeroerp_ci, non su dev
    --   (dove non esistevano piu'); li toglie 20260915-20.
    ) x WHERE x.n ~ 'reservations|mag_res_'),
    0,
    '1) nessun oggetto della tabella, ne'' trigger sui padri, nomina piu'' reservations (ne'' mag_res_)');

SELECT is(
    (SELECT count(*)::int FROM pg_trigger
      WHERE tgrelid = 'magazzino.movimenti_attesi'::regclass AND NOT tgisinternal
        AND tgname IN ('trg_movimenti_attesi_audit_data_user_upd',
                       'trg_movimenti_attesi_gen_tx_id_ins_upd',
                       'trg_movimenti_attesi_z90_storico_upd_dlt',
                       'trg_movimenti_attesi_a10_articoli_require_attivo_ins_upd',
                       'trg_movimenti_attesi_a10_magazzini_require_attivo_ins_upd',
                       'trg_movimenti_attesi_a10_ubicazioni_require_attivo_ins_upd',
                       'trg_movimenti_attesi_a10_causali_require_attivo_ins_upd',
                       'trg_movimenti_attesi_a10_sorgenti_require_attivo_ins_upd',
                       'trg_movimenti_attesi_a10_lotti_require_attivo_ins_upd',
                       'trg_movimenti_attesi_a10_assets_require_attivo_ins_upd')),
    10,
    '2) i generati col nome nuovo ci sono tutti (a ci_apply avvenuto): audit, tx_id, storico, sette require_attivo');

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo));
END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

CREATE TEMP TABLE _fix (mag bigint, art uuid, sr bigint, inv_riga bigint, cau_out bigint, cau_inv bigint, src_inv bigint);

DO $fix$
DECLARE
    v_ef  magazzino.magazzini.emittente_fiscale_id%TYPE;
    v_ind anagrafiche.indirizzi_dettaglio.id%TYPE;
    v_art catalogo.articoli.id%TYPE;
    v_mag magazzino.magazzini.id%TYPE;
    v_inv magazzino.inventari.id%TYPE;
    v_ir  magazzino.inventari_righe.id%TYPE;
BEGIN
    SELECT emittente_fiscale_id INTO v_ef FROM _mondo;
    -- L'indirizzo si FABBRICA (dato di macchina: zero righe su un DB da zero);
    -- l'articolo e' uno dei seed ONERE_* di catalogo, presente per contratto.
    v_ind := dbops.fn_pgtap_crea_indirizzo_dettaglio('attesi');
    SELECT a.id INTO v_art FROM catalogo.articoli a WHERE a.attivo ORDER BY a.id LIMIT 1;
    IF v_art IS NULL THEN
        RAISE EXCEPTION 'fixture: serve almeno un articolo attivo (seed di catalogo)';
    END IF;
    v_mag := magazzino.fn_crea_magazzino('PGT-MA1', 'pgTAP attesi', v_ind, '{}'::jsonb, v_ef);
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata)
    VALUES (v_inv, v_art, 5) RETURNING id INTO v_ir;

    INSERT INTO _fix
    SELECT v_mag, v_art,
           -- il soggetto-ruolo dell'emittente stesso: un soggetto che l'operatore vede
           (SELECT soggetto_ruolo_id FROM _mondo),
           v_ir,
           (SELECT id FROM magazzino.causali WHERE codice_interno = 'SCARICO_VEN'),
           (SELECT id FROM magazzino.causali WHERE codice_interno = 'INV_INIZIALE'),
           (SELECT id FROM config.sorgenti WHERE codice_interno = 'INVENTARIO_RIGA');
END $fix$;

-- ============================================================
-- 3..4 Il verso
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, causale_id, qta, nota)
       SELECT art, mag, cau_out, 0, 'zero' FROM _fix $$,
    'P0001', NULL,
    '3) qta = 0: parla il guard del verso');

SELECT throws_like(
    $$ INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, causale_id, qta, nota)
       SELECT art, mag, cau_out, 3, 'x' FROM _fix $$,
    '%Verso incoerente%SCARICO_VEN%',
    '4) uscita con quantita'' positiva: la frase di E_MAG_MOVIMENTO_VERSO_INCOERENTE');

-- ============================================================
-- 5..6 Per chi e'
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, causale_id, qta, nota)
       SELECT art, mag, cau_out, -1, '   ' FROM _fix $$,
    '23514', NULL,
    '5) la riga muta (ne'' sorgente ne'' soggetto, nota di soli spazi): chk_mag_movimenti_attesi_per_chi');

-- ⚠️ Una CTE che scrive non puo' stare in una sotto-select: l'INSERT e'
--   un'istruzione sua, l'asserzione rilegge la riga.
INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, causale_id, qta, soggetto_ruolo_id, data_prevista)
SELECT art, mag, cau_out, -10, sr, now() + interval '3 day' FROM _fix;
SELECT is(
    (SELECT a.stato || '/' || coalesce(a.data_chiusura::text, 'NULL')
       FROM magazzino.movimenti_attesi a
      WHERE a.soggetto_ruolo_id = (SELECT sr FROM _fix)),
    'APERTA/NULL',
    '6) il blocco manuale per un soggetto passa, e nasce APERTA senza data di chiusura');

-- ============================================================
-- 7..9 La sorgente
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, causale_id, qta, sorgente_riga, nota)
       SELECT art, mag, cau_inv, 5, inv_riga, 'x' FROM _fix $$,
    '23514', NULL,
    '7) una chiave senza tipo: chk_mag_movimenti_attesi_sorgente_chiave');

SELECT throws_ok(
    $$ INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id, sorgente_riga, data_prevista)
       SELECT art, mag, cau_inv, 5, src_inv, inv_riga, now() FROM _fix $$,
    '23514', NULL,
    '8) con un documento la data e'' la sua: chk_mag_movimenti_attesi_data_solo_senza_documento');

SELECT lives_ok(
    $$ INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id, sorgente_riga)
       SELECT art, mag, cau_inv, 5, src_inv, inv_riga FROM _fix $$,
    '9) con documento e senza data passa (il guard tipizzato ha trovato la riga di inventario)');

-- ============================================================
-- 10..13 Il ciclo
-- ============================================================
SELECT throws_ok(
    $$ UPDATE magazzino.movimenti_attesi SET stato = 'CHIUSA' WHERE soggetto_ruolo_id = (SELECT sr FROM _fix) $$,
    '23514', NULL,
    '10) CHIUSA senza data_chiusura: chk_mag_movimenti_attesi_chiusura');

SELECT throws_ok(
    $$ UPDATE magazzino.movimenti_attesi SET data_chiusura = now() WHERE soggetto_ruolo_id = (SELECT sr FROM _fix) $$,
    '23514', NULL,
    '11) APERTA con data_chiusura: chk_mag_movimenti_attesi_chiusura');

UPDATE magazzino.movimenti_attesi SET stato = 'CHIUSA', data_chiusura = now()
 WHERE soggetto_ruolo_id = (SELECT sr FROM _fix);
SELECT is(
    (SELECT a.stato FROM magazzino.movimenti_attesi a WHERE a.soggetto_ruolo_id = (SELECT sr FROM _fix)),
    'CHIUSA',
    '12) liberare il blocco = CHIUSA con la data: passa');

SELECT throws_ok(
    $$ INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, causale_id, qta, nota, stato)
       SELECT art, mag, cau_out, -1, 'x', 'picked' FROM _fix $$,
    '23514', NULL,
    '13) picked non e'' uno stato: chk_mag_movimenti_attesi_stato (APERTA | CHIUSA)');

-- ============================================================
-- 14 L'ancora
-- ============================================================
-- ⚠️ Dal catalogo, non per INSERT. Sotto il runner la RLS e' attiva e
--   PostgreSQL valuta il WITH CHECK della policy PRIMA dei vincoli di riga
--   (ExecWithCheckOptions precede ExecConstraints): con magazzino_id NULL la
--   policy non e' vera ed esce 42501, il NOT NULL non viene mai raggiunto.
--   Provato il 15-09: come owner (RLS bypassata) usciva 23502, come
--   zeroerp_app 42501. Pinnare il 42501 sarebbe pinnare il sintomo; il NOT
--   NULL e' struttura e si legge dove sta.
SELECT col_not_null('magazzino', 'movimenti_attesi', 'magazzino_id',
    '14) magazzino_id NOT NULL — e'' l''ancora del perimetro (M-6)');

-- ============================================================
-- 15 Il lettore: un atteso in entrata non e' un blocco
-- ============================================================
-- A questo punto su (mag, art) restano: il -10 del soggetto, CHIUSO dal test 12,
-- e il +5 con documento del test 9, APERTO. Nessun movimento a registro. Se
-- vw_disponibilita contasse il +5 come blocco, comparirebbe una riga.
SELECT is(
    (SELECT count(*) FROM magazzino.vw_disponibilita d JOIN _fix f ON d.magazzino_id = f.mag AND d.articolo_id = f.art),
    0::bigint,
    '15) un atteso in ENTRATA aperto non e'' un blocco: vw_disponibilita non ne fa una riga');

SELECT * FROM finish();
ROLLBACK;
