-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_preventivo — il BB del preventivo
-- Riferimento: brief-db-fixture-rls-documenti-costruiti (giro 2).
-- rev 2026-10-25 (brief-modello-documento-vendita §8, giro 6): l'emissione
--   chiede almeno una riga attiva (E_PREV_NESSUNA_RIGA_ATTIVA, ora nel guard
--   di transizione) e lo stato passa dal verbo sotto la porta. Il builder resta
--   SENZA righe: uno stato oltre la bozza si chiede a
--   dbops.fn_pgtap_crea_preventivo_con_righe (test 5, che costruisce anche il
--   preventivo della seconda chiamata del test 6), e chiederlo a questo builder
--   si ferma sull'emissione (test 6b, nuovo). Il parametro di stato di QUESTO
--   builder resta provato su uno stato che non chiede righe (test 5b, nuovo:
--   ANNULLATO, dalla bozza). Prima il test 5 chiedeva EMESSO a un preventivo
--   senza righe, uno stato che il modello non ammette. Plan 7 -> 9.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - costruisce il mondo e la testata, e la testata e' SCRIVIBILE: e' la
--     prova che i guard del dominio la accettano;
--   - l'emittente e' quello che il billing account pretende, l'istanza e la
--     utility sono quelle del billing account;
--   - il numero lo assegna il dominio, non la fixture;
--   - lo stato si sceglie alla nascita, e uno inesistente parla; uno oltre la
--     bozza chiede righe: il builder senza righe si ferma sull'emissione, e lo
--     costruisce dbops.fn_pgtap_crea_preventivo_con_righe;
--   - una seconda chiamata riusa l'azienda di chi agisce, con un cliente nuovo.
--
-- Elenco test (plan 9):
--   1) la funzione esiste con la firma dichiarata
--   2) la testata esiste, col billing account e l'istanza tornati
--   3) l'emittente e' quello del billing account (il guard emittente/BA)
--   4) numero assegnato dal dominio, validita' aperta da oggi
--   5) stato: quello chiesto alla nascita (EMESSO, non il default), dal
--      builder con le righe
--   5b) stato chiesto a questo builder, senza righe: ANNULLATO (dalla bozza)
--   6) seconda chiamata: stessa azienda, cliente nuovo
--   6b) senza righe EMESSO non si raggiunge: si ferma sull'emissione
--   7) guard: uno stato che non esiste parla invece di scrivere NULL
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre la funzione esaminata, che qui
--   viene chiamata come la chiamera' un file su un database ricostruito: senza
--   nessuna veste in sessione. Aprirlo prima nasconderebbe meta' del contratto.

SELECT plan(9);

-- 1) La firma
SELECT has_function(
    'dbops', 'fn_pgtap_crea_preventivo',
    ARRAY['text', 'character varying'],
    'dbops.fn_pgtap_crea_preventivo(text, character varying) esiste con la firma dichiarata'
);

-- Fixture: il primo preventivo, dal nulla
CREATE TEMP TABLE t_p1 AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('presidio preventivo 1');

-- 2) La testata c'e', ed e' quella tornata
SELECT is(
    (SELECT p.billing_account_id::text || '/' || p.istanza_utility_id::text
            || '/' || p.utility_id::text
       FROM vendite.preventivi p
      WHERE p.id = (SELECT preventivo_id FROM t_p1)),
    (SELECT billing_account_id::text || '/' || istanza_utility_id::text
            || '/' || utility_id::text FROM t_p1),
    'la testata esiste e porta billing account, istanza e utility tornati dalla funzione'
);

-- 3) L'emittente e' quello che il billing account pretende
SELECT is(
    (SELECT p.emittente_fiscale_id FROM vendite.preventivi p
      WHERE p.id = (SELECT preventivo_id FROM t_p1)),
    anagrafiche.fn_get_emittente_fiscale_pk((SELECT billing_account_id FROM t_p1)),
    'l''emittente della testata e'' quello del billing account (trgfn_preventivi_guard_emittente_ba)'
);

-- 4) Numero dal dominio, validita' da oggi
SELECT ok(
    (SELECT p.numero IS NOT NULL AND p.validita_dal = script.fn_data_operativa()
            AND p.validita_al > p.validita_dal
       FROM vendite.preventivi p WHERE p.id = (SELECT preventivo_id FROM t_p1)),
    'il numero lo assegna il dominio (trgfn_preventivi_gen_codice); validita'' aperta da oggi'
);

-- 5) Lo stato si sceglie alla nascita
-- ⭐ rev 2026-10-25 (giro 6): oltre la bozza serve una riga attiva, e la
--   scrive il builder gemello; la testata la costruisce comunque
--   dbops.fn_pgtap_crea_preventivo, che resta il soggetto del test 6.
CREATE TEMP TABLE t_em AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo_con_righe('presidio preventivo emesso', 'EMESSO');

SELECT is(
    (SELECT s.codice_interno
       FROM vendite.preventivi p
       JOIN config.stati_doc_preventivi s ON s.id = p.stato_doc_preventivo_id
      WHERE p.id = (SELECT preventivo_id FROM t_em)),
    'EMESSO'::character varying,
    'lo stato e'' quello chiesto alla nascita, non il default'
);

-- 5b) Il parametro di stato di questo builder, su uno stato che non chiede
--   righe: l'annullo esce direttamente dalla bozza.
CREATE TEMP TABLE t_ann AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('presidio preventivo annullato', 'ANNULLATO');

SELECT is(
    (SELECT s.codice_interno
       FROM vendite.preventivi p
       JOIN config.stati_doc_preventivi s ON s.id = p.stato_doc_preventivo_id
      WHERE p.id = (SELECT preventivo_id FROM t_ann)),
    'ANNULLATO'::character varying,
    'senza righe, il builder porta allo stato chiesto quando la strada non chiede righe (ANNULLATO)'
);

-- 6) Seconda chiamata: il contesto e' ormai aperto, l'azienda si riusa
SELECT is(
    (SELECT (e.emittente_fiscale_id = p1.emittente_fiscale_id)::text
         || ' ' || (e.billing_account_id <> p1.billing_account_id)::text
       FROM t_p1 p1, t_em e),
    'true true',
    'seconda chiamata: stessa azienda di chi agisce, cliente nuovo'
);

-- 6b) Senza righe, uno stato oltre la bozza non si raggiunge: l'emissione
--   chiede almeno una riga attiva (guard di transizione), e il builder non ne
--   scrive. E' il motivo per cui esiste fn_pgtap_crea_preventivo_con_righe.
SELECT throws_like($$
    SELECT dbops.fn_pgtap_crea_preventivo('presidio emesso senza righe', 'EMESSO')
$$,
    '%senza righe attive%',
    'senza righe EMESSO non si raggiunge: si ferma sull''emissione (E_PREV_NESSUNA_RIGA_ATTIVA)'
);

-- 7) Guard: uno stato che non esiste
SELECT throws_like($$
    SELECT dbops.fn_pgtap_crea_preventivo('presidio stato', 'NON_ESISTE')
$$,
    '%nessuno stato documento preventivo%',
    'guard: uno stato inesistente parla, invece di scrivere un NULL nella testata'
);

SELECT * FROM finish();
ROLLBACK;
