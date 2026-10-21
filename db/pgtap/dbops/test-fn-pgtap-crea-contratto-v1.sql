-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_contratto — il builder del contratto
-- Riferimento: richiesta BE del 2026-10-21 (R-1, smoke-group-attivita-
--   contratto); stati ammessi: decisione di Tid D-2 dello stesso giorno.
--   changeSet 20261021-69.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - costruisce il mondo (azienda, operatore, cliente) e il contratto nasce
--     dalla MADRE di produzione vendite.fn_create_contratto: numero, emittente
--     di chi agisce, il BA del mondo;
--   - lo stato si raggiunge per la strada dell'applicazione: ATTIVO (con un
--     listino del mondo, perche' un contratto si attiva su un listino),
--     ANNULLATO (dal verbo); DRAFT resta senza listino;
--   - il terzo parametro riusa un cliente gia' costruito e RIFIUTA un billing
--     account di un'altra azienda;
--   - CESSATO, e ogni altro codice, non si costruiscono: parlano prima di
--     scrivere.
--
-- Elenco test (plan 8):
--   1) la funzione esiste con la firma dichiarata
--   2) ATTIVO dal nulla: testata ATTIVO, con numero, BA ed emittente tornati
--   3) ATTIVO: il contratto ha un listino dell'azienda di chi agisce, e la
--      versione congelata all'attivazione
--   4) terzo parametro, DRAFT: stesso cliente, contratto nuovo, nessun listino
--   5) terzo parametro, ANNULLATO: lo stato e' quello del verbo
--   6) senza terzo parametro: cliente nuovo, stessa azienda
--   7) guard: un BA di un'altra azienda parla
--   8) guard: CESSATO non si costruisce
--
-- ⚠️ La fixture apre il contesto chiamando il BB: qui si usa il BB come lo
--   usera' un file vero — prima chiamata senza contesto, come in CI.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre la funzione esaminata, che qui
--   viene chiamata come la chiamera' un file su un database ricostruito: senza
--   nessuna veste in sessione. Aprirlo prima nasconderebbe meta' del contratto.

SELECT plan(8);

-- ============================================================
-- 1) La firma
-- ============================================================
SELECT has_function(
    'dbops', 'fn_pgtap_crea_contratto',
    ARRAY['text', 'character varying', 'bigint'],
    'dbops.fn_pgtap_crea_contratto(text, character varying, bigint) esiste con la firma dichiarata'
);

-- ============================================================
-- Fixture: un'altra azienda, PRIMA del contesto (una seconda azienda si
-- costruisce coi builder atomici, prima del contesto). Il suo CLIENTE no:
-- sotto la RLS un billing account lo scrive solo chi lavora in quell'azienda,
-- quindi nasce col contesto su di lei, subito prima del test 7.
-- ============================================================
CREATE TEMP TABLE t_altrui AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Il primo contratto, dal nulla: apre il contesto sull'azienda del mondo.
CREATE TEMP TABLE t_k1 AS
SELECT * FROM dbops.fn_pgtap_crea_contratto('presidio contratto 1', 'ATTIVO');

-- ============================================================
-- 2) ATTIVO dal nulla
-- ============================================================
SELECT is(
    (SELECT s.codice_interno::text
         || ' ' || (k.numero = t.numero)::text
         || ' ' || (k.billing_account_id = t.billing_account_id)::text
         || ' ' || (k.emittente_fiscale_id = t.emittente_fiscale_id)::text
       FROM t_k1 t
       JOIN vendite.contratti k ON k.id = t.contratto_id
       JOIN config.stati_doc_contratti s ON s.id = k.stato_doc_contratto_id),
    'ATTIVO true true true',
    '2) ATTIVO: la testata porta lo stato, il numero, il BA e l''emittente tornati'
);

-- ============================================================
-- 3) ATTIVO: il listino del mondo
-- ============================================================
-- ⚠️ Un contratto si attiva su un listino con una versione attiva, o con una
--   riga AGGIUNTA con prezzo (trgfn_contratti_freeze_listino_versione): il
--   builder da' il listino, le righe restano al test.
SELECT is(
    (SELECT (l.emittente_soggetto_ruolo_id = t.emittente_soggetto_ruolo_id)::text
         || ' ' || (k.listino_versione_id IS NOT NULL)::text
       FROM t_k1 t
       JOIN vendite.contratti k ON k.id = t.contratto_id
       JOIN vendite.listini l ON l.id = k.listino_id),
    'true true',
    '3) ATTIVO: listino dell''azienda di chi agisce, versione congelata all''attivazione'
);

-- ============================================================
-- 4-5) Il terzo parametro: lo STESSO cliente
-- ============================================================
CREATE TEMP TABLE t_k2 AS
SELECT * FROM dbops.fn_pgtap_crea_contratto(
                 'presidio contratto 2', 'DRAFT',
                 (SELECT billing_account_id FROM t_k1));

SELECT is(
    (SELECT (k2.billing_account_id = k1.billing_account_id)::text
         || ' ' || (k2.contratto_id <> k1.contratto_id)::text
         || ' ' || s.codice_interno::text
         || ' ' || (k.listino_id IS NULL)::text
       FROM t_k1 k1, t_k2 k2
       JOIN vendite.contratti k ON k.id = k2.contratto_id
       JOIN config.stati_doc_contratti s ON s.id = k.stato_doc_contratto_id),
    'true true DRAFT true',
    '4) col terzo parametro, DRAFT: stesso cliente, contratto nuovo, nessun listino'
);

CREATE TEMP TABLE t_k3 AS
SELECT * FROM dbops.fn_pgtap_crea_contratto(
                 'presidio contratto 3', 'ANNULLATO',
                 (SELECT billing_account_id FROM t_k1));

SELECT is(
    (SELECT s.codice_interno::text
       FROM vendite.contratti k
       JOIN config.stati_doc_contratti s ON s.id = k.stato_doc_contratto_id
      WHERE k.id = (SELECT contratto_id FROM t_k3)),
    'ANNULLATO',
    '5) ANNULLATO: lo stato e'' quello del verbo vendite.fn_annulla_contratto'
);

-- ============================================================
-- 6) Senza terzo parametro: cliente nuovo, stessa azienda
-- ============================================================
CREATE TEMP TABLE t_k4 AS
SELECT * FROM dbops.fn_pgtap_crea_contratto('presidio contratto 4');

SELECT is(
    (SELECT (k4.billing_account_id <> k1.billing_account_id)::text
         || ' ' || (k4.emittente_soggetto_ruolo_id = k1.emittente_soggetto_ruolo_id)::text
       FROM t_k1 k1, t_k4 k4),
    'true true',
    '6) senza terzo parametro: un cliente nuovo, ma dentro la stessa azienda'
);

-- ============================================================
-- 7-8) I guard
-- ============================================================
-- Il cliente dell'altra azienda lo crea l'altra azienda: il legame lo scrive
-- il trigger z90 verso chi agisce. Poi il contesto torna sull'operatore del
-- mondo, che e' chi chiede il contratto.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM t_altrui));
END $ctx$;

CREATE TEMP TABLE t_ba_altrui AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('presidio contratto altrui');

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM t_k1));
END $ctx$;

SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_crea_contratto('presidio altrui', 'DRAFT', %s)$$,
           (SELECT billing_account_id FROM t_ba_altrui)),
    '%e'' legato all''emittente%',
    '7) guard: un billing account di un''altra azienda parla, invece di sbattere sul guard emittente/BA'
);

SELECT throws_like(
    $$SELECT dbops.fn_pgtap_crea_contratto('presidio cessato', 'CESSATO')$$,
    '%non costruibile dal builder%',
    '8) guard: CESSATO non si costruisce (vuole valido_al e passa da ATTIVO: e'' il caso del test)'
);

SELECT * FROM finish();
ROLLBACK;
