-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce DUE aziende e un cliente con
--   billing account legato alla prima: come `zeroerp_app` l'INSERT del BA
--   muore al RETURNING quando l'emittente di chi agisce non e' quello di
--   default (la policy di lettura risolve il BA non ancora mappato sul
--   default; il legame lo scrive un trigger AFTER). Il perimetro che qui si
--   misura lo applicano LE FUNZIONI DI RICERCA (scope esplicito, risolto da
--   `app.current_user_id`), non una policy: il ruolo di connessione non cambia
--   cio' che rispondono.
-- pgTAP test per Zero ERP
--
-- Passo 1 del cantiere «perimetro emittente» (decisione Q2/C):
-- la ricerca universale risolve lo scope emittente DA SE'.
-- Brief: brief-db-perimetro-emittente-liste-e-gerarchia-ba.md
--
-- Elenco test (plan 15):
--    0) PRECONDIZIONE: il contesto pgTAP e' un operatore con scope proprio
--   script.fn_get_emittenti_scope_sr_effettivo
--    1) restrizione assente (NULL) -> NON e' NULL           ⭐ la correzione
--    2) restrizione assente (NULL) -> = scope di diritto
--    3) restrizione vuota ('{}')   -> '{}', mai NULL
--    4) restrizione fuori scope    -> '{}'  (non allarga)
--    5) restrizione = proprio scope-> scope di diritto
--    6) attore nullo + nessuna restrizione -> NULL (convenzione famiglia)
--    7) attore nullo + restrizione -> la restrizione resta valida
--   script.fn_search_soggetti_universale
--    8) il parametro non decide piu': NULL == proprio scope (conteggio)
--    9) restrizione fuori scope -> zero risultati
--   script.fn_get_search_detail
--   10) il parametro non decide piu': NULL == proprio scope
--   11) restrizione fuori scope -> righe vuote
--   fixture a DUE emittenti
--   12) PRECONDIZIONE: il cliente di prova, oggi, la ricerca lo TROVA
--   13) * spostato il suo BA sull'altro emittente, il cliente SPARISCE
--   14)   per lo scope-universo c'e' ancora: sparito dal perimetro, non dai dati
--
-- Scopo:
--  - verificare che NESSUN valore passato dal chiamante possa ALLARGARE
--    cio' che le due funzioni di ricerca mostrano. Prima, il filtro si
--    accendeva su `p_emittente_ids IS NOT NULL`: NULL — cioe' cio' in cui
--    Python appiattisce la lista vuota — valeva «nessuna restrizione».
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (2026-09-12). Fino a quel giorno i
--   test 8-14 pescavano un cliente e un secondo emittente fra i dati ESISTENTI
--   e, se non li trovavano, SALTAVANO — «istanza con un solo emittente attivo».
--   Su un database ricostruito dai changelog: contesto vuoto, test 1-5 rossi e
--   8-14 saltati. Ora:
--     - due aziende A e B con `dbops.fn_pgtap_crea_emittente_operatore()`, piu'
--       una terza il cui operatore diventa super admin (binding SUPER_ADMIN)
--       per la contro-asserzione del test 14;
--     - un cliente con billing account legato ad A, con
--       `dbops.fn_pgtap_crea_cliente_ba(..., A)`: e' per costruzione MAPPATO,
--       dentro il mio scope, fuori da qualunque albero, senza storia e con un
--       solo BA — le cinque condizioni che la vecchia fixture doveva cercare;
--     - la ragione sociale porta un termine che nessun altro soggetto ha, cosi'
--       la ricerca dei test 8-13 e' significativa e non pesca il rumore
--       dell'istanza.
--   Il mondo si costruisce PRIMA di aprire il contesto: con un operatore in
--   sessione il trigger z90 del BA scriverebbe un secondo legame.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- Fixture: il mondo
-- ============================================================
CREATE TEMP TABLE _mondi ON COMMIT DROP AS
SELECT 'A'  AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B'  AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'SA' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

INSERT INTO config.profili_accesso_bindings
    (profilo_accesso_id, identita_digitale_id, attivo)
VALUES ((SELECT id FROM config.profili_accesso WHERE codice = 'SUPER_ADMIN'),
        (SELECT identita_id FROM _mondi WHERE lato = 'SA'), true);

-- Il cliente di prova, legato ad A. Il termine di ricerca e' una parola che
-- esiste solo qui.
-- ⚠️ Utility BASE (richiede_pdp = false): la riga in anagrafiche.clienti qui
--   sotto passa da un guard che pretende il PDP per ENERGIA/GAS/IDRICO, e un
--   punto di prelievo non appartiene a questo test.
CREATE TEMP TABLE _t_cliente ON COMMIT DROP AS
SELECT c.*, 'ZQXWSCOPE'::text AS termine
  FROM dbops.fn_pgtap_crea_cliente_ba(
           'ZQXWSCOPE',
           (SELECT u.id FROM config.utilities u WHERE u.codice_interno = 'BASE'),
           (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'A')) c;

-- ⚠️ La riga in anagrafiche.clienti va scritta a parte: l'helper si ferma al
--   billing account, e il filtro di scope della ricerca (ramo CL) risolve
--   l'emittente passando da `clienti.billing_account_id`. Senza questa riga il
--   soggetto esiste ma la ricerca non lo considera un cliente — e i test 12-14
--   misurerebbero l'assenza di una riga, non il perimetro. Stesse colonne che
--   scrive il backend (clienti_repository.create_cliente).
INSERT INTO anagrafiche.clienti
    (istanza_utility_id, billing_account_id, soggetto_ruolo_id,
     stato_cliente_id, data_attivazione)
SELECT c.istanza_utility_id, c.billing_account_id, c.soggetto_ruolo_id,
       (SELECT sc.id FROM config.stati_cliente sc WHERE sc.codice_interno = 'AT'),
       CURRENT_DATE
  FROM _t_cliente c;

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'A'));
END $ctx$;

-- L'operatore di contesto e' NON super admin e CON la sua riga in
-- config.user_emittenti_fiscali: quindi il suo scope di diritto e' un array
-- di cardinalita' 1, mai NULL. Su questo poggiano i test 1-5: senza,
-- misurerebbero il ramo super admin.
CREATE TEMP TABLE _t_ctx ON COMMIT DROP AS
SELECT m.auth_user_id AS user_id FROM _mondi m WHERE m.lato = 'A';

CREATE TEMP TABLE _t_scope ON COMMIT DROP AS
SELECT script.fn_get_emittenti_scope_sr_ids((SELECT user_id FROM _t_ctx)) AS sr_ids;

-- Un soggetto_ruolo_id che NON esiste: per costruzione fuori da qualunque
-- scope. ⚠️ Non e' l'emittente B: quello serve ai test 12-14, dove il BA si
--   sposta davvero; qui l'id inesistente e' la scelta giusta.
CREATE TEMP TABLE _t_fuori ON COMMIT DROP AS
SELECT COALESCE(MAX(sr.id), 0) + 1000000 AS sr_id
  FROM anagrafiche.soggetti_ruoli sr;

-- Precondizione dichiarata: se saltasse, i test 1-5 sarebbero verdi per
-- sottrazione (confronterebbero NULL con NULL).
SELECT isnt(
    (SELECT sr_ids FROM _t_scope),
    NULL,
    '0. PRECONDIZIONE: il contesto pgTAP e'' un operatore con scope proprio (non super admin)'
);

-- ============================================================
-- Asserzioni — la funzione di scope effettivo
-- ============================================================

SELECT isnt(
    script.fn_get_emittenti_scope_sr_effettivo((SELECT user_id FROM _t_ctx), NULL),
    NULL,
    '1. ⭐ restrizione assente (NULL) NON significa piu'' "nessuna restrizione"'
);

SELECT is(
    script.fn_get_emittenti_scope_sr_effettivo((SELECT user_id FROM _t_ctx), NULL),
    (SELECT sr_ids FROM _t_scope),
    '2. restrizione assente -> vale lo scope di diritto'
);

SELECT is(
    script.fn_get_emittenti_scope_sr_effettivo((SELECT user_id FROM _t_ctx), '{}'::bigint[]),
    '{}'::bigint[],
    '3. restrizione vuota resta vuota: ''{}'' non degrada mai a NULL'
);

SELECT is(
    script.fn_get_emittenti_scope_sr_effettivo(
        (SELECT user_id FROM _t_ctx),
        ARRAY[(SELECT sr_id FROM _t_fuori)]::bigint[]
    ),
    '{}'::bigint[],
    '4. restrizione fuori scope -> ''{}'': l''intersezione non allarga'
);

SELECT is(
    script.fn_get_emittenti_scope_sr_effettivo(
        (SELECT user_id FROM _t_ctx),
        (SELECT sr_ids FROM _t_scope)
    ),
    (SELECT sr_ids FROM _t_scope),
    '5. restrizione = proprio scope -> invariato (il caso del backend di oggi)'
);

-- Attore nullo: convenzione della famiglia (fn_scope_ef_whitelist_via_efba
-- ramo 1). Non e' un fail-open nuovo, e' quello gia' dichiarato altrove.
SELECT is(
    script.fn_get_emittenti_scope_sr_effettivo(NULL, NULL),
    NULL,
    '6. attore nullo (batch) senza restrizione -> NULL, come da convenzione famiglia'
);

SELECT is(
    script.fn_get_emittenti_scope_sr_effettivo(
        NULL,
        ARRAY[(SELECT sr_id FROM _t_fuori)]::bigint[]
    ),
    ARRAY[(SELECT sr_id FROM _t_fuori)]::bigint[],
    '7. attore nullo CON restrizione -> la restrizione resta: e'' restringente'
);

-- ============================================================
-- Asserzioni — le due funzioni di ricerca
-- ============================================================
-- Serve il tipo ruolo CL (l'unico a cui si applica il filtro emittente) e un
-- termine che matchi almeno una riga: senza, il confronto sarebbe vacuo
-- (0 = 0) e il file diventerebbe verde per sottrazione. Il termine e' quello
-- del cliente costruito, che matcha lui e nessun altro.
CREATE TEMP TABLE _t_cl ON COMMIT DROP AS
SELECT tr.id AS tipo_ruolo_id
  FROM config.tipi_ruoli tr
 WHERE tr.codice_interno = 'CL';

CREATE TEMP TABLE _t_cl_sog ON COMMIT DROP AS
SELECT c.soggetto_id, c.termine FROM _t_cliente c;

SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        NULL)),
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        (SELECT sr_ids FROM _t_scope))),
    '8. ricerca CL: passare NULL o il proprio scope da lo stesso risultato (il parametro non decide piu'')'
);

SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        ARRAY[(SELECT sr_id FROM _t_fuori)]::bigint[])),
    0::bigint,
    '9. ricerca CL con restrizione fuori scope -> zero risultati (fail-closed)'
);

SELECT is(
    script.fn_get_search_detail(
        (SELECT soggetto_id FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        NULL,
        NULL),
    script.fn_get_search_detail(
        (SELECT soggetto_id FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        NULL,
        (SELECT sr_ids FROM _t_scope)),
    '10. dettaglio CL: passare NULL o il proprio scope da lo stesso risultato'
);

SELECT is(
    script.fn_get_search_detail(
        (SELECT soggetto_id FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        NULL,
        ARRAY[(SELECT sr_id FROM _t_fuori)]::bigint[]) -> 'righe',
    '[]'::jsonb,
    '11. dettaglio CL con restrizione fuori scope -> righe vuote (fail-closed)'
);

-- ============================================================
-- 12-14) ⭐ LA FIXTURE A DUE EMITTENTI
--
--   I test 8-11 verificano l'INVARIANTE «il parametro non decide piu'»: due
--   chiamate che devono dare lo stesso risultato. Nessuno di loro dimostra la
--   cosa che al perimetro interessa davvero — che un cliente di un ALTRO
--   emittente SPARISCE. Per quello si sposta davvero il billing account del
--   cliente sotto l'altro emittente (B) e si guarda se la ricerca lo mostra
--   ancora.
--
--   ⭐ E si chiude con la contro-asserzione che rende il verde leggibile: il
--   soggetto non e' sparito dai DATI, e' sparito dal PERIMETRO. Senza il
--   test 14 un errore di fixture — soggetto cancellato, termine sbagliato —
--   darebbe lo stesso zero del test 13, e verrebbe letto come una prova.
--
--   ⚠️ Lo spostamento passa dal guard di storia (20260826-49): un cliente che
--   ha gia' documenti numerati non si sposta. Il cliente costruito non ne ha,
--   per costruzione.
-- ============================================================
CREATE TEMP TABLE _t_ef2 ON COMMIT DROP AS
SELECT m.soggetto_ruolo_id AS ef_altro FROM _mondi m WHERE m.lato = 'B';

CREATE TEMP TABLE _t_due ON COMMIT DROP AS
SELECT c.soggetto_ruolo_id, c.billing_account_id AS ba_id, c.termine
  FROM _t_cliente c;

-- 12) Precondizione: oggi quel cliente la ricerca lo TROVA. Senza questa riga
--     i due test sotto sarebbero verdi anche partendo da zero risultati.
SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_due), (SELECT tipo_ruolo_id FROM _t_cl), NULL) r
      WHERE r.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _t_due)),
    1::bigint,
    '12. PRECONDIZIONE fixture a due emittenti: il cliente di prova oggi si vede'
);

-- Lo spostamento: il billing account del cliente passa all'ALTRO emittente.
UPDATE anagrafiche.emittenti_fiscali_billing_account
   SET emittente_soggetto_ruolo_id = (SELECT ef_altro FROM _t_ef2)
 WHERE billing_account_id = (SELECT ba_id FROM _t_due);

-- 13) ⭐ Il cliente di un altro emittente SPARISCE dalla ricerca. E' la cosa
--     che i test 8-11 non dimostravano.
SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_due), (SELECT tipo_ruolo_id FROM _t_cl), NULL) r
      WHERE r.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _t_due)),
    0::bigint,
    '13. ⭐ spostato il BA sull''altro emittente, il cliente sparisce dalla ricerca'
);

-- 14) La contro-asserzione: per chi ha l'universo nello scope il soggetto c'e'
--     ancora. Sparito dal perimetro, non dai dati.
SELECT set_config('app.current_user_id',
                  (SELECT m.auth_user_id FROM _mondi m WHERE m.lato = 'SA')::text,
                  false);

SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_due), (SELECT tipo_ruolo_id FROM _t_cl), NULL) r
      WHERE r.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _t_due)),
    1::bigint,
    '14. per lo scope-universo il soggetto c''e'' ancora: sparito dal perimetro, non dai dati'
);

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
