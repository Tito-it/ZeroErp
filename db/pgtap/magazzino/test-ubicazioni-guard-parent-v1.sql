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
-- ⚠️ Gira come l'applicazione. Dal Lotto 1 (brief-db-magazzino-tutte-le-scritture-dal-verbo)
--   le ubicazioni le scrivono i verbi SECURITY DEFINER: le fixture nascono da
--   dbops.fn_pgtap_crea_ubicazione, i casi passano da magazzino.fn_aggiungi_ubicazione e
--   fn_modifica_ubicazione (l'operatore ha TUTTO sull'area magazzino, scritto dal test).
--   Il guard legge il padre nel perimetro di chi agisce (20261122-11): i test 4 e 5
--   misurano che dentro il verbo la frase non nomini il magazzino dell'altra azienda.
-- rev 2026-11-22: tolti due casi che l'applicazione non puo' piu' tentare — la nascita
--   con parent_id = id (il verbo non prende l'id: il ramo lo prova il 7) e il cambio di
--   magazzino_id (il verbo non lo ammette: E_CAMPO_NON_AMMESSO al 10; il lucchetto resta
--   dichiarato al 9). Al loro posto il padre altrui in modifica (5).
--
-- Elenco test (plan 13):
--    1) nascita con padre dello stesso magazzino: passa
--    2) nascita con padre di un altro magazzino (stessa azienda): E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO, la frase nomina i due magazzini
--    3) modifica di parent_id verso un'ubicazione di un altro magazzino: idem
--    4) nascita con padre di un'altra azienda: stesso codice, fail-closed, la frase non nomina il suo magazzino
--    5) modifica di parent_id verso il padre di un'altra azienda: la stessa frase
--    6) modifica R.parent_id = C2 (ciclo di lunghezza 3): E_MAG_UBICAZIONE_PADRE_CICLICO
--    7) modifica C1.parent_id = C1: idem
--    8) modifica C2.parent_id = R (risalire verso un antenato): passa
--    9) magazzino_id e' dichiarata immutabile in automation_lock_columns
--   10) ...e il verbo di modifica non la ammette: E_CAMPO_NON_AMMESSO
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
    v_ubi_a  := dbops.fn_pgtap_crea_ubicazione(v_mag_a,  'PGT-UGP-UA',  p_tipo_id => v_tipo);
    v_ubi_a2 := dbops.fn_pgtap_crea_ubicazione(v_mag_a2, 'PGT-UGP-UA2', p_tipo_id => v_tipo);
    -- La catena R -> C1 -> C2, tutta in A.
    v_r  := dbops.fn_pgtap_crea_ubicazione(v_mag_a, 'PGT-UGP-R',  p_tipo_id => v_tipo);
    v_c1 := dbops.fn_pgtap_crea_ubicazione(v_mag_a, 'PGT-UGP-C1', jsonb_build_object('parent_id', v_r),  v_tipo);
    v_c2 := dbops.fn_pgtap_crea_ubicazione(v_mag_a, 'PGT-UGP-C2', jsonb_build_object('parent_id', v_c1), v_tipo);

    -- La seconda azienda: il suo magazzino e la sua ubicazione, nel SUO contesto.
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo_b));
    v_mag_b := dbops.fn_pgtap_crea_magazzino('PGT-UGP-B', true);
    v_ubi_b := dbops.fn_pgtap_crea_ubicazione(v_mag_b, 'PGT-UGP-UB', p_tipo_id => v_tipo);
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo));

    INSERT INTO _fix VALUES (v_mag_a, v_mag_a2, v_mag_b, v_ubi_a, v_ubi_a2, v_ubi_b, v_r, v_c1, v_c2, v_tipo);
END $fix$;

-- I casi passano dai verbi: l'operatore di A ha TUTTO sull'area magazzino (scelta del test).
INSERT INTO config.user_override_aree (auth_user_id, area_id, livello, motivo)
SELECT m.auth_user_id, af.id, 'TUTTO', 'pgTAP: guard del padre, casi dai verbi'
  FROM _mondo m, config.aree_funzionali af
 WHERE af.schema_db = 'magazzino';

-- ============================================================
-- 1-4 Il padre sta nello stesso magazzino
-- ============================================================
SELECT lives_ok(
    $$ SELECT magazzino.fn_aggiungi_ubicazione(mag_a, 'PGT-UGP-OK', tipo, jsonb_build_object('parent_id', ubi_a)) FROM _fix $$,
    '1) nascita con padre dello stesso magazzino: passa');

SELECT throws_like(
    $$ SELECT magazzino.fn_aggiungi_ubicazione(mag_a2, 'PGT-UGP-KO', tipo, jsonb_build_object('parent_id', ubi_a)) FROM _fix $$,
    '%L''ubicazione padre PGT-UGP-UA non appartiene al magazzino PGT-UGP-A2: appartiene al magazzino PGT-UGP-A.%',
    '2) nascita con padre di un altro magazzino: la frase nomina i due magazzini');

SELECT throws_like(
    $$ SELECT magazzino.fn_modifica_ubicazione(mag_a2, ubi_a2, jsonb_build_object('parent_id', ubi_a)) FROM _fix $$,
    '%L''ubicazione padre PGT-UGP-UA non appartiene al magazzino PGT-UGP-A2%',
    '3) modifica di parent_id verso un''ubicazione di un altro magazzino: rifiutata');

SELECT throws_like(
    $$ SELECT magazzino.fn_aggiungi_ubicazione(mag_a, 'PGT-UGP-KOB', tipo, jsonb_build_object('parent_id', ubi_b)) FROM _fix $$,
    '%non appartiene al magazzino PGT-UGP-A: non è visibile con i permessi di chi sta operando.%',
    '4) nascita con padre di un''altra azienda: fuori perimetro non si vede, si rifiuta (fail-closed), la frase non nomina il suo magazzino');

SELECT throws_like(
    $$ SELECT magazzino.fn_modifica_ubicazione(mag_a, r, jsonb_build_object('parent_id', ubi_b)) FROM _fix $$,
    '%non appartiene al magazzino PGT-UGP-A: non è visibile con i permessi di chi sta operando.%',
    '5) modifica di parent_id verso il padre di un''altra azienda: la stessa frase');

-- ============================================================
-- 6-8 La gerarchia non ha cicli
-- ============================================================

SELECT throws_like(
    $$ SELECT magazzino.fn_modifica_ubicazione(mag_a, r, jsonb_build_object('parent_id', c2)) FROM _fix $$,
    '%L''ubicazione PGT-UGP-R non può avere come padre PGT-UGP-C2: sarebbe un ciclo%',
    '6) modifica R.parent_id = C2 (ciclo di lunghezza 3): rifiutata');

SELECT throws_like(
    $$ SELECT magazzino.fn_modifica_ubicazione(mag_a, c1, jsonb_build_object('parent_id', c1)) FROM _fix $$,
    '%L''ubicazione PGT-UGP-C1 non può avere come padre PGT-UGP-C1: sarebbe un ciclo%',
    '7) modifica C1.parent_id = C1: rifiutata');

SELECT lives_ok(
    $$ SELECT magazzino.fn_modifica_ubicazione(mag_a, c2, jsonb_build_object('parent_id', r)) FROM _fix $$,
    '8) modifica C2.parent_id = R (verso un antenato, nessun ciclo): passa');

-- ============================================================
-- 9-10 magazzino_id e' immutabile (D1): la sede e' il lock delle colonne
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM dbops.automation_lock_columns l
             WHERE l.target_schema = 'magazzino' AND l.target_table = 'ubicazioni'
               AND l.column_name = 'magazzino_id'
               AND l.error_code = 'E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE' AND l.enabled),
    '9) ubicazioni.magazzino_id e'' dichiarata immutabile in automation_lock_columns');

-- Il lucchetto difende dallo scrittore diretto (il migratore); l'applicazione passa dal
-- verbo, che magazzino_id non lo ammette fra i campi modificabili.
SELECT is(
    dbops.fn_pgtap_codice_errore(
        $$SELECT magazzino.fn_modifica_ubicazione((SELECT mag_a FROM _fix), (SELECT ubi_a FROM _fix),
              jsonb_build_object('magazzino_id', (SELECT mag_a2 FROM _fix)))$$),
    'E_CAMPO_NON_AMMESSO',
    '10) ...e il verbo di modifica non la ammette: E_CAMPO_NON_AMMESSO');

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
