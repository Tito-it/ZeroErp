-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: un lotto con un documento in errore non diventa definitivo, e una
--   fattura in errore non va avanti al suo lotto.
-- Riferimento: brief-modello-documento-vendita §4-septies, R-1 (Tid,
--   2026-10-24): «se un documento e' in errore gli altri non possono passare a
--   uno stato definitivo: prima i documenti non conformi si tolgono dal lotto».
--   changeSet 20261024-34 (invariante lotto <-> fatture) e 20261024-35 (guard
--   di transizione del lotto). Completa D-Q (2026-07-31).
-- rev 2026-10-27 (brief-modello-documento-vendita §15, giro 11): con la porta sul
--   lotto (20261027-18) lo stato si scrive dai verbi. Il lotto avanza dal giro della
--   pipeline (vendite.fn_lotto_proietta_stato_step), come nel processo vero; il test 5
--   annulla col verbo del lotto (vendite.fn_cambia_stato_lotto, nessuna azione: Q-F2).
--   Attese invariate.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - (a) un lotto FERMO (vw_lotti_segnalazioni_summary.fermo) non entra in uno
--     stato congelato e non abortito: E_PIPELINE_LOTTO_CRITICAL;
--   - un passaggio NON congelato resta ammesso, e cosi' l'annullo;
--   - ritirata la segnalazione (il documento e' a posto), il lotto avanza;
--   - (b) la fattura in errore resta INDIETRO al lotto (ammesso), ma una
--     fattura in errore gia' congelata non si aggancia a un lotto che non lo e'.
--
-- Elenco test (plan 8):
--   1) fixture: lotto in bozza con due fatture, una in errore (critical)
--   2) (a) il lotto fermo non passa a DEFINITIVA
--   3) ...e il messaggio e' quello del runner (stesso codice, due punti)
--   4) un passaggio non congelato (EMESSA) resta ammesso; la fattura in
--      errore resta indietro, in bozza
--   5) l'annullo di un lotto fermo resta ammesso
--   6) ritirata la segnalazione, il lotto e le fatture arrivano a DEFINITIVA
--   7) (b) una fattura in errore gia' DEFINITIVA non si aggancia a un lotto in bozza
--   8) (b) una fattura in errore in bozza si aggancia a un lotto EMESSO: resta indietro
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_fattura,
--   chiamato come su un database ricostruito: senza nessuna veste in sessione.

SELECT plan(8);

-- ============================================================
-- Fixture: il mondo, due fatture dello stesso cliente, un lotto
-- ============================================================
CREATE TEMP TABLE t_fa AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('lotto fermo A');
CREATE TEMP TABLE t_fb AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('lotto fermo B', 'DRAFT', (SELECT billing_account_id FROM t_fa));

-- Il lotto del cliente, col tipo documento delle fatture.
CREATE TEMP TABLE t_l AS
SELECT * FROM dbops.fn_pgtap_crea_lotto(
    'lotto fermo', 'DRAFT', (SELECT billing_account_id FROM t_fa),
    (SELECT tipo_doc_fiscale_id FROM t_fa), p_del_cliente => true);

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, stato_doc_fiscale_id)
SELECT l.lotto_id, f.fattura_id, f.stato_doc_fiscale_id
  FROM t_l l, (SELECT fattura_id, stato_doc_fiscale_id FROM t_fa
               UNION ALL SELECT fattura_id, stato_doc_fiscale_id FROM t_fb) f;

-- A esce dalla bozza completa (indirizzi e intestazione dai building block,
-- come la pipeline); B va in errore: una segnalazione 'C' (il flag critical lo
-- accende il trigger vero).
SELECT vendite.fn_snapshot_indirizzi_fattura(fattura_id),
       vendite.fn_snapshot_intestazione_fattura(fattura_id)
  FROM t_fa;

INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta)
SELECT fattura_id, now(), 'pgTAP: documento in errore', 'C', FALSE,
       jsonb_build_object('task', 'pgtap_lotto_fermo', 'source', 'pgtap_lotto_fermo')
  FROM t_fb;

-- Il lotto avanza come nel giro: lotto e fatture nella stessa unita' di
-- lavoro, il controllo di coerenza a fine passo.
CREATE OR REPLACE FUNCTION pg_temp.porta_lotto(p_codice text) RETURNS void
LANGUAGE plpgsql AS $f$
BEGIN
    SET CONSTRAINTS ALL DEFERRED;
    PERFORM vendite.fn_lotto_proietta_stato_step(
        (SELECT lotto_id FROM t_l),
        (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno = p_codice));
    PERFORM vendite.fn_sync_lotto_fatture_stato(
        (SELECT lotto_id FROM t_l),
        (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno = p_codice));
    SET CONSTRAINTS ALL IMMEDIATE;
END $f$;

-- 1) La forma della fixture
SELECT is(
    (SELECT count(*)::text || ' ' || bool_or(f.critical)::text || ' ' || bool_and(s.fermo)::text
       FROM vendite.fatturazione_lotti_fatture lf
       JOIN vendite.fatture f ON f.id = lf.fattura_id
       JOIN vendite.vw_lotti_segnalazioni_summary s ON s.lotto_id = lf.lotto_id
      WHERE lf.lotto_id = (SELECT lotto_id FROM t_l)),
    '2 true true',
    '1) fixture: lotto in bozza con due fatture, una in errore; il lotto risulta FERMO'
);

SELECT pg_temp.porta_lotto('EMESSA');

-- 2-3) (a) Il lotto fermo non diventa definitivo
SELECT throws_like(
    $$SELECT pg_temp.porta_lotto('DEFINITIVA')$$,
    'Lotto bloccato per segnalazioni critiche o documenti in errore%',
    '2) (a) il lotto fermo non passa a DEFINITIVA'
);

SELECT ok(
    (SELECT count(*) = 1 FROM config.codici_errore c
      WHERE c.codice = 'E_PIPELINE_LOTTO_CRITICAL' AND c.obsoleto_dal IS NULL),
    '3) il codice e'' quello del runner (E_PIPELINE_LOTTO_CRITICAL), vivo: una regola, due punti di applicazione'
);

-- 4) Il passaggio non congelato e' passato; la fattura in errore e' rimasta indietro
SELECT is(
    (SELECT sl.codice_interno::text || ' ' || sa.codice_interno::text || ' ' || sb.codice_interno::text
       FROM vendite.fatturazione_lotti l
       JOIN config.stati_doc_fiscale sl ON sl.id = l.stato_doc_fiscale_id
      CROSS JOIN vendite.fatture fa JOIN config.stati_doc_fiscale sa ON sa.id = fa.stato_doc_fiscale_id
      CROSS JOIN vendite.fatture fb JOIN config.stati_doc_fiscale sb ON sb.id = fb.stato_doc_fiscale_id
      WHERE l.id = (SELECT lotto_id FROM t_l)
        AND fa.id = (SELECT fattura_id FROM t_fa)
        AND fb.id = (SELECT fattura_id FROM t_fb)),
    'EMESSA EMESSA DRAFT',
    '4) EMESSA (non congelato) resta ammesso: la sana avanza, quella in errore resta indietro'
);

-- 5) L'annullo di un lotto fermo resta ammesso (stato abortito). Un lotto a
--    parte, vuoto, fermato da una segnalazione critica di lotto.
CREATE TEMP TABLE t_l2 AS
SELECT * FROM dbops.fn_pgtap_crea_lotto(
    'lotto fermo da annullare', 'DRAFT', (SELECT billing_account_id FROM t_fa),
    p_gruppo_key_trattenuto => 'PGTAP-LOTTO-FERMO');

SELECT lives_ok(
    format($$SELECT * FROM vendite.fn_cambia_stato_lotto(%s, 'ANNULLATA')$$, (SELECT lotto_id FROM t_l2)),
    '5) l''annullo di un lotto fermo resta ammesso: lo stato abortito non e'' «definitivo»'
);

-- 6) Ritirata la segnalazione (il documento e' a posto) il lotto avanza.
--    B si completa come A, poi la sua segnalazione si ritira: e' la via
--    d'uscita di D-Q (correggere e rilanciare), l'altra e' estrarla dal lotto.
SELECT vendite.fn_snapshot_indirizzi_fattura(fattura_id),
       vendite.fn_snapshot_intestazione_fattura(fattura_id)
  FROM t_fb;
-- ⚠️ Ritiro e passaggio nella STESSA unita' di lavoro, come il rilancio dello
--   step: ritirata la segnalazione, B non e' piu' in errore e deve gia' stare
--   nello stato del lotto.
DO $rilancio$
BEGIN
    SET CONSTRAINTS ALL DEFERRED;
    UPDATE vendite.fatture_log l SET disabilitato = TRUE
     WHERE l.fattura_id = (SELECT fattura_id FROM t_fb)
       AND l.meta->>'task' = 'pgtap_lotto_fermo';
    PERFORM vendite.fn_sync_lotto_fatture_stato(
        (SELECT lotto_id FROM t_l),
        (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'EMESSA'));
    SET CONSTRAINTS ALL IMMEDIATE;
END $rilancio$;

SELECT lives_ok(
    $$SELECT pg_temp.porta_lotto('DEFINITIVA')$$,
    '6) ritirata la segnalazione, il lotto e le fatture arrivano a DEFINITIVA'
);

-- 7) (b) Una fattura in errore gia' definitiva non si aggancia a un lotto in bozza
CREATE TEMP TABLE t_fc AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('lotto fermo C', 'DEFINITIVA', (SELECT billing_account_id FROM t_fa));
INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta)
SELECT fattura_id, now(), 'pgTAP: documento in errore', 'C', FALSE,
       jsonb_build_object('task', 'pgtap_lotto_fermo', 'source', 'pgtap_lotto_fermo')
  FROM t_fc;
CREATE TEMP TABLE t_l3 AS
SELECT * FROM dbops.fn_pgtap_crea_lotto(
    'lotto in bozza', 'DRAFT', (SELECT billing_account_id FROM t_fa),
    (SELECT tipo_doc_fiscale_id FROM t_fa), p_del_cliente => true);

SELECT throws_like(
    format($$INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, stato_doc_fiscale_id)
             VALUES (%s, %s, %s)$$,
           (SELECT lotto_id FROM t_l3), (SELECT fattura_id FROM t_fc), (SELECT stato_doc_fiscale_id FROM t_fc)),
    '%stato fiscale diverso da quello del lotto%',
    '7) (b) una fattura in errore gia'' DEFINITIVA non si aggancia a un lotto in bozza: un definitivo non convive con un errore'
);

-- 8) (b) Una fattura in errore che resta indietro si aggancia: l'eccezione vale ancora
CREATE TEMP TABLE t_fd AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('lotto fermo D', 'DRAFT', (SELECT billing_account_id FROM t_fa));
INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta)
SELECT fattura_id, now(), 'pgTAP: documento in errore', 'C', FALSE,
       jsonb_build_object('task', 'pgtap_lotto_fermo', 'source', 'pgtap_lotto_fermo')
  FROM t_fd;
CREATE TEMP TABLE t_l4 AS
SELECT * FROM dbops.fn_pgtap_crea_lotto(
    'lotto emesso', 'EMESSA', (SELECT billing_account_id FROM t_fa),
    (SELECT tipo_doc_fiscale_id FROM t_fa), p_del_cliente => true);

SELECT lives_ok(
    format($$INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, stato_doc_fiscale_id)
             VALUES (%s, %s, %s)$$,
           (SELECT lotto_id FROM t_l4), (SELECT fattura_id FROM t_fd), (SELECT stato_doc_fiscale_id FROM t_fd)),
    '8) (b) una fattura in errore in bozza si aggancia a un lotto EMESSO: resta indietro, e'' ammesso'
);

SELECT * FROM finish();
ROLLBACK;
