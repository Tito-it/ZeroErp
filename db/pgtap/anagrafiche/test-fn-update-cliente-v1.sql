-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-differiti: escluso — la fixture non soddisfa un vincolo DIFFERITO e la
--   ragione e' scritta per esteso piu' sotto. Debito noto (§22.4): quando la
--   fixture viene completata, si toglie questa riga e si rimette il
--   SET CONSTRAINTS ALL IMMEDIATE nel punto in cui l'unita' di lavoro e' completa.
-- pgTAP per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: anagrafiche.fn_update_cliente (piano analisi-fix-transazioni, #1)
--
-- Copre:
--   * happy path       : categoria BA + campi cliente aggiornati insieme.
--   * delta semantics   : solo le chiavi presenti cambiano; le altre restano.
--   * ATOMICITA'        : se l'UPDATE clienti fallisce (FK inesistente),
--                         anche la scrittura della categoria sul BA viene
--                         annullata (o tutto o niente). E' il cuore del fix:
--                         prova che non resta piu' lo stato parziale.
--   * not found         : cliente inesistente => E_CLIENTE_NON_TROVATO.
--   * nothing to change : nessuna categoria e nessun campo => (false, false).
--
-- Nota RLS: fn_update_cliente e' SECURITY INVOKER, quindi eredita le policy
-- RLS di billing_account. L'enforcement RLS (fail-closed senza GUC, scope
-- emittente) e' coperto dai test RLS dedicati di billing_account e non viene
-- ri-verificato qui: questo file isola la correttezza funzionale + atomicita'.
--
-- Idempotente: gira dentro un'unica transazione chiusa da ROLLBACK, non
-- lascia residui. CF di test dedicato per non collidere con altre fixture.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ QUESTO FILE NON USA `SET CONSTRAINTS ALL IMMEDIATE`, a differenza degli
--   altri, e non e' una dimenticanza.
--   `anagrafiche.soggetti` ha TRE guard DEFERRABLE INITIALLY DEFERRED —
--   indirizzi, contatti, dati societari — e li' la deferralita' e' il CONTRATTO
--   DEL DOMINIO: si crea il soggetto, poi il suo indirizzo, e la completezza si
--   verifica al COMMIT. E' per questo che anagrafiche.fn_crea_soggetto_pf puo'
--   restituire un soggetto ancora incompleto, ed e' cosi' che la usa il backend.
--   Forzare IMMEDIATE pretenderebbe l'indirizzo nell'istante stesso dell'INSERT
--   del soggetto: vieterebbe il pattern che il dominio ha scelto.
--   ⚠️ Resta un buco reale: senza la riga quei guard non vengono esercitati da
--   questo test, e la fixture lascia un soggetto che l'applicazione non
--   potrebbe committare. La correzione vera e' COMPLETARE LA FIXTURE
--   (indirizzo + contatti): allora la riga si rimette e il test verifica sul
--   serio. Brief: brief-db-pgtap-runner-rls-baseline §21.

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ VINCOLI DIFFERITI — ⭐ LA FINESTRA SI RIAPRE, NON SI PRESUME.
--   La fixture costruisce il cliente in istruzioni separate (esenzione
--   dichiarata sopra): vuole i guard di `soggetti` DIFFERITI.
--   ⛔ Ma la riga di contesto qui sopra, quando COSTRUISCE il mondo (database
--   senza operatori: lo scratch `zeroerp_ci`, la CI), ESCE CON I VINCOLI
--   IMMEDIATE (rev 20260921-18, come ogni helper pgTAP). Fino al 2026-09-23 lo
--   mascherava un residuo: `create-gestore-conto-*` committavano l'operatore
--   `PGTR0001` e da li' la riga non costruiva piu'. Tolto quel COMMIT (brief
--   fixture-che-costruiscono giro 2), lo scratch appena ricostruito ha dato
--   ERRORE_FIXTURE: «Indirizzo obbligatorio mancante per soggetto …»
--   all'INSERT del soggetto.
--   La finestra la riapre il file, e dice da se' cosa vuole.
SET CONSTRAINTS ALL DEFERRED;

SELECT plan(20);

-- =========================================================
-- Fixture: soggetto PG + ruolo CL + istanza fittizia + BA + cliente
-- =========================================================
-- Costanti (CF/PIVA finti e dedicati a questo test)
CREATE TEMP TABLE k AS
SELECT
    '01677080440'::text        AS piva_test,
    'RSSMRA80A01H501U'::text   AS cf_test,   -- CF valido (Mario Rossi, 1980-01-01, M), libero
    'CL'::varchar              AS codice_ruolo_cliente,   -- config.tipi_ruoli.codice_interno
    'BASE'::varchar            AS codice_utility_test,     -- config.utilities.codice_interno (richiede_pdp=false)
    1::smallint                AS cat_c1,                  -- categorie_clienti STANDARD (id 1)
    4::smallint                AS cat_c2;                  -- categorie_clienti GOLD     (id 4)

-- 1) Soggetto PG
WITH ins AS (
    INSERT INTO anagrafiche.soggetti (
        ragione_sociale, cognome, nome, sesso, stato_id,
        codice_fiscale, tipo_soggetto_dettaglio_id, storicizza, attivo
    )
    SELECT NULL, 'Rossi', 'Mario', 'M', 1,
           k.cf_test, 1, TRUE, TRUE   -- tipo_soggetto_dettaglio_id 1 = PR (Persona Fisica - Privato, solo CF)
    FROM k
    RETURNING id
)
SELECT id INTO TEMP TABLE tmp_soggetto FROM ins;

SELECT is((SELECT count(*)::int FROM tmp_soggetto), 1,
          'Fixture: inserito 1 soggetto di test');

-- Contatto minimo (constraint soggetti)
INSERT INTO anagrafiche.contatti (
    tipo_contatto_id, soggetto_id, nominativo, email, is_default, default_context
)
SELECT 1, (SELECT id FROM tmp_soggetto),
       'Referente Test fn_update_cliente', 'upd.cliente@example.com', TRUE, 'soggetto';

-- 2) Ruolo CL
CREATE TEMP TABLE tmp_soggetto_ruolo AS
SELECT script.fn_get_or_create_soggetto_ruolo(
           p_soggetto_id  := s.id,
           p_cd_int_ruolo := k.codice_ruolo_cliente
       ) AS id
FROM tmp_soggetto s, k;

-- 3) Istanza fittizia
WITH ins AS (
    INSERT INTO anagrafiche.istanze_utilities (
        fittizia, proprietario_inquilino, soggetto_id, indirizzo_dettaglio_id
    )
    SELECT TRUE, 'I', s.id, NULL
    FROM tmp_soggetto s
    RETURNING id
)
SELECT id INTO TEMP TABLE tmp_istanza FROM ins;

-- 4) Billing account con categoria iniziale C1
WITH ins AS (
    INSERT INTO anagrafiche.billing_account (
        istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id
    )
    SELECT i.id, sr.id, u.id, k.cat_c1
    FROM tmp_istanza i,
         tmp_soggetto_ruolo sr,
         config.utilities u,
         k
    WHERE u.codice_interno = k.codice_utility_test
    RETURNING id
)
SELECT id INTO TEMP TABLE tmp_billing_account FROM ins;

-- 5) Cliente (stato PR)
-- ⚠️ rev 2026-08-29: via `iva_id` dalla fixture — la colonna non esiste piu' su
--   anagrafiche.clienti (changeSet 20260829-22).
WITH ins AS (
    INSERT INTO anagrafiche.clienti (
        soggetto_ruolo_id, istanza_utility_id, stato_cliente_id, billing_account_id
    )
    SELECT sr.id, i.id,
           (SELECT id FROM config.stati_cliente WHERE codice_interno = 'PR' LIMIT 1),
           ba.id
    FROM tmp_soggetto_ruolo sr, tmp_istanza i, tmp_billing_account ba
    RETURNING id
)
SELECT id INTO TEMP TABLE tmp_cliente FROM ins;

SELECT is((SELECT count(*)::int FROM tmp_cliente), 1,
          'Fixture: inserito 1 cliente di test');

SELECT is(
    (SELECT categoria_cliente_id FROM anagrafiche.billing_account
      WHERE id = (SELECT id FROM tmp_billing_account)),
    (SELECT cat_c1 FROM k),
    'Baseline: categoria BA = C1 (STANDARD)');

-- =========================================================
-- HAPPY PATH: categoria (C2) + campi cliente in una sola chiamata
-- =========================================================
CREATE TEMP TABLE r_happy AS
SELECT * FROM anagrafiche.fn_update_cliente(
    (SELECT id FROM tmp_cliente),
    (SELECT cat_c2 FROM k),
    '{"garanzia_importo": 150, "servizio_da_fatturare": false}'::jsonb
);

SELECT is((SELECT categoria_aggiornata FROM r_happy), TRUE,
          'Happy: categoria_aggiornata = TRUE');
SELECT is((SELECT campi_aggiornati FROM r_happy), TRUE,
          'Happy: campi_aggiornati = TRUE');
SELECT is(
    (SELECT categoria_cliente_id FROM anagrafiche.billing_account
      WHERE id = (SELECT id FROM tmp_billing_account)),
    (SELECT cat_c2 FROM k),
    'Happy: categoria BA persistita = C2 (GOLD)');
SELECT is(
    (SELECT garanzia_importo FROM anagrafiche.clienti WHERE id = (SELECT id FROM tmp_cliente)),
    150::numeric,
    'Happy: garanzia_importo persistito = 150');
SELECT is(
    (SELECT servizio_da_fatturare FROM anagrafiche.clienti WHERE id = (SELECT id FROM tmp_cliente)),
    FALSE,
    'Happy: servizio_da_fatturare persistito = false');

-- =========================================================
-- DELTA: solo servizio_da_fatturare; categoria non toccata, garanzia invariata
-- =========================================================
CREATE TEMP TABLE r_delta AS
SELECT * FROM anagrafiche.fn_update_cliente(
    (SELECT id FROM tmp_cliente),
    NULL,
    '{"servizio_da_fatturare": true}'::jsonb
);

SELECT is((SELECT categoria_aggiornata FROM r_delta), FALSE,
          'Delta: categoria_aggiornata = FALSE (categoria non passata)');
SELECT is((SELECT campi_aggiornati FROM r_delta), TRUE,
          'Delta: campi_aggiornati = TRUE');
SELECT is(
    (SELECT servizio_da_fatturare FROM anagrafiche.clienti WHERE id = (SELECT id FROM tmp_cliente)),
    TRUE,
    'Delta: servizio_da_fatturare aggiornato = true');
SELECT is(
    (SELECT garanzia_importo FROM anagrafiche.clienti WHERE id = (SELECT id FROM tmp_cliente)),
    150::numeric,
    'Delta: garanzia_importo INVARIATO = 150 (chiave assente)');

-- =========================================================
-- ATOMICITA' (il cuore del fix): una FK inesistente fa fallire l'UPDATE
-- clienti; la categoria BA (passata C1) NON deve restare scritta.
-- ⚠️ rev 2026-08-29: il veicolo era `iva_id`, colonna che non esiste piu'
--   (changeSet 20260829-22). La PROPRIETA' provata e' la stessa — o tutto o
--   niente — e si prova con un'altra chiave scrivibile che ha una FK:
--   `modalita_pagamento_id`. Cambia il veicolo, non il test.
-- ⚠️ SQLSTATE esplicito 23503: qui la FK e' l'unica strada per fallire, quindi
--   si puo' essere precisi. Prima si passava NULL perche' l'errore poteva
--   arrivare da due parti (FK o guard iva-attivo) e non si sapeva quale.
-- =========================================================
SELECT throws_ok(
    $$ SELECT * FROM anagrafiche.fn_update_cliente(
           (SELECT id FROM tmp_cliente),
           (SELECT cat_c1 FROM k),
           '{"modalita_pagamento_id": 999999}'::jsonb) $$,
    '23503',
    NULL::text,
    'Atomicita'': una FK inesistente fa fallire l''intera chiamata');

SELECT is(
    (SELECT categoria_cliente_id FROM anagrafiche.billing_account
      WHERE id = (SELECT id FROM tmp_billing_account)),
    (SELECT cat_c2 FROM k),
    'Atomicita'': categoria BA ANCORA C2 (la scrittura C1 e'' stata annullata)');
SELECT is(
    (SELECT servizio_da_fatturare FROM anagrafiche.clienti WHERE id = (SELECT id FROM tmp_cliente)),
    TRUE,
    'Atomicita'': cliente invariato (nessuna scrittura parziale)');

-- =========================================================
-- NOT FOUND: cliente inesistente => E_CLIENTE_NON_TROVATO (messaggio parlante)
-- =========================================================
SELECT throws_like(
    $$ SELECT * FROM anagrafiche.fn_update_cliente(-1::bigint, NULL, '{}'::jsonb) $$,
    '%non trovato%',
    'Not found: cliente inesistente => errore E_CLIENTE_NON_TROVATO');

-- =========================================================
-- NOTHING TO CHANGE: nessuna categoria, nessun campo => (false, false)
-- =========================================================
CREATE TEMP TABLE r_nothing AS
SELECT * FROM anagrafiche.fn_update_cliente(
    (SELECT id FROM tmp_cliente), NULL, '{}'::jsonb);

SELECT is((SELECT categoria_aggiornata FROM r_nothing), FALSE,
          'Nothing: categoria_aggiornata = FALSE');
SELECT is((SELECT campi_aggiornati FROM r_nothing), FALSE,
          'Nothing: campi_aggiornati = FALSE');

-- =========================================================
-- SOLO CATEGORIA: torna a C1, senza toccare campi cliente
-- =========================================================
CREATE TEMP TABLE r_onlycat AS
SELECT * FROM anagrafiche.fn_update_cliente(
    (SELECT id FROM tmp_cliente), (SELECT cat_c1 FROM k), '{}'::jsonb);

SELECT is((SELECT categoria_aggiornata FROM r_onlycat), TRUE,
          'Solo categoria: categoria_aggiornata = TRUE');
SELECT is(
    (SELECT categoria_cliente_id FROM anagrafiche.billing_account
      WHERE id = (SELECT id FROM tmp_billing_account)),
    (SELECT cat_c1 FROM k),
    'Solo categoria: categoria BA persistita = C1');

SELECT * FROM finish();

ROLLBACK;
