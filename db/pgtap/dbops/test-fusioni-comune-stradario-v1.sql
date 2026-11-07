-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: le fusioni di comuni e vie, e i tre building block che le reggono
--       dbops.fn_admin_merge_stradario · dbops.fn_admin_merge_comune
--       dbops.fn_fusione_figlie · dbops.fn_fusione_righe_doppie ·
--       dbops.fn_fusione_ripunta_figlie · dbops.fn_audit_log_once
--
-- ChangeSet: 20_code/dbops/20261107-01 … -04, -06, -17, -18 (blocco 2a); 00_schema/config/20261107-09,
--            20_code/*/20261107-10 … -16 (blocco 2b, la via soppressa)
-- Brief: brief-db-revisione-dbops, D3, D4, D45, D60, R6, Q16 (giro 2)
--
-- ⛔ I DIFETTI CHE CHIUDE. La fusione delle vie falliva appena la via aveva un
--   indirizzo (il guard di stradario_id rifiutava, la porta non si apriva); la
--   fusione dei comuni ripuntava solo lo stradario; un doppio fermava tutto col
--   23505 senza dire quali righe. I casi si COSTRUISCONO: comuni, vie e
--   indirizzi del test, non quelli che la macchina ha.
--
-- ⚠️ Ambito dichiarato: delle sei figlie del comune il test popola lo stradario
--   e i codici postali (indirizzi, soggetti, aree di fatturazione chiedono un
--   mondo intero). Il ripuntamento e' lo stesso codice per ogni figlia, letto
--   dal catalogo; il test 17 conta comunque su TUTTE le figlie che nessuna
--   nomini piu' l'origine. Il generico (indice parziale, NULL distinti, indice
--   su espressione, RLS, padre senza chiave) si prova su tabelle temporanee.
--
-- Elenco test (plan 28):
--   LA PORTA DELL'AUDIT
--    1 : fn_audit_log_once scrive la durata nella sua colonna
--    2 : con myapp.log_with_dblink = 'on' la riga nasce nella transazione
--   LA FUSIONE DELLE VIE
--    3 : un indirizzo doppio ferma la fusione con E_MERGE_RIGHE_DOPPIE ...
--    4 : ... senza aver spostato niente ...
--    5 : ... e la porta degli indirizzi resta chiusa
--    6 : il controllo dei doppi nomina le due righe (origine e destinazione)
--    7 : tolto il doppio, la fusione riesce
--    8 : ⭐ D3: gli indirizzi sono sulla via di destinazione
--    9 : subito dopo, nella stessa transazione, il cambio a mano e' rifiutato
--   10 : la riga d'audit: righe ripuntate per tabella, durata in colonna
--   11 : la trasformazione e' nel suo registro
--   12 : stessa via come origine e destinazione: E_MERGE_ORIGINE_UGUALE_DESTINAZIONE
--   13 : una via che non esiste: E_STRADARIO_NON_TROVATO
--   14 : un id assente: E_DBOPS_CHIAMATA_NON_VALIDA
--   LA FUSIONE DEI COMUNI
--   15 : la stessa via VIVA nei due comuni ferma la fusione; la via soppressa non e' un doppio
--   16 : tolto il doppio, la fusione riesce
--   17 : ⭐ D4: nessuna figlia, letta dal catalogo, nomina piu' l'origine
--   18 : vie e codici postali sono sul comune di destinazione
--   19 : un comune che non esiste: E_COMUNE_NON_TROVATO
--   I BUILDING BLOCK, SU TABELLE TEMPORANEE
--   20 : le figlie di un padre: una riga per FK, colonne in coppia
--   21 : indice parziale e NULL distinti: un doppio solo, quello vero
--   22 : NULLS NOT DISTINCT: due NULL collidono
--   23 : ⭐ un indice su espressione sfugge al controllo, e la scrittura lo intercetta
--   24 : ... e annulla le figlie gia' ripuntate
--   25 : un padre senza chiave primaria: E_DBOPS_CHIAMATA_NON_VALIDA
--   26 : ⭐ una figlia sotto RLS per chi lancia: E_MERGE_FIGLIA_SOTTO_RLS
--   27 : il ripuntamento restituisce le righe per figlia, anche a zero
--   28 : una FK composta si ripunta per intero
--   ⚠️ I nomi delle tabelle si confrontano con dbops.fn_nome_qualificato: regclass::text
--      toglie lo schema che sta nel search_path, e quello dell'app ha anagrafiche.
--   LA VIA SOPPRESSA (Q16)
--   29 : la fusione segna la via d'origine soppressa, alla data operativa
--   30 : la chiave delle vie e' parziale sulle vie vive, e la FK comune_id ha il suo indice
--   31 : la ricerca delle vie non la propone piu' ...
--   32 : ... nemmeno quella per comune
--   33 : un indirizzo nuovo sulla via soppressa e' rifiutato
--   34 : una via soppressa non si fonde come origine ...
--   35 : ... ne' come destinazione
--   36 : ⭐ un indirizzo con via nuova, sulla terna di una via soppressa, va sulla via viva
--   37 : il controllo dei doppi dell'indirizzo risolve la via viva, non la soppressa
--
-- Read-only: tutto dentro BEGIN;/ROLLBACK;.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(37);

-- Il CODICE dell'errore viaggia nel canale CONSTRAINT_NAME dell'eccezione
-- P0001 (fn_log_and_raise_error): si pinna il codice, non la frase. Il blocco
-- EXCEPTION e' un savepoint: cio' che la chiamata aveva scritto si annulla.
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

-- ============================================================
-- Il mondo del test: due comuni, un codice postale ciascuno, due vie sul
-- primo, tre indirizzi (il terzo e' il doppio del secondo, sull'altra via).
-- ============================================================
CREATE TEMP TABLE t_ids (chiave text PRIMARY KEY, id bigint NOT NULL);

WITH c AS (
    -- Con la provincia: l'indirizzo vuole una via completa (comune, provincia, CAP).
    INSERT INTO config.comuni (descrizione, provincia_id)
    SELECT d, (SELECT min(id) FROM config.province)
      FROM (VALUES ('PGTAP FUSIONE A'), ('PGTAP FUSIONE B')) v(d)
    RETURNING id, descrizione)
INSERT INTO t_ids
SELECT CASE descrizione WHEN 'PGTAP FUSIONE A' THEN 'comune_a' ELSE 'comune_b' END, id FROM c;

INSERT INTO config.codici_postali (codice, comune_id)
SELECT '99901', id FROM t_ids WHERE chiave = 'comune_a';
INSERT INTO t_ids SELECT 'cp_a', currval(pg_get_serial_sequence('config.codici_postali', 'id'));
INSERT INTO config.codici_postali (codice, comune_id)
SELECT '99902', id FROM t_ids WHERE chiave = 'comune_b';
INSERT INTO t_ids SELECT 'cp_b', currval(pg_get_serial_sequence('config.codici_postali', 'id'));

-- Due vie generali di seed: servono solo come ancora.
INSERT INTO t_ids
SELECT 'sg_' || row_number() OVER (ORDER BY id), id
  FROM (SELECT id FROM config.stradario_generale ORDER BY id LIMIT 2) s;

INSERT INTO config.stradario (comune_id, stradario_generale_id, codice_postale_id)
SELECT (SELECT id FROM t_ids WHERE chiave = 'comune_a'), (SELECT id FROM t_ids WHERE chiave = 'sg_1'),
       (SELECT id FROM t_ids WHERE chiave = 'cp_a');
INSERT INTO t_ids SELECT 'via_1', currval(pg_get_serial_sequence('config.stradario', 'id'));
INSERT INTO config.stradario (comune_id, stradario_generale_id, codice_postale_id)
SELECT (SELECT id FROM t_ids WHERE chiave = 'comune_a'), (SELECT id FROM t_ids WHERE chiave = 'sg_2'),
       (SELECT id FROM t_ids WHERE chiave = 'cp_a');
INSERT INTO t_ids SELECT 'via_2', currval(pg_get_serial_sequence('config.stradario', 'id'));

-- Gli indirizzi dal building block del dominio, come li crea l'applicazione.
INSERT INTO t_ids
SELECT 'ind_1', anagrafiche.fn_get_or_create_indirizzo_dettaglio((SELECT id FROM t_ids WHERE chiave = 'via_1')::int, 1, NULL, NULL, NULL, NULL, NULL);
INSERT INTO t_ids
SELECT 'ind_2', anagrafiche.fn_get_or_create_indirizzo_dettaglio((SELECT id FROM t_ids WHERE chiave = 'via_1')::int, 2, NULL, NULL, NULL, NULL, NULL);
INSERT INTO t_ids
SELECT 'ind_3', anagrafiche.fn_get_or_create_indirizzo_dettaglio((SELECT id FROM t_ids WHERE chiave = 'via_2')::int, 2, NULL, NULL, NULL, NULL, NULL);

CREATE FUNCTION pg_temp.id(p text) RETURNS bigint LANGUAGE sql STABLE AS
$$ SELECT id FROM t_ids WHERE chiave = p $$;

-- ============================================================
-- LA PORTA DELL'AUDIT
-- ============================================================
-- La porta si chiama in un'istruzione e si legge nella successiva: la stessa
-- SELECT non vedrebbe la riga che scrive.
INSERT INTO t_ids SELECT 'audit_1', dbops.fn_audit_log_once(p_function_name => 'pgtap.fusioni',
                                                            p_status => 'OK', p_duration_ms => 42);
SELECT is(
    (SELECT a.duration_ms FROM dbops.audit_log a WHERE a.id = pg_temp.id('audit_1')),
    42,
    '1. fn_audit_log_once scrive la durata nella colonna duration_ms');

-- L'interruttore si rimette poi al valore di prima: spento, il registro degli
-- errori del resto del file non scriverebbe (assente vale acceso).
CREATE TEMP TABLE t_guc AS SELECT current_setting('myapp.log_with_dblink', true) AS v;
SELECT set_config('myapp.log_with_dblink', 'on', true);
INSERT INTO t_ids SELECT 'audit_2', dbops.fn_audit_log_once(p_function_name => 'pgtap.fusioni', p_status => 'OK');
SELECT is(
    (SELECT count(*)::int FROM dbops.audit_log a WHERE a.id = pg_temp.id('audit_2')),
    1,
    '2. con myapp.log_with_dblink = on la riga nasce nella transazione del chiamante (il ramo dblink non c''e'' piu'')');
SELECT set_config('myapp.log_with_dblink', COALESCE((SELECT v FROM t_guc), ''), true);

-- ============================================================
-- LA FUSIONE DELLE VIE
-- ============================================================
SELECT is(
    pg_temp.codice_errore(format('SELECT dbops.fn_admin_merge_stradario(%s, %s)', pg_temp.id('via_1'), pg_temp.id('via_2'))),
    'E_MERGE_RIGHE_DOPPIE',
    '3. un indirizzo uguale sulle due vie ferma la fusione con E_MERGE_RIGHE_DOPPIE');

SELECT is(
    (SELECT count(*)::int FROM anagrafiche.indirizzi_dettaglio
      WHERE id IN (pg_temp.id('ind_1'), pg_temp.id('ind_2')) AND stradario_id = pg_temp.id('via_1')),
    2,
    '4. ... senza aver spostato niente');

SELECT ok(
    current_setting('zeroerp.maintenance_indirizzi_dettaglio', true) IS DISTINCT FROM 'on',
    '5. ... e la porta degli indirizzi resta chiusa dopo il rifiuto');

SELECT is(
    (SELECT jsonb_agg(jsonb_build_object('t', dbops.fn_nome_qualificato(d.tabella), 'o', d.riga_origine, 'd', d.riga_destinazione))
       FROM dbops.fn_fusione_righe_doppie('config.stradario', pg_temp.id('via_1'), pg_temp.id('via_2')) d),
    jsonb_build_array(jsonb_build_object('t', 'anagrafiche.indirizzi_dettaglio',
                                         'o', jsonb_build_object('id', pg_temp.id('ind_2')),
                                         'd', jsonb_build_object('id', pg_temp.id('ind_3')))),
    '6. il controllo dei doppi nomina le due righe: l''indirizzo dell''origine e quello che la destinazione ha gia''');

UPDATE anagrafiche.indirizzi_dettaglio SET civico = 3 WHERE id = pg_temp.id('ind_3');

SELECT lives_ok(
    format('SELECT dbops.fn_admin_merge_stradario(%s, %s)', pg_temp.id('via_1'), pg_temp.id('via_2')),
    '7. tolto il doppio, la fusione delle vie riesce');

SELECT is(
    (SELECT count(*)::int FROM anagrafiche.indirizzi_dettaglio
      WHERE id IN (pg_temp.id('ind_1'), pg_temp.id('ind_2'), pg_temp.id('ind_3'))
        AND stradario_id = pg_temp.id('via_2')),
    3,
    '8. D3: gli indirizzi della via fusa sono sulla via di destinazione');

SELECT is(
    pg_temp.codice_errore(format('UPDATE anagrafiche.indirizzi_dettaglio SET stradario_id = %s WHERE id = %s',
                                 pg_temp.id('via_1'), pg_temp.id('ind_1'))),
    'E_COLONNA_NON_MODIFICABILE',
    '9. subito dopo, nella stessa transazione, il cambio di via a mano e'' di nuovo rifiutato');

SELECT ok(
    (SELECT a.duration_ms IS NOT NULL
        AND a.result -> 'ripuntati' ->> 'anagrafiche.indirizzi_dettaglio' = '2'
        AND NOT (a.result ? 'duration_ms')
       FROM dbops.audit_log a
      WHERE a.function_name = 'dbops.fn_admin_merge_stradario'
        AND a.params ->> 'p_id_orig' = pg_temp.id('via_1')::text
      ORDER BY a.id DESC LIMIT 1),
    '10. la riga d''audit: due indirizzi ripuntati, la durata nella colonna e non in result');

SELECT is(
    (SELECT count(*)::int FROM storico.stradario_trasformazioni
      WHERE via_id_orig = pg_temp.id('via_1') AND via_id_nuovo = pg_temp.id('via_2')),
    1,
    '11. la trasformazione e'' nel suo registro');

SELECT is(
    pg_temp.codice_errore(format('SELECT dbops.fn_admin_merge_stradario(%s, %s)', pg_temp.id('via_2'), pg_temp.id('via_2'))),
    'E_MERGE_ORIGINE_UGUALE_DESTINAZIONE',
    '12. la stessa via come origine e destinazione: E_MERGE_ORIGINE_UGUALE_DESTINAZIONE');

SELECT is(
    pg_temp.codice_errore(format('SELECT dbops.fn_admin_merge_stradario(%s, %s)',
                                 (SELECT max(id) + 1000 FROM config.stradario), pg_temp.id('via_2'))),
    'E_STRADARIO_NON_TROVATO',
    '13. una via che non esiste: E_STRADARIO_NON_TROVATO');

SELECT is(
    pg_temp.codice_errore(format('SELECT dbops.fn_admin_merge_stradario(NULL, %s)', pg_temp.id('via_2'))),
    'E_DBOPS_CHIAMATA_NON_VALIDA',
    '14. un id assente: E_DBOPS_CHIAMATA_NON_VALIDA');

-- ============================================================
-- LA FUSIONE DEI COMUNI
-- ============================================================
-- La stessa via (via generale e codice postale) anche nel comune B.
INSERT INTO config.stradario (comune_id, stradario_generale_id, codice_postale_id)
SELECT pg_temp.id('comune_b'), pg_temp.id('sg_2'), pg_temp.id('cp_a');
INSERT INTO t_ids SELECT 'via_b', currval(pg_get_serial_sequence('config.stradario', 'id'));
-- E nel comune B la via viva con la terna della via 1, che dopo la fusione
-- delle vie e' soppressa: spostata in B, non deve collidere (Q16).
INSERT INTO config.stradario (comune_id, stradario_generale_id, codice_postale_id)
SELECT pg_temp.id('comune_b'), pg_temp.id('sg_1'), pg_temp.id('cp_a');
INSERT INTO t_ids SELECT 'via_b1', currval(pg_get_serial_sequence('config.stradario', 'id'));

SELECT ok(
    pg_temp.codice_errore(format('SELECT dbops.fn_admin_merge_comune(%s, %s)', pg_temp.id('comune_a'), pg_temp.id('comune_b')))
        = 'E_MERGE_RIGHE_DOPPIE'
    AND (SELECT array_agg(d.riga_origine ->> 'id')
           FROM dbops.fn_fusione_righe_doppie('config.comuni', pg_temp.id('comune_a'), pg_temp.id('comune_b')) d)
        = ARRAY[pg_temp.id('via_2')::text],
    '15. la stessa via viva nei due comuni ferma la fusione; la via soppressa, con la stessa terna di una via viva, non e'' un doppio');

UPDATE config.stradario SET codice_postale_id = pg_temp.id('cp_b') WHERE id = pg_temp.id('via_b');

CREATE FUNCTION pg_temp.figlie_che_nominano(p_padre regclass, p_id bigint) RETURNS bigint
LANGUAGE plpgsql AS $$
DECLARE r record; v_n bigint; v_tot bigint := 0;
BEGIN
    FOR r IN SELECT * FROM dbops.fn_fusione_figlie(p_padre) LOOP
        EXECUTE format('SELECT count(*) FROM %s WHERE %I = $1', r.figlia, r.colonne_fk[1])
           INTO v_n USING p_id;
        v_tot := v_tot + v_n;
    END LOOP;
    RETURN v_tot;
END $$;

SELECT lives_ok(
    format('SELECT dbops.fn_admin_merge_comune(%s, %s)', pg_temp.id('comune_a'), pg_temp.id('comune_b')),
    '16. tolto il doppio, la fusione dei comuni riesce');
SELECT is(
    pg_temp.figlie_che_nominano('config.comuni', pg_temp.id('comune_a')),
    0::bigint,
    '17. D4: nessuna figlia del comune, letta dal catalogo, nomina piu'' il comune soppresso');

SELECT is(
    (SELECT count(*)::int FROM config.stradario
      WHERE id IN (pg_temp.id('via_1'), pg_temp.id('via_2')) AND comune_id = pg_temp.id('comune_b'))
  + (SELECT count(*)::int FROM config.codici_postali
      WHERE id = pg_temp.id('cp_a') AND comune_id = pg_temp.id('comune_b')),
    3,
    '18. le due vie e il codice postale del comune soppresso sono sul comune di destinazione');

SELECT is(
    pg_temp.codice_errore(format('SELECT dbops.fn_admin_merge_comune(%s, %s)',
                                 (SELECT max(id) + 1000 FROM config.comuni), pg_temp.id('comune_b'))),
    'E_COMUNE_NON_TROVATO',
    '19. un comune che non esiste: E_COMUNE_NON_TROVATO');

-- ============================================================
-- I BUILDING BLOCK, SU TABELLE TEMPORANEE
-- ============================================================
CREATE TEMP TABLE t_padre (id int PRIMARY KEY, codice text UNIQUE, sotto text, UNIQUE (codice, sotto));
INSERT INTO t_padre VALUES (1, 'P1', 'x'), (2, 'P2', 'x');

CREATE TEMP TABLE t_figlia (
    id     int PRIMARY KEY,
    padre  int REFERENCES t_padre(id),
    k      text,
    attivo boolean NOT NULL DEFAULT true);
CREATE UNIQUE INDEX t_figlia_uq_attivi ON t_figlia (padre, k) WHERE attivo;
INSERT INTO t_figlia VALUES
    (1, 1, 'x',  true),   -- doppio di 2
    (2, 2, 'x',  true),
    (3, 1, 'y',  false),  -- fuori dal predicato: non e' un doppio di 4
    (4, 2, 'y',  false),
    (5, 1, NULL, true),   -- NULL distinti: non e' un doppio di 6
    (6, 2, NULL, true);

CREATE TEMP TABLE t_figlia_nn (id int PRIMARY KEY, padre int REFERENCES t_padre(id), k text);
CREATE UNIQUE INDEX t_figlia_nn_uq ON t_figlia_nn (padre, k) NULLS NOT DISTINCT;
INSERT INTO t_figlia_nn VALUES (1, 1, NULL), (2, 2, NULL);

CREATE TEMP TABLE t_figlia_comp (id int PRIMARY KEY, codice text, sotto text,
                                 FOREIGN KEY (codice, sotto) REFERENCES t_padre(codice, sotto));
INSERT INTO t_figlia_comp VALUES (1, 'P1', 'x');

SELECT is(
    (SELECT array_agg(format('%s:%s>%s', f.figlia, array_to_string(f.colonne_fk, ','), array_to_string(f.colonne_rif, ','))
                      ORDER BY f.figlia::text)
       FROM dbops.fn_fusione_figlie('pg_temp.t_padre') f),
    ARRAY['pg_temp.t_figlia'::regclass::text || ':padre>id',
          'pg_temp.t_figlia_comp'::regclass::text || ':codice,sotto>codice,sotto',
          'pg_temp.t_figlia_nn'::regclass::text || ':padre>id'],
    '20. le figlie di un padre: una riga per FK, le colonne in coppia (anche una FK composta verso un''altra chiave)');

SELECT is(
    (SELECT array_agg(d.riga_origine ->> 'id' ORDER BY d.riga_origine ->> 'id')
       FROM dbops.fn_fusione_righe_doppie('pg_temp.t_padre', 1, 2) d
      WHERE d.tabella = 'pg_temp.t_figlia'::regclass),
    ARRAY['1'],
    '21. indice parziale e NULL distinti: un doppio solo, quello vero (la riga 1 contro la 2)');

SELECT is(
    (SELECT count(*)::int FROM dbops.fn_fusione_righe_doppie('pg_temp.t_padre', 1, 2) d
      WHERE d.tabella = 'pg_temp.t_figlia_nn'::regclass),
    1,
    '22. con NULLS NOT DISTINCT due NULL collidono');

-- Un indice su espressione: il controllo non lo legge, la scrittura si'.
DELETE FROM t_figlia WHERE id = 1;
DELETE FROM t_figlia_nn WHERE id = 1;
CREATE TEMP TABLE t_figlia_expr (id int PRIMARY KEY, padre int REFERENCES t_padre(id), k text);
CREATE UNIQUE INDEX t_figlia_expr_uq ON t_figlia_expr (padre, lower(k));
INSERT INTO t_figlia_expr VALUES (1, 1, 'Z'), (2, 2, 'z');

SELECT is(
    pg_temp.codice_errore($$SELECT dbops.fn_fusione_ripunta_figlie('pg_temp.t_padre', 1, 2)$$),
    'E_MERGE_RIGHE_DOPPIE',
    '23. un doppio su un indice su espressione sfugge al controllo, e la scrittura lo intercetta con lo stesso codice');

SELECT is(
    (SELECT count(*)::int FROM t_figlia WHERE padre = 1),
    2,
    '24. ... e le figlie gia'' ripuntate prima del rifiuto tornano sull''origine');

CREATE TEMP TABLE t_senza_chiave (id int);
SELECT is(
    pg_temp.codice_errore($$SELECT * FROM dbops.fn_fusione_figlie('pg_temp.t_senza_chiave')$$),
    'E_DBOPS_CHIAMATA_NON_VALIDA',
    '25. un padre senza chiave primaria: E_DBOPS_CHIAMATA_NON_VALIDA');

CREATE TEMP TABLE t_figlia_rls (id int PRIMARY KEY, padre int REFERENCES t_padre(id));
ALTER TABLE t_figlia_rls ENABLE ROW LEVEL SECURITY;
ALTER TABLE t_figlia_rls FORCE ROW LEVEL SECURITY;
SELECT is(
    pg_temp.codice_errore($$SELECT * FROM dbops.fn_fusione_figlie('pg_temp.t_padre')$$),
    'E_MERGE_FIGLIA_SOTTO_RLS',
    '26. una figlia sotto RLS per chi lancia: la fusione si ferma prima di scrivere');
DROP TABLE t_figlia_rls;

DELETE FROM t_figlia_expr WHERE id = 1;
SELECT is(
    dbops.fn_fusione_ripunta_figlie('pg_temp.t_padre', 1, 2),
    jsonb_build_object(dbops.fn_nome_qualificato('pg_temp.t_figlia'), 2, dbops.fn_nome_qualificato('pg_temp.t_figlia_comp'), 1,
                       dbops.fn_nome_qualificato('pg_temp.t_figlia_expr'), 0, dbops.fn_nome_qualificato('pg_temp.t_figlia_nn'), 0),
    '27. il ripuntamento restituisce le righe per figlia, anche a zero');

SELECT is(
    (SELECT codice || '/' || sotto FROM t_figlia_comp WHERE id = 1),
    'P2/x',
    '28. una FK composta si ripunta per intero');

-- ============================================================
-- LA VIA SOPPRESSA (Q16)
-- Lo stato: la via 1 e' stata fusa nella via 2 (test 7) ed e' soppressa;
-- con la fusione dei comuni (test 16) e' passata al comune B, dove la via
-- viva via_b1 ha la sua stessa terna.
-- ============================================================
SELECT is(
    (SELECT obsoleto_dal FROM config.stradario WHERE id = pg_temp.id('via_1')),
    script.fn_data_operativa(),
    '29. la fusione segna la via d''origine soppressa, alla data operativa');

SELECT ok(
    (SELECT pg_get_expr(i.indpred, i.indrelid) = '(obsoleto_dal IS NULL)'
       FROM pg_index i WHERE i.indexrelid = 'config.uq_stradario_comune_stradario_gen_cp'::regclass)
    AND to_regclass('config.ix_config_stradario_comune_id') IS NOT NULL,
    '30. la chiave delle vie e'' parziale sulle vie vive, e la FK comune_id ha il suo indice');

SELECT ok(
    EXISTS (SELECT 1 FROM script.fn_search_stradario(pg_temp.id('comune_b')::int, NULL, 10000) r
             WHERE r.stradario_id = pg_temp.id('via_b1'))
    AND NOT EXISTS (SELECT 1 FROM script.fn_search_stradario(pg_temp.id('comune_b')::int, NULL, 10000) r
                     WHERE r.stradario_id = pg_temp.id('via_1')),
    '31. la ricerca delle vie propone la via viva e non la soppressa');

SELECT ok(
    NOT EXISTS (SELECT 1 FROM script.fn_get_stradario(pg_temp.id('comune_b')::int, '') r
                 WHERE r.stradario_id = pg_temp.id('via_1'))
    AND EXISTS (SELECT 1 FROM script.fn_get_stradario(pg_temp.id('comune_b')::int, '') r
                 WHERE r.stradario_id = pg_temp.id('via_b1')),
    '32. nemmeno la ricerca per comune propone la via soppressa');

SELECT is(
    pg_temp.codice_errore(format(
        'SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(%s, 9, NULL, NULL, NULL, NULL, NULL)',
        pg_temp.id('via_1'))),
    'E_CATALOGO_OBSOLETO_NUOVA_ISTANZA',
    '33. un indirizzo nuovo sulla via soppressa e'' rifiutato dal guard del ritiro');

SELECT is(
    pg_temp.codice_errore(format('SELECT dbops.fn_admin_merge_stradario(%s, %s)', pg_temp.id('via_1'), pg_temp.id('via_b1'))),
    'E_STRADARIO_SOPPRESSO',
    '34. una via soppressa non si fonde come origine');

SELECT is(
    pg_temp.codice_errore(format('SELECT dbops.fn_admin_merge_stradario(%s, %s)', pg_temp.id('via_b1'), pg_temp.id('via_1'))),
    'E_STRADARIO_SOPPRESSO',
    '35. ... ne'' come destinazione');

INSERT INTO t_ids
SELECT 'ind_b1', anagrafiche.fn_create_indirizzo(
           p_toponomastica_id  => sg.toponomastica_id,
           p_descrizione_via   => sg.descrizione,
           p_comune_id         => pg_temp.id('comune_b')::int,
           p_codice_postale_id => pg_temp.id('cp_a')::int,
           p_civico            => 7)
  FROM config.stradario_generale sg WHERE sg.id = pg_temp.id('sg_1');
SELECT is(
    (SELECT stradario_id::bigint FROM anagrafiche.indirizzi_dettaglio WHERE id = pg_temp.id('ind_b1')),
    pg_temp.id('via_b1'),
    '36. un indirizzo con via nuova, sulla terna che ha anche una via soppressa, nasce sulla via viva');

SELECT ok(
    EXISTS (SELECT 1 FROM script.fn_check_indirizzo_duplicato(
                p_civico => 7,
                p_stradario_generale_id => pg_temp.id('sg_1')::int,
                p_comune_id => pg_temp.id('comune_b')::int,
                p_codice_postale_id => pg_temp.id('cp_a')::int) d
             WHERE d.indirizzo_dettaglio_id = pg_temp.id('ind_b1')),
    '37. il controllo dei doppi dell''indirizzo risolve la via viva, non la soppressa con la stessa terna');

SELECT * FROM finish();

ROLLBACK;
