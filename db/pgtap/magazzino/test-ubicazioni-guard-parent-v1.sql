-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il guard sul padre di un'ubicazione, magazzino.trgfn_ubicazioni_guard_parent
--   (brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici, R-1 e sezione
--   4-bis): il padre sta nello stesso magazzino, la gerarchia non ha cicli, e
--   magazzino_id e' immutabile (lock delle colonne, D1). Ogni caso e' COSTRUITO.
--
-- ⚠️ Fixture COSTRUITA: azienda e operatore dall'helper, DUE magazzini della
--   stessa azienda (A e A2) e un'ubicazione in ciascuno; in A una catena
--   R -> C1 -> C2 per i cicli lunghi. Una SECONDA azienda con un magazzino e
--   un'ubicazione (costruiti nel suo contesto, e rimesso il primo): e' il padre
--   che sotto RLS non si vede.
-- ⚠️ Gira come l'applicazione: il guard e' INVOKER e legge il padre sotto
--   rls_ubicazioni_ef_whitelist — il test 4 misura proprio questo.
-- ⚠️ Il test 10 dipende dal trigger di lock, che lo genera l'automazione
--   (ci_apply in CI; su dev il job automations_lock_columns): se non c'e'
--   ancora fa skip() dichiarato, non un verde per sottrazione.
--
-- Elenco test (plan 13):
--    1) padre dello stesso magazzino: passa
--    2) INSERT con padre di un altro magazzino (stessa azienda): E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO, la frase nomina i due magazzini
--    3) UPDATE parent_id verso un'ubicazione di un altro magazzino: idem
--    4) padre di un'altra azienda (non visibile sotto RLS): stesso codice, fail-closed, la frase lo dice
--    5) INSERT con parent_id = id: E_MAG_UBICAZIONE_PADRE_CICLICO
--    6) UPDATE R.parent_id = C2 (ciclo di lunghezza 3): E_MAG_UBICAZIONE_PADRE_CICLICO
--    7) UPDATE C1.parent_id = C1: idem
--    8) UPDATE C2.parent_id = R (risalire verso un antenato): passa
--    9) magazzino_id e' dichiarata immutabile in automation_lock_columns
--   10) ...e il lock generato la rifiuta (E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE) — skip se non ancora generato
--   11) il trigger del guard e' montato BEFORE INSERT OR UPDATE OF parent_id
--   12) i sei codici del brief sono a catalogo con la loro classe
--   13) ...e hanno tutti una frase in italiano
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _mondo   AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
CREATE TEMP TABLE _mondo_b AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore('UGP');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

CREATE TEMP TABLE _fix (
    mag_a bigint, mag_a2 bigint, mag_b bigint,
    ubi_a bigint, ubi_a2 bigint, ubi_b bigint,
    r bigint, c1 bigint, c2 bigint,
    tipo bigint
);

DO $fix$
DECLARE
    v_mag_a bigint; v_mag_a2 bigint; v_mag_b bigint;
    v_ubi_a bigint; v_ubi_a2 bigint; v_ubi_b bigint;
    v_r bigint; v_c1 bigint; v_c2 bigint;
    v_tipo bigint;
BEGIN
    SELECT t.id INTO v_tipo FROM config.tipi_ubicazione t WHERE t.attivo ORDER BY t.id LIMIT 1;

    v_mag_a  := dbops.fn_pgtap_crea_magazzino('PGT-UGP-A',  true);
    v_mag_a2 := dbops.fn_pgtap_crea_magazzino('PGT-UGP-A2', true);
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id) VALUES (v_mag_a,  'PGT-UGP-UA',  v_tipo) RETURNING id INTO v_ubi_a;
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id) VALUES (v_mag_a2, 'PGT-UGP-UA2', v_tipo) RETURNING id INTO v_ubi_a2;
    -- La catena R -> C1 -> C2, tutta in A.
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id)            VALUES (v_mag_a, 'PGT-UGP-R',  v_tipo)       RETURNING id INTO v_r;
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id, parent_id) VALUES (v_mag_a, 'PGT-UGP-C1', v_tipo, v_r)  RETURNING id INTO v_c1;
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id, parent_id) VALUES (v_mag_a, 'PGT-UGP-C2', v_tipo, v_c1) RETURNING id INTO v_c2;

    -- La seconda azienda: il suo magazzino e la sua ubicazione, nel SUO contesto.
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo_b));
    v_mag_b := dbops.fn_pgtap_crea_magazzino('PGT-UGP-B', true);
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id) VALUES (v_mag_b, 'PGT-UGP-UB', v_tipo) RETURNING id INTO v_ubi_b;
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo));

    INSERT INTO _fix VALUES (v_mag_a, v_mag_a2, v_mag_b, v_ubi_a, v_ubi_a2, v_ubi_b, v_r, v_c1, v_c2, v_tipo);
END $fix$;

-- ============================================================
-- 1-4 Il padre sta nello stesso magazzino
-- ============================================================
SELECT lives_ok(
    $$ INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id, parent_id)
       SELECT mag_a, 'PGT-UGP-OK', tipo, ubi_a FROM _fix $$,
    '1) padre dello stesso magazzino: passa');

SELECT throws_like(
    $$ INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id, parent_id)
       SELECT mag_a2, 'PGT-UGP-KO', tipo, ubi_a FROM _fix $$,
    '%L''ubicazione padre PGT-UGP-UA non appartiene al magazzino PGT-UGP-A2: appartiene al magazzino PGT-UGP-A.%',
    '2) INSERT con padre di un altro magazzino: la frase nomina i due magazzini');

SELECT throws_like(
    $$ UPDATE magazzino.ubicazioni u SET parent_id = f.ubi_a FROM _fix f WHERE u.id = f.ubi_a2 $$,
    '%L''ubicazione padre PGT-UGP-UA non appartiene al magazzino PGT-UGP-A2%',
    '3) UPDATE parent_id verso un''ubicazione di un altro magazzino: rifiutato');

SELECT throws_like(
    $$ INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id, parent_id)
       SELECT mag_a, 'PGT-UGP-KOB', tipo, ubi_b FROM _fix $$,
    '%non appartiene al magazzino PGT-UGP-A: non è visibile con i permessi di chi sta operando.%',
    '4) padre di un''altra azienda: sotto RLS non si vede, e si rifiuta (fail-closed)');

-- ============================================================
-- 5-8 La gerarchia non ha cicli
-- ============================================================
SELECT throws_like(
    $$ INSERT INTO magazzino.ubicazioni (id, magazzino_id, codice, tipo_id, parent_id)
       SELECT 999999901, mag_a, 'PGT-UGP-SELF', tipo, 999999901 FROM _fix $$,
    '%L''ubicazione PGT-UGP-SELF non può avere come padre PGT-UGP-SELF: sarebbe un ciclo%',
    '5) INSERT con parent_id = id: E_MAG_UBICAZIONE_PADRE_CICLICO');

SELECT throws_like(
    $$ UPDATE magazzino.ubicazioni u SET parent_id = f.c2 FROM _fix f WHERE u.id = f.r $$,
    '%L''ubicazione PGT-UGP-R non può avere come padre PGT-UGP-C2: sarebbe un ciclo%',
    '6) UPDATE R.parent_id = C2 (ciclo di lunghezza 3): rifiutato');

SELECT throws_like(
    $$ UPDATE magazzino.ubicazioni u SET parent_id = f.c1 FROM _fix f WHERE u.id = f.c1 $$,
    '%L''ubicazione PGT-UGP-C1 non può avere come padre PGT-UGP-C1: sarebbe un ciclo%',
    '7) UPDATE C1.parent_id = C1: rifiutato');

SELECT lives_ok(
    $$ UPDATE magazzino.ubicazioni u SET parent_id = f.r FROM _fix f WHERE u.id = f.c2 $$,
    '8) UPDATE C2.parent_id = R (verso un antenato, nessun ciclo): passa');

-- ============================================================
-- 9-10 magazzino_id e' immutabile (D1): la sede e' il lock delle colonne
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM dbops.automation_lock_columns l
             WHERE l.target_schema = 'magazzino' AND l.target_table = 'ubicazioni'
               AND l.column_name = 'magazzino_id'
               AND l.error_code = 'E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE' AND l.enabled),
    '9) ubicazioni.magazzino_id e'' dichiarata immutabile in automation_lock_columns');

-- Il trigger lo genera l'automazione, e si cerca per FUNZIONE e argomenti, non per nome.
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
                  WHERE t.tgrelid = 'magazzino.ubicazioni'::regclass AND NOT t.tgisinternal
                    AND p.proname = 'trgfn_lock_columns'
                    AND pg_get_triggerdef(t.oid) LIKE '%''magazzino_id''%')
    THEN throws_like(
        $$ UPDATE magazzino.ubicazioni u SET magazzino_id = f.mag_a2 FROM _fix f WHERE u.id = f.ubi_a $$,
        '%Il magazzino di un''ubicazione non si cambia (colonna magazzino_id)%',
        '10) il lock generato rifiuta il cambio di magazzino_id')
    ELSE skip('10) lock su magazzino_id non ancora generato (ci_apply / job automations_lock_columns): niente da misurare', 1)
END;

-- ============================================================
-- 11-13 Forma: trigger, codici, frasi
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM pg_trigger t
             WHERE t.tgrelid = 'magazzino.ubicazioni'::regclass
               AND t.tgname = 'trg_ubicazioni_a10_parent_guard_ins_upd'
               AND pg_get_triggerdef(t.oid) LIKE '%BEFORE INSERT OR UPDATE OF parent_id ON magazzino.ubicazioni%'),
    '11) trg_ubicazioni_a10_parent_guard_ins_upd: BEFORE INSERT OR UPDATE OF parent_id');

SELECT is(
    (SELECT string_agg(c.codice || ':' || c.classe, ' ' ORDER BY c.codice)
       FROM config.codici_errore c
      WHERE c.codice IN ('E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO', 'E_MAG_UBICAZIONE_PADRE_CICLICO',
                         'E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE',
                         'E_MAG_MAGAZZINO_NON_TROVATO', 'E_MAG_UBICAZIONE_NON_TROVATA', 'E_MAG_LOTTO_NON_TROVATO')
        AND c.obsoleto_dal IS NULL),
    'E_MAG_LOTTO_NON_TROVATO:NON_TROVATO E_MAG_MAGAZZINO_NON_TROVATO:NON_TROVATO '
    'E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE:CONFLITTO_STATO E_MAG_UBICAZIONE_NON_TROVATA:NON_TROVATO '
    'E_MAG_UBICAZIONE_PADRE_CICLICO:DATO_ERRATO E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO:DATO_ERRATO',
    '12) i sei codici del brief sono a catalogo con la loro classe');

SELECT is(
    (SELECT count(*)::int FROM config.messaggi_errore m
      WHERE m.lingua = 'it' AND m.messaggio NOT LIKE '[MESSAGGIO NON DEFINITO%'
        AND m.codice IN ('E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO', 'E_MAG_UBICAZIONE_PADRE_CICLICO',
                         'E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE',
                         'E_MAG_MAGAZZINO_NON_TROVATO', 'E_MAG_UBICAZIONE_NON_TROVATA', 'E_MAG_LOTTO_NON_TROVATO')),
    6,
    '13) ...e hanno tutti una frase in italiano');

SELECT * FROM finish();
ROLLBACK;
