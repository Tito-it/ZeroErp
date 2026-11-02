-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
-- Elenco test (plan 10):
--    0) PRECONDIZIONE: il contesto pgTAP e' un operatore con scope proprio
--   «non c'e'» del dettaglio (R-4)
--    1) soggetto inesistente -> NULL
--    2) soggetto senza quel ruolo -> NULL
--    3) cliente visibile, nessun filtro -> righe presenti
--    4) cliente visibile, utility che non ha -> righe = [], NON NULL
--   ruolo non ricercabile (Q-2)
--    5) * dettaglio su EF (ricerca_visibile = false) -> E_TIPO_RUOLO_NON_RICERCABILE
--   fixture a DUE emittenti
--    6) PRECONDIZIONE: il cliente di prova, oggi, la ricerca lo TROVA
--    7) * spostato il suo BA sull'altro emittente, la lista non lo mostra (RLS)
--    8) * e il dettaglio risponde NULL: stesso perimetro della lista
--    9)   per lo scope-universo c'e' ancora: sparito dal perimetro, non dai dati
--
-- Rev 2026-10-08 (brief-db-codici-non-trovato-email-e-permessi §5, R-4): il
--   perimetro dei clienti passa alla RLS (cade il filtro a mano delle due
--   funzioni) e il dettaglio dice «non c'e'».
-- Rev 2026-10-10 (stesso brief, R-5, R-6, R-9, Q-2):
--   * escono i test 1-7, che provavano fn_get_emittenti_scope_sr_effettivo
--     (ritirata, 20261010-14), e 8-11, che pinnavano il parametro superato
--     p_emittente_ids (uscito dalla firma, 20261010-11/-12). La proprieta'
--     «utente NULL = nessun accesso» resta provata sulla canonica in
--     script/test-scope-emittenti-fail-closed-v1 (test 10);
--   * il vecchio 16 (ramo ELSE su EF -> una riga) diventa il 5: EF ha
--     ricerca_visibile = false, e dal 2026-10-10 lo dice il DB. Il ramo ELSE
--     con un ruolo ricercabile, la regola unica su entita_esistenza e lo
--     stato dell'entita' li prova script/test-search-regola-unica-visibile-v1;
--   * la riga di anagrafiche.clienti non si scrive piu' a mano: la fa
--     dbops.fn_pgtap_crea_cliente (R-9, regola del 2);
--   * le chiamate alla lista non passano piu' un NULL in terza posizione,
--     che era p_emittente_ids e oggi sarebbe p_limit.
--
-- Scopo:
--  - verificare che lista e dettaglio della ricerca universale rispondano
--    UGUALE su chi si vede, e che il perimetro dei clienti lo faccia la RLS:
--    un cliente di un altro emittente sparisce da tutte e due, e il soggetto
--    resta nei dati (contro-asserzione 9).
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (2026-09-12). Fino a quel giorno i
--   test 8-14 pescavano un cliente e un secondo emittente fra i dati ESISTENTI
--   e, se non li trovavano, SALTAVANO — «istanza con un solo emittente attivo».
--   Su un database ricostruito dai changelog: contesto vuoto, test 1-5 rossi e
--   8-14 saltati. Ora:
--     - due aziende A e B con `dbops.fn_pgtap_crea_emittente_operatore()`, piu'
--       una terza il cui operatore diventa super admin (binding SUPER_ADMIN)
--       per la contro-asserzione del test 9;
--     - un cliente con billing account legato ad A, con
--       `dbops.fn_pgtap_crea_cliente(..., A)`: e' per costruzione MAPPATO,
--       dentro il mio scope, fuori da qualunque albero, senza storia e con un
--       solo BA — le cinque condizioni che la vecchia fixture doveva cercare;
--     - la ragione sociale porta un termine che nessun altro soggetto ha, cosi'
--       la ricerca dei test 6-9 e' significativa e non pesca il rumore
--       dell'istanza.
--   Il mondo si costruisce PRIMA di aprire il contesto: con un operatore in
--   sessione il trigger z90 del BA scriverebbe un secondo legame.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- Fixture: il mondo
-- ============================================================
CREATE TEMP TABLE _mondi ON COMMIT DROP AS
SELECT 'A'  AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B'  AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'SA' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $lega$ BEGIN PERFORM config.fn_lega_profilo_identita((SELECT id FROM config.profili_accesso WHERE codice = 'SUPER_ADMIN'), (SELECT identita_id FROM _mondi WHERE lato = 'SA')); END $lega$;

-- Il cliente di prova, legato ad A. Il termine di ricerca e' una parola che
-- esiste solo qui.
-- ⚠️ Utility BASE (richiede_pdp = false): la riga in anagrafiche.clienti
--   passa da un guard che pretende il PDP per ENERGIA/GAS/IDRICO, e un
--   punto di prelievo non appartiene a questo test.
-- ⭐ Rev 2026-10-10 (R-9): la riga di anagrafiche.clienti la scrive il
--   builder, stato AT con la sua data di attivazione. Prima la scriveva questo
--   file a mano dopo fn_pgtap_crea_cliente_ba: senza quella riga il soggetto
--   esiste ma per la ricerca non e' un cliente, e i test misurerebbero
--   l'assenza di una riga, non il perimetro.
CREATE TEMP TABLE _t_cliente ON COMMIT DROP AS
SELECT c.*, 'ZQXWSCOPE'::text AS termine
  FROM dbops.fn_pgtap_crea_cliente(
           'ZQXWSCOPE',
           (SELECT u.id FROM config.utilities u WHERE u.codice_interno = 'BASE'),
           (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'A')) c;

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'A'));
END $ctx$;

-- L'operatore di contesto e' NON super admin e CON la sua riga in
-- config.user_emittenti_fiscali: quindi il suo scope di diritto e' un array
-- di cardinalita' 1, mai NULL. Su questo poggiano i test 6-8: senza,
-- misurerebbero il ramo super admin, che vede tutto.
CREATE TEMP TABLE _t_ctx ON COMMIT DROP AS
SELECT m.auth_user_id AS user_id FROM _mondi m WHERE m.lato = 'A';

CREATE TEMP TABLE _t_scope ON COMMIT DROP AS
SELECT script.fn_get_emittenti_scope_sr_ids((SELECT user_id FROM _t_ctx)) AS sr_ids;

-- Precondizione dichiarata: se saltasse, il contesto sarebbe uno scope-universo
-- e i test 7-8 sarebbero rossi per la ragione sbagliata, o verdi per caso.
SELECT isnt(
    (SELECT sr_ids FROM _t_scope),
    NULL,
    '0. PRECONDIZIONE: il contesto pgTAP e'' un operatore con scope proprio (non super admin)'
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

-- ============================================================
-- 1-4) ⭐ IL «NON C'E'» DEL DETTAGLIO (rev 2026-10-08, R-4)
--
--   Prima la funzione non restituiva mai NULL: {"righe": []} copriva
--   inesistente, senza ruolo, fuori perimetro e filtro utility a vuoto. Ora
--   NULL (-> 404) per i primi tre, righe = [] solo per il filtro utility.
--   Soggetti COSTRUITI nel test: nessun confronto con i dati presenti.
-- ============================================================

-- 1) Un soggetto che non esiste: uuid nuovo, per costruzione assente.
SELECT is(
    script.fn_get_search_detail(uuidv7(), (SELECT tipo_ruolo_id FROM _t_cl)),
    NULL::jsonb,
    '1. ⭐ soggetto inesistente -> NULL (era {"righe": []})'
);

-- 2) Il soggetto del cliente esiste, ma non e' fornitore.
SELECT is(
    script.fn_get_search_detail(
        (SELECT soggetto_id FROM _t_cl_sog),
        (SELECT tr.id FROM config.tipi_ruoli tr WHERE tr.codice_interno = 'FO')),
    NULL::jsonb,
    '2. ⭐ soggetto senza quel ruolo -> NULL'
);

-- 3) Il cliente visibile, nessun filtro: il caso che c'era gia'.
SELECT is(
    jsonb_array_length(script.fn_get_search_detail(
        (SELECT soggetto_id FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl)) -> 'righe'),
    1,
    '3. cliente visibile senza filtro -> la sua riga'
);

-- 4) Lo stesso cliente, filtrato su un'utility che non ha: il soggetto c'e',
--     e' il filtro che restringe a zero. Risultato vero, non «non trovato».
SELECT is(
    script.fn_get_search_detail(
        (SELECT soggetto_id FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        (SELECT u.id FROM config.utilities u
          WHERE u.id <> (SELECT c.utility_id FROM _t_cliente c)
          ORDER BY u.id LIMIT 1)) -> 'righe',
    '[]'::jsonb,
    '4. ⭐ cliente visibile, utility che non ha -> righe = [] (non NULL: la cosa c''e'')'
);

-- ============================================================
-- 5) ⭐ RUOLO NON RICERCABILE (rev 2026-10-10, Q-2)
--
--   EF ha ricerca_visibile = false. Fino al 2026-10-10 lo controllava solo il
--   backend e il dettaglio rispondeva una riga (era il vecchio test 16, ramo
--   ELSE); ora lo dice la regola unica del DB, per lista e dettaglio. Il
--   codice viaggia nel canale CONSTRAINT_NAME dell'eccezione P0001: si pinna
--   il codice, non la frase del catalogo.
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

SELECT is(
    pg_temp.codice_errore(format(
        $q$SELECT script.fn_get_search_detail(%L::uuid, %s)$q$,
        (SELECT sr.soggetto_id FROM anagrafiche.soggetti_ruoli sr
          WHERE sr.id = (SELECT m.soggetto_ruolo_id FROM _mondi m WHERE m.lato = 'A')),
        (SELECT tr.id FROM config.tipi_ruoli tr WHERE tr.codice_interno = 'EF'))),
    'E_TIPO_RUOLO_NON_RICERCABILE',
    '5. ⭐ dettaglio su EF (ricerca_visibile = false) -> E_TIPO_RUOLO_NON_RICERCABILE (era una riga)'
);

-- ============================================================
-- 6-9) ⭐ LA FIXTURE A DUE EMITTENTI
--
--   Si sposta davvero il billing account del cliente sotto l'altro emittente
--   (B) e si guarda se lista e dettaglio lo mostrano ancora. Dal 2026-10-08
--   a nasconderlo e' la RLS di anagrafiche.clienti, non un filtro delle
--   funzioni: lista e dettaglio devono rispondere uguale.
--
--   ⭐ E si chiude con la contro-asserzione che rende il verde leggibile: il
--   soggetto non e' sparito dai DATI, e' sparito dal PERIMETRO. Senza il
--   test 9 un errore di fixture — soggetto cancellato, termine sbagliato —
--   darebbe lo stesso zero del test 7, e verrebbe letto come una prova.
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

-- 6) Precondizione: oggi quel cliente la ricerca lo TROVA. Senza questa riga
--     i test sotto sarebbero verdi anche partendo da zero risultati.
SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_due), (SELECT tipo_ruolo_id FROM _t_cl)) r
      WHERE r.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _t_due)),
    1::bigint,
    '6. PRECONDIZIONE fixture a due emittenti: il cliente di prova oggi si vede'
);

-- Lo spostamento: il billing account del cliente passa all'ALTRO emittente.
UPDATE anagrafiche.emittenti_fiscali_billing_account
   SET emittente_soggetto_ruolo_id = (SELECT ef_altro FROM _t_ef2)
 WHERE billing_account_id = (SELECT ba_id FROM _t_due);

-- 7) ⭐ Il cliente di un altro emittente SPARISCE dalla lista.
SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_due), (SELECT tipo_ruolo_id FROM _t_cl)) r
      WHERE r.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _t_due)),
    0::bigint,
    '7. ⭐ spostato il BA sull''altro emittente, il cliente sparisce dalla lista (RLS)'
);

-- 8) ⭐ E il dettaglio dice «non c'e'»: inesistente e fuori perimetro escono
--     uguali, di proposito (il 404 non rivela un cliente di un altro emittente).
SELECT is(
    script.fn_get_search_detail(
        (SELECT soggetto_id FROM _t_due), (SELECT tipo_ruolo_id FROM _t_cl)),
    NULL::jsonb,
    '8. ⭐ il dettaglio dello stesso cliente -> NULL: stesso perimetro della lista'
);

-- 9) La contro-asserzione: per chi ha l'universo nello scope il soggetto c'e'
--     ancora. Sparito dal perimetro, non dai dati.
SELECT set_config('app.current_user_id',
                  (SELECT m.auth_user_id FROM _mondi m WHERE m.lato = 'SA')::text,
                  false);

SELECT is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_due), (SELECT tipo_ruolo_id FROM _t_cl)) r
      WHERE r.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _t_due)),
    1::bigint,
    '9. per lo scope-universo il soggetto c''e'' ancora: sparito dal perimetro, non dai dati'
);

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
