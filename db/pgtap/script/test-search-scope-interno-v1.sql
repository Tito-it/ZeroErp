-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Passo 1 del cantiere «perimetro emittente» (decisione Q2/C):
-- la ricerca universale risolve lo scope emittente DA SE'.
-- Brief: docs/it/dev/work-in-progress/brief-db-perimetro-emittente-liste-e-gerarchia-ba.md
--
-- Elenco test (plan 12):
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
--
-- Scopo:
--  - verificare che NESSUN valore passato dal chiamante possa ALLARGARE
--    cio' che le due funzioni di ricerca mostrano. Prima, il filtro si
--    accendeva su `p_emittente_ids IS NOT NULL`: NULL — cioe' cio' in cui
--    Python appiattisce la lista vuota — valeva «nessuna restrizione».
--
-- ⚠️ NOTA SULLA COPERTURA, da leggere prima di fidarsi del verde.
--   I test 1-7 sono deterministici e sono LA correzione: girano sulla
--   funzione di scope e non dipendono dai dati.
--   I test 8-11 verificano l'INVARIANTE «il parametro non decide piu'»
--   confrontando due chiamate. NON dimostrano che un cliente di un altro
--   emittente sparisce: per quello servirebbe una fixture a DUE emittenti
--   con un cliente per ciascuno, che questo file NON costruisce. E' un
--   buco dichiarato, non coperto per sbaglio.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- Fixture
-- ============================================================
-- L'operatore di contesto e' garantito NON super admin e CON la sua riga
-- in config.user_emittenti_fiscali (vedi fn_pgtap_set_contesto_operatore):
-- quindi il suo scope di diritto e' un array di cardinalita' 1, mai NULL.
-- Su questo poggiano i test 1-5: senza, misurerebbero il ramo super admin.
CREATE TEMP TABLE _t_ctx ON COMMIT DROP AS
SELECT
    NULLIF(current_setting('app.current_user_id', true), '')::integer AS user_id;

CREATE TEMP TABLE _t_scope ON COMMIT DROP AS
SELECT script.fn_get_emittenti_scope_sr_ids((SELECT user_id FROM _t_ctx)) AS sr_ids;

-- Un soggetto_ruolo_id che NON esiste: per costruzione fuori da qualunque
-- scope, senza bisogno di un secondo emittente nei dati.
-- ⚠️ Non si "pesca" un emittente diverso dai dati: sarebbe data-dependent
--   (l'istanza potrebbe averne uno solo) e il test passerebbe a giorni alterni.
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
-- (0 = 0) e il file diventerebbe verde per sottrazione.
CREATE TEMP TABLE _t_cl ON COMMIT DROP AS
SELECT tr.id AS tipo_ruolo_id
  FROM config.tipi_ruoli tr
 WHERE tr.codice_interno = 'CL';

-- ⚠️ ORDER BY obbligatorio: senza, quale soggetto esca dipende dal piano.
--   Si sceglie UNA volta e si proietta da qui (soggetto + termine insieme),
--   invece di due sotto-select che potrebbero pescare righe diverse.
CREATE TEMP TABLE _t_cl_sog ON COMMIT DROP AS
SELECT s.id                                       AS soggetto_id,
       substring(s.ragione_sociale_completa, 1, 4) AS termine
  FROM anagrafiche.soggetti_ruoli sr
  JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
 WHERE sr.tipo_ruolo_id = (SELECT tipo_ruolo_id FROM _t_cl)
   AND s.attivo = true
   AND length(btrim(s.ragione_sociale_completa)) >= 4
 ORDER BY s.ragione_sociale_completa, sr.id
 LIMIT 1;

SELECT CASE WHEN EXISTS (SELECT 1 FROM _t_cl_sog)
  THEN is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        NULL)),
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        (SELECT sr_ids FROM _t_scope))),
    '8. ricerca CL: passare NULL o il proprio scope da lo stesso risultato (il parametro non decide piu'')'
  )
  ELSE skip('8. nessun cliente attivo con ragione sociale >= 4 caratteri: confronto non significativo', 1)
END;

SELECT CASE WHEN EXISTS (SELECT 1 FROM _t_cl_sog)
  THEN is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        ARRAY[(SELECT sr_id FROM _t_fuori)]::bigint[])),
    0::bigint,
    '9. ricerca CL con restrizione fuori scope -> zero risultati (fail-closed)'
  )
  ELSE skip('9. nessun cliente attivo utilizzabile come soggetto di prova', 1)
END;

SELECT CASE WHEN EXISTS (SELECT 1 FROM _t_cl_sog)
  THEN is(
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
  )
  ELSE skip('10. nessun cliente attivo utilizzabile come soggetto di prova', 1)
END;

SELECT CASE WHEN EXISTS (SELECT 1 FROM _t_cl_sog)
  THEN is(
    script.fn_get_search_detail(
        (SELECT soggetto_id FROM _t_cl_sog),
        (SELECT tipo_ruolo_id FROM _t_cl),
        NULL,
        ARRAY[(SELECT sr_id FROM _t_fuori)]::bigint[]) -> 'righe',
    '[]'::jsonb,
    '11. dettaglio CL con restrizione fuori scope -> righe vuote (fail-closed)'
  )
  ELSE skip('11. nessun cliente attivo utilizzabile come soggetto di prova', 1)
END;

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
