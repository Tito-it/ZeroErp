-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: i conti bancari — la forma, i lucchetti, l'IBAN della filiale, lo
--       sportello unico per paese, il predefinito, lo snapshot del mandato
--
-- Elenco test (plan 26):
--   1) emittenti_fiscali_utilities.utility_id e' integer, come config.utilities.id
--   2) Italia dichiara ABI e CAB nell'IBAN: posizioni 6,5 e 11,5
--   3) i tre EXCLUDE del predefinito per periodo esistono, e sono esclusioni
--   4) i due CHECK «predefinito non bloccato» esistono
--   5) i due guard immediati «conto attivo» dei legami non ci sono piu'
--   6) il conto si salva normalizzato: IBAN e BIC senza separatori (il BIC di 11 scritto a gruppi, 14), il paese dall'IBAN
--   7) l'IBAN non si cambia -> E_CONTO_BANCARIO_IBAN_IMMUTABILE
--   8) ... ma lo stesso IBAN riscritto con gli spazi passa (normalizzazione a01 prima del lucchetto)
--   9) un IBAN italiano che non porta ABI e CAB della filiale -> E_CONTO_IBAN_FILIALE_INCOERENTE
--  10) il conto non passa su una filiale con altri codici -> E_CONTO_IBAN_FILIALE_INCOERENTE
--  11) un IBAN di un paese senza posizioni dichiarate non si confronta (limite dichiarato)
--  12) la filiale con conti non cambia codici -> E_FILIALE_CODICI_CONTI_INCOERENTI
--  13) la filiale si salva normalizzata (codice con spazi e trattini)
--  14) due filiali con gli stessi codici nello stesso paese -> E_FILIALE_DUPLICATA
--  15) lo stesso sportello in un altro paese non e' occupato (la funzione dei guard)
--  16) il verso del soggetto e' montato su soggetti.stato_id (presidio di forma)
--  17) l'uso del legame del soggetto non si cambia -> E_CONTO_LEGAME_IMMUTABILE
--  18) l'istanza del legame del ruolo non si cambia -> E_CONTO_LEGAME_IMMUTABILE
--  19) un legame predefinito e bloccato non nasce -> E_CONTO_PREDEFINITO_BLOCCATO
--  20) un predefinito non si blocca -> E_CONTO_PREDEFINITO_BLOCCATO
--  21) due predefiniti dello stesso ruolo e uso che si sovrappongono -> E_CONTO_PREDEFINITO_SOVRAPPOSTO
--  22) un cambio programmato: due predefiniti in periodi contigui passano
--  23) il predefinito di un'istanza e quello di tutto il ruolo non si incontrano
--  24) la seconda porta: due predefiniti del soggetto sovrapposti -> E_CONTO_PREDEFINITO_SOVRAPPOSTO
--  25) un legame su un conto spento -> E_ATTIVO_PADRE_NON_ATTIVO (il REQUIRE, sede unica)
--  26) lo snapshot del mandato SEPA e' l'IBAN del conto, qualunque cosa si mandi
--
-- Scopo:
--   collaudare il giro T8a della revisione di anagrafiche. Ogni caso si
--   COSTRUISCE: filiali, conti e legami nascono nel test (bank_branches e'
--   dato di macchina, vuota su un database ricostruito). Si gira come
--   l'applicazione.
--   ⭐ Il test 8 presidia l'ordine dei trigger del conto: la normalizzazione
--   (a01) prima del lucchetto (a10). Con l'ordine rovesciato lo stesso IBAN
--   scritto «come si legge» sarebbe un cambio.
--   ⭐ Il test 15 presidia che l'unicita' sia PER PAESE, non globale, sulla
--   funzione condivisa: il caso non si costruisce (nature del seed tutte
--   italiane). Il 16 e' un presidio di forma del verso del soggetto.
--   ⭐ I test 22 e 23 presidiano che il vincolo del predefinito dica la regola
--   e non di piu': un cambio programmato e il gradino dell'istanza sono leciti.
--
-- Brief: brief-db-revisione-anagrafiche §25.10, §25.11 (giro T8a)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(26);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _cli AS
SELECT 'A' AS lato, c.* FROM dbops.fn_pgtap_crea_cliente_ba('conti T8a A') c
UNION ALL
SELECT 'B' AS lato, c.* FROM dbops.fn_pgtap_crea_cliente_ba('conti T8a B') c;

CREATE TEMP TABLE _fil AS
SELECT 'A' AS lato, f.* FROM dbops.fn_pgtap_crea_filiale_bancaria('T8a A') f;
INSERT INTO _fil SELECT 'B', f.* FROM dbops.fn_pgtap_crea_filiale_bancaria('T8a B') f;
INSERT INTO _fil SELECT 'C', f.* FROM dbops.fn_pgtap_crea_filiale_bancaria('T8a C') f;

-- I riferimenti, letti in un'istruzione separata da quelle dei builder.
CREATE TEMP TABLE _r AS
SELECT (SELECT bank_branch_id     FROM _fil WHERE lato = 'A') AS fil_a,
       (SELECT bank_branch_id     FROM _fil WHERE lato = 'B') AS fil_b,
       (SELECT bank_branch_id     FROM _fil WHERE lato = 'C') AS fil_c,
       (SELECT banca_soggetto_id  FROM _fil WHERE lato = 'C') AS banca_c_sogg,
       (SELECT soggetto_ruolo_id  FROM _cli WHERE lato = 'A') AS sr_a,
       (SELECT soggetto_id        FROM _cli WHERE lato = 'A') AS sogg_a,
       (SELECT istanza_utility_id FROM _cli WHERE lato = 'A') AS ist_a,
       (SELECT billing_account_id FROM _cli WHERE lato = 'A') AS ba_a;

-- Un conto di prova, coerente con la filiale A, scritto come si legge.
CREATE TEMP TABLE _iban AS
SELECT dbops.fn_pgtap_iban(fil_a, 'T8A FORMA 1') AS forma,
       dbops.fn_pgtap_iban(fil_a, 'T8A FORMA 2') AS altro,
       dbops.fn_pgtap_iban(fil_a, 'T8A P1')      AS p1,
       dbops.fn_pgtap_iban(fil_a, 'T8A P2')      AS p2,
       dbops.fn_pgtap_iban(fil_a, 'T8A P3')      AS p3,
       dbops.fn_pgtap_iban(fil_a, 'T8A SPENTO')  AS spento
  FROM _r;

-- La forma stampata: gruppi di quattro con spazi, un trattino, minuscolo.
CREATE TEMP TABLE _stampato AS
SELECT lower(substr(forma, 1, 4) || ' ' || substr(forma, 5, 4) || '-' || substr(forma, 9, 4) || ' '
             || substr(forma, 13)) AS forma
  FROM _iban;

-- ============================================================
-- 1-5. La struttura
-- ============================================================
SELECT is(
    (SELECT format_type(a.atttypid, a.atttypmod)
       FROM pg_attribute a
      WHERE a.attrelid = 'anagrafiche.emittenti_fiscali_utilities'::regclass
        AND a.attname = 'utility_id'),
    'integer',
    '1) emittenti_fiscali_utilities.utility_id e'' integer, come config.utilities.id');

SELECT is(
    (SELECT array[iban_pos_banca, iban_len_banca, iban_pos_filiale, iban_len_filiale]::int[]
       FROM config.stati WHERE codice_iso2 = 'IT'),
    array[6, 5, 11, 5],
    '2) Italia dichiara ABI e CAB nell''IBAN: posizioni 6,5 e 11,5');

SELECT is(
    (SELECT count(*)::int FROM pg_constraint
      WHERE contype = 'x'
        AND conname IN ('ex_scb_predefinito_per_periodo',
                        'ex_src_bancari_predefinito_istanza_periodo',
                        'ex_src_bancari_predefinito_no_istanza_periodo')),
    3,
    '3) i tre EXCLUDE del predefinito per periodo esistono, e sono esclusioni');

SELECT is(
    (SELECT count(*)::int FROM pg_constraint
      WHERE contype = 'c'
        AND conname IN ('chk_soggetti_conti_bancari_predefinito_non_bloccato',
                        'chk_soggetti_ruoli_conti_bancari_predefinito_non_bloccato')),
    2,
    '4) i due CHECK «predefinito non bloccato» esistono');

SELECT is(
    (SELECT count(*)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'anagrafiche'
        AND p.proname IN ('trgfn_soggetti_conti_bancari_guard',
                          'trgfn_soggetti_ruoli_conti_bancari_guard')),
    0,
    '5) i due guard immediati «conto attivo» dei legami non ci sono piu''');

-- ============================================================
-- 6-8. La forma del conto e il lucchetto dell'IBAN
-- ============================================================
CREATE TEMP TABLE _conto AS
WITH ins AS (
    INSERT INTO anagrafiche.conti_bancari (iban, bic_swift, paese, bank_branch_id, attivo, storicizza)
    -- ⭐ Un BIC di 11 caratteri scritto a gruppi e' lungo 14: arriva alla
    --   normalizzazione perche' la colonna e' text, e la lunghezza la giudica
    --   il CHECK sul valore normalizzato (D-T8a-14).
    SELECT s.forma, 'bppi it-rr xxx', 'FR', r.fil_a, true, false
      FROM _stampato s, _r r
    RETURNING id, iban, bic_swift, paese
)
SELECT * FROM ins;

SELECT is(
    (SELECT array[c.iban::text, c.bic_swift::text, c.paese::text] FROM _conto c),
    (SELECT array[i.forma::text, 'BPPIITRRXXX', 'IT'] FROM _iban i),
    '6) il conto si salva normalizzato: IBAN e BIC senza separatori, il paese dall''IBAN');

SELECT throws_like(
    $$UPDATE anagrafiche.conti_bancari SET iban = (SELECT altro FROM _iban)
       WHERE id = (SELECT id FROM _conto)$$,
    '%un IBAN sbagliato e'' un altro conto%',
    '7) l''IBAN non si cambia -> E_CONTO_BANCARIO_IBAN_IMMUTABILE');

SELECT lives_ok(
    $$UPDATE anagrafiche.conti_bancari SET iban = (SELECT forma FROM _stampato)
       WHERE id = (SELECT id FROM _conto)$$,
    '8) lo stesso IBAN riscritto con gli spazi passa: la normalizzazione viene prima del lucchetto');

-- ============================================================
-- 9-12. L'IBAN della filiale, nei due versi
-- ============================================================
SELECT throws_like(
    $$INSERT INTO anagrafiche.conti_bancari (iban, bank_branch_id, storicizza)
      SELECT dbops.fn_pgtap_iban(r.fil_b, 'T8A INCOERENTE'), r.fil_a, false FROM _r r$$,
    '%della filiale scelta%',
    '9) un IBAN italiano che non porta ABI e CAB della filiale -> E_CONTO_IBAN_FILIALE_INCOERENTE');

SELECT throws_like(
    $$UPDATE anagrafiche.conti_bancari SET bank_branch_id = (SELECT fil_b FROM _r)
       WHERE id = (SELECT id FROM _conto)$$,
    '%della filiale scelta%',
    '10) il conto non passa su una filiale con altri codici -> E_CONTO_IBAN_FILIALE_INCOERENTE');

SELECT lives_ok(
    $$INSERT INTO anagrafiche.conti_bancari (iban, bank_branch_id, storicizza)
      SELECT 'DE89370400440532013000', r.fil_a, false FROM _r r$$,
    '11) un IBAN di un paese senza posizioni dichiarate non si confronta (limite dichiarato)');

SELECT throws_like(
    $$UPDATE anagrafiche.bank_branches SET branch_code = '99998'
       WHERE id = (SELECT fil_a FROM _r)$$,
    '%non tornerebbero%',
    '12) la filiale con conti non cambia codici -> E_FILIALE_CODICI_CONTI_INCOERENTI');

-- ============================================================
-- 13-16. La forma della filiale e lo sportello unico per paese
-- ============================================================
UPDATE anagrafiche.bank_branches SET branch_code = ' 9 9-9 9 7 '
 WHERE id = (SELECT fil_b FROM _r);

SELECT is(
    (SELECT branch_code::text FROM anagrafiche.bank_branches WHERE id = (SELECT fil_b FROM _r)),
    '99997',
    '13) la filiale si salva normalizzata (codice con spazi e trattini)');

SELECT throws_like(
    $$UPDATE anagrafiche.bank_branches
         SET branch_code = (SELECT branch_code FROM anagrafiche.bank_branches WHERE id = (SELECT fil_a FROM _r))
       WHERE id = (SELECT fil_c FROM _r)$$,
    '%nello stesso paese%',
    '14) due filiali con gli stessi codici nello stesso paese -> E_FILIALE_DUPLICATA');

-- ⚠️ Il caso «stesso sportello in due paesi» non si COSTRUISCE: le nature del
--   seed sono tutte italiane, e una banca persona giuridica di un altro paese
--   il builder non la sa fare (la forma giuridica e' obbligatoria e nessuna e'
--   estera); spostarla di paese lo rifiuta, giustamente, il guard della forma.
--   Si prova la funzione che i due guard condividono, e il montaggio del verso
--   del soggetto: sono presidi di forma, dichiarati tali.
SELECT is(
    (SELECT anagrafiche.fn_filiale_stessi_codici(NULL, a.bank_code, a.branch_code,
                (SELECT id FROM config.stati WHERE codice_iso2 = 'DE' ORDER BY id LIMIT 1))
       FROM anagrafiche.bank_branches a WHERE a.id = (SELECT fil_a FROM _r)),
    NULL,
    '15) lo sportello di A non e'' occupato in un altro paese: l''unicita'' e'' per paese (la funzione dei guard)');

SELECT is(
    (SELECT pg_get_triggerdef(t.oid) LIKE '%BEFORE UPDATE OF stato_id ON anagrafiche.soggetti%'
       FROM pg_trigger t
      WHERE t.tgrelid = 'anagrafiche.soggetti'::regclass
        AND t.tgfoid = 'anagrafiche.trgfn_soggetti_guard_filiali_unica_per_paese()'::regprocedure),
    true,
    '16) il verso del soggetto e'' montato: BEFORE UPDATE OF stato_id su anagrafiche.soggetti (presidio di forma)');

-- ============================================================
-- 17-18. I lucchetti dei legami
-- ============================================================
CREATE TEMP TABLE _scb AS
WITH ins AS (
    INSERT INTO anagrafiche.soggetti_conti_bancari
        (soggetto_id, conto_bancario_id, uso, predefinito, bloccato, storicizza)
    SELECT r.sogg_a, c.id, 'PAGAMENTO', false, false, false
      FROM _r r, _conto c
    RETURNING id
)
SELECT id FROM ins;

SELECT throws_like(
    $$UPDATE anagrafiche.soggetti_conti_bancari SET uso = 'RIMBORSO'
       WHERE id = (SELECT id FROM _scb)$$,
    '%del legame col conto non e'' modificabile%',
    '17) l''uso del legame del soggetto non si cambia -> E_CONTO_LEGAME_IMMUTABILE');

CREATE TEMP TABLE _src AS
WITH ins AS (
    INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
        (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, bloccato, storicizza)
    SELECT r.sr_a, c.id, 'PAGAMENTO', false, false, false
      FROM _r r, _conto c
    RETURNING id
)
SELECT id FROM ins;

SELECT throws_like(
    $$UPDATE anagrafiche.soggetti_ruoli_conti_bancari SET istanza_utility_id = (SELECT ist_a FROM _r)
       WHERE id = (SELECT id FROM _src)$$,
    '%del legame col conto non e'' modificabile%',
    '18) l''istanza del legame del ruolo non si cambia -> E_CONTO_LEGAME_IMMUTABILE');

-- ============================================================
-- 19-24. Il predefinito
-- ============================================================
CREATE TEMP TABLE _cp AS
WITH ins AS (
    INSERT INTO anagrafiche.conti_bancari (iban, bank_branch_id, storicizza)
    SELECT v.iban, r.fil_a, false
      FROM _r r,
           LATERAL (VALUES ('p1', (SELECT p1 FROM _iban)),
                           ('p2', (SELECT p2 FROM _iban)),
                           ('p3', (SELECT p3 FROM _iban))) v(k, iban)
    RETURNING id, iban
)
SELECT i.id, CASE i.iban WHEN (SELECT p1 FROM _iban) THEN 'p1'
                         WHEN (SELECT p2 FROM _iban) THEN 'p2' ELSE 'p3' END AS k
  FROM ins i;

SELECT throws_like(
    $$INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
          (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, bloccato, storicizza)
      SELECT r.sr_a, c.id, 'INCASSO', true, true, false
        FROM _r r, _cp c WHERE c.k = 'p1'$$,
    '%predefinito non si puo'' bloccare%',
    '19) un legame predefinito e bloccato non nasce -> E_CONTO_PREDEFINITO_BLOCCATO');

-- Il predefinito di tutto il ruolo fino al 31 marzo 2030.
INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
    (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, bloccato, valido_al, storicizza)
SELECT r.sr_a, c.id, 'INCASSO', true, false, DATE '2030-03-31', false
  FROM _r r, _cp c WHERE c.k = 'p1';

SELECT throws_like(
    $$UPDATE anagrafiche.soggetti_ruoli_conti_bancari SET bloccato = true
       WHERE conto_bancario_id = (SELECT id FROM _cp WHERE k = 'p1') AND uso = 'INCASSO'$$,
    '%predefinito non si puo'' bloccare%',
    '20) un predefinito non si blocca -> E_CONTO_PREDEFINITO_BLOCCATO');

SELECT throws_like(
    $$INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
          (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, bloccato, valido_dal, storicizza)
      SELECT r.sr_a, c.id, 'INCASSO', true, false, DATE '2030-03-31', false
        FROM _r r, _cp c WHERE c.k = 'p2'$$,
    '%periodo che si sovrappone%',
    '21) due predefiniti dello stesso ruolo e uso che si sovrappongono -> E_CONTO_PREDEFINITO_SOVRAPPOSTO');

SELECT lives_ok(
    $$INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
          (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, bloccato, valido_dal, storicizza)
      SELECT r.sr_a, c.id, 'INCASSO', true, false, DATE '2030-04-01', false
        FROM _r r, _cp c WHERE c.k = 'p2'$$,
    '22) un cambio programmato: due predefiniti in periodi contigui passano');

SELECT lives_ok(
    $$INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
          (soggetto_ruolo_id, conto_bancario_id, istanza_utility_id, uso, predefinito, bloccato, storicizza)
      SELECT r.sr_a, c.id, r.ist_a, 'INCASSO', true, false, false
        FROM _r r, _cp c WHERE c.k = 'p3'$$,
    '23) il predefinito di un''istanza e quello di tutto il ruolo non si incontrano');

INSERT INTO anagrafiche.soggetti_conti_bancari
    (soggetto_id, conto_bancario_id, uso, predefinito, bloccato, storicizza)
SELECT r.sogg_a, c.id, 'GENERICO', true, false, false
  FROM _r r, _cp c WHERE c.k = 'p1';

SELECT throws_like(
    $$INSERT INTO anagrafiche.soggetti_conti_bancari
          (soggetto_id, conto_bancario_id, uso, predefinito, bloccato, valido_dal, storicizza)
      SELECT r.sogg_a, c.id, 'GENERICO', true, false, DATE '2031-01-01', false
        FROM _r r, _cp c WHERE c.k = 'p2'$$,
    '%periodo che si sovrappone%',
    '24) la seconda porta: due predefiniti del soggetto sovrapposti -> E_CONTO_PREDEFINITO_SOVRAPPOSTO');

-- ============================================================
-- 25. Il conto del legame e' attivo: una sede, il REQUIRE
-- ============================================================
CREATE TEMP TABLE _spento AS
WITH ins AS (
    INSERT INTO anagrafiche.conti_bancari (iban, bank_branch_id, attivo, storicizza)
    SELECT i.spento, r.fil_a, false, false FROM _r r, _iban i
    RETURNING id
)
SELECT id FROM ins;

SELECT throws_like(
    $$INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
          (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, bloccato, storicizza)
      SELECT r.sr_a, s.id, 'RIMBORSO', false, false, false FROM _r r, _spento s$$,
    '%non è attiva%',
    '25) un legame su un conto spento -> E_ATTIVO_PADRE_NON_ATTIVO (il REQUIRE, sede unica)');

-- ============================================================
-- 26. Lo snapshot del mandato
-- ============================================================
INSERT INTO pagamenti.sepa_mandati
    (soggetto_ruolo_conto_id, billing_account_id, umr, schema, stato, iban_snapshot, storicizza)
SELECT s.id, r.ba_a, 'PGTAP-T8A-UMR-1', 'CORE', 'IN_VALIDAZIONE', 'DE89370400440532013000', false
  FROM _src s, _r r;

SELECT is(
    (SELECT m.iban_snapshot::text FROM pagamenti.sepa_mandati m WHERE m.umr = 'PGTAP-T8A-UMR-1'),
    (SELECT i.forma::text FROM _iban i),
    '26) lo snapshot del mandato SEPA e'' l''IBAN del conto, qualunque cosa si mandi');

SELECT * FROM finish();
ROLLBACK;
