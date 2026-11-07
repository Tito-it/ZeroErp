-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: le testate di vendita (ordine, bolla, reso, contratto) si cancellano
--   SOLO da bozza vuota: in bozza e senza righe attive. Il guard
--   vendite.trgfn_doc_guard_delete_solo_bozza, montato BEFORE DELETE.
-- ChangeSet: 20261106-88, -89, -90, -91 (giro T.4); codici E_DELETE_DOC_CON_RIGHE,
--   E_DELETE_CONTRATTO_CON_SUCCESSIVI.
-- Brief: brief-db-sorgente-documento-e-riga §7.2 lotto T, giro T.4 (V-4)
-- ------------------------------------------------------------
-- Indice test (plan 19):
--   LA FORMA
--    1) il guard e' montato BEFORE DELETE FOR EACH ROW sulle quattro testate
--       e sulla bozza email, e su nessun'altra tabella
--    2) e' SECURITY DEFINER, con pg_catalog primo nel search_path
--    3) E_DELETE_DOC_CON_RIGHE e' a catalogo, vivo, CONFLITTO_STATO, con la
--       frase a un segnaposto
--   ORDINE
--    4) in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE
--    5) ...e l'ordine e la riga ci sono ancora
--    6) tolta la riga, la bozza vuota si cancella
--    7) confermato: E_DELETE_DOC_NON_BOZZA (lo stato si dice prima delle righe)
--   BOLLA
--    8) in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE
--    9) con la sola riga disattivata e' vuota: si cancella, e la riga la segue
--   RESO (V-4)
--   10) confermato: E_DELETE_DOC_NON_BOZZA
--   11) ...e le righe ci sono ancora
--   12) in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE
--   13) tolta la riga, la bozza vuota si cancella
--   CONTRATTO (Tid, 2026-11-06)
--   14) in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE
--   15) in bozza vuota: si cancella
--   LA FRASE
--   16) il rifiuto nomina il documento, senza segnaposti grezzi
--   IL CONTRATTO PRECEDENTE (Tid, 2026-11-07)
--   17) fk_contratti_parent e' ON DELETE NO ACTION: i successori non si staccano
--   18) un contratto in bozza vuota che e' il precedente di un altro non si
--       cancella: E_DELETE_CONTRATTO_CON_SUCCESSIVI, e il successore lo conserva
--   19) l'indice della FK c'e', parziale (parent_contratto_id IS NOT NULL)
--
-- ⚠️ Il mondo si COSTRUISCE coi builder dbops.fn_pgtap_*: un file che scegliesse
--   i documenti fra quelli esistenti passerebbe a vuoto in CI.
-- ⚠️ Lo stato fuori bozza del contratto non ha un caso qui: la meta' «bozza»
--   della regola e' la stessa funzione, provata su ordine (7) e reso (10), e il
--   montaggio sul contratto e' il test 1.
-- ⚠️ Che il guard veda anche le righe che la RLS nasconderebbe (2) non si
--   costruisce: la policy delle righe risolve l'emittente dalla testata, quindi
--   una riga invisibile di una testata visibile non esiste. Il 2 presidia la
--   postura che rende la regola indipendente da quella policy.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(19);

-- L'esito di un'istruzione: PASSA, il codice d'errore applicativo (dal
-- CONSTRAINT dell'errore di fn_log_and_raise_error), o SQLSTATE + vincolo.
CREATE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_s text; v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN 'PASSA';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    RETURN CASE WHEN v_s = 'P0001' AND coalesce(v_c, '') <> '' THEN v_c
                ELSE v_s || coalesce(' ' || nullif(v_c, ''), '') END;
END
$f$;

CREATE FUNCTION pg_temp.messaggio(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
BEGIN
    EXECUTE p_sql;
    RETURN 'PASSA';
EXCEPTION WHEN OTHERS THEN
    RETURN SQLERRM;
END
$f$;

-- ============================================================
-- LA FORMA
-- ============================================================
-- tgtype: 1 = ROW, 2 = BEFORE, 8 = DELETE; nessun INSERT (4) ne' UPDATE (16).
-- ⚠️ Schema e nome dal catalogo, non da regclass::text: quello omette lo schema
--   quando sta nel search_path di chi lancia (come app, config.email_outbox
--   uscirebbe senza schema).
SELECT is(
    ARRAY(SELECT format('%I.%I', n.nspname, c.relname)
            FROM pg_trigger tg
            JOIN pg_class c     ON c.oid = tg.tgrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE tg.tgfoid = 'vendite.trgfn_doc_guard_delete_solo_bozza()'::regprocedure
             AND NOT tg.tgisinternal
             AND (tg.tgtype & 1) = 1 AND (tg.tgtype & 2) = 2 AND (tg.tgtype & 8) = 8
             AND (tg.tgtype & (4 | 16)) = 0
           ORDER BY 1),
    ARRAY['config.email_outbox', 'vendite.contratti', 'vendite.ddt', 'vendite.ordini', 'vendite.resi'],
    '1) il guard e'' montato BEFORE DELETE FOR EACH ROW su ordini, bolle, resi, contratti e bozza email, e basta');

SELECT ok(
    (SELECT p.prosecdef AND p.proconfig[1] LIKE 'search_path=pg_catalog%'
       FROM pg_proc p WHERE p.oid = 'vendite.trgfn_doc_guard_delete_solo_bozza()'::regprocedure),
    '2) il guard e'' SECURITY DEFINER, con pg_catalog primo nel search_path');

SELECT ok(
    (SELECT c.classe = 'CONFLITTO_STATO' AND c.obsoleto_dal IS NULL
            AND (SELECT count(*) FROM regexp_matches(m.messaggio, '%s', 'g')) = 1
       FROM config.codici_errore c
       JOIN config.messaggi_errore m ON m.codice = c.codice AND m.lingua = 'it'
      WHERE c.codice = 'E_DELETE_DOC_CON_RIGHE'),
    '3) E_DELETE_DOC_CON_RIGHE e'' a catalogo, vivo, CONFLITTO_STATO, con la frase a un segnaposto');

-- ============================================================
-- Il mondo
-- ============================================================
CREATE TEMP TABLE _o AS
SELECT ordine_id, ordine_riga_id FROM dbops.fn_pgtap_crea_ordine_con_righe('PGT-T4-OB', 'DRAFT');
CREATE TEMP TABLE _oc AS
SELECT ordine_id FROM dbops.fn_pgtap_crea_ordine_con_righe('PGT-T4-OC', 'CONFERMATO');
CREATE TEMP TABLE _d AS
SELECT ddt_id, ddt_riga_id FROM dbops.fn_pgtap_crea_ddt_senza_ordine('PGT-T4-DB', 'DRAFT');
CREATE TEMP TABLE _rc AS
SELECT reso_id FROM dbops.fn_pgtap_crea_reso('PGT-T4-RC');
CREATE TEMP TABLE _rb AS
SELECT reso_id, resi_riga_id FROM dbops.fn_pgtap_crea_reso('PGT-T4-RB', p_stato_codice_interno => 'DRAFT');
CREATE TEMP TABLE _c AS
SELECT contratto_id FROM dbops.fn_pgtap_crea_contratto('PGT-T4-CB', 'DRAFT');
CREATE TEMP TABLE _cv AS
SELECT contratto_id FROM dbops.fn_pgtap_crea_contratto('PGT-T4-CV', 'DRAFT');
-- Il contratto precedente (in bozza vuota) e il suo successore, che lo dichiara.
CREATE TEMP TABLE _cp AS
SELECT contratto_id FROM dbops.fn_pgtap_crea_contratto('PGT-T4-CP', 'DRAFT');
CREATE TEMP TABLE _cs AS
SELECT contratto_id FROM dbops.fn_pgtap_crea_contratto('PGT-T4-CS', 'DRAFT');
UPDATE vendite.contratti SET parent_contratto_id = (SELECT contratto_id FROM _cp)
 WHERE id = (SELECT contratto_id FROM _cs);

-- La riga del contratto in bozza: un'aggiunta a prezzo dichiarato, come
-- vendite/test-trgfn-doc-righe-lock-fuori-bozza-v1.
INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa, tipo_erogazione)
SELECT (SELECT contratto_id FROM _c), dbops.fn_pgtap_crea_articolo('PGT-T4-ART'), 'AGGIUNTA', 99.00, 1.00, 'UNA_TANTUM';

-- ============================================================
-- ORDINE
-- ============================================================
SELECT is(pg_temp.esito(format('DELETE FROM vendite.ordini WHERE id = %s', (SELECT ordine_id FROM _o))),
    'E_DELETE_DOC_CON_RIGHE',
    '4) ordine in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE');

SELECT ok(
    EXISTS (SELECT 1 FROM vendite.ordini WHERE id = (SELECT ordine_id FROM _o))
    AND EXISTS (SELECT 1 FROM vendite.ordini_righe WHERE id = (SELECT ordine_riga_id FROM _o)),
    '5) ...e l''ordine e la riga ci sono ancora');

DELETE FROM vendite.ordini_righe WHERE id = (SELECT ordine_riga_id FROM _o);

SELECT is(pg_temp.esito(format('DELETE FROM vendite.ordini WHERE id = %s', (SELECT ordine_id FROM _o))),
    'PASSA',
    '6) tolta la riga, la bozza vuota si cancella');

SELECT is(pg_temp.esito(format('DELETE FROM vendite.ordini WHERE id = %s', (SELECT ordine_id FROM _oc))),
    'E_DELETE_DOC_NON_BOZZA',
    '7) ordine confermato: E_DELETE_DOC_NON_BOZZA, prima delle righe');

-- ============================================================
-- BOLLA
-- ============================================================
SELECT is(pg_temp.esito(format('DELETE FROM vendite.ddt WHERE id = %s', (SELECT ddt_id FROM _d))),
    'E_DELETE_DOC_CON_RIGHE',
    '8) bolla in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE');

UPDATE vendite.ddt_righe SET attivo = false WHERE id = (SELECT ddt_riga_id FROM _d);

-- ⚠️ L'esito e il conteggio in due istruzioni: una SELECT sola leggerebbe le
--   righe con lo snapshot preso prima del DELETE che la funzione esegue.
CREATE TEMP TABLE _d_esito AS
SELECT pg_temp.esito(format('DELETE FROM vendite.ddt WHERE id = %s', (SELECT ddt_id FROM _d))) AS esito;

SELECT is(
    (SELECT esito FROM _d_esito)
      || '|' || (SELECT count(*) FROM vendite.ddt_righe WHERE id = (SELECT ddt_riga_id FROM _d))::text,
    'PASSA|0',
    '9) con la sola riga disattivata la bolla e'' vuota: si cancella, e la riga la segue');

-- ============================================================
-- RESO (V-4)
-- ============================================================
SELECT is(pg_temp.esito(format('DELETE FROM vendite.resi WHERE id = %s', (SELECT reso_id FROM _rc))),
    'E_DELETE_DOC_NON_BOZZA',
    '10) reso confermato: E_DELETE_DOC_NON_BOZZA');

SELECT ok(EXISTS (SELECT 1 FROM vendite.resi_righe WHERE reso_id = (SELECT reso_id FROM _rc) AND attivo),
    '11) ...e le sue righe ci sono ancora');

SELECT is(pg_temp.esito(format('DELETE FROM vendite.resi WHERE id = %s', (SELECT reso_id FROM _rb))),
    'E_DELETE_DOC_CON_RIGHE',
    '12) reso in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE');

DELETE FROM vendite.resi_righe WHERE id = (SELECT resi_riga_id FROM _rb);

SELECT is(pg_temp.esito(format('DELETE FROM vendite.resi WHERE id = %s', (SELECT reso_id FROM _rb))),
    'PASSA',
    '13) tolta la riga, il reso in bozza vuoto si cancella');

-- ============================================================
-- CONTRATTO
-- ============================================================
SELECT is(pg_temp.esito(format('DELETE FROM vendite.contratti WHERE id = %s', (SELECT contratto_id FROM _c))),
    'E_DELETE_DOC_CON_RIGHE',
    '14) contratto in bozza con una riga attiva: E_DELETE_DOC_CON_RIGHE');

SELECT is(pg_temp.esito(format('DELETE FROM vendite.contratti WHERE id = %s', (SELECT contratto_id FROM _cv))),
    'PASSA',
    '15) contratto in bozza vuoto: si cancella');

-- ============================================================
-- LA FRASE
-- ============================================================
SELECT ok(
    (SELECT m LIKE 'Contratto %ha ancora delle righe: si può eliminare solo una bozza vuota.%'
            AND m NOT LIKE '%\%s%'
       FROM pg_temp.messaggio(format('DELETE FROM vendite.contratti WHERE id = %s', (SELECT contratto_id FROM _c))) AS m),
    '16) il rifiuto nomina il documento, senza segnaposti grezzi');

-- ============================================================
-- IL CONTRATTO PRECEDENTE
-- ============================================================
SELECT is(
    (SELECT c.confdeltype::text FROM pg_constraint c
      WHERE c.conname = 'fk_contratti_parent' AND c.conrelid = 'vendite.contratti'::regclass),
    'a',
    '17) fk_contratti_parent e'' ON DELETE NO ACTION: i successori non si staccano in silenzio');

SELECT is(
    pg_temp.esito(format('DELETE FROM vendite.contratti WHERE id = %s', (SELECT contratto_id FROM _cp)))
      || '|' || (SELECT (c.parent_contratto_id = (SELECT contratto_id FROM _cp))::text
                   FROM vendite.contratti c WHERE c.id = (SELECT contratto_id FROM _cs)),
    'E_DELETE_CONTRATTO_CON_SUCCESSIVI|true',
    '18) il precedente in bozza vuota di un altro contratto non si cancella, e il successore lo conserva');

SELECT ok(
    EXISTS (SELECT 1 FROM pg_index i
             WHERE i.indrelid = 'vendite.contratti'::regclass
               AND i.indexrelid = to_regclass('vendite.ix_contratti_parent_contratto_id')
               AND pg_get_expr(i.indpred, i.indrelid) = '(parent_contratto_id IS NOT NULL)'),
    '19) l''indice della FK c''e'', parziale: guard e controllo referenziale cercano i successori a ogni DELETE');

SELECT * FROM finish();
ROLLBACK;
