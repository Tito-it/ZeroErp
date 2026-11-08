-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test — la mappa dello scope di storico e chi la legge
--   dbops.storico_scope_policy · dbops.fn_storico_risolvi_scope
--
-- Brief: brief-db-rls-storico-scope-congelato.md §4b (D1, D3)
-- ChangeSet: 00_schema/dbops/20260911-21 · 20_code/dbops/20260911-22 ·
--            80_data/changelog/20260911-23 (seed CSV)
--
-- ⭐ LA MAPPA È ANCHE IL PRESIDIO. Una madre col trigger di storico senza riga
--   qui è una madre che nessuno ha guardato; una madre protetta dalla RLS con
--   modo NESSUNO è un debito che deve calare. Questo file è il rosso che lo dice
--   — e dice anche se la mappa MENTE rispetto al catalogo (una colonna che non
--   c'è, una FK che non punta dove la riga dichiara, una catena che non finisce).
--
-- ⭐ IL RESOLVER SI PROVA SUI VALORI, NON SUI DATI. EF, SR e i casi vuoti si
--   provano passando un jsonb costruito; la catena PADRE si costruisce su tre
--   tabelle TEMPORANEE con tre tipi di `id` diversi (bigint, integer, uuid),
--   dichiarate nella mappa dentro la transazione. Il ROLLBACK pulisce tutto.
--   ⚠️ Le prove di coerenza (1-10) girano PRIMA di inserire le righe di prova:
--   quelle righe puntano a tabelle senza FK e le farebbero rosse a ragione.
--
-- ⚠️ Gira come l'applicazione (runner di default): il resolver è SECURITY
--   DEFINER e lo chiamerà il trigger sotto zeroerp_app — è ESATTAMENTE il
--   percorso da collaudare. Le righe di prova nella mappa le scrive l'app,
--   che sulle tabelle di dbops ha i DML del loop dei grant.
--
-- Elenco test (plan 36):
--   MAPPA — completezza
--    1  : gemello «esiste»: ci sono madri col trigger di storico
--    2  : ogni madre col trigger di storico ha la sua riga
--    3  : gemello «esiste»: ci sono madri in RLS col trigger
--    4  : nessuna madre in RLS col trigger è dichiarata NESSUNO
--    5  : nessuna riga di mappa orfana (madre inesistente o senza trigger)
--   MAPPA — coerenza col catalogo
--    6  : EF/SR/BA: la colonna dichiarata esiste sulla madre
--    6-bis: COPPIA: le due colonne sono una FK composta verso la coppia del BA (rev 2026-10-09)
--    7  : PADRE: la colonna è una FK monocolonna verso il padre dichiarato
--    8  : PADRE: il padre ha la colonna `id` (è così che il resolver lo cerca)
--    9  : ogni catena PADRE termina in EF/SR/BA entro il tetto (niente cicli)
--   10  : ogni modo ammesso dal CHECK ha il suo ramo nel resolver
--   RESOLVER — postura
--   11  : SECURITY DEFINER
--   12  : search_path fissato
--   13  : il proprietario della funzione possiede ogni padre in RLS che legge
--   14  : gemello del 13: almeno un padre in RLS esiste
--   15  : zeroerp_app ha EXECUTE (lo chiama il trigger)
--   16  : PUBLIC non ha EXECUTE
--   RESOLVER — comportamento sui valori
--   17  : EF: copia la colonna (77 → 77)
--   18  : EF: colonna assente → NULL
--   19  : SR → EF (una coppia qualsiasi del catalogo, 1:1; skip dichiarato se non ce n'è)
--   20  : SR sconosciuto → NULL
--   21  : PADRE a due salti su tabelle temporanee (bigint → integer → uuid) → 4242
--   22  : PADRE con FK nulla → NULL
--   23  : PADRE con padre sparito → NULL
--   24  : NESSUNO → NULL (prima riga NESSUNO della mappa)
--   25  : madre non mappata → NULL
--   26  : ciclo nella mappa → P0001 (l'unico caso in cui solleva)
--   27  : ciclo nella mappa → la frase del catalogo
--   28  : BA non mappato, IN SESSIONE → l'emittente dell'operatore (D13, dal 20260913-01)
--   28-bis: BA non mappato, SENZA sessione → l'emittente di default (skip dichiarato se manca)
--   28-ter : COPPIA: il BA della coppia, poi il suo emittente (rev 2026-10-09)
--   28-quater: COPPIA: coppia senza BA → NULL
--   LA VISTA DI PRESIDIO — dbops.vw_storico_scope_da_dichiarare (digest)
--   29  : oggi è VUOTA: dice la stessa cosa dei test 2, 4, 5
--   30  : ⭐ una madre costruita col trigger e senza riga → SENZA_RIGA
--   31  : ⭐ la stessa, con RLS accesa e riga NESSUNO → PROTETTA_NESSUNO (e non più SENZA_RIGA)
--   32  : ⭐ una riga di mappa senza madre → RIGA_SENZA_MADRE; e la vista è a catalogo (ZERO, settimanale)
--   33  : ⭐ una riga di mappa su uno schema senza USAGE per chi legge → RIGA_SENZA_MADRE, non un errore (rev 2026-11-08)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ IMMEDIATE anche per la FK differita della mappa: le righe di prova che
--   puntano a un padre devono trovarlo GIÀ inserito, o la prova sbaglia bersaglio.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(37);

-- ============================================================
-- MAPPA — completezza
-- ============================================================
CREATE TEMP TABLE _madri ON COMMIT DROP AS
SELECT DISTINCT c.oid AS madre_oid, n.nspname AS sch, c.relname AS tab, c.relrowsecurity AS rls
  FROM pg_trigger t
  JOIN pg_class c     ON c.oid = t.tgrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE t.tgfoid = 'script.trgfn_storico_generic'::regproc
   AND NOT t.tgisinternal;

SELECT cmp_ok((SELECT count(*) FROM _madri), '>', 0::bigint,
              '1. gemello «esiste»: ci sono madri col trigger di storico');

SELECT is((SELECT count(*) FROM _madri m
            WHERE NOT EXISTS (SELECT 1 FROM dbops.storico_scope_policy p
                               WHERE p.schema_tabella = m.sch AND p.nome_tabella = m.tab)),
          0::bigint,
          '2. ogni madre col trigger di storico ha la sua riga nella mappa');

SELECT cmp_ok((SELECT count(*) FROM _madri WHERE rls), '>', 0::bigint,
              '3. gemello «esiste»: ci sono madri in RLS col trigger di storico');

SELECT is((SELECT count(*) FROM _madri m
             JOIN dbops.storico_scope_policy p
               ON p.schema_tabella = m.sch AND p.nome_tabella = m.tab
            WHERE m.rls AND p.modo = 'NESSUNO'),
          0::bigint,
          '4. nessuna madre in RLS col trigger è dichiarata NESSUNO — è il debito che deve calare');

SELECT is((SELECT count(*) FROM dbops.storico_scope_policy p
            WHERE NOT EXISTS (SELECT 1 FROM _madri m
                               WHERE m.sch = p.schema_tabella AND m.tab = p.nome_tabella)),
          0::bigint,
          '5. nessuna riga di mappa orfana: ogni riga è una madre esistente col trigger');

-- ============================================================
-- MAPPA — coerenza col catalogo
-- ============================================================
SELECT is((SELECT count(*) FROM dbops.storico_scope_policy p
            WHERE p.modo IN ('EF', 'SR', 'BA')
              AND NOT EXISTS (SELECT 1 FROM pg_attribute a
                               WHERE a.attrelid = (SELECT rc.oid FROM pg_class rc JOIN pg_namespace rn ON rn.oid = rc.relnamespace WHERE rn.nspname = p.schema_tabella AND rc.relname = p.nome_tabella)
                                 AND a.attname  = p.colonna
                                 AND NOT a.attisdropped)),
          0::bigint,
          '6. EF/SR/BA: la colonna dichiarata esiste sulla madre');

-- ⭐ rev 2026-10-09 (brief-db-istanza-nasce-col-ba): il modo COPPIA dichiara DUE
--   colonne, «<istanza>,<utility>». La mappa non mente se sulla madre c'e' una
--   FK composta che le porta, in quell'ordine, su anagrafiche.billing_account
--   (istanza_utility_id, utility_id): e' la chiave con cui il resolver cerca il BA.
SELECT is((SELECT count(*) FROM dbops.storico_scope_policy p
            WHERE p.modo = 'COPPIA'
              AND NOT EXISTS (
                  SELECT 1
                    FROM pg_constraint con
                    JOIN pg_attribute a1 ON a1.attrelid = con.conrelid  AND a1.attnum = con.conkey[1]
                    JOIN pg_attribute a2 ON a2.attrelid = con.conrelid  AND a2.attnum = con.conkey[2]
                    JOIN pg_attribute r1 ON r1.attrelid = con.confrelid AND r1.attnum = con.confkey[1]
                    JOIN pg_attribute r2 ON r2.attrelid = con.confrelid AND r2.attnum = con.confkey[2]
                   WHERE con.contype = 'f'
                     AND array_length(con.conkey, 1) = 2
                     AND con.conrelid  = (SELECT rc.oid FROM pg_class rc JOIN pg_namespace rn ON rn.oid = rc.relnamespace WHERE rn.nspname = p.schema_tabella AND rc.relname = p.nome_tabella)
                     AND con.confrelid = 'anagrafiche.billing_account'::regclass
                     AND a1.attname = split_part(p.colonna, ',', 1)
                     AND a2.attname = split_part(p.colonna, ',', 2)
                     AND r1.attname = 'istanza_utility_id'
                     AND r2.attname = 'utility_id')),
          0::bigint,
          '6-bis. COPPIA: le due colonne dichiarate sono una FK composta verso la coppia di anagrafiche.billing_account');

SELECT is((SELECT count(*) FROM dbops.storico_scope_policy p
            WHERE p.modo = 'PADRE'
              AND NOT EXISTS (
                  SELECT 1
                    FROM pg_constraint con
                    JOIN pg_class      c  ON c.oid  = con.conrelid
                    JOIN pg_namespace  n  ON n.oid  = c.relnamespace
                    JOIN pg_class      fc ON fc.oid = con.confrelid
                    JOIN pg_namespace  fn ON fn.oid = fc.relnamespace
                    JOIN pg_attribute  a  ON a.attrelid = con.conrelid AND a.attnum = con.conkey[1]
                   WHERE con.contype = 'f'
                     AND array_length(con.conkey, 1) = 1
                     AND n.nspname  = p.schema_tabella AND c.relname  = p.nome_tabella
                     AND a.attname  = p.colonna
                     AND fn.nspname = p.padre_schema   AND fc.relname = p.padre_tabella)),
          0::bigint,
          '7. PADRE: la colonna è una FK monocolonna verso il padre dichiarato — la mappa non mente sul catalogo');

SELECT is((SELECT count(*) FROM dbops.storico_scope_policy p
            WHERE p.modo = 'PADRE'
              AND NOT EXISTS (SELECT 1 FROM pg_attribute a
                               WHERE a.attrelid = (SELECT rc.oid FROM pg_class rc JOIN pg_namespace rn ON rn.oid = rc.relnamespace WHERE rn.nspname = p.padre_schema AND rc.relname = p.padre_tabella)
                                 AND a.attname  = 'id'
                                 AND NOT a.attisdropped)),
          0::bigint,
          '8. PADRE: il padre ha la colonna id, che è come il resolver lo cerca');

WITH RECURSIVE catena AS (
    SELECT p.id AS radice, p.modo, p.padre_schema, p.padre_tabella, 0 AS salti
      FROM dbops.storico_scope_policy p
     WHERE p.modo = 'PADRE'
    UNION ALL
    SELECT c.radice, m.modo, m.padre_schema, m.padre_tabella, c.salti + 1
      FROM catena c
      JOIN dbops.storico_scope_policy m
        ON m.schema_tabella = c.padre_schema AND m.nome_tabella = c.padre_tabella
     WHERE c.modo = 'PADRE' AND c.salti < 8
)
SELECT is((SELECT count(*) FROM (
              SELECT radice, bool_or(modo IN ('EF', 'SR', 'BA', 'COPPIA')) AS termina
                FROM catena GROUP BY radice) x
            WHERE NOT termina),
          0::bigint,
          '9. ogni catena PADRE termina in EF/SR/BA/COPPIA entro il tetto: niente cicli, niente catene che finiscono nel vuoto');

-- Il vocabolario si legge dal CHECK (è il contratto), non da un elenco scritto
-- qui: un modo nuovo senza il suo ramo nel resolver fa rosso.
CREATE TEMP TABLE _modi ON COMMIT DROP AS
SELECT DISTINCT m[1] AS modo
  FROM pg_constraint con,
       regexp_matches(pg_get_constraintdef(con.oid), '''([A-Z]+)''', 'g') m
 WHERE con.conname = 'chk_storico_scope_policy_modo';

SELECT is((SELECT count(*) FROM _modi md
            WHERE NOT EXISTS (
                SELECT 1 FROM pg_proc p
                 WHERE p.oid = 'dbops.fn_storico_risolvi_scope(text,text,jsonb,integer)'::regprocedure
                   AND p.prosrc LIKE '%WHEN ''' || md.modo || ''' THEN%'))
          + CASE WHEN (SELECT count(*) FROM _modi) = 0 THEN 1 ELSE 0 END,
          0::bigint,
          '10. ogni modo ammesso dal CHECK ha il suo ramo WHEN nel resolver (e il CHECK ha almeno un modo)');

-- ============================================================
-- RESOLVER — postura
-- ============================================================
SELECT is((SELECT p.prosecdef FROM pg_proc p
            WHERE p.oid = 'dbops.fn_storico_risolvi_scope(text,text,jsonb,integer)'::regprocedure),
          true,
          '11. fn_storico_risolvi_scope è SECURITY DEFINER: catturare lo scope è un atto di sistema');

SELECT ok((SELECT EXISTS (SELECT 1 FROM pg_proc p, unnest(p.proconfig) cfg
                           WHERE p.oid = 'dbops.fn_storico_risolvi_scope(text,text,jsonb,integer)'::regprocedure
                             AND cfg LIKE 'search_path=%')),
          '12. search_path fissato: una DEFINER non risolve nomi dal search_path del chiamante');

-- ⚠️ Attraversa la RLS solo perché il PROPRIETARIO della funzione possiede i
--   padri (ENABLE senza FORCE). Non si presume: si asserisce.
SELECT is((SELECT count(*) FROM (
              SELECT DISTINCT p.padre_schema, p.padre_tabella
                FROM dbops.storico_scope_policy p WHERE p.modo = 'PADRE') padri
             JOIN pg_class c ON c.oid = (SELECT rc.oid FROM pg_class rc JOIN pg_namespace rn ON rn.oid = rc.relnamespace WHERE rn.nspname = padri.padre_schema AND rc.relname = padri.padre_tabella)
            WHERE c.relrowsecurity
              AND c.relowner <> (SELECT f.proowner FROM pg_proc f
                                  WHERE f.oid = 'dbops.fn_storico_risolvi_scope(text,text,jsonb,integer)'::regprocedure)),
          0::bigint,
          '13. il proprietario del resolver possiede ogni padre in RLS che legge: è ciò che gli fa attraversare la RLS');

SELECT cmp_ok((SELECT count(*) FROM (
                  SELECT DISTINCT p.padre_schema, p.padre_tabella
                    FROM dbops.storico_scope_policy p WHERE p.modo = 'PADRE') padri
                 JOIN pg_class c ON c.oid = (SELECT rc.oid FROM pg_class rc JOIN pg_namespace rn ON rn.oid = rc.relnamespace WHERE rn.nspname = padri.padre_schema AND rc.relname = padri.padre_tabella)
                WHERE c.relrowsecurity),
              '>', 0::bigint,
              '14. gemello del 13: almeno un padre in RLS esiste, la lente vede davvero');

SELECT is(has_function_privilege('zeroerp_app',
            'dbops.fn_storico_risolvi_scope(text,text,jsonb,integer)', 'EXECUTE'), true,
          '15. zeroerp_app ha EXECUTE: la chiama il trigger, che gira come l''app');

SELECT is((SELECT count(*) FROM pg_proc p, aclexplode(p.proacl) a
            WHERE p.oid = 'dbops.fn_storico_risolvi_scope(text,text,jsonb,integer)'::regprocedure
              AND a.grantee = 0 AND a.privilege_type = 'EXECUTE'),
          0::bigint,
          '16. PUBLIC non ha EXECUTE sul resolver');

-- ============================================================
-- RESOLVER — comportamento sui valori
-- ============================================================
SELECT is(dbops.fn_storico_risolvi_scope('vendite', 'ddt', '{"emittente_fiscale_id": 77}'::jsonb),
          77::bigint,
          '17. EF: copia la colonna (77 → 77)');

SELECT is(dbops.fn_storico_risolvi_scope('vendite', 'ddt', '{}'::jsonb),
          NULL::bigint,
          '18. EF: colonna assente → NULL, fail-closed sulla shadow');

-- SR → EF è una relazione 1:1 del catalogo: la prova UNA coppia qualsiasi, presa in
-- modo deterministico. ⚠️ Non l'helper fn_pgtap_emittente_operatore(): quello
-- SOLLEVA quando non ci sono emittenti (la CI nasce con anagrafiche vuoto) e
-- l'errore abortirebbe la transazione, portandosi via tutte le asserzioni a
-- valle — successo alla prima corsa su zeroerp_ci, 2026-09-11. Dove non c'è
-- nessuna coppia il ramo si dichiara: lo prova il 20 (sconosciuto → NULL).
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM anagrafiche.emittenti_fiscali) THEN
        is((SELECT dbops.fn_storico_risolvi_scope('vendite', 'fatture',
                       jsonb_build_object('emittente_soggetto_ruolo_id', ef.soggetto_ruolo_id))
              FROM anagrafiche.emittenti_fiscali ef ORDER BY ef.id LIMIT 1),
           (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef ORDER BY ef.id LIMIT 1),
           '19. SR → EF: il soggetto-ruolo di un emittente si normalizza al suo emittenti_fiscali.id')
    ELSE
        skip('19. nessun emittente fiscale su questo database (la CI nasce vuoto): il ramo SR si prova solo col 20', 1)
END;

SELECT is(dbops.fn_storico_risolvi_scope('vendite', 'fatture', '{"emittente_soggetto_ruolo_id": -1}'::jsonb),
          NULL::bigint,
          '20. SR sconosciuto → NULL');

-- Fixture: una catena a due salti su tabelle TEMPORANEE, con tre tipi di id
-- diversi — è il caso che il resolver deve saper castare. Le righe di mappa
-- si inseriscono col padre PRIMA del figlio: la FK è IMMEDIATE qui sopra.
CREATE TEMP TABLE padre_prova  (id bigint,  emittente_fiscale_id bigint) ON COMMIT DROP;
CREATE TEMP TABLE figlio_prova (id integer, padre_id bigint)            ON COMMIT DROP;
CREATE TEMP TABLE nipote_prova (id uuid,    figlio_id integer)          ON COMMIT DROP;
CREATE TEMP TABLE ciclo_a      (id bigint,  b_id bigint)                ON COMMIT DROP;
CREATE TEMP TABLE ciclo_b      (id bigint,  a_id bigint)                ON COMMIT DROP;
-- ⚠️ Le temp table sono di CHI LE CREA — qui l'applicazione — e il resolver le
--   legge come il SUO proprietario (SECURITY DEFINER): senza questo GRANT
--   risponde «permesso negato per la tabella figlio_prova» (successo alla prima
--   corsa, 2026-09-11). Sulle tabelle vere il problema non esiste: sono del
--   proprietario. Il nome del proprietario si legge dal catalogo, perché non è
--   lo stesso su dev (titodb) e in CI (zeroerp).
DO $grant$
DECLARE
    v_owner text := (SELECT pg_get_userbyid(p.proowner) FROM pg_proc p
                      WHERE p.oid = 'dbops.fn_storico_risolvi_scope(text,text,jsonb,integer)'::regprocedure);
BEGIN
    EXECUTE format('GRANT SELECT ON pg_temp.padre_prova, pg_temp.figlio_prova, pg_temp.nipote_prova, '
                   'pg_temp.ciclo_a, pg_temp.ciclo_b TO %I', v_owner);
END
$grant$;
INSERT INTO padre_prova  VALUES (10, 4242);
INSERT INTO figlio_prova VALUES (20, 10);
INSERT INTO dbops.storico_scope_policy (id, schema_tabella, nome_tabella, modo, colonna, padre_schema, padre_tabella) VALUES
    (900001, 'pg_temp', 'padre_prova',  'EF',    'emittente_fiscale_id', NULL,      NULL),
    (900002, 'pg_temp', 'figlio_prova', 'PADRE', 'padre_id',             'pg_temp', 'padre_prova'),
    (900003, 'pg_temp', 'nipote_prova', 'PADRE', 'figlio_id',            'pg_temp', 'figlio_prova');

SELECT is(dbops.fn_storico_risolvi_scope('pg_temp', 'nipote_prova', '{"figlio_id": 20}'::jsonb),
          4242::bigint,
          '21. PADRE a due salti (uuid → integer → bigint): risale e copia l''EF del capostipite');

SELECT is(dbops.fn_storico_risolvi_scope('pg_temp', 'nipote_prova', '{"figlio_id": null}'::jsonb),
          NULL::bigint,
          '22. PADRE con FK nulla → NULL');

SELECT is(dbops.fn_storico_risolvi_scope('pg_temp', 'nipote_prova', '{"figlio_id": 999}'::jsonb),
          NULL::bigint,
          '23. PADRE con padre sparito → NULL (ammesso dal modello: nessuna FK sulle shadow)');

SELECT is((SELECT dbops.fn_storico_risolvi_scope(p.schema_tabella, p.nome_tabella, '{"emittente_fiscale_id": 1}'::jsonb)
             FROM dbops.storico_scope_policy p
            WHERE p.modo = 'NESSUNO' ORDER BY p.id LIMIT 1),
          NULL::bigint,
          '24. NESSUNO → NULL anche se la riga portasse una colonna con quel nome');

SELECT is(dbops.fn_storico_risolvi_scope('pg_catalog', 'pg_class', '{}'::jsonb),
          NULL::bigint,
          '25. madre non mappata → NULL, e il test 2 la vedrebbe');

-- Fixture: il ciclo. Le due righe si puntano a vicenda: in UNA istruzione,
-- perché la FK è IMMEDIATE e ciascuna ha bisogno dell'altra.
INSERT INTO ciclo_a VALUES (1, 1);
INSERT INTO ciclo_b VALUES (1, 1);
INSERT INTO dbops.storico_scope_policy (id, schema_tabella, nome_tabella, modo, colonna, padre_schema, padre_tabella) VALUES
    (900004, 'pg_temp', 'ciclo_a', 'PADRE', 'b_id', 'pg_temp', 'ciclo_b'),
    (900005, 'pg_temp', 'ciclo_b', 'PADRE', 'a_id', 'pg_temp', 'ciclo_a');

SELECT throws_ok(
    $$ SELECT dbops.fn_storico_risolvi_scope('pg_temp', 'ciclo_a', '{"b_id": 1}'::jsonb) $$,
    'P0001', NULL,
    '26. ciclo nella mappa → errore di dominio: l''unico caso in cui il resolver solleva');

SELECT throws_like(
    $$ SELECT dbops.fn_storico_risolvi_scope('pg_temp', 'ciclo_a', '{"b_id": 1}'::jsonb) $$,
    '%gira ancora in cerchio%',
    '27. ciclo nella mappa → la frase di E_STORICO_SCOPE_CATENA_CICLICA');

-- BA: un billing account non mappato segue la RISERVA di fn_get_ba_emittente_sr_id,
-- che dal 20260913-01 (D13) ha due facce: IN SESSIONE è l'emittente di chi agisce,
-- SENZA sessione è il default dell'installazione. Fino a quel giorno questo test
-- pinnava il default CON il contesto aperto, e passava per coincidenza —
-- l'operatore di contesto era quello del default.
-- ⚠️ Le aziende costruite sono DUE e il contesto passa alla seconda: sullo
--   scratch della CI la prima creata diventa il default per bootstrap, e con
--   una sola le due facce risponderebbero lo stesso emittente. Il contesto del
--   preambolo si salva e si rimette dopo, perché i test 29-32 non c'entrano.
CREATE TEMP TABLE _ctx_preambolo ON COMMIT DROP AS
SELECT current_setting('app.current_user_id', true) AS user_id;

CREATE TEMP TABLE _mondi_ba ON COMMIT DROP AS
SELECT 'A'::text AS lato, m.*
  FROM dbops.fn_pgtap_crea_emittente_operatore() m;

INSERT INTO _mondi_ba
SELECT 'B'::text, m.*
  FROM dbops.fn_pgtap_crea_emittente_operatore() m;

SELECT set_config('app.current_user_id',
                  (SELECT auth_user_id::text FROM _mondi_ba WHERE lato = 'B'),
                  true);

SELECT is(dbops.fn_storico_risolvi_scope('anagrafiche', 'billing_account', '{"id": -1}'::jsonb),
          (SELECT emittente_fiscale_id FROM _mondi_ba WHERE lato = 'B'),
          '28. BA non mappato, IN SESSIONE → l''emittente dell''operatore, convertito in EF (D13)');

SELECT set_config('app.current_user_id', '', true);

SELECT CASE
    WHEN EXISTS (SELECT 1 FROM anagrafiche.emittenti_fiscali_billing_account d WHERE d.is_default) THEN
        is(dbops.fn_storico_risolvi_scope('anagrafiche', 'billing_account', '{"id": -1}'::jsonb),
           (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
              JOIN anagrafiche.emittenti_fiscali_billing_account d ON d.emittente_soggetto_ruolo_id = ef.soggetto_ruolo_id
             WHERE d.is_default),
           '28-bis. BA non mappato, SENZA sessione → l''emittente di default, convertito in EF')
    ELSE
        skip('28-bis. nessun emittente di default su questo database: il ramo BA senza sessione non si può esercitare qui', 1)
END;

-- Il contesto del preambolo torna com'era (transazionale, come le due righe sopra).
SELECT set_config('app.current_user_id', (SELECT user_id FROM _ctx_preambolo), true);

-- ⭐ rev 2026-10-09 (brief-db-istanza-nasce-col-ba): il modo COPPIA, sui valori.
--   Un mondo costruito: il suo cliente ha un BA legato all'emittente del mondo.
--   La riga di prova porta la sua coppia; il resolver deve arrivare a QUELL'emittente.
CREATE TEMP TABLE _mondo_coppia ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('storico scope coppia');

SELECT is(dbops.fn_storico_risolvi_scope('anagrafiche', 'istanze_dati_precontrattuali',
            (SELECT jsonb_build_object('istanza_utility_id', m.istanza_utility_id,
                                       'utility_id',         m.utility_id)
               FROM _mondo_coppia m)),
          (SELECT emittente_fiscale_id FROM _mondo_coppia),
          '28-ter. COPPIA: il BA della coppia (istanza, utility), poi il suo emittente');

SELECT is(dbops.fn_storico_risolvi_scope('anagrafiche', 'istanze_dati_precontrattuali',
            (SELECT jsonb_build_object('istanza_utility_id', m.istanza_utility_id,
                                       'utility_id',         -1)
               FROM _mondo_coppia m)),
          NULL::bigint,
          '28-quater. COPPIA: una coppia senza BA → NULL, fail-closed sulla shadow');

-- ============================================================
-- LA VISTA DI PRESIDIO — porta nel digest ciò che i test 2, 4, 5 dicono in CI
-- ============================================================
-- ⚠️ Le righe di mappa di prova inserite sopra (pg_temp.padre_prova, …) NON
--   hanno una madre col trigger: la vista le elenca, a ragione, come
--   RIGA_SENZA_MADRE. Il «vuota» si asserisce sul mondo vero, escludendo la
--   fixture di questo file — e il 32 usa proprio quelle righe come caso.
SELECT is((SELECT count(*) FROM dbops.vw_storico_scope_da_dichiarare v
            WHERE v.madre NOT LIKE 'pg_temp%'),
          0::bigint,
          '29. la vista di presidio è vuota sul mondo vero: dice la stessa cosa dei test 2, 4, 5');

-- Una madre COSTRUITA col trigger di storico e nessuna riga di mappa. Il
-- trigger non scatta mai (nessuna scrittura): basta che sia montato.
CREATE TEMP TABLE zz_madre_prova (id bigint PRIMARY KEY, storicizza boolean NOT NULL DEFAULT true) ON COMMIT DROP;
CREATE TRIGGER trg_zz_madre_prova_z90_storico_upd_dlt BEFORE UPDATE OR DELETE ON zz_madre_prova
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_storico_generic('zz_madre_prova_id');

SELECT is((SELECT string_agg(v.motivo, ',') FROM dbops.vw_storico_scope_da_dichiarare v
            WHERE v.madre LIKE '%.zz_madre_prova'),
          'SENZA_RIGA',
          '30. una madre col trigger e senza riga di mappa: la vista la elenca come SENZA_RIGA');

-- La stessa madre, protetta e dichiarata NESSUNO: la sua storia è aperta.
ALTER TABLE zz_madre_prova ENABLE ROW LEVEL SECURITY;
INSERT INTO dbops.storico_scope_policy (id, schema_tabella, nome_tabella, modo, ragione) VALUES
    (900201, 'pg_temp', 'zz_madre_prova', 'NESSUNO',
     'Madre di prova del pgTAP dichiarata NESSUNO con la RLS accesa: serve a provare che la vista veda il debito.');

SELECT is((SELECT string_agg(v.motivo, ',') FROM dbops.vw_storico_scope_da_dichiarare v
            WHERE v.madre LIKE '%.zz_madre_prova'),
          'PROTETTA_NESSUNO',
          '31. la stessa madre in RLS con riga NESSUNO: PROTETTA_NESSUNO, e non più SENZA_RIGA');

-- Le righe di prova dei test 21-27 non hanno madre col trigger: sono il caso
-- RIGA_SENZA_MADRE. E la vista deve stare a catalogo come ZERO settimanale.
SELECT ok((SELECT count(*) FROM dbops.vw_storico_scope_da_dichiarare v
            WHERE v.madre = 'pg_temp.padre_prova' AND v.motivo = 'RIGA_SENZA_MADRE') = 1
          AND (SELECT natura = 'ZERO' AND cadenza = 'SETTIMANALE' AND attivo AND obsoleto_dal IS NULL
                      AND registro = 'dbops.storico_scope_policy'
                 FROM dbops.presidi WHERE vista = 'dbops.vw_storico_scope_da_dichiarare'),
          '32. una riga di mappa senza madre è RIGA_SENZA_MADRE; e la vista è a catalogo come ZERO settimanale sul registro giusto');

-- ⭐ rev 2026-11-08 (brief-db-revisione-dbops §22): la vista è security_invoker, e
--   la madre di una riga si cerca sul catalogo, non con to_regclass, che SOLLEVA
--   su uno schema senza USAGE per chi legge (successo con shop.ricevute, riga 126).
--   pg_toast non ha USAGE né per l'app né per il migratore: la riga di prova vale
--   con tutti e due i runner. Con to_regclass il SELECT andrebbe in errore.
INSERT INTO dbops.storico_scope_policy (id, schema_tabella, nome_tabella, modo, colonna) VALUES
    (900202, 'pg_toast', 'zz_riga_schema_chiuso', 'EF', 'emittente_fiscale_id');

SELECT is((SELECT string_agg(v.motivo, ',') FROM dbops.vw_storico_scope_da_dichiarare v
            WHERE v.madre = 'pg_toast.zz_riga_schema_chiuso'),
          'RIGA_SENZA_MADRE',
          '33. una riga di mappa su uno schema senza USAGE per chi legge: RIGA_SENZA_MADRE, non un errore');

SELECT * FROM finish();
ROLLBACK;
