-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Passo 1 del cantiere «perimetro emittente» (decisione Q2/C):
-- la ricerca universale risolve lo scope emittente DA SE'.
-- Brief: docs/it/dev/work-in-progress/brief-db-perimetro-emittente-liste-e-gerarchia-ba.md
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
--   fixture a DUE emittenti (il buco dichiarato sotto, chiuso il 2026-08-18)
--   12) PRECONDIZIONE: c'e' un secondo emittente e il cliente di prova si vede
--   13) * spostato il suo BA sull'altro emittente, il cliente SPARISCE
--   14)   per lo scope-universo c'e' ancora: sparito dal perimetro, non dai dati
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
--   emittente sparisce.
--   ⭐ Quella prova e' arrivata il 2026-08-18 con i test 12-14, che costruiscono
--   la fixture a due emittenti spostando davvero il billing account del cliente
--   sotto l'altro emittente. Restano condizionati alla presenza di un SECONDO
--   emittente attivo in istanza: se non c'e', saltano dichiarandolo.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

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
-- 12-14) ⭐ LA FIXTURE A DUE EMITTENTI — il buco dichiarato sopra, chiuso
--
--   I test 8-11 verificano l'INVARIANTE «il parametro non decide piu'»: due
--   chiamate che devono dare lo stesso risultato. Nessuno di loro dimostra la
--   cosa che al perimetro interessa davvero — che un cliente di un ALTRO
--   emittente SPARISCE. Per quello serve un secondo emittente, e la misura di
--   Fase 0 ha stabilito che l'istanza ne ha due.
--
--   ⚠️ Il secondo emittente NON si usa come "restrizione fuori scope" (quello
--   e' il test 4, e li' l'id inesistente e' la scelta giusta). Qui si sposta
--   davvero il billing account del cliente sotto l'altro emittente e si guarda
--   se la ricerca lo mostra ancora.
--
--   ⭐ E si chiude con la contro-asserzione che rende il verde leggibile: il
--   soggetto non e' sparito dai DATI, e' sparito dal PERIMETRO. Senza il
--   test 14 un errore di fixture — soggetto cancellato, termine sbagliato —
--   darebbe lo stesso zero del test 13, e verrebbe letto come una prova.
-- ============================================================
CREATE TEMP TABLE _t_ef2 ON COMMIT DROP AS
SELECT (SELECT ef.soggetto_ruolo_id
          FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.attivo
           AND NOT (ef.soggetto_ruolo_id = ANY (COALESCE((SELECT sr_ids FROM _t_scope), '{}'::bigint[])))
         ORDER BY ef.soggetto_ruolo_id
         LIMIT 1) AS ef_altro;

-- Il cliente di prova: CL, con billing account MAPPATO (se ricadesse sul
-- gestore globale l'UPDATE sotto toccherebbe zero righe, in silenzio),
-- OGGI dentro il mio scope — e' la condizione che rende il caso
-- significativo — e fuori da qualunque albero, per non chiamare in causa
-- il guard di P-1 che con questo test non c'entra.
CREATE TEMP TABLE _t_due ON COMMIT DROP AS
SELECT sr.id                                       AS soggetto_ruolo_id,
       cl.billing_account_id                       AS ba_id,
       substring(s.ragione_sociale_completa, 1, 4) AS termine
  FROM anagrafiche.clienti cl
  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = cl.soggetto_ruolo_id
  JOIN anagrafiche.soggetti s        ON s.id  = sr.soggetto_id
  JOIN anagrafiche.billing_account ba ON ba.id = cl.billing_account_id
 WHERE sr.tipo_ruolo_id = (SELECT tipo_ruolo_id FROM _t_cl)
   AND s.attivo
   AND length(btrim(s.ragione_sociale_completa)) >= 4
   AND ba.parent_account_id IS NULL
   AND NOT EXISTS (SELECT 1 FROM anagrafiche.billing_account f
                    WHERE f.parent_account_id = ba.id)
   AND EXISTS (SELECT 1 FROM anagrafiche.emittenti_fiscali_billing_account e
                WHERE e.billing_account_id = ba.id)
   AND script.fn_get_ba_emittente_sr_id(ba.id)
       = ANY (COALESCE((SELECT sr_ids FROM _t_scope), '{}'::bigint[]))
   -- ⭐ 2026-08-26 — e SENZA STORIA, che e' il terzo guard da schivare.
   --   Dal changeSet 20260826-49 un cliente che ha gia' fatture o commesse
   --   NON si sposta su un altro emittente: quei documenti congelano chi li
   --   ha emessi, e spostarlo li lascerebbe orfani. Qui lo spostamento e'
   --   solo il MEZZO per costruire il caso — il soggetto del test e' la
   --   ricerca — quindi si sceglie un cliente su cui e' ancora lecito.
   --   ⚠️ La storia si chiede ad anagrafiche.fn_ba_ha_storia_emittente e NON
   --   con un NOT EXISTS scritto qui: quella funzione e' SECURITY DEFINER,
   --   mentre un conteggio diretto girerebbe sotto RLS e risponderebbe
   --   «nessuna storia» per i documenti che non vedo — scegliendo proprio il
   --   cliente su cui il guard poi scatta.
   --   ⭐ 2026-08-31: la storia non e' piu' «fatture e commesse» — si deriva da
   --   vendite.famiglie_documento, cioe' da QUALUNQUE documento gia' numerato
   --   su un registro — e il si'/no lo da' questa funzione, che esce al primo
   --   che trova invece di contarli tutti.
   AND NOT anagrafiche.fn_ba_ha_storia_emittente(ba.id)
   -- ⭐ E con UN SOLO billing account, che era una condizione IMPLICITA della
   --   fixture e non era scritta: il test 13 chiede che il soggetto SPARISCA
   --   dalla ricerca, ma la ricerca lo trova attraverso QUALUNQUE suo billing
   --   account in perimetro. Se il soggetto ne ha due, spostarne uno non lo
   --   toglie di mezzo e il test misura zero spostamenti invece di uno.
   --   Finora reggeva per il cliente che il LIMIT 1 pescava, non per costruzione.
   AND NOT EXISTS (SELECT 1 FROM anagrafiche.billing_account ba2
                    WHERE ba2.soggetto_ruolo_id = sr.id
                      AND ba2.id <> ba.id)
 ORDER BY s.ragione_sociale_completa, sr.id
 LIMIT 1;

-- 12) Precondizione: c'e' un secondo emittente e un cliente spostabile, e
--     oggi quel cliente la ricerca lo TROVA. Senza questa riga i due test
--     sotto sarebbero verdi anche partendo da zero risultati.
SELECT CASE WHEN (SELECT ef_altro FROM _t_ef2) IS NOT NULL
             AND EXISTS (SELECT 1 FROM _t_due)
  THEN is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_due), (SELECT tipo_ruolo_id FROM _t_cl), NULL) r
      WHERE r.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _t_due)),
    1::bigint,
    '12. PRECONDIZIONE fixture a due emittenti: il cliente di prova oggi si vede'
  )
  ELSE skip('12. istanza con un solo emittente attivo, o nessun cliente CL mappato, fuori albero e senza storia', 1)
END;

-- Lo spostamento: il billing account del cliente passa all'ALTRO emittente.
UPDATE anagrafiche.emittenti_fiscali_billing_account
   SET emittente_soggetto_ruolo_id = (SELECT ef_altro FROM _t_ef2)
 WHERE billing_account_id = (SELECT ba_id FROM _t_due)
   AND (SELECT ef_altro FROM _t_ef2) IS NOT NULL;

-- 13) ⭐ Il cliente di un altro emittente SPARISCE dalla ricerca. E' la cosa
--     che i test 8-11 non dimostravano.
SELECT CASE WHEN (SELECT ef_altro FROM _t_ef2) IS NOT NULL
             AND EXISTS (SELECT 1 FROM _t_due)
  THEN is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_due), (SELECT tipo_ruolo_id FROM _t_cl), NULL) r
      WHERE r.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _t_due)),
    0::bigint,
    '13. ⭐ spostato il BA sull''altro emittente, il cliente sparisce dalla ricerca'
  )
  ELSE skip('13. istanza con un solo emittente attivo, o nessun cliente CL utilizzabile', 1)
END;

-- 14) La contro-asserzione: per chi ha l'universo nello scope il soggetto c'e'
--     ancora. Sparito dal perimetro, non dai dati.
SELECT set_config('app.current_user_id',
                  COALESCE((SELECT idg.auth_user_id
                              FROM anagrafiche.identita_digitali idg
                             WHERE idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
                               AND idg.attivo
                               AND script.fn_is_super_admin(idg.auth_user_id)
                             ORDER BY idg.auth_user_id
                             LIMIT 1)::text,
                           current_setting('app.current_user_id', true)),
                  false);

SELECT CASE WHEN (SELECT ef_altro FROM _t_ef2) IS NOT NULL
             AND EXISTS (SELECT 1 FROM _t_due)
             AND script.fn_get_emittenti_scope_sr_ids(
                   NULLIF(current_setting('app.current_user_id', true), '')::integer) IS NULL
  THEN is(
    (SELECT count(*) FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM _t_due), (SELECT tipo_ruolo_id FROM _t_cl), NULL) r
      WHERE r.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM _t_due)),
    1::bigint,
    '14. per lo scope-universo il soggetto c''e'' ancora: sparito dal perimetro, non dai dati'
  )
  ELSE skip('14. nessun super admin operatore in istanza, o fixture non costruita', 1)
END;

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
