-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_fattura — il BB della testata fiscale
-- Riferimento: brief-db-fixture-che-costruiscono-giro-2.md §7 (decisione 6),
--   migliorie-generali-da-test-valutazione.md §3 D7.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - costruisce la catena intera: mondo, coppia (emittente, utility),
--     registro coerente, testata — e la testata e' SCRIVIBILE, che e' la
--     prova che i quattro anelli ci sono tutti;
--   - il registro appartiene all'azienda di chi agisce, e il billing account
--     pure: e' cio' che i guard del dominio pretendono;
--   - il terzo parametro riusa un cliente gia' costruito invece di farne uno
--     nuovo, e RIFIUTA un billing account di un'altra azienda;
--   - lo stato si sceglie alla nascita, e uno inesistente parla.
--
-- Elenco test (plan 8):
--   1) la funzione esiste con la firma dichiarata
--   2) la testata esiste davvero, e porta il registro e il BA tornati
--   3) il registro e' dell'azienda di chi agisce
--   4) la coppia (emittente, utility) NON e' scritta: valgono i parametri di sistema (R-4)
--   5) stato: quello chiesto alla nascita (EMESSA, non il default)
--   6) terzo parametro: stesso cliente, stesso registro, testata NUOVA
--   7) senza terzo parametro: cliente nuovo, stessa azienda
--   8) guard: uno stato che non esiste parla invece di scrivere NULL
--
-- ⚠️ La fixture apre il contesto chiamando il BB: la riga del template
--   sarebbe ridondante, ma non dannosa. Qui si usa il BB come lo usera' un
--   file vero — prima chiamata senza contesto, come in CI.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto), quindi nessuna unita' di
--   lavoro di questo file resta a meta' strada.
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre la funzione esaminata, che qui
--   viene chiamata come la chiamera' un file su un database ricostruito: senza
--   nessuna veste in sessione. Aprirlo prima nasconderebbe meta' del contratto.

SELECT plan(8);

-- ============================================================
-- 1) La firma
-- ============================================================
SELECT has_function(
    'dbops', 'fn_pgtap_crea_fattura',
    ARRAY['text', 'character varying', 'bigint'],
    'dbops.fn_pgtap_crea_fattura(text, character varying, bigint) esiste con la firma dichiarata'
);

-- ============================================================
-- Fixture: la prima fattura, dal nulla
-- ============================================================
CREATE TEMP TABLE t_f1 AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('presidio fattura 1');

-- ============================================================
-- 2) La testata c'e', ed e' quella tornata
-- ============================================================
SELECT is(
    (SELECT f.registro_id::text || '/' || f.billing_account_id::text
       FROM vendite.fatture f
      WHERE f.id = (SELECT fattura_id FROM t_f1)),
    (SELECT registro_id::text || '/' || billing_account_id::text FROM t_f1),
    'la testata esiste e porta il registro e il billing account tornati dalla funzione'
);

-- ============================================================
-- 3) Il registro e' dell'azienda di chi agisce
-- ============================================================
-- ⚠️ E' l'anello che un file non indovina: un registro di un'altra azienda lo
--   rifiuta `vendite.trgfn_fatture_guard_registro_emittente`, e su un database
--   ricostruito di registri non ce n'e' nessuno da pescare.
SELECT is(
    (SELECT r.emittente_soggetto_ruolo_id
       FROM vendite.registri_fatturazione r
      WHERE r.id = (SELECT registro_id FROM t_f1)),
    (SELECT emittente_soggetto_ruolo_id FROM t_f1),
    'il registro appartiene all''azienda di chi agisce'
);

-- ============================================================
-- 4) La coppia (emittente, utility) non si scrive piu'
-- ============================================================
-- ⚠️ Rovesciato il 2026-10-21 (20261021-17, brief-db-modelli-documento-standard
--   §10.7 R-4): l'helper non scrive piu' la riga, perche' la testata non la
--   pretende piu'. La fattura del mondo e' quella di un emittente nuovo: i
--   parametri d'importo sono quelli di sistema dell'utility.
SELECT is(
    (SELECT row(p.personalizzata, p.arrotondamento_importi_dec IS NOT NULL)::text
       FROM t_f1, anagrafiche.fn_parametri_importo_utility(
                    t_f1.emittente_soggetto_ruolo_id, t_f1.utility_id) p),
    row(false, true)::text,
    'la coppia (emittente, utility) non e'' scritta: la fattura usa i parametri di sistema'
);

-- ============================================================
-- 5) Lo stato si sceglie alla nascita
-- ============================================================
CREATE TEMP TABLE t_emessa AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('presidio fattura emessa', 'EMESSA');

SELECT is(
    (SELECT s.codice_interno
       FROM vendite.fatture f
       JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id
      WHERE f.id = (SELECT fattura_id FROM t_emessa)),
    'EMESSA'::character varying,
    'lo stato e'' quello chiesto alla nascita, non il default'
);

-- ============================================================
-- 6) Il terzo parametro: la seconda fattura dello STESSO cliente
-- ============================================================
CREATE TEMP TABLE t_f2 AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
                 'presidio fattura 2', 'DRAFT',
                 (SELECT billing_account_id FROM t_f1));

SELECT is(
    (SELECT (f2.billing_account_id = f1.billing_account_id)::text
         || ' ' || (f2.registro_id = f1.registro_id)::text
         || ' ' || (f2.fattura_id <> f1.fattura_id)::text
       FROM t_f1 f1, t_f2 f2),
    'true true true',
    'col terzo parametro: stesso cliente, stesso registro, testata nuova'
);

-- ============================================================
-- 7) Senza terzo parametro: cliente nuovo, stessa azienda
-- ============================================================
CREATE TEMP TABLE t_f3 AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('presidio fattura 3');

SELECT is(
    (SELECT (f3.billing_account_id <> f1.billing_account_id)::text
         || ' ' || (f3.emittente_soggetto_ruolo_id = f1.emittente_soggetto_ruolo_id)::text
       FROM t_f1 f1, t_f3 f3),
    'true true',
    'senza terzo parametro: un cliente nuovo, ma dentro la stessa azienda'
);

-- ============================================================
-- 8) Guard: uno stato che non esiste
-- ============================================================
-- ⚠️ Senza il guard, `stato_doc_fiscale_id` uscirebbe NULL e il file morirebbe
--   sul NOT NULL della testata — un errore che non nomina ne' la fixture ne'
--   il parametro sbagliato.
SELECT throws_like($$
    SELECT dbops.fn_pgtap_crea_fattura('presidio stato', 'NON_ESISTE')
$$,
    '%nessuno stato documento fiscale%',
    'guard: uno stato inesistente parla, invece di scrivere un NULL nella testata'
);

SELECT * FROM finish();
ROLLBACK;
