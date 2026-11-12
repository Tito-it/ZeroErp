-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il vocabolario fiscale dice a chi si applica uno stato e da dove il
--   documento e' congelato; guard e check di fattura e lotto lo leggono da li'.
--   ChangeSet: 20261112-48 (guard della fattura), -49 (guard del lotto), -50
--   (script.fn_check_lotto_fatture_pre_fiscali), -51
--   (vendite.trgfn_fatture_guard_uscita_draft), -52
--   (vendite.fn_imposta_data_documento_lotto).
--   Brief: brief-db-stati-documento-dal-vocabolario §4.5 (S-7) e §4.1 (S-2),
--   giro 1.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - a ogni cambio di stato, la DESTINAZIONE deve applicarsi al documento:
--     applica_fattura per la fattura, applica_lotto per il lotto; altrimenti
--     E_LOTTO_PARAMETRO_NON_COERENTE, prima della matrice;
--   - «pre-fiscale» e' uno stato con congela_fiscale = false, letto dal
--     vocabolario: spostata la marca, la risposta segue;
--   - i corpi che leggono questi significati non nominano i codici DRAFT ed
--     EMESSA (presidio sulla FORMA, dichiarato tale), tranne il cancello IVA
--     del guard della fattura, che nomina EMESSA per scelta: il vocabolario
--     fiscale non ha la colonna emissione, che e' il verbo «Emetti» e la
--     fattura non passa da li' (decisione R-1 del brief). Il test 8 tiene
--     l'eccezione a UN punto solo.
--
-- ⭐ OGNI RIFIUTO HA IL SUO CONTRASTO: lo stesso passaggio, con la colonna
--   rimessa a posto, passa. Un guard che rifiutasse sempre sarebbe verde sul
--   solo rifiuto.
-- ⭐ I CASI SI COSTRUISCONO: fattura e lotto dai builder, le marche spostate
--   in transazione sul vocabolario. Nessuno skip.
--
-- Elenco test (plan 8):
--   1) fattura: lo stato d'arrivo con applica_fattura = false -> rifiutato
--   2) fattura: lo stesso passaggio con applica_fattura = true -> passa
--   3) lotto: lo stato d'arrivo con applica_lotto = false -> rifiutato
--   4) lotto: lo stesso passaggio con applica_lotto = true -> passa
--   5) pre-fiscale: un lotto con una fattura in bozza -> nessun motivo
--   6) ⭐ la marca spostata: congela_fiscale = true sulla bozza -> il motivo
--      E_LOTTO_FATTURE_NON_PRE_FISCALI
--   7) forma: i quattro corpi non nominano DRAFT ne' EMESSA
--   8) forma: il guard della fattura nomina EMESSA solo per il cancello IVA
--      (eccezione voluta, non debito)
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- ============================================================
-- Fixture: una fattura EMESSA e un lotto in bozza, dello stesso cliente
-- ============================================================
-- ⚠️ La fattura nasce EMESSA dal builder: il passaggio provato (EMESSA ->
--   INVIATA) non esce dalla bozza, cosi' il guard dell'uscita dalla bozza
--   (che viene dopo) non si mette in mezzo al contrasto del test 2.
CREATE TEMP TABLE t_fattura AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('stato fiscale dal vocabolario', 'EMESSA');

CREATE TEMP TABLE t_lotto AS
SELECT * FROM dbops.fn_pgtap_crea_lotto(
    'stato fiscale dal vocabolario', 'DRAFT',
    (SELECT f.billing_account_id FROM t_fattura f));

-- ============================================================
-- 1-2) La fattura: applica_fattura sulla destinazione
-- ============================================================
-- In transazione INVIATA smette di applicarsi alla fattura. INVIATA non e' lo
-- stato iniziale, quindi il CHECK chk_stati_doc_fiscale_iniziale_applica lo
-- ammette.
UPDATE config.stati_doc_fiscale SET applica_fattura = false WHERE codice_interno = 'INVIATA';

SELECT throws_like(
    $$SELECT dbops.fn_pgtap_porta_a_stato('vendite.fatture',
                                          (SELECT fattura_id FROM t_fattura), 'INVIATA')$$,
    '%stato non applicabile a fattura%',
    '1. fattura: uno stato d''arrivo che non si applica alla fattura e'' rifiutato'
);

UPDATE config.stati_doc_fiscale SET applica_fattura = true WHERE codice_interno = 'INVIATA';

SELECT lives_ok(
    $$SELECT dbops.fn_pgtap_porta_a_stato('vendite.fatture',
                                          (SELECT fattura_id FROM t_fattura), 'INVIATA')$$,
    '2. fattura: lo stesso passaggio, con applica_fattura = true, passa'
);

-- ============================================================
-- 3-4) Il lotto: applica_lotto sulla destinazione
-- ============================================================
-- Un secondo lotto, vuoto: il primo serve al test 5 con la sua fattura.
CREATE TEMP TABLE t_lotto_vuoto AS
SELECT * FROM dbops.fn_pgtap_crea_lotto(
    'stato fiscale dal vocabolario, vuoto', 'DRAFT',
    (SELECT f.billing_account_id FROM t_fattura f));

UPDATE config.stati_doc_fiscale SET applica_lotto = false WHERE codice_interno = 'EMESSA';

SELECT throws_like(
    $$SELECT dbops.fn_pgtap_porta_a_stato('vendite.fatturazione_lotti',
                                          (SELECT lotto_id FROM t_lotto_vuoto), 'EMESSA')$$,
    '%stato non applicabile a lotto%',
    '3. lotto: uno stato d''arrivo che non si applica al lotto e'' rifiutato'
);

UPDATE config.stati_doc_fiscale SET applica_lotto = true WHERE codice_interno = 'EMESSA';

SELECT lives_ok(
    $$SELECT dbops.fn_pgtap_porta_a_stato('vendite.fatturazione_lotti',
                                          (SELECT lotto_id FROM t_lotto_vuoto), 'EMESSA')$$,
    '4. lotto: lo stesso passaggio, con applica_lotto = true, passa'
);

-- ============================================================
-- 5-6) Pre-fiscale = non congelato, dal vocabolario
-- ============================================================
-- Una fattura in bozza nel lotto in bozza: la prima e' gia' INVIATA.
CREATE TEMP TABLE t_fattura_bozza AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
    'stato fiscale dal vocabolario, bozza', 'DRAFT',
    (SELECT f.billing_account_id FROM t_fattura f));

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id)
SELECT l.lotto_id, f.fattura_id FROM t_lotto l, t_fattura_bozza f;

SELECT is(
    script.fn_check_lotto_fatture_pre_fiscali((SELECT lotto_id FROM t_lotto)),
    '[]'::jsonb,
    '5. pre-fiscale: una fattura in bozza nel lotto non da'' motivi'
);

-- ⭐ La marca spostata: la bozza diventa «congelata». Se la check ricordasse
--   i codici DRAFT ed EMESSA, la risposta resterebbe [].
UPDATE config.stati_doc_fiscale SET congela_fiscale = true WHERE iniziale;

SELECT is(
    (SELECT m ->> 'codice'
       FROM jsonb_array_elements(
                script.fn_check_lotto_fatture_pre_fiscali((SELECT lotto_id FROM t_lotto))) m),
    'E_LOTTO_FATTURE_NON_PRE_FISCALI',
    '6. con congela_fiscale = true sulla bozza, la stessa fattura non e'' piu'' pre-fiscale'
);

-- ============================================================
-- 7-8) La forma dei corpi — presidio sulla FORMA, dichiarato tale
-- ============================================================
-- ⚠️ Prova che i codici non sono scritti nei corpi (commenti tolti), non che
--   il comportamento sia giusto: quello lo provano i test 1-6.
SELECT is(
    (SELECT array_agg(p.oid::regprocedure::text ORDER BY p.oid::regprocedure::text)
       FROM pg_proc p
      WHERE p.oid IN ('vendite.trgfn_fatturazione_lotti_guard_stato()'::regprocedure,
                      'script.fn_check_lotto_fatture_pre_fiscali(bigint)'::regprocedure,
                      'vendite.trgfn_fatture_guard_uscita_draft()'::regprocedure,
                      'vendite.fn_imposta_data_documento_lotto(bigint,date)'::regprocedure)
        AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ '''(DRAFT|EMESSA)'''),
    NULL::text[],
    '7. forma: guard del lotto, pre-fiscale, uscita dalla bozza e data del lotto non nominano DRAFT ne'' EMESSA'
);

SELECT is(
    (SELECT (SELECT count(*)::int
               FROM regexp_matches(regexp_replace(p.prosrc, '--[^\n]*', '', 'g'),
                                   '''(DRAFT|EMESSA)''', 'g'))
       FROM pg_proc p
      WHERE p.oid = 'vendite.trgfn_fatture_guard_stato()'::regprocedure),
    1,
    '8. forma: il guard della fattura nomina un solo codice, EMESSA del cancello IVA (eccezione voluta, R-1)'
);

SELECT * FROM finish();
ROLLBACK;
