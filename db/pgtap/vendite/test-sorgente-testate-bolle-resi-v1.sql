-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la PROVENIENZA di testata di bolle e resi nella grammatica del
--   modello: il tipo del documento + una sola chiave, quella del key_selector
--   (per ordine, reso e bolla: sorgente_id). La riconsegna dichiara il reso
--   (D-4); la corsia di fatturazione dell'ordine dietro di lei resta leggibile.
-- ChangeSet: 20261106-63 … -73 (giro T.2)
-- Brief: brief-db-sorgente-documento-e-riga §7.2 lotto T, giro T.2
-- ------------------------------------------------------------
-- Indice test (plan 19):
--   LA FORMA
--    1) bolla e reso hanno il CHECK di forma
--    2) il reso non ha piu' il NOT NULL su sorgente_uid (le due chiavi sono alternative)
--    3) il guard unico e' montato su bolla e reso: DOCUMENTO, BLOCCA
--    4) il lock fuori bozza di bolla e reso ferma anche sorgente_id
--   I VERBI
--    5) bolla dall'ordine: la testata cita ORDINE_VENDITA con l'id dell'ordine
--    6) reso (builder, come il BE): DDT_VENDITA con l'id della bolla
--    7) riconsegna: la testata cita RESO_VENDITA con l'id del reso (D-4)
--    8) ... e la corsia di fatturazione dietro di lei e' quella dell'ordine
--   LE VISTE DI LISTA
--    9) vw_ddt_lista, bolla dall'ordine: ordine d'origine e sorgente_id
--   10) vw_ddt_lista, riconsegna: nessun ordine d'origine, sorgente_id = il reso
--   11) vw_resi_lista: la bolla d'origine e sorgente_id
--   IL GUARD UNICO E LA FORMA (bolla e reso in bozza)
--   12) l'uid per un tipo a chiave id: E_SORG_CHIAVE_NON_CONFORME
--   13) un ordine che non c'e': E_SORG_NOT_FOUND
--   14) la chiave senza il tipo, sulla bolla: il CHECK di forma (23514)
--   15) il reso col tipo e senza chiave: E_SORG_CHIAVE_NON_CONFORME
--   IL LOCK FUORI BOZZA
--   16) sulla bolla consegnata la provenienza non cambia: E_DOC_SORGENTE_FUORI_BOZZA
--   LA CAPABILITY
--   17) bolla in bozza: sorgente_id fra le colonne non modificabili
--   18) reso in bozza: idem
--   PRESIDIO
--   19) nessuna bolla e nessun reso con l'uid per un tipo a chiave id
--
-- ⚠️ Il mondo si COSTRUISCE coi builder dbops.fn_pgtap_*, che passano dai verbi.
--   Gira come l'applicazione (operatore in sessione, RLS attiva).
-- ⚠️ Il 19 e' un presidio su cio' che c'e': i casi li provano 5-15. In CI le
--   tabelle sono vuote fuori da questo file.
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

-- ============================================================
-- LA FORMA
-- ============================================================
SELECT is(
  (SELECT string_agg(k.conname, ', ' ORDER BY k.conname) FROM pg_constraint k
    WHERE k.contype = 'c' AND k.conname IN ('chk_ddt_sorgente_forma', 'chk_resi_sorgente_forma')),
  'chk_ddt_sorgente_forma, chk_resi_sorgente_forma',
  '1) bolla e reso hanno il CHECK di forma della provenienza');

SELECT is(
  (SELECT is_nullable FROM information_schema.columns
    WHERE table_schema = 'vendite' AND table_name = 'resi' AND column_name = 'sorgente_uid'),
  'YES',
  '2) resi.sorgente_uid e'' nullable: sorgente_id e sorgente_uid sono alternative');

SELECT results_eq(
  $$SELECT tabella::text COLLATE "default", livello_minimo, azione_cancellazione
      FROM script.fn_sorgente_guard_montaggi()
     WHERE tabella IN ('vendite.ddt'::regclass, 'vendite.resi'::regclass)
     ORDER BY 1$$,
  $$VALUES ('vendite.ddt', 'DOCUMENTO', 'BLOCCA'),
           ('vendite.resi', 'DOCUMENTO', 'BLOCCA')$$,
  '3) il guard unico e'' montato su bolla e reso: livello DOCUMENTO, azione BLOCCA');

SELECT is(
  (SELECT count(*)::int FROM pg_trigger t
    WHERE t.tgname IN ('trg_ddt_a05_lock_fuori_bozza_upd', 'trg_resi_a05_lock_fuori_bozza_upd')
      AND encode(t.tgargs, 'escape') ~ '\\000sorgente_id\\000E_DOC_SORGENTE_FUORI_BOZZA\\000'),
  2,
  '4) il lock fuori bozza di bolla e reso ferma anche sorgente_id');

-- ============================================================
-- Fixture: ordine -> bolla consegnata -> reso -> riconsegna; una bolla e un
-- reso in bozza per i casi del guard.
-- ============================================================
CREATE TEMP TABLE _t AS
SELECT (SELECT id FROM config.sorgenti WHERE codice_interno = 'ORDINE_VENDITA') AS t_ord,
       (SELECT id FROM config.sorgenti WHERE codice_interno = 'DDT_VENDITA')    AS t_ddt,
       (SELECT id FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA')   AS t_reso;

CREATE TEMP TABLE _ddt AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('sorgente testate',
         p_quantita => 10, p_prezzo => 20, p_fatturazione_trigger => 'SPEDITO');

CREATE TEMP TABLE _reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('sorgente testate', (SELECT ddt_id FROM _ddt), 3, 'RESO_PER_RICONSEGNA');

CREATE TEMP TABLE _ric AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna((SELECT reso_id FROM _reso),
         p_resi_riga_id => (SELECT resi_riga_id FROM _reso), p_quantita => 3);

CREATE TEMP TABLE _bozza AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('sorgente testate bozza', 'DRAFT',
         p_quantita => 5, p_prezzo => 20);

CREATE TEMP TABLE _reso_bozza AS
SELECT * FROM dbops.fn_pgtap_crea_reso('sorgente testate', (SELECT ddt_id FROM _ddt), 1,
         'RESO_A_CREDITO', 'DRAFT');

-- ============================================================
-- I VERBI
-- ============================================================
SELECT is(
  (SELECT format('%s|%s|%s', d.sorgente_tipo_id = t.t_ord, d.sorgente_id = x.ordine_id, d.sorgente_uid IS NULL)
     FROM vendite.ddt d, _t t, _ddt x WHERE d.id = x.ddt_id),
  't|t|t',
  '5) bolla dall''ordine: la testata cita ORDINE_VENDITA con l''id dell''ordine, senza uid');

SELECT is(
  (SELECT format('%s|%s|%s', r.sorgente_tipo_id = t.t_ddt, r.sorgente_id = x.ddt_id, r.sorgente_uid IS NULL)
     FROM vendite.resi r, _t t, _reso x WHERE r.id = x.reso_id),
  't|t|t',
  '6) reso: la testata cita DDT_VENDITA con l''id della bolla, senza uid');

SELECT is(
  (SELECT format('%s|%s|%s', d.sorgente_tipo_id = t.t_reso, d.sorgente_id = s.reso_id, d.sorgente_uid IS NULL)
     FROM vendite.ddt d, _t t, _reso s, _ric c WHERE d.id = c.ddt_id),
  't|t|t',
  '7) riconsegna: la testata cita RESO_VENDITA con l''id del reso, non l''ordine (D-4)');

SELECT is(
  (SELECT vendite.fn_ddt_trigger_ordine_testata(d.sorgente_tipo_id, d.sorgente_uid, d.sorgente_id)
     FROM vendite.ddt d, _ric c WHERE d.id = c.ddt_id),
  'SPEDITO',
  '8) ... e la corsia di fatturazione dietro la riconsegna e'' quella dell''ordine (SPEDITO)');

-- ============================================================
-- LE VISTE DI LISTA
-- ============================================================
SELECT is(
  (SELECT format('%s|%s', v.ordine_origine_id = x.ordine_id, v.sorgente_id = x.ordine_id)
     FROM vendite.vw_ddt_lista v, _ddt x WHERE v.id = x.ddt_id),
  't|t',
  '9) vw_ddt_lista, bolla dall''ordine: l''ordine d''origine e sorgente_id');

SELECT is(
  (SELECT format('%s|%s', v.ordine_origine_id IS NULL, v.sorgente_id = s.reso_id)
     FROM vendite.vw_ddt_lista v, _ric c, _reso s WHERE v.id = c.ddt_id),
  't|t',
  '10) vw_ddt_lista, riconsegna: nessun ordine d''origine, sorgente_id = il reso');

SELECT is(
  (SELECT format('%s|%s', v.ddt_origine_id = x.ddt_id, v.sorgente_id = x.ddt_id)
     FROM vendite.vw_resi_lista v, _reso x WHERE v.id = x.reso_id),
  't|t',
  '11) vw_resi_lista: la bolla d''origine e sorgente_id');

-- ============================================================
-- IL GUARD UNICO E LA FORMA, su bolla e reso in bozza
-- ============================================================
SELECT is(
  pg_temp.esito(format('UPDATE vendite.ddt SET sorgente_id = NULL, sorgente_uid = %L WHERE id = %s',
                       (SELECT ordine_uid FROM _bozza), (SELECT ddt_id FROM _bozza))),
  'E_SORG_CHIAVE_NON_CONFORME',
  '12) l''uid dell''ordine per un tipo a chiave id: E_SORG_CHIAVE_NON_CONFORME');

SELECT is(
  pg_temp.esito(format('UPDATE vendite.ddt SET sorgente_id = -1 WHERE id = %s', (SELECT ddt_id FROM _bozza))),
  'E_SORG_NOT_FOUND',
  '13) un ordine che non c''e'': E_SORG_NOT_FOUND');

SELECT is(
  pg_temp.esito(format('UPDATE vendite.ddt SET sorgente_tipo_id = NULL WHERE id = %s', (SELECT ddt_id FROM _bozza))),
  '23514 chk_ddt_sorgente_forma',
  '14) la chiave senza il tipo, sulla bolla: il CHECK di forma');

SELECT is(
  pg_temp.esito(format('UPDATE vendite.resi SET sorgente_id = NULL WHERE id = %s', (SELECT reso_id FROM _reso_bozza))),
  'E_SORG_CHIAVE_NON_CONFORME',
  '15) il reso col tipo e senza chiave: E_SORG_CHIAVE_NON_CONFORME (un reso ha sempre una provenienza)');

-- ============================================================
-- IL LOCK FUORI BOZZA
-- ============================================================
SELECT is(
  pg_temp.esito(format('UPDATE vendite.ddt SET sorgente_id = %s WHERE id = %s',
                       (SELECT ordine_id FROM _bozza), (SELECT ddt_id FROM _ddt))),
  'E_DOC_SORGENTE_FUORI_BOZZA',
  '16) sulla bolla consegnata la provenienza non cambia: E_DOC_SORGENTE_FUORI_BOZZA');

-- ============================================================
-- LA CAPABILITY
-- ============================================================
SELECT ok(
  (SELECT script.fn_available_actions_ddt(ddt_id) -> 'non_editable_fields' ? 'sorgente_id' FROM _bozza),
  '17) bolla in bozza: sorgente_id fra le colonne non modificabili');

SELECT ok(
  (SELECT script.fn_available_actions_reso(reso_id) -> 'non_editable_fields' ? 'sorgente_id' FROM _reso_bozza),
  '18) reso in bozza: sorgente_id fra le colonne non modificabili');

-- ============================================================
-- PRESIDIO (su cio' che c'e')
-- ============================================================
SELECT is_empty(
  $$SELECT 'ddt ' || d.id FROM vendite.ddt d JOIN config.sorgenti s ON s.id = d.sorgente_tipo_id
     WHERE s.key_selector = 'id' AND d.sorgente_uid IS NOT NULL
    UNION ALL
    SELECT 'reso ' || r.id FROM vendite.resi r JOIN config.sorgenti s ON s.id = r.sorgente_tipo_id
     WHERE s.key_selector = 'id' AND r.sorgente_uid IS NOT NULL$$,
  '19) nessuna bolla e nessun reso con l''uid per un tipo a chiave id');

SELECT * FROM finish();
ROLLBACK;
