-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: i trigger ATTIVO orfani — il lettore dbops.fn_trigger_attivo_orfani,
--   il ritiro dbops.fn_ritira_attivo_orfani e il loro aggancio al generatore.
-- Riferimento: brief-be-utenti-di-sviluppo §9.5 (R-1, Q-1); changeSet
--   20261021-21 … -23.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - un trigger ATTIVO e' orfano quando una tabella o una colonna che il SUO
--     corpo legge non esiste: dopo un DROP TABLE della figlia (TABELLA_ASSENTE)
--     o un DROP COLUMN della colonna FK (COLONNA_ASSENTE);
--   - ⛔ «senza FK» NON e' orfano: un require scritto a mano su una chiave
--     polimorfa ha i nomi vivi e resta;
--   - un trigger con meno argomenti del minimo e' un errore di scrittura:
--     il lettore lo riporta, il ritiro non lo tocca;
--   - dopo il ritiro il padre si spegne, e i trigger validi sono ancora li';
--   - il generatore chiama il ritiro (chi genera ritira).
--
-- Elenco test (plan 10):
--   1) firma del lettore
--   2) firma del ritiro
--   3) PRESIDIO: nel database (fuori dalla fixture) nessun orfano
--   4) lettore sulla fixture: esattamente i tre casi attesi, col loro motivo
--   5) COLONNA_ASSENTE nomina la colonna che manca
--   6) il ritiro toglie i due orfani della fixture
--   7) dopo il ritiro, sulla fixture resta solo ARGOMENTI_INSUFFICIENTI
--   8) i due trigger validi (block con FK, require polimorfo) ci sono ancora
--   9) il padre si spegne
--  10) il generatore chiama dbops.fn_ritira_attivo_orfani nel ramo fuori dal dry run
--
-- ⚠️ Il test 3 e' un PRESIDIO su cio' che c'e', e va letto cosi': in CI e'
--   verde per costruzione (ci_apply gira dopo i DROP, il generatore non crea
--   mai un orfano); su un database di sviluppo e' rosso finche' il job
--   automations_attivo non ha ripulito. La regola la provano i test 4-9, sulla
--   fixture che si costruiscono.
-- ⚠️ Fixture su tabelle TEMP: nessun DDL su tabelle condivise (nessun lock
--   conteso), nessun privilegio di schema richiesto; il ROLLBACK porta via tutto.
--   I trigger sono scritti a mano con la grammatica del generatore.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il file legge e scrive solo il catalogo e tabelle
--   TEMP sue: nessuna tabella sotto RLS, nessuna veste da aprire.

SELECT plan(10);

-- ============================================================
-- 1-2) Le firme
-- ============================================================
SELECT has_function(
    'dbops', 'fn_trigger_attivo_orfani', ARRAY[]::text[],
    'dbops.fn_trigger_attivo_orfani() esiste'
);
SELECT has_function(
    'dbops', 'fn_ritira_attivo_orfani', ARRAY[]::text[],
    'dbops.fn_ritira_attivo_orfani() esiste'
);

-- ============================================================
-- 3) PRESIDIO: nessun orfano nel database, PRIMA della fixture e del ritiro
-- ============================================================
SELECT is_empty(
    $$SELECT format('%s %s: %s (%s)', o.tabella::regclass, o.trigger_nome, o.motivo, o.dettaglio)
        FROM dbops.fn_trigger_attivo_orfani() AS o$$,
    'presidio: nessun trigger ATTIVO nomina una tabella o una colonna che non esiste (su dev: rosso fino al job automations_attivo)'
);

-- ============================================================
-- Fixture: un padre, tre figlie, una tabella polimorfa, un secondo padre
-- ============================================================
CREATE TEMP TABLE t_padre      (id bigint PRIMARY KEY, attivo boolean NOT NULL DEFAULT true);
CREATE TEMP TABLE t_figlia_ok  (id bigint PRIMARY KEY, padre_id bigint REFERENCES t_padre (id), attivo boolean NOT NULL DEFAULT true);
CREATE TEMP TABLE t_figlia_via (id bigint PRIMARY KEY, padre_id bigint REFERENCES t_padre (id));
CREATE TEMP TABLE t_figlia_col (id bigint PRIMARY KEY, padre_id bigint REFERENCES t_padre (id));
-- chiave polimorfa: nessuna FK, nomi vivi
CREATE TEMP TABLE t_polimorfa  (id bigint PRIMARY KEY, target_id bigint);
CREATE TEMP TABLE t_padre_rotto (id bigint PRIMARY KEY, attivo boolean NOT NULL DEFAULT true);

DO $fixture$
DECLARE
    v_s pg_catalog.pg_namespace.nspname%TYPE :=
        (SELECT n.nspname FROM pg_catalog.pg_namespace n WHERE n.oid = pg_my_temp_schema());
BEGIN
    -- block validi e orfani da essere (stessa grammatica del generatore)
    EXECUTE format($t$CREATE TRIGGER trg_t_ok_block BEFORE UPDATE OF attivo ON %1$I.t_padre FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children(%1$L, 't_figlia_ok', 'padre_id', 'id', 'attivo')$t$, v_s);
    EXECUTE format($t$CREATE TRIGGER trg_t_via_block BEFORE UPDATE OF attivo ON %1$I.t_padre FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children(%1$L, 't_figlia_via', 'padre_id', 'id', 'attivo')$t$, v_s);
    EXECUTE format($t$CREATE TRIGGER trg_t_col_block BEFORE UPDATE OF attivo ON %1$I.t_padre FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children(%1$L, 't_figlia_col', 'padre_id', 'id', 'attivo')$t$, v_s);
    -- require scritto a mano su chiave polimorfa: legittimo
    EXECUTE format($t$CREATE TRIGGER trg_t_poli_require AFTER INSERT OR UPDATE ON %1$I.t_polimorfa FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent(%1$L, 't_padre', 'attivo', 'target_id', 'id')$t$, v_s);
    -- errore di scrittura: due argomenti, il minimo del block e' tre
    EXECUTE format($t$CREATE TRIGGER trg_t_rotto_block BEFORE UPDATE OF attivo ON %1$I.t_padre_rotto FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children(%1$L, 't_figlia_ok')$t$, v_s);
END
$fixture$;

-- i due modi in cui un nome muore
DROP TABLE t_figlia_via;
ALTER TABLE t_figlia_col DROP COLUMN padre_id;

CREATE TEMP VIEW v_orfani_fixture AS
SELECT o.trigger_nome::text AS trigger_nome, o.motivo, o.dettaglio
  FROM dbops.fn_trigger_attivo_orfani() AS o
 WHERE o.tabella IN ('t_padre'::regclass, 't_polimorfa'::regclass, 't_padre_rotto'::regclass);

-- ============================================================
-- 4) Il lettore: i tre casi, ognuno col suo motivo; i validi no
-- ============================================================
SELECT set_eq(
    $$SELECT trigger_nome, motivo FROM v_orfani_fixture$$,
    $$VALUES ('trg_t_col_block',   'COLONNA_ASSENTE'),
             ('trg_t_rotto_block', 'ARGOMENTI_INSUFFICIENTI'),
             ('trg_t_via_block',   'TABELLA_ASSENTE')$$,
    'lettore: tabella assente, colonna assente e argomenti insufficienti; il block con FK e il require polimorfo no'
);

-- ============================================================
-- 5) COLONNA_ASSENTE dice quale
-- ============================================================
SELECT matches(
    (SELECT dettaglio FROM v_orfani_fixture WHERE trigger_nome = 'trg_t_col_block'),
    't_figlia_col\.padre_id$',
    'COLONNA_ASSENTE nomina la colonna che manca (t_figlia_col.padre_id)'
);

-- ============================================================
-- 6) Il ritiro toglie i due orfani della fixture
-- ============================================================
SELECT dbops.fn_ritira_attivo_orfani();

SELECT is(
    (SELECT count(*)::integer FROM pg_catalog.pg_trigger t
      WHERE t.tgrelid = 't_padre'::regclass
        AND t.tgname IN ('trg_t_via_block', 'trg_t_col_block')),
    0,
    'ritiro: il block verso la tabella eliminata e quello verso la colonna eliminata non ci sono piu'''
);

-- ============================================================
-- 7) Resta solo l'errore di scrittura
-- ============================================================
SELECT set_eq(
    $$SELECT trigger_nome, motivo FROM v_orfani_fixture$$,
    $$VALUES ('trg_t_rotto_block', 'ARGOMENTI_INSUFFICIENTI')$$,
    'dopo il ritiro resta solo ARGOMENTI_INSUFFICIENTI: non e'' un residuo, lo corregge una persona'
);

-- ============================================================
-- 8) I validi restano
-- ============================================================
SELECT set_eq(
    $$SELECT t.tgname::text FROM pg_catalog.pg_trigger t
       WHERE t.tgrelid IN ('t_padre'::regclass, 't_polimorfa'::regclass)
         AND NOT t.tgisinternal$$,
    $$VALUES ('trg_t_ok_block'), ('trg_t_poli_require')$$,
    'il block con la FK viva e il require sulla chiave polimorfa (senza FK) restano'
);

-- ============================================================
-- 9) Il padre si spegne (era il 500 di vendite.listini)
-- ============================================================
INSERT INTO t_padre (id) VALUES (1);

SELECT lives_ok(
    $$UPDATE t_padre SET attivo = false WHERE id = 1$$,
    'dopo il ritiro il padre senza figlie si spegne'
);

-- ============================================================
-- 10) Chi genera ritira
-- ============================================================
SELECT matches(
    pg_get_functiondef('dbops.fn_run_automations_attivo(text, text[], boolean)'::regprocedure),
    'IF NOT p_dry_run THEN\s+PERFORM dbops\.fn_ritira_attivo_eccezioni\(\);(\s+--[^\n]*)*\s+PERFORM dbops\.fn_ritira_attivo_orfani\(\);\s+END IF;',
    'il generatore chiama dbops.fn_ritira_attivo_orfani in testa, fuori dal dry run, accanto al ritiro delle eccezioni'
);

SELECT * FROM finish();
ROLLBACK;
