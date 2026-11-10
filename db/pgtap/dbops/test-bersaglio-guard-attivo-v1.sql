-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test monta i trigger ATTIVO su tabelle TEMP sue (CREATE TRIGGER, DDL) e
--   dichiara un tipo di prova in config.tipi_entita, che l'applicazione non scrive. Le letture dei
--   guard rispondono solo per tabelle del proprietario del database (lo prova, come app,
--   dbops/test-guard-attivo-occhi-del-proprietario-v1). Stesso criterio di
--   dbops/test-guard-attivo-grammatica-e-codici-v1.
--
-- Test: i rifiuti dei guard ATTIVO non nominano tabelle; la riga in causa la dice il bersaglio.
-- Riferimento: brief-db-revisione-dbops, S-BE-1 (§35).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la tabella di un tipo sta in config.tipi_entita.tabella (tipo non sorgente) o in
--     config.sorgenti.target_table (tipo sorgente): una sede per tipo, una tabella per al piu' un tipo;
--   - script.fn_bersaglio_di_riga da' il bersaglio solo se il catalogo dichiara la tabella, la
--     colonna e' la chiave del tipo, e (per un tipo sorgente) la sorgente ha una pagina;
--   - le cinque frasi della famiglia non hanno segnaposti, e un rifiuto vero porta la frase del
--     catalogo, senza nomi di tabelle;
--   - «padre non attivo» e «padre ritirato» portano il bersaglio del padre quando il tipo c'e';
--     «padre inesistente» e il BLOCK no;
--   - i motivi delle due check di disattivazione non portano piu' i valori della frase.
--
-- Elenco test (plan 21):
--   1)  config.tipi_entita.tabella esiste, text
--   2)  i tre vincoli della colonna (forma, non sorgente, univoca)
--   3)  PRESIDIO: ogni tabella dichiarata esiste e ha la colonna chiave del tipo
--   4)  PRESIDIO: nessuna tabella dichiarata e' anche la target_table di una sorgente
--   5)  bersaglio di una riga di un tipo non sorgente (ARTICOLO)
--   6)  nessun bersaglio per una tabella senza tipo (config.iva)
--   7)  nessun bersaglio se la colonna non e' la chiave del tipo
--   8)  nessun bersaglio senza valore
--   9)  bersaglio di una sorgente con una pagina (FATTURA)
--  10)  nessun bersaglio per una sorgente senza pagina (EVENTO_ASSET)
--  11)  PRESIDIO: le cinque frasi della famiglia non hanno segnaposti
--  12)  padre spento: E_ATTIVO_PADRE_NON_ATTIVO, con la frase del catalogo
--  13)  ... e il bersaglio del padre, dal tipo dichiarato
--  14)  padre spento senza tipo: lo stesso codice, nessun bersaglio
--  15)  padre assente (chiave senza FK): E_PADRE_INESISTENTE, frase del catalogo, nessun bersaglio
--  16)  padre ritirato: E_CATALOGO_OBSOLETO_NUOVA_ISTANZA, frase del catalogo
--  17)  ... e il bersaglio del padre
--  18)  BLOCK con figlie attive: E_ATTIVO_BLOCK_CHILDREN_ACTIVE, frase del catalogo, nessun bersaglio
--  19)  BLOCK con figlie senza attivo: E_ATTIVO_BLOCK_CHILDREN_EXIST, frase del catalogo
--  20)  PRESIDIO sul testo: nessun motivo di script.fn_check_registro_disattivabile porta valori
--  21)  ... ne' di script.fn_check_famiglia_documento_disattivabile
--
-- ⚠️ I test 3, 4 e 11 sono presidi sul catalogo che c'e'; la regola la provano i test 5-10 e 12-20
--   sulla fixture che si costruiscono. 20 e 21 leggono il corpo.
-- ⚠️ Il contesto del diario (padre, figlia, colonna, valore) non si prova qui: dbops.error_log si
--   scrive fuori transazione, via dblink, solo col canale acceso, e il test non dipende dalla
--   configurazione della macchina.
-- ⚠️ Fixture su tabelle TEMP e un tipo di prova: il ROLLBACK porta via tutto. I trigger sono
--   immediati e scritti a mano con la grammatica del generatore.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il file legge i cataloghi e scrive solo tabelle TEMP sue e un tipo di
--   prova: nessuna tabella sotto RLS, nessuna veste da aprire.

SELECT plan(21);

-- Il rifiuto, nei tre canali che il backend legge: codice, frase, bersaglio.
CREATE FUNCTION pg_temp.rifiuto(p_sql text) RETURNS jsonb
LANGUAGE plpgsql AS $$
DECLARE v_c text; v_m text; v_d text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME, v_m = MESSAGE_TEXT, v_d = PG_DATATYPE_NAME;
    RETURN jsonb_build_object('codice', v_c, 'frase', v_m, 'bersaglio', NULLIF(v_d, ''));
END $$;

CREATE FUNCTION pg_temp.frase(p_codice text) RETURNS text
LANGUAGE sql AS $$
    SELECT m.messaggio FROM config.messaggi_errore m WHERE m.codice = p_codice AND m.lingua = 'it'
$$;

-- ============================================================
-- 1-4) La colonna e il catalogo
-- ============================================================
SELECT col_type_is('config', 'tipi_entita', 'tabella', 'text',
    '1) config.tipi_entita.tabella esiste, text (non regclass: un OID segue i RENAME in silenzio)');

SELECT is(
    (SELECT string_agg(c.conname, ', ' ORDER BY c.conname)
       FROM pg_constraint c
      WHERE c.conrelid = 'config.tipi_entita'::regclass
        AND c.conname IN ('chk_tipi_entita_tabella_forma', 'chk_tipi_entita_tabella_non_sorgente',
                          'uq_tipi_entita_tabella')),
    'chk_tipi_entita_tabella_forma, chk_tipi_entita_tabella_non_sorgente, uq_tipi_entita_tabella',
    '2) i tre vincoli della colonna: forma schema.tabella, NULL per un tipo sorgente, una tabella per al piu'' un tipo');

SELECT is(
    (SELECT string_agg(t.codice || ' ' || t.tabella, ', ' ORDER BY t.codice)
       FROM config.tipi_entita t
      WHERE t.tabella IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM pg_attribute a
                         WHERE a.attrelid = to_regclass(t.tabella)
                           AND a.attname = t.key_selector AND a.attnum > 0 AND NOT a.attisdropped)),
    NULL,
    '3) presidio: ogni tabella dichiarata esiste e ha la colonna chiave del tipo');

SELECT is(
    (SELECT string_agg(t.codice || ' ' || s.codice_interno, ', ' ORDER BY t.codice)
       FROM config.tipi_entita t
       JOIN config.sorgenti s ON s.target_table = to_regclass(t.tabella)),
    NULL,
    '4) presidio: nessuna tabella dichiarata e'' anche la target_table di una sorgente (una sede per tabella)');

-- ============================================================
-- 5-10) Il building block, sul catalogo vero
-- ============================================================
SELECT is(script.fn_bersaglio_di_riga('catalogo', 'articoli', 'id', '42'),
    jsonb_build_array(jsonb_build_object('tipo', 'ARTICOLO', 'id', '42')),
    '5) una riga di catalogo.articoli e'' il bersaglio ARTICOLO');

SELECT is(script.fn_bersaglio_di_riga('config', 'iva', 'id', '1'), NULL,
    '6) config.iva non ha un tipo: nessun bersaglio, la frase regge da sola');

SELECT is(script.fn_bersaglio_di_riga('catalogo', 'articoli', 'codice', 'X'), NULL,
    '7) la colonna non e'' la chiave del tipo: nessun bersaglio (porterebbe altrove)');

SELECT is(script.fn_bersaglio_di_riga('catalogo', 'articoli', 'id', NULL), NULL,
    '8) senza valore nessun bersaglio');

SELECT is(script.fn_bersaglio_di_riga('vendite', 'fatture', 'id', '7'),
    jsonb_build_array(jsonb_build_object('tipo', 'FATTURA', 'id', '7')),
    '9) una sorgente con una pagina: la sua target_table da'' il tipo');

SELECT is(script.fn_bersaglio_di_riga('magazzino', 'eventi_assets', 'id', '7'), NULL,
    '10) una sorgente senza pagina (apribile falso): nessun bersaglio');

-- ============================================================
-- 11) Le frasi
-- ============================================================
SELECT is(
    (SELECT string_agg(m.codice, ', ' ORDER BY m.codice)
       FROM config.messaggi_errore m
      WHERE m.codice IN ('E_ATTIVO_PADRE_NON_ATTIVO', 'E_PADRE_INESISTENTE', 'E_CATALOGO_OBSOLETO_NUOVA_ISTANZA',
                         'E_ATTIVO_BLOCK_CHILDREN_ACTIVE', 'E_ATTIVO_BLOCK_CHILDREN_EXIST')
        AND m.messaggio LIKE '%\%%'),
    NULL,
    '11) presidio: le cinque frasi della famiglia non hanno segnaposti (i guard passano il variadico vuoto)');

-- ============================================================
-- Fixture: un padre con un tipo, uno senza, le figlie
-- ============================================================
CREATE TEMP TABLE t_padre       (id bigint PRIMARY KEY, attivo boolean NOT NULL DEFAULT true, obsoleto_dal date);
CREATE TEMP TABLE t_padre_muto  (id bigint PRIMARY KEY, attivo boolean NOT NULL DEFAULT true);
CREATE TEMP TABLE t_figlia      (id bigint PRIMARY KEY, padre_id bigint REFERENCES t_padre (id), attivo boolean NOT NULL DEFAULT true);
CREATE TEMP TABLE t_figlia_muta (id bigint PRIMARY KEY, padre_id bigint REFERENCES t_padre_muto (id), attivo boolean NOT NULL DEFAULT true);
CREATE TEMP TABLE t_figlia_nuda (id bigint PRIMARY KEY, padre_id bigint REFERENCES t_padre (id));
-- chiave senza FK: il padre puo' mancare
CREATE TEMP TABLE t_poli        (id bigint PRIMARY KEY, target_id bigint);
CREATE TEMP TABLE t_obs         (id bigint PRIMARY KEY, padre_id bigint REFERENCES t_padre (id));

INSERT INTO t_padre (id, attivo, obsoleto_dal) VALUES
    (1, true,  NULL),
    (2, false, NULL),
    (3, true,  DATE '2000-01-01'),
    (4, true,  NULL);
INSERT INTO t_padre_muto (id, attivo) VALUES (2, false);

DO $fixture$
DECLARE
    v_s pg_catalog.pg_namespace.nspname%TYPE :=
        (SELECT n.nspname FROM pg_catalog.pg_namespace n WHERE n.oid = pg_my_temp_schema());
BEGIN
    EXECUTE format($t$CREATE TRIGGER trg_t_req AFTER INSERT OR UPDATE ON %1$I.t_figlia FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent(%1$L, 't_padre', 'attivo', 'padre_id', 'id')$t$, v_s);
    EXECUTE format($t$CREATE TRIGGER trg_t_req_muta AFTER INSERT OR UPDATE ON %1$I.t_figlia_muta FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent(%1$L, 't_padre_muto', 'attivo', 'padre_id', 'id')$t$, v_s);
    EXECUTE format($t$CREATE TRIGGER trg_t_poli AFTER INSERT OR UPDATE ON %1$I.t_poli FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent(%1$L, 't_padre', 'attivo', 'target_id', 'id')$t$, v_s);
    EXECUTE format($t$CREATE TRIGGER trg_t_obs BEFORE INSERT OR UPDATE ON %1$I.t_obs FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent(%1$L, 't_padre', 'obsoleto_dal', 'padre_id', 'id')$t$, v_s);
    EXECUTE format($t$CREATE TRIGGER trg_t_blk BEFORE UPDATE OF attivo ON %1$I.t_padre FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children(%1$L, 't_figlia', 'padre_id', 'id', 'attivo')$t$, v_s);
    EXECUTE format($t$CREATE TRIGGER trg_t_blk_nuda BEFORE UPDATE OF attivo ON %1$I.t_padre FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children(%1$L, 't_figlia_nuda', 'padre_id', 'id', 'attivo')$t$, v_s);
    -- il tipo di prova: la sua tabella e' il padre TEMP
    INSERT INTO config.tipi_entita (codice, etichetta_key, key_selector, tabella, note)
         VALUES ('PGTAP_SBE1', 'pgtap.sbe1', 'id', v_s || '.t_padre', 'Tipo di prova del pgTAP.');
END
$fixture$;

-- ============================================================
-- 12-17) I due require
-- ============================================================
CREATE TEMP TABLE tmp_r AS SELECT
    pg_temp.rifiuto($$INSERT INTO t_figlia (id, padre_id) VALUES (10, 2)$$)        AS spento,
    pg_temp.rifiuto($$INSERT INTO t_figlia_muta (id, padre_id) VALUES (10, 2)$$)   AS spento_muto,
    pg_temp.rifiuto($$INSERT INTO t_poli (id, target_id) VALUES (10, 999)$$)       AS assente,
    pg_temp.rifiuto($$INSERT INTO t_obs (id, padre_id) VALUES (10, 3)$$)           AS ritirato;

SELECT is((SELECT spento - 'bersaglio' FROM tmp_r),
    jsonb_build_object('codice', 'E_ATTIVO_PADRE_NON_ATTIVO', 'frase', pg_temp.frase('E_ATTIVO_PADRE_NON_ATTIVO')),
    '12) padre spento: E_ATTIVO_PADRE_NON_ATTIVO, con la frase del catalogo (nessun nome di tabella)');

SELECT is((SELECT spento ->> 'bersaglio' FROM tmp_r), 'PGTAP_SBE1:2',
    '13) ... e il bersaglio del padre, dal tipo che ne dichiara la tabella');

SELECT is((SELECT spento_muto FROM tmp_r),
    jsonb_build_object('codice', 'E_ATTIVO_PADRE_NON_ATTIVO', 'frase', pg_temp.frase('E_ATTIVO_PADRE_NON_ATTIVO'),
                       'bersaglio', NULL),
    '14) padre spento senza tipo: lo stesso rifiuto, nessun bersaglio');

SELECT is((SELECT assente FROM tmp_r),
    jsonb_build_object('codice', 'E_PADRE_INESISTENTE', 'frase', pg_temp.frase('E_PADRE_INESISTENTE'),
                       'bersaglio', NULL),
    '15) padre assente: E_PADRE_INESISTENTE, frase del catalogo, nessun bersaglio (punterebbe al vuoto)');

SELECT is((SELECT ritirato - 'bersaglio' FROM tmp_r),
    jsonb_build_object('codice', 'E_CATALOGO_OBSOLETO_NUOVA_ISTANZA', 'frase', pg_temp.frase('E_CATALOGO_OBSOLETO_NUOVA_ISTANZA')),
    '16) padre ritirato: E_CATALOGO_OBSOLETO_NUOVA_ISTANZA, con la frase del catalogo');

SELECT is((SELECT ritirato ->> 'bersaglio' FROM tmp_r), 'PGTAP_SBE1:3',
    '17) ... e il bersaglio del padre');

-- ============================================================
-- 18-19) Il BLOCK
-- ============================================================
INSERT INTO t_figlia (id, padre_id) VALUES (20, 1);
INSERT INTO t_figlia_nuda (id, padre_id) VALUES (20, 4);

SELECT is(pg_temp.rifiuto($$UPDATE t_padre SET attivo = false WHERE id = 1$$),
    jsonb_build_object('codice', 'E_ATTIVO_BLOCK_CHILDREN_ACTIVE', 'frase', pg_temp.frase('E_ATTIVO_BLOCK_CHILDREN_ACTIVE'),
                       'bersaglio', NULL),
    '18) BLOCK con figlie attive: E_ATTIVO_BLOCK_CHILDREN_ACTIVE, frase del catalogo, nessun bersaglio');

SELECT is(pg_temp.rifiuto($$UPDATE t_padre SET attivo = false WHERE id = 4$$),
    jsonb_build_object('codice', 'E_ATTIVO_BLOCK_CHILDREN_EXIST', 'frase', pg_temp.frase('E_ATTIVO_BLOCK_CHILDREN_EXIST'),
                       'bersaglio', NULL),
    '19) BLOCK con figlie senza attivo: E_ATTIVO_BLOCK_CHILDREN_EXIST, frase del catalogo');

-- ============================================================
-- 20-21) Le due check di disattivazione
-- ============================================================
SELECT unalike(pg_get_functiondef('script.fn_check_registro_disattivabile(bigint)'::regprocedure),
    '%''valori''%',
    '20) i motivi di script.fn_check_registro_disattivabile non portano i valori della frase');

SELECT unalike(pg_get_functiondef('script.fn_check_famiglia_documento_disattivabile(integer)'::regprocedure),
    '%''valori''%',
    '21) ... ne'' quelli di script.fn_check_famiglia_documento_disattivabile');

SELECT * FROM finish();
ROLLBACK;
