-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU GPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: vendite.fn_create_contratto (piano analisi-fix-transazioni, #2)
--
-- Copre:
--   * happy senza utility : crea la testata (stato DRAFT) + numero, nessuna
--                           riga utility.
--   * happy con utility    : crea testata + riga contratti_utilities dal payload.
--   * ATOMICITA'           : se l'INSERT utility fallisce (classe_utenza
--                            inesistente), il contratto NON deve restare creato
--                            (nessun orfano). E' il cuore del fix.
--
-- Nota sul numero: `script.fn_generate_codice` usa una SEQUENCE (nextval), che
-- per definizione NON fa rollback. Quindi un fallimento lascia un "buco" nella
-- numerazione (gap innocuo, gia' cosi' prima del fix). Il fix elimina il danno
-- reale — il contratto orfano — non il gap di sequenza: il test verifica quello.
--
-- Riusa un billing_account esistente SENZA precontrattuali (per non far scattare
-- lo snapshot automatico trgfn_contratti_snapshot_precontrattuali). Idempotente:
-- BEGIN ... ROLLBACK.
-- ------------------------------------------------------------

BEGIN;

SELECT plan(9);

-- =========================================================
-- Precondizione: BA senza precontrattuali (con emittente)
-- =========================================================
-- BA senza precontrattuali e con emittente fiscale risolvibile (efba): passiamo
-- l'emittente esplicito nel payload perche' in sessione pgTAP la GUC e' vuota
-- (il trigger default_emittente richiede l'emittente esplicito senza GUC; il
-- guard_emittente_scope invece fa skip con GUC vuota).
CREATE TEMP TABLE tmp_ba AS
SELECT ba.id AS billing_account_id, ba.istanza_utility_id, ba.utility_id,
       ef.id AS emittente_fiscale_id
FROM anagrafiche.billing_account ba
JOIN anagrafiche.emittenti_fiscali_billing_account efba
       ON efba.billing_account_id = ba.id
JOIN anagrafiche.emittenti_fiscali ef
       ON ef.soggetto_ruolo_id = efba.emittente_soggetto_ruolo_id
LEFT JOIN anagrafiche.istanze_dati_precontrattuali idp
       ON idp.istanza_utility_id = ba.istanza_utility_id
      AND idp.utility_id = ba.utility_id
WHERE idp.id IS NULL
ORDER BY ba.id
LIMIT 1;

SELECT is((SELECT count(*)::int FROM tmp_ba), 1,
          'Precondizione: esiste un billing_account senza precontrattuali con emittente');

-- =========================================================
-- HAPPY senza utility
-- =========================================================
CREATE TEMP TABLE r1 AS
SELECT * FROM vendite.fn_create_contratto(
    jsonb_build_object(
        'billing_account_id',  (SELECT billing_account_id FROM tmp_ba),
        'emittente_fiscale_id',(SELECT emittente_fiscale_id FROM tmp_ba),
        'istanza_utility_id',  (SELECT istanza_utility_id FROM tmp_ba),
        'utility_id',          (SELECT utility_id FROM tmp_ba)
    ),
    NULL
);

SELECT ok((SELECT contratto_id FROM r1) IS NOT NULL,
          'Happy no-utility: contratto_id ritornato non nullo');

SELECT is(
    (SELECT sd.codice_interno
       FROM vendite.contratti c
       JOIN config.stati_doc_contratti sd ON sd.id = c.stato_doc_contratto_id
      WHERE c.id = (SELECT contratto_id FROM r1)),
    'DRAFT',
    'Happy no-utility: contratto creato in stato DRAFT');

SELECT is(
    (SELECT c.numero FROM vendite.contratti c WHERE c.id = (SELECT contratto_id FROM r1)),
    (SELECT numero FROM r1),
    'Happy no-utility: numero ritornato = numero persistito');

SELECT is(
    (SELECT count(*)::int FROM vendite.contratti_utilities
      WHERE contratto_id = (SELECT contratto_id FROM r1)),
    0,
    'Happy no-utility: nessuna riga contratti_utilities');

-- =========================================================
-- HAPPY con utility
-- =========================================================
CREATE TEMP TABLE r2 AS
SELECT * FROM vendite.fn_create_contratto(
    jsonb_build_object(
        'billing_account_id',  (SELECT billing_account_id FROM tmp_ba),
        'emittente_fiscale_id',(SELECT emittente_fiscale_id FROM tmp_ba),
        'istanza_utility_id',  (SELECT istanza_utility_id FROM tmp_ba),
        'utility_id',          (SELECT utility_id FROM tmp_ba)
    ),
    -- utility 'BASE' non ammette dimensione tipo/classe: usiamo un campo libero
    jsonb_build_object(
        'istanza_utility_id', (SELECT istanza_utility_id FROM tmp_ba),
        'utility_id',         (SELECT utility_id FROM tmp_ba),
        'param_2_txt',        'PGTAP2'
    )
);

SELECT ok((SELECT contratto_id FROM r2) IS NOT NULL,
          'Happy con-utility: contratto_id ritornato non nullo');

SELECT is(
    (SELECT param_2_txt FROM vendite.contratti_utilities
      WHERE contratto_id = (SELECT contratto_id FROM r2)),
    'PGTAP2',
    'Happy con-utility: riga contratti_utilities creata con param_2_txt');

-- =========================================================
-- ATOMICITA': INSERT utility invalido (classe non ammessa per questa utility)
-- => l'intera fn fallisce e NON deve restare alcun contratto orfano.
-- =========================================================
CREATE TEMP TABLE tmp_cnt_before AS
SELECT count(*)::int AS n FROM vendite.contratti
 WHERE billing_account_id = (SELECT billing_account_id FROM tmp_ba);

SELECT throws_ok(
    $$ SELECT * FROM vendite.fn_create_contratto(
           jsonb_build_object(
               'billing_account_id',  (SELECT billing_account_id FROM tmp_ba),
               'emittente_fiscale_id',(SELECT emittente_fiscale_id FROM tmp_ba),
               'istanza_utility_id',  (SELECT istanza_utility_id FROM tmp_ba),
               'utility_id',          (SELECT utility_id FROM tmp_ba)),
           jsonb_build_object(
               'istanza_utility_id', (SELECT istanza_utility_id FROM tmp_ba),
               'utility_id',         (SELECT utility_id FROM tmp_ba),
               'classe_utenza_id',   999999)) $$,
    NULL::text,
    NULL::text,
    'Atomicita'': INSERT utility invalido fa fallire l''intera chiamata');

SELECT is(
    (SELECT count(*)::int FROM vendite.contratti
      WHERE billing_account_id = (SELECT billing_account_id FROM tmp_ba)),
    (SELECT n FROM tmp_cnt_before),
    'Atomicita'': nessun contratto orfano creato (INSERT testata annullato)');

SELECT * FROM finish();

ROLLBACK;
