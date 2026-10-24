-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_commessa — il BB della commessa
-- Riferimento: brief-db-fixture-rls-documenti-costruiti (giro 3).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - costruisce il mondo e apre la commessa con la MADRE del dominio
--     (vendite.fn_get_or_create_commessa): codice ed emittente li decide lei;
--   - l'emittente e' quello del billing account;
--   - la competenza e' il mese corrente;
--   - una seconda chiamata riusa l'azienda di chi agisce, con un cliente nuovo;
--   - rev 2026-10-24 (20261024-26, brief-modello-documento-vendita Q-2): lo
--     stato chiesto si raggiunge per la matrice, sul billing account del test,
--     con l'attivita' che l'uscita dalla bozza pretende;
--   - rev 2026-10-24 (20261024-32, R-3): a richiesta scrive la sorgente ROOT.
--
-- Elenco test (plan 13):
--   1) la funzione esiste con la firma dichiarata
--   2) la commessa esiste, col codice e il billing account tornati
--   3) l'emittente e' quello del billing account
--   4) la competenza e' il mese corrente
--   5) il codice l'ha assegnato il dominio (non vuoto)
--   6) seconda chiamata: stessa azienda, cliente nuovo
--   7) senza stato: resta nello stato iniziale, senza attivita'
--   8) PRONTA_FATTURAZIONE sul BA chiesto: stato raggiunto, stesso cliente
--   9) ...con UN'attivita' APPROVATA e NON_EMESSA, quella tornata
--  10) p_con_attivita => false: l'uscita senza lavoro la ferma il guard vero
--  11) uno stato che non c'e' solleva, nominando il builder
--  12) senza richiesta nessuna sorgente ROOT
--  13) p_con_sorgente_root: UNA riga ROOT, sorgente COMMESSA, chiave l'id
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre la funzione esaminata, che qui
--   viene chiamata come la chiamera' un file su un database ricostruito: senza
--   nessuna veste in sessione. Aprirlo prima nasconderebbe meta' del contratto.

SELECT plan(13);

-- 1) La firma
SELECT has_function(
    'dbops', 'fn_pgtap_crea_commessa',
    ARRAY['text', 'character varying', 'bigint', 'boolean', 'boolean'],
    'dbops.fn_pgtap_crea_commessa(text, character varying, bigint, boolean, boolean) esiste con la firma dichiarata'
);

-- Fixture: la prima commessa, dal nulla
CREATE TEMP TABLE t_c1 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('presidio commessa 1');

-- 2) La commessa c'e', ed e' quella tornata
SELECT is(
    (SELECT c.codice::text || '/' || c.billing_account_id::text
       FROM vendite.commesse c
      WHERE c.id = (SELECT commessa_id FROM t_c1)),
    (SELECT commessa_codice::text || '/' || billing_account_id::text FROM t_c1),
    'la commessa esiste e porta il codice e il billing account tornati dalla funzione'
);

-- 3) L'emittente e' quello del billing account
SELECT is(
    (SELECT c.emittente_soggetto_ruolo_id FROM vendite.commesse c
      WHERE c.id = (SELECT commessa_id FROM t_c1)),
    anagrafiche.fn_get_emittente_fiscale_id((SELECT billing_account_id FROM t_c1)),
    'l''emittente della commessa e'' quello del billing account'
);

-- 4) La competenza e' il mese corrente
SELECT is(
    (SELECT c.competenza_dal::text || '/' || c.competenza_al::text
       FROM vendite.commesse c WHERE c.id = (SELECT commessa_id FROM t_c1)),
    date_trunc('month', script.fn_data_operativa())::date::text || '/'
        || (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date::text,
    'la competenza e'' il mese corrente: le attivita'' del builder gemello ci cadono dentro'
);

-- 5) Il codice dal dominio
SELECT ok(
    (SELECT btrim(commessa_codice) <> '' FROM t_c1),
    'il codice l''ha assegnato la madre (vendite.fn_get_or_create_commessa), non la fixture'
);

-- 6) Seconda chiamata: il contesto e' ormai aperto, l'azienda si riusa
CREATE TEMP TABLE t_c2 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('presidio commessa 2');

SELECT is(
    (SELECT (c2.emittente_fiscale_id = c1.emittente_fiscale_id)::text
         || ' ' || (c2.billing_account_id <> c1.billing_account_id)::text
         || ' ' || (c2.commessa_id <> c1.commessa_id)::text
       FROM t_c1 c1, t_c2 c2),
    'true true true',
    'seconda chiamata: stessa azienda di chi agisce, cliente nuovo, commessa nuova'
);

-- 7) Senza stato: come prima, nello stato iniziale e senza lavoro
SELECT is(
    (SELECT (c.stato_commessa_id = script.fn_stato_iniziale_id('vendite.stati_commessa'::regclass))::text
         || ' ' || (t.attivita_id IS NULL)::text
         || ' ' || (SELECT count(*) FROM vendite.commesse_attivita ca WHERE ca.commessa_id = c.id)::text
       FROM t_c1 t JOIN vendite.commesse c ON c.id = t.commessa_id),
    'true true 0',
    'senza stato la commessa resta nello stato iniziale, senza attivita'''
);

-- Fixture: una commessa emittibile del cliente della prima
CREATE TEMP TABLE t_c3 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa(
    'presidio commessa 3', 'PRONTA_FATTURAZIONE', (SELECT billing_account_id FROM t_c1));

-- 8) Lo stato raggiunto, sul cliente chiesto
SELECT is(
    (SELECT s.codice_interno::text || ' ' || (c.billing_account_id = t1.billing_account_id)::text
            || ' ' || (t.stato_commessa_id = c.stato_commessa_id)::text
       FROM t_c3 t
       JOIN vendite.commesse c ON c.id = t.commessa_id
       JOIN vendite.stati_commessa s ON s.id = c.stato_commessa_id
      CROSS JOIN t_c1 t1),
    'PRONTA_FATTURAZIONE true true',
    'PRONTA_FATTURAZIONE raggiunta per la matrice, sul billing account chiesto, e lo stato tornato e'' quello vero'
);

-- 9) Il lavoro che l'uscita dalla bozza pretende: uno, ed e' quello tornato
SELECT is(
    (SELECT count(*)::text || ' ' || bool_and(ca.id = t.attivita_id)::text
            || ' ' || bool_and(ca.stato_approvazione = 'APPROVATA' AND ca.stato_emissione = 'NON_EMESSA')::text
       FROM t_c3 t JOIN vendite.commesse_attivita ca ON ca.commessa_id = t.commessa_id),
    '1 true true',
    'fuori bozza la commessa ha UN''attivita'' APPROVATA e NON_EMESSA, quella tornata dal builder'
);

-- 10) Senza lavoro l'uscita non passa: lo dice il guard di transizione
SELECT throws_like(
    $$SELECT * FROM dbops.fn_pgtap_crea_commessa('presidio commessa 4', 'PRONTA_FATTURAZIONE', NULL, false)$$,
    '%senza almeno una riga approvata%',
    'p_con_attivita => false: PRONTA_FATTURAZIONE senza righe la ferma il guard vero, non il builder'
);

-- 11) Uno stato che non c'e'
SELECT throws_like(
    $$SELECT * FROM dbops.fn_pgtap_crea_commessa('presidio commessa 5', 'NON_ESISTE')$$,
    'fn_pgtap_crea_commessa: nessuno stato di commessa attivo%',
    'uno stato che non c''e'' solleva prima di costruire, nominando il builder'
);

-- 12) Senza richiesta, nessuna sorgente ROOT (la madre non la scrive)
SELECT is(
    (SELECT count(*)::int FROM vendite.commesse_sorgenti cs
      WHERE cs.commessa_id = (SELECT commessa_id FROM t_c3) AND cs.ruolo_link = 'ROOT'),
    0,
    'senza p_con_sorgente_root la commessa non ha una sorgente ROOT'
);

-- 13) La sorgente ROOT a richiesta
CREATE TEMP TABLE t_c6 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa(
    'presidio commessa 6', 'PRONTA_FATTURAZIONE', (SELECT billing_account_id FROM t_c1),
    p_con_sorgente_root => true);

SELECT is(
    (SELECT count(*)::text || ' ' || bool_and(s.codice_interno = 'COMMESSA')::text
            || ' ' || bool_and(cs.sorgente_uid = t.commessa_id::text)::text
       FROM t_c6 t
       JOIN vendite.commesse_sorgenti cs ON cs.commessa_id = t.commessa_id AND cs.ruolo_link = 'ROOT'
       JOIN config.sorgenti s ON s.id = cs.sorgente_tipo_id),
    '1 true true',
    'p_con_sorgente_root: UNA sorgente ROOT, di tipo COMMESSA, con chiave l''id della commessa'
);

SELECT * FROM finish();
ROLLBACK;
