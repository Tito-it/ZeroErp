-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_ordine — il BB dell'ordine di vendita
-- Riferimento: brief-db-fixture-rls-documenti-costruiti (giro 2).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - costruisce il mondo e la testata, e la testata e' SCRIVIBILE: e' la
--     prova che i guard del dominio la accettano;
--   - l'emittente e' quello che il billing account pretende;
--   - numero e registro li assegna il dominio, non la fixture;
--   - lo stato chiesto NON si scrive alla nascita: l'ordine nasce in bozza
--     (trigger della nascita) e il builder lo porta avanti per la matrice,
--     sotto i guard veri; uno stato inesistente parla (rev 2026-10-24,
--     20261024-23, brief-modello-documento-vendita N-1);
--   - una seconda chiamata riusa l'azienda di chi agisce, con un cliente nuovo;
--   - il terzo parametro riusa un cliente gia' costruito (il secondo ordine
--     dello stesso cliente) e RIFIUTA un billing account di un'altra azienda
--     (rev 2026-10-22, 20261022-10, richiesta BE R-3).
--
-- Elenco test (plan 10):
--   1) la funzione esiste con la firma dichiarata
--   2) la testata esiste, col cliente e il billing account tornati
--   3) l'emittente e' quello del billing account (il guard emittente/BA)
--   4) numero e registro assegnati dal dominio
--   5) stato: quello chiesto, raggiunto per la matrice (ANNULLATO, non il default)
--   6) seconda chiamata: stessa azienda, cliente nuovo
--   7) guard: uno stato che non esiste parla invece di scrivere NULL
--   8) terzo parametro: stesso cliente, ordine nuovo
--   9) terzo parametro: un BA di un'altra azienda parla
--  10) un passaggio che vuole le righe (CONFERMATO) il builder non lo salta:
--      lo rifiuta il guard vero (rev 2026-10-24)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre la funzione esaminata, che qui
--   viene chiamata come la chiamera' un file su un database ricostruito: senza
--   nessuna veste in sessione. Aprirlo prima nasconderebbe meta' del contratto.

SELECT plan(10);

-- 1) La firma
SELECT has_function(
    'dbops', 'fn_pgtap_crea_ordine',
    ARRAY['text', 'character varying', 'bigint'],
    'dbops.fn_pgtap_crea_ordine(text, character varying, bigint) esiste con la firma dichiarata'
);

-- Fixture: un'altra azienda, PRIMA del contesto (una seconda azienda si
-- costruisce coi builder atomici, prima del contesto). Il suo cliente nasce
-- sotto il suo contesto, subito prima del test 9.
CREATE TEMP TABLE t_altrui AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Fixture: il primo ordine, dal nulla
CREATE TEMP TABLE t_o1 AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('presidio ordine 1');

-- 2) La testata c'e', ed e' quella tornata
SELECT is(
    (SELECT o.soggetto_ruolo_id::text || '/' || o.billing_account_id::text
       FROM vendite.ordini o
      WHERE o.id = (SELECT ordine_id FROM t_o1)),
    (SELECT cliente_soggetto_ruolo_id::text || '/' || billing_account_id::text FROM t_o1),
    'la testata esiste e porta il cliente e il billing account tornati dalla funzione'
);

-- 3) L'emittente e' quello che il billing account pretende
SELECT is(
    (SELECT o.emittente_fiscale_id FROM vendite.ordini o
      WHERE o.id = (SELECT ordine_id FROM t_o1)),
    anagrafiche.fn_get_emittente_fiscale_pk((SELECT billing_account_id FROM t_o1)),
    'l''emittente della testata e'' quello del billing account (trgfn_ordini_guard_emittente_ba)'
);

-- 4) Numero e registro dal dominio
SELECT ok(
    (SELECT o.numero IS NOT NULL AND o.registro_id IS NOT NULL
       FROM vendite.ordini o WHERE o.id = (SELECT ordine_id FROM t_o1)),
    'numero e registro li assegna il dominio (trgfn_ordini_gen_numero), non la fixture'
);

-- 5) Lo stato chiesto: l'ordine nasce in bozza e ci arriva per la matrice
--    (rev 2026-10-24). ANNULLATO dalla bozza non vuole righe.
CREATE TEMP TABLE t_conf AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('presidio ordine annullato', 'ANNULLATO');

SELECT is(
    (SELECT s.codice_interno
       FROM vendite.ordini o
       JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
      WHERE o.id = (SELECT ordine_id FROM t_conf)),
    'ANNULLATO'::character varying,
    'lo stato e'' quello chiesto, raggiunto per la matrice dalla bozza'
);

-- 6) Seconda chiamata: il contesto e' ormai aperto, l'azienda si riusa
SELECT is(
    (SELECT (c.emittente_fiscale_id = o1.emittente_fiscale_id)::text
         || ' ' || (c.billing_account_id <> o1.billing_account_id)::text
       FROM t_o1 o1, t_conf c),
    'true true',
    'seconda chiamata: stessa azienda di chi agisce, cliente nuovo'
);

-- 7) Guard: uno stato che non esiste
-- ⚠️ Senza il guard `stato_doc_ordine_id` uscirebbe NULL e il file morirebbe
--   sul NOT NULL della testata, con un errore che non nomina il parametro.
SELECT throws_like($$
    SELECT dbops.fn_pgtap_crea_ordine('presidio stato', 'NON_ESISTE')
$$,
    '%nessuno stato documento ordine%',
    'guard: uno stato inesistente parla, invece di scrivere un NULL nella testata'
);

-- 8) Terzo parametro: il secondo ordine dello STESSO cliente
CREATE TEMP TABLE t_o2 AS
SELECT * FROM dbops.fn_pgtap_crea_ordine(
                 'presidio ordine 2', 'DRAFT', (SELECT billing_account_id FROM t_o1));

SELECT is(
    (SELECT (o2.billing_account_id = o1.billing_account_id)::text
         || ' ' || (o2.cliente_soggetto_ruolo_id = o1.cliente_soggetto_ruolo_id)::text
         || ' ' || (o2.ordine_id <> o1.ordine_id)::text
         || ' ' || (o.billing_account_id = o1.billing_account_id)::text
       FROM t_o1 o1, t_o2 o2
       JOIN vendite.ordini o ON o.id = o2.ordine_id),
    'true true true true',
    'col terzo parametro: stesso cliente, ordine nuovo, e la testata porta quel billing account'
);

-- 9) Terzo parametro: un BA di un'altra azienda
-- Il cliente dell'altra azienda lo crea l'altra azienda (sotto la RLS un BA lo
-- scrive chi lavora in quell'azienda; il legame lo scrive il trigger z90). Poi
-- il contesto torna sull'operatore del mondo.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM t_altrui));
END $ctx$;

CREATE TEMP TABLE t_ba_altrui AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('presidio ordine altrui');

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM t_o1));
END $ctx$;

SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_crea_ordine('presidio altrui', 'DRAFT', %s)$$,
           (SELECT billing_account_id FROM t_ba_altrui)),
    'fn_pgtap_crea_ordine: il billing account % e'' legato all''emittente%',
    'guard: un billing account di un''altra azienda parla, nominando il builder'
);

-- 10) Un passaggio che vuole le righe il builder non lo salta (rev 2026-10-24,
--     20261024-23): l'ordine nasce in bozza, e da li' a CONFERMATO lo ferma il
--     guard vero (trgfn_ordini_guard_transizione). Le righe sono del test, che
--     poi porta avanti con dbops.fn_pgtap_porta_a_stato.
SELECT throws_like(
    $$SELECT dbops.fn_pgtap_crea_ordine('presidio ordine senza righe', 'CONFERMATO')$$,
    'Ordine % senza righe: impossibile confermare%',
    'CONFERMATO senza righe: il builder passa dalla matrice, e il guard della conferma lo ferma (E_ORDINE_CONFERMA_SENZA_RIGHE)'
);

SELECT * FROM finish();
ROLLBACK;
