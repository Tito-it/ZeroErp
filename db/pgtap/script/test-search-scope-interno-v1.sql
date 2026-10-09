-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce DUE aziende e un cliente con
--   billing account legato alla prima: come `zeroerp_app` l'INSERT del BA
--   muore al RETURNING quando l'emittente di chi agisce non e' quello di
--   default (la policy di lettura risolve il BA non ancora mappato sul
--   default; il legame lo scrive un trigger AFTER). Dal 2026-10-08 il
--   perimetro dei clienti lo applica la RLS di anagrafiche.clienti, non piu'
--   un filtro dentro le funzioni: le asserzioni sulle ricerche girano dopo
--   `ALTER TABLE anagrafiche.clienti FORCE ROW LEVEL SECURITY`, dentro questa
--   transazione, cosi' l'owner subisce le policy come l'app.
-- pgTAP test per Zero ERP
--
-- Passo 1 del cantiere «perimetro emittente» (decisione Q2/C):
-- la ricerca universale risolve lo scope emittente DA SE'.
-- Brief: brief-db-perimetro-emittente-liste-e-gerarchia-ba.md
--
-- Elenco test (plan 21):
--    0) PRECONDIZIONE: il contesto pgTAP e' un operatore con scope proprio
--   script.fn_get_emittenti_scope_sr_effettivo
--    1) restrizione assente (NULL) -> NON e' NULL           ⭐ la correzione
--    2) restrizione assente (NULL) -> = scope di diritto
--    3) restrizione vuota ('{}')   -> '{}', mai NULL
--    4) restrizione fuori scope    -> '{}'  (non allarga)
--    5) restrizione = proprio scope-> scope di diritto
--    6) attore nullo + nessuna restrizione -> '{}' (rev 2026-10-04, Q-1: era NULL)
--    7) attore nullo + restrizione -> '{}' (rev 2026-10-04, Q-1: era la restrizione)
--   le due ricerche, con FORCE ROW LEVEL SECURITY su anagrafiche.clienti
--    8) lista: p_emittente_ids NULL == proprio scope (parametro superato)
--    9) lista: restrizione fuori scope == NULL (superato: non e' piu' letto)
--   10) dettaglio: NULL == proprio scope
--   11) dettaglio: restrizione fuori scope == NULL (superato)
--   «non c'e'» del dettaglio (rev 2026-10-08, R-4, decisione di Tid)
--   12) soggetto inesistente -> NULL
--   13) soggetto senza quel ruolo -> NULL
--   14) cliente visibile, nessun filtro -> righe presenti
--   15) cliente visibile, utility che non ha -> righe = [], NON NULL
--   16) ramo ELSE (EF) con soggetto-ruolo esistente -> una riga
--   fixture a DUE emittenti
--   17) PRECONDIZIONE: il cliente di prova, oggi, la ricerca lo TROVA
--   18) * spostato il suo BA sull'altro emittente, la lista non lo mostra (RLS)
--   19) * e il dettaglio risponde NULL: stesso perimetro della lista
--   20)   per lo scope-universo c'e' ancora: sparito dal perimetro, non dai dati
--
-- Rev 2026-10-08 (brief-db-codici-non-trovato-email-e-permessi §5, R-4): il
--   perimetro dei clienti passa alla RLS (cade il filtro a mano delle due
--   funzioni) e il dettaglio dice «non c'e'». I test 9 e 11 erano «restrizione
--   fuori scope -> zero/righe vuote (fail-closed)»: il parametro e' superato e
--   non si legge piu', quindi pinnano ora che NON decide. La sparizione del
--   cliente fuori perimetro la provano 18 e 19, ed e' la RLS a farla.
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

SELECT plan(21);

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
       script.fn_data_operativa()
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

-- Attore nullo: nessun accesso.
-- ⚠️ Rev 2026-10-04 (Q-1, brief-db-esclusioni-implicite): qui si pinnava la
--   «convenzione della famiglia» (utente NULL = nessuno scope di diritto da
--   opporre), cioe' NULL = tutto per le due ricerche, che leggono l'utente
--   dalla GUC. La famiglia e' cambiata insieme (canonica, via_efba): un
--   utente NULL non vede niente, con o senza restrizione.
SELECT is(
    script.fn_get_emittenti_scope_sr_effettivo(NULL, NULL),
    '{}'::bigint[],
    '6. attore nullo senza restrizione -> ''{}'' (era NULL = tutto)'
);

SELECT is(
    script.fn_get_emittenti_scope_sr_effettivo(
        NULL,
        ARRAY[(SELECT sr_id FROM _t_fuori)]::bigint[]
    ),
    '{}'::bigint[],
    '7. attore nullo CON restrizione -> ''{}'' (era la restrizione stessa)'
);

-- ============================================================
-- Asserzioni — le due funzioni di ricerca
-- ============================================================
-- Serve il tipo ruolo CL e un termine che matchi almeno una riga: senza, il
-- confronto sarebbe vacuo (0 = 0) e il file diventerebbe verde per
-- sottrazione. Il termine e' quello del cliente costruito, che matcha lui e
-- nessun altro.
CREATE TEMP TABLE _t_cl ON COMMIT DROP AS
SELECT tr.id AS tipo_ruolo_id
  FROM config.tipi_ruoli tr
 WHERE tr.codice_interno = 'CL';

CREATE TEMP TABLE _t_cl_sog ON COMMIT DROP AS
SELECT c.soggetto_id, c.termine FROM _t_cliente c;

-- ⭐ Da qui in poi l'owner subisce la RLS di anagrafiche.clienti, come l'app
--   (rev 2026-10-08): il perimetro dei clienti lo fa la policy, e un owner
--   senza FORCE la salterebbe. Il ROLLBACK finale lo spegne.
-- ⚠️ lock_timeout: e' DDL su una tabella condivisa, meglio un errore leggibile
--   che un'attesa muta dietro un'altra sessione.
SET LOCAL lock_timeout = '5s';
ALTER TABLE anagrafiche.clienti FORCE ROW LEVEL SECURITY;
RESET lock_timeout;

-- 8-11) Il parametro p_emittente_ids e' SUPERATO (2026-10-08): non si legge
--   piu', quindi qualunque valore da' lo stesso risultato di NULL.
SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        NULL)),
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        (SELECT sr_ids FROM _t_scope))),
    '8. ricerca CL: passare NULL o il proprio scope da lo stesso risultato (il parametro non decide)'
);

SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        ARRAY[(SELECT sr_id FROM _t_fuori)]::bigint[])),
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        NULL)),
    '9. ricerca CL: una restrizione fuori scope non cambia niente (p_emittente_ids superato, il perimetro e'' la RLS)'
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
        ARRAY[(SELECT sr_id FROM _t_fuori)]::bigint[]),
    script.fn_get_search_detail(
        (SELECT soggetto_id FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        NULL,
        NULL),
    '11. dettaglio CL: una restrizione fuori scope non cambia niente (p_emittente_ids superato)'
);

-- ============================================================
-- 12-16) ⭐ IL «NON C'E'» DEL DETTAGLIO (rev 2026-10-08, R-4)
--
--   Prima la funzione non restituiva mai NULL: {"righe": []} copriva
--   inesistente, senza ruolo, fuori perimetro e filtro utility a vuoto. Ora
--   NULL (-> 404) per i primi tre, righe = [] solo per il filtro utility.
--   Soggetti COSTRUITI nel test: nessun confronto con i dati presenti.
-- ============================================================

-- 12) Un soggetto che non esiste: uuid nuovo, per costruzione assente.
SELECT is(
    script.fn_get_search_detail(uuidv7(), (SELECT tipo_ruolo_id FROM _t_cl)),
    NULL::jsonb,
    '12. ⭐ soggetto inesistente -> NULL (era {"righe": []})'
);

-- 13) Il soggetto del cliente esiste, ma non e' fornitore.
SELECT is(
    script.fn_get_search_detail(
        (SELECT soggetto_id FROM _t_cl_sog),
        (SELECT tr.id FROM config.tipi_ruoli tr WHERE tr.codice_interno = 'FO')),
    NULL::jsonb,
    '13. ⭐ soggetto senza quel ruolo -> NULL'
);

-- 14) Il cliente visibile, nessun filtro: il caso che c'era gia'.
SELECT is(
    jsonb_array_length(script.fn_get_search_detail(
        (SELECT soggetto_id FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl)) -> 'righe'),
    1,
    '14. cliente visibile senza filtro -> la sua riga'
);

-- 15) Lo stesso cliente, filtrato su un'utility che non ha: il soggetto c'e',
--     e' il filtro che restringe a zero. Risultato vero, non «non trovato».
SELECT is(
    script.fn_get_search_detail(
        (SELECT soggetto_id FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        (SELECT u.id FROM config.utilities u
          WHERE u.id <> (SELECT c.utility_id FROM _t_cliente c)
          ORDER BY u.id LIMIT 1)) -> 'righe',
    '[]'::jsonb,
    '15. ⭐ cliente visibile, utility che non ha -> righe = [] (non NULL: la cosa c''e'')'
);

-- 16) Ramo ELSE: l'emittente A come soggetto-ruolo EF, che esiste.
SELECT is(
    jsonb_array_length(script.fn_get_search_detail(
        (SELECT sr.soggetto_id FROM anagrafiche.soggetti_ruoli sr
          WHERE sr.id = (SELECT m.soggetto_ruolo_id FROM _mondi m WHERE m.lato = 'A')),
        (SELECT tr.id FROM config.tipi_ruoli tr WHERE tr.codice_interno = 'EF')) -> 'righe'),
    1,
    '16. ramo ELSE (EF) con soggetto-ruolo esistente -> una riga, come prima'
);

-- ============================================================
-- 17-20) ⭐ LA FIXTURE A DUE EMITTENTI
--
--   Si sposta davvero il billing account del cliente sotto l'altro emittente
--   (B) e si guarda se lista e dettaglio lo mostrano ancora. Dal 2026-10-08
--   a nasconderlo e' la RLS di anagrafiche.clienti, non un filtro delle
--   funzioni: lista e dettaglio devono rispondere uguale.
--
--   ⭐ E si chiude con la contro-asserzione che rende il verde leggibile: il
--   soggetto non e' sparito dai DATI, e' sparito dal PERIMETRO. Senza il
--   test 20 un errore di fixture — soggetto cancellato, termine sbagliato —
--   darebbe lo stesso zero del test 18, e verrebbe letto come una prova.
--
--   ⚠️ Lo spostamento passa dal guard di storia (20260826-49): un cliente che
--   ha gia' documenti numerati non si sposta. Il cliente costruito non ne ha,
--   per costruzione.
-- ============================================================
CREATE TEMP TABLE _t_ef2 ON COMMIT DROP AS
SELECT m.soggetto_ruolo_id AS ef_altro FROM _mondi m WHERE m.lato = 'B';

CREATE TEMP TABLE _t_due ON COMMIT DROP AS
SELECT c.soggetto_ruolo_id, c.soggetto_id, c.billing_account_id AS ba_id, c.termine
  FROM _t_cliente c;

-- 17) Precondizione: oggi quel cliente la ricerca lo TROVA. Senza questa riga
--     i test sotto sarebbero verdi anche partendo da zero risultati.
SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_due), (SELECT tipo_ruolo_id FROM _t_cl), NULL) r
      WHERE r.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _t_due)),
    1::bigint,
    '17. PRECONDIZIONE fixture a due emittenti: il cliente di prova oggi si vede'
);

-- Lo spostamento: il billing account del cliente passa all'ALTRO emittente.
UPDATE anagrafiche.emittenti_fiscali_billing_account
   SET emittente_soggetto_ruolo_id = (SELECT ef_altro FROM _t_ef2)
 WHERE billing_account_id = (SELECT ba_id FROM _t_due);

-- 18) ⭐ Il cliente di un altro emittente SPARISCE dalla lista.
SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_due), (SELECT tipo_ruolo_id FROM _t_cl), NULL) r
      WHERE r.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _t_due)),
    0::bigint,
    '18. ⭐ spostato il BA sull''altro emittente, il cliente sparisce dalla lista (RLS)'
);

-- 19) ⭐ E il dettaglio dice «non c'e'»: inesistente e fuori perimetro escono
--     uguali, di proposito (il 404 non rivela un cliente di un altro emittente).
SELECT is(
    script.fn_get_search_detail(
        (SELECT soggetto_id FROM _t_due), (SELECT tipo_ruolo_id FROM _t_cl)),
    NULL::jsonb,
    '19. ⭐ il dettaglio dello stesso cliente -> NULL: stesso perimetro della lista'
);

-- 20) La contro-asserzione: per chi ha l'universo nello scope il soggetto c'e'
--     ancora. Sparito dal perimetro, non dai dati.
SELECT set_config('app.current_user_id',
                  (SELECT m.auth_user_id FROM _mondi m WHERE m.lato = 'SA')::text,
                  false);

SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_due), (SELECT tipo_ruolo_id FROM _t_cl), NULL) r
      WHERE r.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _t_due)),
    1::bigint,
    '20. per lo scope-universo il soggetto c''e'' ancora: sparito dal perimetro, non dai dati'
);

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
