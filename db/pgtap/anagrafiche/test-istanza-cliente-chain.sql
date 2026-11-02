-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Elenco test (plan 26):
-- 1) Creato esattamente un PDP GAS dedicato al test
-- 2) Esiste uno stato_cliente con codice_interno = AT
-- 3) Esiste uno stato_cliente con codice_interno = AN
-- 4) Esiste uno stato_cliente con codice_interno = CH
-- 5) Costruito il soggetto 1
-- 6) Costruito il soggetto 2
-- 7) Creata istanza base di test collegata al PDP dedicato
-- 8) Inserito primo cliente di test per istanza base
-- 9) Per il primo cliente della catena, parent_istanza_id dell’istanza base è NULL
-- 10) Inserita seconda istanza_utility per lo stesso PDP
-- 11) fn_subentro_cliente chiude il cliente precedente attivo sul PDP (CLI1)
-- 12) Cliente precedente chiuso con data_chiusura = data attivazione nuovo - 1 giorno
-- 13) Cliente precedente impostato a stato CH dopo subentro
-- 14) Inserito secondo cliente ATTIVO su seconda istanza
-- 15) Seconda istanza ha parent_istanza_id puntato all’istanza base
-- 16) Inserita terza istanza_utility per lo stesso PDP
-- 17) fn_subentro_cliente chiude il cliente precedente attivo sul PDP (CLI2)
-- 18) Cliente precedente chiuso con data_chiusura = data attivazione nuovo - 1 giorno
-- 19) Cliente precedente impostato a stato CH dopo subentro
-- 20) Inserito terzo cliente ANNULLATO su terza istanza
-- 21) Istanza del cliente AN ha parent_istanza_id NULL (esclusa dalla catena)
-- 22) Inserita quarta istanza_utility per lo stesso PDP
-- 23) Inserito quarto cliente ATTIVO su quarta istanza
-- 24) Quarta istanza ha parent_istanza_id puntato alla seconda istanza
-- 25) Per il cliente 4, utility_id è coerente tra clienti e billing_account
-- 26) Nel dataset di test, il vincolo 1 cliente per istanza è rispettato
--
-- Scopo:
--  - Verificare la catena parent_istanza_id su anagrafiche.istanze_utilities
--    calcolata da anagrafiche.trgfn_clienti_set_parent_istanza()
--  - Integrare la logica con billing_account:
--      * Ogni cliente ha un billing_account collegato alla stessa istanza
--      * clienti.utility_id viene sincronizzato da billing_account.utility_id
--  - Scenario:
--      * PDP GAS dedicato al test (creato on-the-fly)
--      * 4 istanze/4 clienti sullo stesso PDP:
--          - CLI1: attivo (prima istanza) → parent_istanza_id NULL
--          - CLI2: attivo → parent_istanza_id = istanza CLI1
--          - CLI3: annullato (stato AN) → fuori dalla catena
--          - CLI4: attivo → parent_istanza_id = istanza CLI2
--        Verifiche:
--          - catena lineare corretta
--          - clienti AN esclusi
--          - fn_subentro_cliente chiude il cliente precedente (stato CH, data_chiusura -1 giorno)
--          - sync utility da billing_account
--          - 1 cliente per istanza (nel dataset di test)
-- Autore: Tid (
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. Messa in testa e non in coda
--   apposta: in coda scatterebbero tutti insieme DOPO il cleanup, su righe
--   ormai cancellate, e fallirebbero per un motivo che non riguarda il test.
--   Brief: brief-db-pgtap-runner-rls-baseline §17.
--   ⚠️ NON e' qui: vedi il `SET CONSTRAINTS ALL IMMEDIATE` piu' sotto, dopo
--   la quarta coppia istanza+billing_account. In testa scattava prima che
--   l'unita' di lavoro fosse completa, e il file moriva sulla fixture.

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(26);
-- =========================================================
--  Setup chiavi test univoche (evita DELETE bloccate da policy ruoli)
-- =========================================================
CREATE TEMP TABLE tmp_test_keys AS WITH s AS (
    SELECT substring(
            md5(clock_timestamp()::text || random()::text),
            1,
            8
        ) AS suffix
)
SELECT suffix,
    ('TST-IU-CB-' || suffix) AS iu_base_code,
    ('TST-IU-C2-' || suffix) AS iu_2_code,
    ('TST-IU-C3-' || suffix) AS iu_3_code,
    ('TST-IU-C4-' || suffix) AS iu_4_code,
    ('TST-BA-C1-' || suffix) AS ba_1_code,
    ('TST-BA-C2-' || suffix) AS ba_2_code,
    ('TST-BA-C3-' || suffix) AS ba_3_code,
    ('TST-BA-C4-' || suffix) AS ba_4_code,
    ('TST-CLI-C1-' || suffix) AS cli_1_code,
    ('TST-CLI-C2-' || suffix) AS cli_2_code,
    ('TST-CLI-C3-' || suffix) AS cli_3_code,
    ('TST-CLI-C4-' || suffix) AS cli_4_code
FROM s;

-- ⚠️ anagrafiche.billing_account.categoria_cliente_id e' NOT NULL: la fixture
--   era rimasta indietro rispetto alla colonna, e le quattro INSERT sotto
--   morivano tutte sul vincolo. Si sceglie UNA volta e con ORDER BY, cosi' le
--   quattro BA hanno per forza la stessa categoria e la scelta e' ripetibile
--   fra le corse (cantiere LIMIT 1, §27 del brief).
CREATE TEMP TABLE tmp_categoria_cliente AS
SELECT id AS categoria_cliente_id
  FROM anagrafiche.categorie_clienti
 ORDER BY id
 LIMIT 1;
-- =========================================================
-- 0) Precondizioni: PDP test dedicato, stati cliente, soggetti
-- =========================================================
-- 0.1) PDP GAS dedicato al test (isolamento da dati preesistenti)
-- ⭐ 2026-09-23: il PDP lo costruisce dbops.fn_pgtap_crea_pdp. Prima lo si
--   costruiva qui a mano, su uno stradario CABLATO (`stradario_id = 4`) e con
--   un codice derivato dal suffisso: era la prima copia di una logica che altri
--   quattro file volevano, e con il builder si ritira (regola del 2).
CREATE TEMP TABLE tmp_pdp_test AS
SELECT p.pdp_id AS id,
       p.indirizzo_dettaglio_id,
       p.utility_id
FROM dbops.fn_pgtap_crea_pdp('GAS') p;
SELECT is(
        (
            SELECT count(*)::int
            FROM tmp_pdp_test
        ),
        1,
        'Creato esattamente un PDP GAS dedicato al test'
    );
-- 0.2) Stati cliente: AT (attivo) e AN (annullato)
CREATE TEMP TABLE tmp_stato_attivo AS
SELECT id
FROM config.stati_cliente
WHERE codice_interno = 'AT'
LIMIT 1;
SELECT is(
        (
            SELECT count(*)::int
            FROM tmp_stato_attivo
        ),
        1,
        'Esiste uno stato_cliente con codice_interno = AT'
    );
CREATE TEMP TABLE tmp_stato_annullato AS
SELECT id
FROM config.stati_cliente
WHERE codice_interno = 'AN'
LIMIT 1;
SELECT is(
        (
            SELECT count(*)::int
            FROM tmp_stato_annullato
        ),
        1,
        'Esiste uno stato_cliente con codice_interno = AN'
    );
CREATE TEMP TABLE tmp_stato_chiuso AS
SELECT id
FROM config.stati_cliente
WHERE codice_interno = 'CH'
LIMIT 1;
SELECT is(
        (
            SELECT count(*)::int
            FROM tmp_stato_chiuso
        ),
        1,
        'Esiste uno stato_cliente con codice_interno = CH'
    );
-- 0.3) Soggetti di test
-- ⛔ 2026-09-23: erano «due soggetti reali esistenti», per partita IVA di
--   QUESTA macchina: su un database ricostruito dai changelog non ci sono.
--   Si costruiscono: due persone giuridiche, ciascuna col suo ruolo CL
--   completo degli indirizzi di ruolo.
CREATE TEMP TABLE tmp_soggetto_1 AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Catena soggetto 1') AS id;
SELECT is(
        (
            SELECT count(*)::int
            FROM tmp_soggetto_1
            WHERE id IS NOT NULL
        ),
        1,
        'Costruito il soggetto 1'
    );
CREATE TEMP TABLE tmp_soggetto_2 AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Catena soggetto 2') AS id;
SELECT is(
        (
            SELECT count(*)::int
            FROM tmp_soggetto_2
            WHERE id IS NOT NULL
        ),
        1,
        'Costruito il soggetto 2'
    );
-- 0.4) Ruolo CLIENTE per i due soggetti, con i suoi indirizzi di ruolo
CREATE TEMP TABLE tmp_sr_1 AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(s.id, 'CL') AS soggetto_ruolo_id
FROM tmp_soggetto_1 s;
CREATE TEMP TABLE tmp_sr_2 AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(s.id, 'CL') AS soggetto_ruolo_id
FROM tmp_soggetto_2 s;
-- ⚠️ La finestra differita si riapre DICHIARANDOLA (2026-09-23). Il file
--   contava su quella «di default» dopo la riga di contesto, e i builder qui
--   sopra escono IMMEDIATE come ogni helper: l'istanza base moriva sul guard
--   differito dei satelliti. Si richiude dopo la quarta coppia, come prima.
SET CONSTRAINTS ALL DEFERRED;
-- 0.5) Creazione istanza base di test per il PDP (prima anello della catena)
WITH ins_iu_base AS (
    INSERT INTO anagrafiche.istanze_utilities (
            fittizia,
            codice,
            proprietario_inquilino,
            soggetto_id,
            indirizzo_dettaglio_id,
            pdp_id
        )
    SELECT FALSE,
        (
            SELECT iu_base_code
            FROM tmp_test_keys
        ),
        'P',
        -- proprietario
        s1.id,
        p.indirizzo_dettaglio_id,
        p.id
    FROM tmp_soggetto_1 s1,
        tmp_pdp_test p
    RETURNING *
)
SELECT * INTO TEMP TABLE tmp_iu_base
FROM ins_iu_base;
SELECT is(
        (
            SELECT count(*)::int
            FROM tmp_iu_base
        ),
        1,
        'Creata istanza base di test collegata al PDP dedicato'
    );
-- =========================================================
-- Creazione billing_account per ogni istanza di test
-- (BA: 1 per istanza, stessa utility del PDP)
-- =========================================================
-- BA per istanza base
CREATE TEMP TABLE tmp_ba_1 AS WITH ins_ba AS (
    INSERT INTO anagrafiche.billing_account (
            istanza_utility_id,
            soggetto_ruolo_id,
            utility_id,
            categoria_cliente_id,
            codice
        )
    SELECT iu.id,
        sr.soggetto_ruolo_id,
        p.utility_id,
        (SELECT categoria_cliente_id FROM tmp_categoria_cliente),
        (
            SELECT ba_1_code
            FROM tmp_test_keys
        )
    FROM tmp_iu_base iu,
        tmp_sr_1 sr,
        tmp_pdp_test p
    RETURNING id,
        istanza_utility_id,
        utility_id
)
SELECT *
FROM ins_ba;
-- =========================================================
-- 1) Primo cliente per il PDP (istanza base) → parent_istanza_id NULL
-- =========================================================
-- ⚠️ rev 2026-08-29: via la CTE `iva`, la colonna `iva_id` e il join su di essa.
--   anagrafiche.clienti.iva_id non esiste piu' (changeSet 20260829-22):
--   l'aliquota la decide la merce, non il cliente.
WITH ins_cli AS (
    INSERT INTO anagrafiche.clienti (
            soggetto_ruolo_id,
            istanza_utility_id,
            stato_cliente_id,
            data_attivazione,
            billing_account_id,
            codice_cliente_importato
        )
    SELECT sr.soggetto_ruolo_id,
        iu.id,
        sc_at.id,
        DATE '2025-01-01',
        ba.id,
        (
            SELECT cli_1_code
            FROM tmp_test_keys
        )
    FROM tmp_sr_1 sr,
        tmp_iu_base iu,
        tmp_stato_attivo sc_at,
        tmp_ba_1 ba
    RETURNING id,
        istanza_utility_id
)
SELECT * INTO TEMP TABLE tmp_cli_1
FROM ins_cli;
SELECT is(
        (
            SELECT count(*)::int
            FROM tmp_cli_1
        ),
        1,
        'Inserito primo cliente di test (TST-CLI-CHAIN-001) per istanza base'
    );
-- Verifica: l’istanza base deve avere parent_istanza_id NULL
SELECT ok(
        (
            SELECT parent_istanza_id IS NULL
            FROM anagrafiche.istanze_utilities
            WHERE id = (
                    SELECT istanza_utility_id
                    FROM tmp_cli_1
                )
        ),
        'Per il primo cliente della catena, parent_istanza_id dell’istanza base è NULL'
    );
-- =========================================================
-- 2) Seconda istanza + cliente ATTIVO → parent_istanza_id = istanza_base.id
-- =========================================================
-- 2.1) Creazione seconda istanza collegata allo stesso PDP, con stesso indirizzo
WITH ins_iu2 AS (
    INSERT INTO anagrafiche.istanze_utilities (
            fittizia,
            codice,
            proprietario_inquilino,
            soggetto_id,
            indirizzo_dettaglio_id,
            pdp_id
        )
    SELECT FALSE,
        (
            SELECT iu_2_code
            FROM tmp_test_keys
        ),
        'I',
        -- inquilino
        s2.id,
        p.indirizzo_dettaglio_id,
        p.id
    FROM tmp_soggetto_2 s2,
        tmp_pdp_test p
    RETURNING *
)
SELECT * INTO TEMP TABLE tmp_iu_2
FROM ins_iu2;
SELECT is(
        (
            SELECT count(*)::int
            FROM tmp_iu_2
        ),
        1,
        'Inserita seconda istanza_utility (TST-IU-CHAIN-002) per lo stesso PDP'
    );
-- 2.2) Billing account per istanza 2
CREATE TEMP TABLE tmp_ba_2 AS WITH ins_ba AS (
    INSERT INTO anagrafiche.billing_account (
            istanza_utility_id,
            soggetto_ruolo_id,
            utility_id,
            categoria_cliente_id,
            codice
        )
    SELECT iu.id,
        sr.soggetto_ruolo_id,
        p.utility_id,
        (SELECT categoria_cliente_id FROM tmp_categoria_cliente),
        (
            SELECT ba_2_code
            FROM tmp_test_keys
        )
    FROM tmp_iu_2 iu,
        tmp_sr_2 sr,
        tmp_pdp_test p
    RETURNING id,
        istanza_utility_id,
        utility_id
)
SELECT *
FROM ins_ba;
-----------------------------------------------------------
-- 2.3.0) Subentro: chiude il cliente precedente sul PDP prima di creare il nuovo
CREATE TEMP TABLE tmp_subentro1 AS
SELECT script.fn_subentro_cliente(
        (
            SELECT id
            FROM tmp_pdp_test
        ),
        DATE '2025-06-01'
    ) AS cliente_chiuso_id;
SELECT is(
        (
            SELECT cliente_chiuso_id::bigint
            FROM tmp_subentro1
        ),
        (
            SELECT id::bigint
            FROM tmp_cli_1
        ),
        'fn_subentro_cliente chiude il cliente precedente attivo sul PDP (CLI2)'
    );
SELECT is(
        (
            SELECT data_chiusura::date
            FROM anagrafiche.clienti
            WHERE id = (
                    SELECT id
                    FROM tmp_cli_1
                )
        ),
        (DATE '2025-06-01' - 1),
        'Cliente precedente chiuso con data_chiusura = data attivazione nuovo - 1 giorno'
    );
SELECT is(
        (
            SELECT stato_cliente_id::int
            FROM anagrafiche.clienti
            WHERE id = (
                    SELECT id
                    FROM tmp_cli_1
                )
        ),
        (
            SELECT id::int
            FROM tmp_stato_chiuso
        ),
        'Cliente precedente impostato a stato CH dopo subentro'
    );
----------------------------------------------------------
-- 2.3) Cliente 2 ATTIVO per istanza 2
-- ⚠️ rev 2026-08-29: via la CTE `iva`, la colonna `iva_id` e il join su di essa.
--   anagrafiche.clienti.iva_id non esiste piu' (changeSet 20260829-22):
--   l'aliquota la decide la merce, non il cliente.
WITH ins_cli2 AS (
    INSERT INTO anagrafiche.clienti (
            soggetto_ruolo_id,
            istanza_utility_id,
            stato_cliente_id,
            data_attivazione,
            billing_account_id,
            codice_cliente_importato
        )
    SELECT sr.soggetto_ruolo_id,
        iu2.id,
        sc_at.id,
        DATE '2025-06-01',
        ba2.id,
        (
            SELECT cli_2_code
            FROM tmp_test_keys
        )
    FROM tmp_sr_2 sr,
        tmp_iu_2 iu2,
        tmp_stato_attivo sc_at,
        tmp_ba_2 ba2
    RETURNING id,
        istanza_utility_id
)
SELECT * INTO TEMP TABLE tmp_cli_2
FROM ins_cli2;
SELECT is(
        (
            SELECT count(*)::int
            FROM tmp_cli_2
        ),
        1,
        'Inserito secondo cliente ATTIVO (TST-CLI-CHAIN-002) su seconda istanza'
    );
-- Verifica: parent_istanza_id della seconda istanza = id istanza_base
SELECT is(
        (
            SELECT parent_istanza_id::bigint
            FROM anagrafiche.istanze_utilities
            WHERE id = (
                    SELECT istanza_utility_id
                    FROM tmp_cli_2
                )
        ),
        (
            SELECT id::bigint
            FROM tmp_iu_base
        ),
        'Seconda istanza ha parent_istanza_id puntato all’istanza base (catena corretta)'
    );
-- =========================================================
-- 3) Terza istanza + cliente AN (annullato) → escluso dalla catena
-- =========================================================
-- 3.1) Creazione terza istanza per stesso PDP
WITH ins_iu3 AS (
    INSERT INTO anagrafiche.istanze_utilities (
            fittizia,
            codice,
            proprietario_inquilino,
            soggetto_id,
            indirizzo_dettaglio_id,
            pdp_id
        )
    SELECT FALSE,
        (
            SELECT iu_3_code
            FROM tmp_test_keys
        ),
        'I',
        s1.id,
        p.indirizzo_dettaglio_id,
        p.id
    FROM tmp_soggetto_1 s1,
        tmp_pdp_test p
    RETURNING *
)
SELECT * INTO TEMP TABLE tmp_iu_3
FROM ins_iu3;
SELECT is(
        (
            SELECT count(*)::int
            FROM tmp_iu_3
        ),
        1,
        'Inserita terza istanza_utility (TST-IU-CHAIN-003) per lo stesso PDP'
    );
-- 3.2) Billing account per istanza 3
CREATE TEMP TABLE tmp_ba_3 AS WITH ins_ba AS (
    INSERT INTO anagrafiche.billing_account (
            istanza_utility_id,
            soggetto_ruolo_id,
            utility_id,
            categoria_cliente_id,
            codice
        )
    SELECT iu.id,
        sr.soggetto_ruolo_id,
        p.utility_id,
        (SELECT categoria_cliente_id FROM tmp_categoria_cliente),
        (
            SELECT ba_3_code
            FROM tmp_test_keys
        )
    FROM tmp_iu_3 iu,
        tmp_sr_1 sr,
        tmp_pdp_test p
    RETURNING id,
        istanza_utility_id,
        utility_id
)
SELECT *
FROM ins_ba;
-- 3.3.0) Subentro: chiude il cliente precedente sul PDP prima di creare il nuovo
CREATE TEMP TABLE tmp_subentro3 AS
SELECT script.fn_subentro_cliente(
        (
            SELECT id
            FROM tmp_pdp_test
        ),
        DATE '2025-09-01'
    ) AS cliente_chiuso_id;
SELECT is(
        (
            SELECT cliente_chiuso_id::bigint
            FROM tmp_subentro3
        ),
        (
            SELECT id::bigint
            FROM tmp_cli_2
        ),
        'fn_subentro_cliente chiude il cliente precedente attivo sul PDP (CLI3)'
    );
SELECT is(
        (
            SELECT data_chiusura::date
            FROM anagrafiche.clienti
            WHERE id = (
                    SELECT id
                    FROM tmp_cli_2
                )
        ),
        (DATE '2025-09-01' - 1),
        'Cliente precedente chiuso con data_chiusura = data attivazione nuovo - 1 giorno'
    );
SELECT is(
        (
            SELECT stato_cliente_id::int
            FROM anagrafiche.clienti
            WHERE id = (
                    SELECT id
                    FROM tmp_cli_2
                )
        ),
        (
            SELECT id::int
            FROM tmp_stato_chiuso
        ),
        'Cliente precedente impostato a stato CH dopo subentro'
    );
-- 3.3) Cliente 3 ANNULLATO (stato = AN) → deve essere escluso dalla catena
-- ⚠️ rev 2026-08-29: via la CTE `iva`, la colonna `iva_id` e il join su di essa.
--   anagrafiche.clienti.iva_id non esiste piu' (changeSet 20260829-22):
--   l'aliquota la decide la merce, non il cliente.
WITH ins_cli3 AS (
    INSERT INTO anagrafiche.clienti (
            soggetto_ruolo_id,
            istanza_utility_id,
            stato_cliente_id,
            data_attivazione,
            data_chiusura,
            billing_account_id,
            codice_cliente_importato
        )
    SELECT sr.soggetto_ruolo_id,
        iu3.id,
        sc_an.id,
        DATE '2025-09-01',
        DATE '2025-09-01',
        ba3.id,
        (
            SELECT cli_3_code
            FROM tmp_test_keys
        )
    FROM tmp_sr_1 sr,
        tmp_iu_3 iu3,
        tmp_stato_annullato sc_an,
        tmp_ba_3 ba3
    RETURNING id,
        istanza_utility_id
)
SELECT * INTO TEMP TABLE tmp_cli_3
FROM ins_cli3;
SELECT is(
        (
            SELECT count(*)::int
            FROM tmp_cli_3
        ),
        1,
        'Inserito terzo cliente ANNULLATO (TST-CLI-CHAIN-003) su terza istanza'
    );
-- Verifica: l’istanza 3 (cliente AN) NON deve avere parent_istanza_id valorizzato
SELECT ok(
        (
            SELECT parent_istanza_id IS NULL
            FROM anagrafiche.istanze_utilities
            WHERE id = (
                    SELECT istanza_utility_id
                    FROM tmp_cli_3
                )
        ),
        'Istanza del cliente AN (TST-CLI-CHAIN-003) ha parent_istanza_id NULL (esclusa dalla catena)'
    );
-- =========================================================
-- 4) Quarta istanza + cliente ATTIVO → deve agganciarsi alla seconda istanza
--    (l’ultima ATTIVA con data_attivazione non NULL, ignorando quella AN)
-- =========================================================
-- 4.1) Creazione quarta istanza per stesso PDP
WITH ins_iu4 AS (
    INSERT INTO anagrafiche.istanze_utilities (
            fittizia,
            codice,
            proprietario_inquilino,
            soggetto_id,
            indirizzo_dettaglio_id,
            pdp_id
        )
    SELECT FALSE,
        (
            SELECT iu_4_code
            FROM tmp_test_keys
        ),
        'I',
        s2.id,
        p.indirizzo_dettaglio_id,
        p.id
    FROM tmp_soggetto_2 s2,
        tmp_pdp_test p
    RETURNING *
)
SELECT * INTO TEMP TABLE tmp_iu_4
FROM ins_iu4;
SELECT is(
        (
            SELECT count(*)::int
            FROM tmp_iu_4
        ),
        1,
        'Inserita quarta istanza_utility (TST-IU-CHAIN-004) per lo stesso PDP'
    );
-- 4.2) Billing account per istanza 4
CREATE TEMP TABLE tmp_ba_4 AS WITH ins_ba AS (
    INSERT INTO anagrafiche.billing_account (
            istanza_utility_id,
            soggetto_ruolo_id,
            utility_id,
            categoria_cliente_id,
            codice
        )
    SELECT iu.id,
        sr.soggetto_ruolo_id,
        p.utility_id,
        (SELECT categoria_cliente_id FROM tmp_categoria_cliente),
        (
            SELECT ba_4_code
            FROM tmp_test_keys
        )
    FROM tmp_iu_4 iu,
        tmp_sr_2 sr,
        tmp_pdp_test p
    RETURNING id,
        istanza_utility_id,
        utility_id
)
SELECT *
FROM ins_ba;

-- ⚠️ QUI, e non in testa al file: e' il punto in cui l'unita' di lavoro e'
--   completa. Il trigger differito trg_istanze_utilities_z90_require_utility_
--   dichiarata_ins pretende che ogni istanza abbia almeno un satellite, e in
--   questo file istanza e satellite nascono in DUE istruzioni separate, per
--   quattro coppie. Con IMMEDIATE in testa il vincolo scattava a fine della
--   prima INSERT, quando il billing_account non c'era ancora: il file moriva
--   sulla fixture senza arrivare alle asserzioni.
--   Metterlo dopo la PRIMA coppia non basterebbe: da li' in poi ogni istruzione
--   e' immediata, e le tre istanze successive fallirebbero allo stesso modo.
--   Va dopo la QUARTA — e comunque prima del cleanup, altrimenti scatterebbe su
--   righe gia' cancellate (§22.5 del brief pgtap-runner-rls-baseline).
SET CONSTRAINTS ALL IMMEDIATE;

-- 4.3) Subentro: chiude il cliente precedente sul PDP prima di creare il nuovo
/*
 CREATE TEMP TABLE tmp_subentro AS
 SELECT script.fn_subentro_cliente(
 (SELECT id FROM tmp_pdp_test),
 DATE '2025-10-01'
 ) AS cliente_chiuso_id;
 
 SELECT is(
 (SELECT cliente_chiuso_id::bigint FROM tmp_subentro),
 (SELECT id::bigint FROM tmp_cli_2),
 'fn_subentro_cliente chiude il cliente precedente attivo sul PDP (CLI3)'
 );
 
 SELECT is(
 (
 SELECT data_chiusura::date
 FROM anagrafiche.clienti
 WHERE id = (SELECT id FROM tmp_cli_2)
 ),
 (DATE '2025-10-01' - 1),
 'Cliente precedente chiuso con data_chiusura = data attivazione nuovo - 1 giorno'
 );
 
 SELECT is(
 (
 SELECT stato_cliente_id::int
 FROM anagrafiche.clienti
 WHERE id = (SELECT id FROM tmp_cli_2)
 ),
 (SELECT id::int FROM tmp_stato_chiuso),
 'Cliente precedente impostato a stato CH dopo subentro'
 );
 */
-- 4.4) Cliente 4 ATTIVO per istanza 4 (data più recente)
-- ⚠️ rev 2026-08-29: via la CTE `iva`, la colonna `iva_id` e il join su di essa.
--   anagrafiche.clienti.iva_id non esiste piu' (changeSet 20260829-22):
--   l'aliquota la decide la merce, non il cliente.
WITH ins_cli4 AS (
    INSERT INTO anagrafiche.clienti (
            soggetto_ruolo_id,
            istanza_utility_id,
            stato_cliente_id,
            data_attivazione,
            billing_account_id,
            codice_cliente_importato
        )
    SELECT sr.soggetto_ruolo_id,
        iu4.id,
        sc_at.id,
        DATE '2025-10-01',
        ba4.id,
        (
            SELECT cli_4_code
            FROM tmp_test_keys
        )
    FROM tmp_sr_2 sr,
        tmp_iu_4 iu4,
        tmp_stato_attivo sc_at,
        tmp_ba_4 ba4
    RETURNING id,
        istanza_utility_id
)
SELECT * INTO TEMP TABLE tmp_cli_4
FROM ins_cli4;
SELECT is(
        (
            SELECT count(*)::int
            FROM tmp_cli_4
        ),
        1,
        'Inserito quarto cliente ATTIVO (TST-CLI-CHAIN-004) su quarta istanza'
    );
-- Verifica: quarta istanza deve avere come parent l’istanza_2 (ultima ATTIVA non AN)
SELECT is(
        (
            SELECT parent_istanza_id::bigint
            FROM anagrafiche.istanze_utilities
            WHERE id = (
                    SELECT istanza_utility_id
                    FROM tmp_cli_4
                )
        ),
        (
            SELECT id::bigint
            FROM tmp_iu_2
        ),
        'Quarta istanza ha parent_istanza_id puntato alla seconda istanza (esclude cliente AN dalla catena)'
    );
-- =========================================================
-- 5) Verifica logica billing_account / utility / 1 cliente per istanza
-- =========================================================
-- 5.1) Verifica che clienti.utility_id sia sincronizzato con billing_account.utility_id (esempio su CLI4)
SELECT is(
        (
            SELECT c.utility_id::int
            FROM anagrafiche.clienti c
            WHERE c.id = (
                    SELECT id
                    FROM tmp_cli_4
                )
        ),
        (
            SELECT ba.utility_id::int
            FROM anagrafiche.billing_account ba
                JOIN anagrafiche.clienti c ON c.billing_account_id = ba.id
            WHERE c.id = (
                    SELECT id
                    FROM tmp_cli_4
                )
        ),
        'Per il cliente 4, utility_id è coerente tra clienti e billing_account (sync da trigger)'
    );
-- 5.2) Verifica 1 cliente per istanza nel dataset di test
SELECT is(
        (
            WITH cli AS (
                SELECT id,
                    istanza_utility_id
                FROM tmp_cli_1
                UNION ALL
                SELECT id,
                    istanza_utility_id
                FROM tmp_cli_2
                UNION ALL
                SELECT id,
                    istanza_utility_id
                FROM tmp_cli_3
                UNION ALL
                SELECT id,
                    istanza_utility_id
                FROM tmp_cli_4
            )
            SELECT count(DISTINCT istanza_utility_id)::int
            FROM cli
        ),
        (
            WITH cli AS (
                SELECT id,
                    istanza_utility_id
                FROM tmp_cli_1
                UNION ALL
                SELECT id,
                    istanza_utility_id
                FROM tmp_cli_2
                UNION ALL
                SELECT id,
                    istanza_utility_id
                FROM tmp_cli_3
                UNION ALL
                SELECT id,
                    istanza_utility_id
                FROM tmp_cli_4
            )
            SELECT count(*)::int
            FROM cli
        ),
        'Nel dataset di test, il vincolo 1 cliente per istanza è rispettato'
    );
-- Fine test
SELECT *
FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
