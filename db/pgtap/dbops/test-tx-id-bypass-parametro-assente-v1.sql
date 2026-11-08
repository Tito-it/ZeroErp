-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture toglie la riga tx_id_bypass_enabled di
--   config.parameters (catalogo scritto dal seed) e monta un trigger su una
--   tabella temporanea.
--
-- Test: dbops.trgfn_tx_id_managed senza il parametro del bypass (D12).
-- Brief: brief-db-revisione-dbops, giro 9, blocco 9b (§24, N6). changeSet 20261109-52.
--
-- ⚠️ Perche' quasi tutto e' sulla forma del corpo. Il valore finale lo decide
--   COALESCE(dbops.tx_id di sessione, valore calcolato, uuidv7()): con la GUC di
--   sessione impostata vince lei in tutti e due i rami, e senza la GUC i due rami
--   danno la sentinella quando il canale di log e' spento (la CI). Il ramo preso
--   non si vede dal risultato, e l'avviso col canale spento non si persiste. Si
--   prova quindi che il corpo legge il parametro mancante come «spento» con il
--   suo avviso, e che una scrittura senza parametro passa.
--   (Il COALESCE finale che fa vincere l'id di sessione anche quando non e'
--   registrato e' un nodo a parte: §24.6 del brief.)
-- ⚠️ Il valore NULL del parametro il modello non lo ammette
--   (config.parameters.default_value e' NOT NULL).
--
-- Elenco test (plan 5):
--   1) il ramo «parametro assente» scrive W_TXID_BYPASS_PARAMETRO_ASSENTE
--   2) ... e non piu' un E_ che non ferma (E_ERRORE_PARAMETRI_TABELLA)
--   3) il parametro assente vale spento: il corpo lo porta a false
--   4) una scrittura tracciata senza il parametro passa, col bypass di sessione
--   5) il codice e' registrato come AVVISO
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

SELECT matches(
    (SELECT prosrc FROM pg_proc WHERE oid = 'dbops.trgfn_tx_id_managed()'::regprocedure),
    'IF v_bypass_enabled IS NULL THEN.*W_TXID_BYPASS_PARAMETRO_ASSENTE',
    '1) parametro assente: l''avviso W_TXID_BYPASS_PARAMETRO_ASSENTE');

SELECT doesnt_match(
    (SELECT prosrc FROM pg_proc WHERE oid = 'dbops.trgfn_tx_id_managed()'::regprocedure),
    'E_ERRORE_PARAMETRI_TABELLA',
    '2) ... e non un E_ che non ferma');

SELECT matches(
    (SELECT prosrc FROM pg_proc WHERE oid = 'dbops.trgfn_tx_id_managed()'::regprocedure),
    'W_TXID_BYPASS_PARAMETRO_ASSENTE.*v_bypass_enabled := false;.*IF NOT v_bypass_enabled THEN',
    '3) il parametro assente vale spento, poi si legge l''override di sessione');

CREATE TEMP TABLE pgtap_txid (id int, tx_id uuid);
CREATE TRIGGER trg_pgtap_txid BEFORE INSERT ON pgtap_txid
    FOR EACH ROW EXECUTE FUNCTION dbops.trgfn_tx_id_managed();

DELETE FROM config.parameters WHERE code = 'tx_id_bypass_enabled';
SELECT set_config('myapp.bypass_tx_id_check', 'true', true);

SELECT lives_ok($$INSERT INTO pgtap_txid (id) VALUES (1)$$,
    '4) senza il parametro la scrittura tracciata passa (col bypass di sessione)');

SELECT is((SELECT classe FROM config.codici_errore WHERE codice = 'W_TXID_BYPASS_PARAMETRO_ASSENTE'),
          'AVVISO',
          '5) W_TXID_BYPASS_PARAMETRO_ASSENTE e'' registrato come AVVISO');

SELECT * FROM finish();

ROLLBACK;
