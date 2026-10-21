-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_mondo_cliente — il BB di composizione delle fixture
-- Riferimento: brief-db-fixture-che-costruiscono-giro-2.md §3,
--   migliorie-generali-da-test-valutazione.md §3 D7.
--
-- pgtap-contesto: escluso — il SOGGETTO del test e' proprio l'apertura del
--   contesto. La riga del template aprirebbe il contesto prima della prima
--   chiamata e cancellerebbe il ramo A, che e' la meta' che conta: su un
--   database ricostruito nessuno ha ancora aperto niente. Il contesto lo apre
--   la funzione esaminata, e il test lo verifica (caso 3).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - senza contesto COSTRUISCE azienda + operatore e apre il contesto su lui;
--   - con un contesto aperto RIUSA l'azienda di chi agisce, e il cliente nuovo
--     e' legato a QUELLA (il trigger z90 lega all'emittente di chi agisce);
--   - due guard parlano invece di tornare una tupla con un NULL dentro: la
--     sigla chiesta a contesto aperto, e un contesto su chi non ha emittente.
--
-- Elenco test (plan 9):
--   1) la funzione esiste con la firma dichiarata
--   2) RAMO A: senza contesto l'azienda si COSTRUISCE (codice PGTRnnnn)
--   3) RAMO A: il contesto resta aperto sull'operatore tornato
--   4) il legame BA -> emittente punta all'azienda del mondo, non al default
--   5) l'operatore tornato ha quell'emittente (fail-closed P-2a)
--   6) l'identita' tornata e' OPERATORE ed e' attiva
--   7) RAMO B: la seconda chiamata riusa l'azienda e crea un cliente nuovo
--   8) guard: p_sigla chiesta con il contesto gia' aperto
--   9) guard: contesto aperto su un utente senza emittente
--
-- ⚠️ La funzione apre il contesto a livello di SESSIONE (come la riga del
--   template): dopo il ROLLBACK la GUC resta valorizzata su un utente che non
--   esiste piu'. Non da' fastidio perche' il runner lancia un processo per
--   file — e' la stessa proprieta' della rev 20260920-01.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa, e qui e' la posizione giusta. La funzione
--   esaminata e' una saga che apre e RICHIUDE la finestra differita da se'
--   (e' il contratto di ogni helper), quindi non c'e' nessuna unita' di
--   lavoro del file che resti a meta' strada.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- 1) La firma
-- ============================================================
SELECT has_function(
    'dbops', 'fn_pgtap_crea_mondo_cliente',
    ARRAY['text', 'character varying'],
    'dbops.fn_pgtap_crea_mondo_cliente(text, character varying) esiste con la firma dichiarata'
);

-- ============================================================
-- Fixture: il ramo A, cioe' la prima chiamata di un database vuoto
-- ============================================================
CREATE TEMP TABLE t_mondo_1 AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('presidio mondo 1');

-- ============================================================
-- 2) Il mondo si costruisce
-- ============================================================
SELECT matches(
    (SELECT emittente_codice FROM t_mondo_1),
    '^PGTR[0-9]{4}$',
    'RAMO A: senza contesto l''azienda si COSTRUISCE, e porta il codice dei mondi di fixture (PGTRnnnn)'
);

-- ============================================================
-- 3) Il contesto e' aperto su chi e' stato costruito
-- ============================================================
SELECT is(
    current_setting('app.current_user_id', true) || '/' || current_setting('app.ruolo_applicativo', true),
    (SELECT auth_user_id::text FROM t_mondo_1) || '/OPERATORE',
    'RAMO A: il contesto resta aperto sull''operatore tornato, con la veste OPERATORE'
);

-- ============================================================
-- 4) Il legame del billing account
-- ============================================================
-- ⚠️ E' l'asserzione che distingue questo BB da «due chiamate in fila»: senza
--   l'ordine giusto il trigger z90 legherebbe il BA all'emittente di DEFAULT,
--   cioe' a un'altra azienda, e sotto RLS il cliente non si vedrebbe.
SELECT is(
    (SELECT efba.emittente_soggetto_ruolo_id
       FROM anagrafiche.emittenti_fiscali_billing_account efba
      WHERE efba.billing_account_id = (SELECT billing_account_id FROM t_mondo_1)),
    (SELECT emittente_soggetto_ruolo_id FROM t_mondo_1),
    'il billing account e'' legato all''azienda del mondo, non all''emittente di default'
);

-- ============================================================
-- 5) L'operatore ha quell'emittente
-- ============================================================
SELECT is(
    (SELECT uef.emittente_fiscale_id
       FROM config.user_emittenti_fiscali uef
      WHERE uef.auth_user_id = (SELECT auth_user_id FROM t_mondo_1)),
    (SELECT emittente_fiscale_id FROM t_mondo_1),
    'l''operatore tornato ha in config.user_emittenti_fiscali proprio quell''emittente (fail-closed P-2a)'
);

-- ============================================================
-- 6) L'identita' tornata
-- ============================================================
SELECT is(
    (SELECT idg.ruolo_applicativo::text || '/' || idg.attivo::text
       FROM anagrafiche.identita_digitali idg
      WHERE idg.id = (SELECT identita_id FROM t_mondo_1)),
    'OPERATORE/true',
    'l''identita'' tornata e'' un''identita'' OPERATORE attiva: senza, l''operatore non sarebbe selezionabile dal contesto'
);

-- ============================================================
-- 7) Il ramo B
-- ============================================================
CREATE TEMP TABLE t_mondo_2 AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('presidio mondo 2');

SELECT is(
    (SELECT (m2.emittente_fiscale_id = m1.emittente_fiscale_id)
         || ' ' || (m2.auth_user_id = m1.auth_user_id)::text
         || ' ' || (m2.billing_account_id <> m1.billing_account_id)::text
         || ' ' || (m2.cliente_soggetto_ruolo_id <> m1.cliente_soggetto_ruolo_id)::text
       FROM t_mondo_1 m1, t_mondo_2 m2),
    'true true true true',
    'RAMO B: con il contesto aperto l''azienda e l''operatore sono gli stessi, e il cliente e'' nuovo'
);

-- ============================================================
-- 8) Guard: la sigla chiesta a contesto aperto
-- ============================================================
-- ⚠️ Non e' pignoleria sul parametro: una sigla accettata in silenzio qui
--   significherebbe un'azienda nuova con il cliente legato a quella VECCHIA.
SELECT throws_like($$
    SELECT dbops.fn_pgtap_crea_mondo_cliente('etichetta', 'ALTRA')
$$,
    '%qui l''azienda non si sceglie%',
    'guard: p_sigla chiesta con il contesto gia'' aperto rimanda ai builder atomici invece di costruire di nascosto'
);

-- ============================================================
-- 9) Guard: un contesto che non puo' scrivere
-- ============================================================
-- La GUC si cambia in modo TRANSAZIONALE (terzo argomento true): il rollback
-- del sotto-blocco di throws_like la riporta da se' a quella del mondo.
-- Rev 2026-10-21 (20261021-68): l'azienda la dice il risolutore, e il messaggio
--   nomina anche la scelta del super admin; il caso del super admin con
--   l'emittente scelto e' in test-fn-pgtap-crea-mondo-cliente-risolutore-v1.
SELECT throws_like($$
    DO $guard$
    BEGIN
        PERFORM set_config('app.current_user_id', '2147483647', true);
        PERFORM dbops.fn_pgtap_crea_mondo_cliente('contesto senza emittente');
    END $guard$
$$,
    '%non ha un''azienda su cui scrivere%',
    'guard: un contesto aperto su un utente senza emittente parla invece di tornare una tupla con un NULL dentro'
);

SELECT * FROM finish();
ROLLBACK;
