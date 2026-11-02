-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
--   - lo stato si sceglie alla nascita, e uno inesistente parla;
--   - rev 2026-10-24 (20261024-27, brief-modello-documento-vendita Q-2): fuori
--     bozza la fattura puo' arrivare SENZA indirizzi e/o SENZA intestazione,
--     spogliata nell'ultimo stato non congelato del percorso;
--   - rev 2026-10-24 (20261024-36, R-5): minimo, totale a pagare e termine
--     di pagamento alla nascita;
--   - rev 2026-10-24 (20261024-42): la fattura senza utility.
--
-- Elenco test (plan 15):
--   1) la funzione esiste con la firma dichiarata
--   2) la testata esiste davvero, e porta il registro e il BA tornati
--   3) il registro e' dell'azienda di chi agisce
--   4) la coppia (emittente, utility) NON e' scritta: valgono i parametri di sistema (R-4)
--   5) stato: quello chiesto alla nascita (EMESSA, non il default)
--   6) terzo parametro: stesso cliente, stesso registro, testata NUOVA
--   7) senza terzo parametro: cliente nuovo, stessa azienda
--   8) guard: uno stato che non esiste parla invece di scrivere NULL
--   9) DEFINITIVA senza spoliazione: indirizzi e intestazione ci sono
--  10) DEFINITIVA spogliata di tutto: lo stato e' quello, gli snapshot no
--  11) EMESSA spogliata dei soli indirizzi: l'intestazione resta
--  12) guard: spogliare una fattura che resta in bozza parla
--  13) senza i tre valori: minimo false, totale e termine vuoti (come prima)
--  14) minimo, totale a pagare e termine scritti alla nascita
--  15) p_senza_utility: la fattura nasce senza utility; senza, ha quella del cliente
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

SELECT plan(15);

-- ============================================================
-- 1) La firma
-- ============================================================
SELECT has_function(
    'dbops', 'fn_pgtap_crea_fattura',
    ARRAY['text', 'character varying', 'bigint', 'boolean', 'boolean', 'boolean', 'numeric', 'bigint', 'boolean'],
    'dbops.fn_pgtap_crea_fattura(text, character varying, bigint, boolean, boolean, boolean, numeric, bigint, boolean) esiste con la firma dichiarata'
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

-- ============================================================
-- 9-12) Fuori bozza, con e senza gli snapshot (rev 2026-10-24, Q-2)
-- ============================================================
CREATE TEMP TABLE t_f4 AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
    'presidio definitiva', 'DEFINITIVA', (SELECT billing_account_id FROM t_f1));
CREATE TEMP TABLE t_f5 AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
    'presidio nuda', 'DEFINITIVA', (SELECT billing_account_id FROM t_f1), true, true);
CREATE TEMP TABLE t_f6 AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
    'presidio senza indirizzi', 'EMESSA', (SELECT billing_account_id FROM t_f1), true, false);

-- La forma che si legge: stato, intestazione presente, numero di indirizzi.
CREATE TEMP TABLE t_forma AS
SELECT t.caso, s.codice_interno::text || ' '
           || (f.emittente_snapshot IS NOT NULL AND f.cliente_snapshot IS NOT NULL)::text || ' '
           || (SELECT count(*) FROM vendite.fatture_indirizzi i WHERE i.fattura_id = f.id)::text AS forma
  FROM (SELECT 'piena' AS caso, fattura_id FROM t_f4
        UNION ALL SELECT 'nuda', fattura_id FROM t_f5
        UNION ALL SELECT 'senza_indirizzi', fattura_id FROM t_f6) t
  JOIN vendite.fatture f ON f.id = t.fattura_id
  JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id;

SELECT ok(
    (SELECT forma LIKE 'DEFINITIVA true %' AND forma NOT LIKE '% 0' FROM t_forma WHERE caso = 'piena'),
    'DEFINITIVA senza spoliazione: indirizzi e intestazione scritti dai building block, come la pipeline'
);

SELECT is(
    (SELECT forma FROM t_forma WHERE caso = 'nuda'),
    'DEFINITIVA false 0',
    'DEFINITIVA spogliata: lo stato e'' quello chiesto, senza indirizzi ne'' intestazione'
);

SELECT is(
    (SELECT forma FROM t_forma WHERE caso = 'senza_indirizzi'),
    'EMESSA true 0',
    'EMESSA spogliata dei soli indirizzi: l''intestazione resta'
);

SELECT throws_like($$
    SELECT dbops.fn_pgtap_crea_fattura('presidio bozza nuda', 'DRAFT', NULL, true)
$$,
    'fn_pgtap_crea_fattura: DRAFT e'' lo stato iniziale%',
    'guard: spogliare una fattura che resta in bozza parla, la bozza nasce gia'' senza'
);

-- ============================================================
-- 13-14) Minimo, totale a pagare e termine alla nascita (rev 2026-10-24, R-5)
-- ============================================================
SELECT is(
    (SELECT f.minimo::text || ' ' || (f.totale_a_pagare IS NULL)::text || ' ' || (f.termine_pagamento_id IS NULL)::text
       FROM vendite.fatture f WHERE f.id = (SELECT fattura_id FROM t_f1)),
    'false true true',
    '13) senza i tre valori: minimo false, totale a pagare e termine vuoti, come prima'
);

CREATE TEMP TABLE t_f7 AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
    'presidio minimo', 'DRAFT', (SELECT billing_account_id FROM t_f1), false, false,
    true, 123.45,
    (SELECT tp.id FROM config.termini_pagamento tp WHERE tp.attivo IS TRUE ORDER BY tp.id LIMIT 1));

SELECT is(
    (SELECT f.minimo::text || ' ' || f.totale_a_pagare::text || ' '
            || (f.termine_pagamento_id = (SELECT tp.id FROM config.termini_pagamento tp
                                            WHERE tp.attivo IS TRUE ORDER BY tp.id LIMIT 1))::text
       FROM vendite.fatture f WHERE f.id = (SELECT fattura_id FROM t_f7)),
    'true 123.45 true',
    '14) minimo, totale a pagare e termine di pagamento scritti alla nascita'
);

-- 15) La fattura senza utility (rev 2026-10-24, 20261024-42)
CREATE TEMP TABLE t_f8 AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
    'presidio senza utility', 'DRAFT', (SELECT billing_account_id FROM t_f1),
    p_senza_utility => true);

SELECT is(
    (SELECT (f8.utility_id IS NULL)::text || ' ' || ((SELECT utility_id FROM t_f8) IS NULL)::text
            || ' ' || (f1.utility_id = (SELECT utility_id FROM t_f1))::text
       FROM vendite.fatture f8, vendite.fatture f1
      WHERE f8.id = (SELECT fattura_id FROM t_f8) AND f1.id = (SELECT fattura_id FROM t_f1)),
    'true true true',
    '15) p_senza_utility: la fattura nasce senza utility e il builder torna quella scritta (NULL); senza, ha quella del cliente'
);

SELECT * FROM finish();
ROLLBACK;
