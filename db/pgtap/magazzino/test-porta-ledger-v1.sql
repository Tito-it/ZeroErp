-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: LA PORTA del ledger (D-L2-b, sezione 4.1, 6-ter C1/C2): l'app legge
--   e non scrive; scrive solo la primitiva, DEFINER del PROPRIETARIO delle
--   tabelle, e la primitiva la chiamano solo i VERBI (fn_posta_inventario,
--   fn_posta_rettifica), che applicano registra_magazzino. E' il presidio che
--   tiene allineate le TRE sedi della postura (forward 90_end, loop ci_apply,
--   provisioning), per le tabelle E per le funzioni riservate: verde su dev e
--   rosso sul DB da zero e' la forma in cui la terza si dimentica.
--   Brief: brief-db-magazzino-lotto-2-motore, sezione 7;
--   brief-db-magazzino-verbi-con-permesso, sezioni 2.3 e 3.2.
--
-- ⭐ Rev 2026-09-24 (brief-db-magazzino-verbi-con-permesso, P-4): la porta era
--   chiusa a meta' — l'app eseguiva la primitiva e il ricalcolo. I test 7, 12,
--   13, 14 cambiano SOGGETTO (dalla primitiva ai verbi) e nascono 17 e 18.
--   ⚠️ Si perde una prova, dichiarata: i vecchi 12 e 13 erano l'unica prova di
--   COMPORTAMENTO del ramo «dentro una DEFINER» del guard di scope (C1). Il ramo
--   resta la rete sotto i verbi, ma l'app non lo raggiunge piu' (il verbo ferma
--   prima fuori perimetro e senza identita'), e da owner non si esercita
--   (current_user = session_user). Resta la prova strutturale (11).
--
-- ⚠️ Gira come l'APPLICAZIONE, ed e' il punto: la postura si asserisce con
--   has_table_privilege('zeroerp_app', ...) — mai role_table_grants, cieco
--   fuori dal ruolo connesso — e col COMPORTAMENTO (42501 su un INSERT diretto).
--   Due aziende costruite come app cambiando contesto operatore: il magazzino
--   B nasce nel contesto di B, il tentativo si fa nel contesto di A.
--
-- Elenco test (plan 18):
--   La postura (has_table_privilege):
--    1) movimenti: SELECT si', INSERT/UPDATE/DELETE no
--    2) valore_giacenza: idem
--    3) movimenti_attesi: SELECT si', INSERT/UPDATE/DELETE no (rev 2026-09-28: dal Lotto 3
--       i blocchi li scrivono i verbi fn_apri_blocco / fn_libera_blocco, D-L3-j)
--   Il comportamento:
--    4) INSERT diretto sul ledger come app -> 42501 (permesso negato)
--    5) UPDATE diretto su valore_giacenza -> 42501
--    6) DELETE su movimenti_attesi -> 42501
--    7) la primitiva chiamata DIRETTAMENTE dall'app -> 42501 (la porta sulla funzione)
--   La primitiva:
--    8) e' SECURITY DEFINER e il suo proprietario e' il proprietario delle tre tabelle (proowner = relowner)
--    9) il pin search_path contiene public (fn_log_and_raise_error, dblink)
--   10) le altre DEFINER del lotto (fn_ricalcola_valore_giacenza, dbops.fn_sorgenti_orfane) hanno il pin
--   Il perimetro e i verbi:
--   11) il guard di scope e' montato sulle tre tabelle con il modo magazzino
--   12) il verbo su un inventario di un ALTRO emittente -> «Documento ... non trovato»
--   13) il verbo SENZA identita' in sessione -> E_PERMESSO_NEGATO
--   14) il verbo nel perimetro, con registra_magazzino -> PASSA: la porta e' una porta
--   Il lock (struttura: la serializzazione non si prova in pgTAP):
--   15) la primitiva contiene pg_advisory_xact_lock a due argomenti col suo namespace
--   16) ...e la chiave e' (magazzino, articolo) — il perimetro del controllo
--   Le funzioni riservate (has_function_privilege):
--   17) primitiva e ricalcolo: l'app NON li esegue (neanche via PUBLIC)
--   18) i due verbi: l'app li esegue
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
CREATE TEMP TABLE _mondo_b AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore('PORTB');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

CREATE TEMP TABLE _fix (mag bigint, mag_b bigint, art uuid, src bigint, r1 bigint, r2 bigint, r3 bigint, r4 bigint, cau bigint, inv1 bigint, inv_b bigint);
DO $fix$
DECLARE v_mag bigint; v_mag_b bigint; v_art uuid; v_inv bigint; v_tmp bigint; v_r bigint[] := '{}'; v_i bigint[] := '{}'; v_inv_b bigint; i int;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-L2P-A', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-L2P-ART', true, false, false);
    FOR i IN 1..4 LOOP
        INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
        INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) VALUES (v_inv, v_art, i) RETURNING id INTO v_tmp;
        v_r := v_r || v_tmp;
        v_i := v_i || v_inv;
    END LOOP;
    -- Il magazzino B, e un suo inventario CONFIRM, nascono nel contesto di B.
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo_b));
    v_mag_b := dbops.fn_pgtap_crea_magazzino('PGT-L2P-B', false);
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag_b) RETURNING id INTO v_inv_b;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) VALUES (v_inv_b, v_art, 5);
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv_b;
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo));
    INSERT INTO _fix VALUES (v_mag, v_mag_b, v_art,
                             -- rev 2026-11-09 (giro M.3): il tipo e' il documento, INVENTARIO_RIGA non e' piu' una sorgente.
                             (SELECT id FROM config.sorgenti WHERE codice_interno = 'INVENTARIO'),
                             v_r[1], v_r[2], v_r[3], v_r[4],
                             (SELECT id FROM magazzino.causali WHERE codice_interno = 'INV_INIZIALE'),
                             v_i[1], v_inv_b);
END $fix$;
-- I verbi applicano registra_magazzino: l'operatore di fixture non ce l'ha (P-5).
DO $az$ BEGIN PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _mondo), 'registra_magazzino'); END $az$;

-- ============================================================
-- 1-3 La postura
-- ============================================================
SELECT is(
    (SELECT (has_table_privilege('zeroerp_app', 'magazzino.movimenti', 'SELECT'),
             has_table_privilege('zeroerp_app', 'magazzino.movimenti', 'INSERT'),
             has_table_privilege('zeroerp_app', 'magazzino.movimenti', 'UPDATE'),
             has_table_privilege('zeroerp_app', 'magazzino.movimenti', 'DELETE'))::text),
    '(t,f,f,f)',
    '1) movimenti: l''app legge e basta');
SELECT is(
    (SELECT (has_table_privilege('zeroerp_app', 'magazzino.valore_giacenza', 'SELECT'),
             has_table_privilege('zeroerp_app', 'magazzino.valore_giacenza', 'INSERT'),
             has_table_privilege('zeroerp_app', 'magazzino.valore_giacenza', 'UPDATE'),
             has_table_privilege('zeroerp_app', 'magazzino.valore_giacenza', 'DELETE'))::text),
    '(t,f,f,f)',
    '2) valore_giacenza: la copia la scrive la primitiva');
SELECT is(
    (SELECT (has_table_privilege('zeroerp_app', 'magazzino.movimenti_attesi', 'SELECT'),
             has_table_privilege('zeroerp_app', 'magazzino.movimenti_attesi', 'INSERT'),
             has_table_privilege('zeroerp_app', 'magazzino.movimenti_attesi', 'UPDATE'),
             has_table_privilege('zeroerp_app', 'magazzino.movimenti_attesi', 'DELETE'))::text),
    '(t,f,f,f)',
    '3) movimenti_attesi: sola lettura — i blocchi li aprono e li liberano i verbi (Lotto 3, D-L3-j)');

-- ============================================================
-- 4-7 Il comportamento (come app: e' il runner a garantirlo)
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, qta, causale_id, sorgente_tipo_id, sorgente_id, sorgente_riga)
       SELECT art, mag, 1, cau, src, inv1, r1 FROM _fix $$,
    '42501', NULL,
    '4) INSERT diretto sul ledger: permesso negato');
SELECT throws_ok(
    $$ UPDATE magazzino.valore_giacenza SET valore = valore WHERE false $$,
    '42501', NULL,
    '5) UPDATE su valore_giacenza: permesso negato (anche a zero righe: il permesso si controlla prima)');
SELECT throws_ok(
    $$ DELETE FROM magazzino.movimenti_attesi WHERE false $$,
    '42501', NULL,
    '6) DELETE su movimenti_attesi: permesso negato');
SELECT throws_ok(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'INV_INIZIALE', 1, src, r1, NULL, 3) FROM _fix $$,
    '42501', NULL,
    '7) la primitiva chiamata direttamente dall''app: permesso negato — si passa solo dai verbi');

-- ============================================================
-- 8-10 La primitiva: DEFINER del proprietario, con il pin
-- ============================================================
SELECT is(
    (SELECT (p.prosecdef,
             (SELECT count(DISTINCT c.relowner) = 1 AND min(c.relowner) = p.proowner
                FROM pg_class c WHERE c.oid IN ('magazzino.movimenti'::regclass, 'magazzino.valore_giacenza'::regclass, 'magazzino.movimenti_attesi'::regclass)))::text
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'magazzino' AND p.proname = 'fn_scrivi_movimento'),
    '(t,t)',
    '8) SECURITY DEFINER, e il proprietario della funzione e'' il proprietario delle tre tabelle');
SELECT ok(
    (SELECT p.proconfig::text LIKE '%search_path=pg_catalog, public, pg_temp%'
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'magazzino' AND p.proname = 'fn_scrivi_movimento'),
    '9) il pin del search_path contiene public (la catena passa da dblink)');
SELECT is(
    (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE (n.nspname, p.proname) IN (('magazzino', 'fn_ricalcola_valore_giacenza'), ('dbops', 'fn_sorgenti_orfane'))
        AND p.prosecdef AND p.proconfig::text LIKE '%search_path=pg_catalog, public, pg_temp%'),
    2::bigint,
    '10) le altre due DEFINER del lotto: DEFINER con il pin');

-- ============================================================
-- 11-14 Il perimetro, e i verbi come sola strada
-- ============================================================
SELECT is(
    (SELECT count(*) FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
      WHERE p.proname = 'trgfn_guard_emittente_scope'
        AND t.tgrelid IN ('magazzino.movimenti'::regclass, 'magazzino.valore_giacenza'::regclass, 'magazzino.movimenti_attesi'::regclass)
        AND pg_get_triggerdef(t.oid) LIKE '%(''magazzino'', ''magazzino_id'')%'),
    3::bigint,
    '11) il guard di scope e'' montato sulle tre tabelle col modo magazzino');
SELECT throws_like(
    $$ SELECT * FROM magazzino.fn_posta_inventario((SELECT inv_b FROM _fix)) $$,
    '%Documento %non trovato%',
    '12) il verbo su un inventario di un altro emittente: non trovato (il predicato della policy, dentro il verbo DEFINER)');
-- Senza identita': la GUC svuotata. Il verbo si ferma al guard, prima di leggere.
SELECT set_config('app.current_user_id', '', true);
SELECT throws_like(
    $$ SELECT * FROM magazzino.fn_posta_inventario((SELECT inv1 FROM _fix)) $$,
    '%Non hai i permessi per questa operazione%',
    '13) il verbo SENZA identita'': E_PERMESSO_NEGATO (la porta non e'' aperta a chi non dice chi e'')');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;
UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = (SELECT inv1 FROM _fix);
SELECT lives_ok(
    $$ SELECT * FROM magazzino.fn_posta_inventario((SELECT inv1 FROM _fix)) $$,
    '14) il verbo nel perimetro, con registra_magazzino: passa — la porta e'' una porta');

-- ============================================================
-- 15-16 Il lock (struttura)
-- ============================================================
SELECT ok(
    (SELECT pg_get_functiondef(p.oid) LIKE '%pg_advisory_xact_lock(%hashtext(''magazzino.fn_scrivi_movimento'')%'
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'magazzino' AND p.proname = 'fn_scrivi_movimento'),
    '15) pg_advisory_xact_lock a due argomenti, namespace = il nome della funzione');
SELECT ok(
    (SELECT pg_get_functiondef(p.oid) LIKE '%hashtext(p_magazzino_id::text || '':'' || p_articolo_id::text)%'
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'magazzino' AND p.proname = 'fn_scrivi_movimento'),
    '16) la chiave del lock e'' (magazzino, articolo): il perimetro di tutto cio'' che si legge dentro');

-- ============================================================
-- 17-18 Le funzioni riservate
-- ============================================================
-- has_function_privilege sull'app risponde anche per PUBLIC (che ha =X per
-- default): false qui vuol dire revocato a entrambi.
SELECT is(
    (SELECT (has_function_privilege('zeroerp_app', 'magazzino.fn_scrivi_movimento'::regproc, 'EXECUTE'),
             has_function_privilege('zeroerp_app', 'magazzino.fn_ricalcola_valore_giacenza'::regproc, 'EXECUTE'))::text),
    '(f,f)',
    '17) primitiva e ricalcolo: l''app non li esegue, ne'' direttamente ne'' via PUBLIC');
SELECT is(
    (SELECT (has_function_privilege('zeroerp_app', 'magazzino.fn_posta_inventario'::regproc, 'EXECUTE'),
             has_function_privilege('zeroerp_app', 'magazzino.fn_posta_rettifica'::regproc, 'EXECUTE'))::text),
    '(t,t)',
    '18) i due verbi: l''app li esegue — sono la sola strada verso il registro');

SELECT * FROM finish();
ROLLBACK;
