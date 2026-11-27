-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- rev 2026-11-27 (brief-db-motivo-override-obbligatorio §6.3): il motivo di un override e' obbligatorio (20261126-80): i casi 3, 6 e 9 lo scrivono. Il 9 senza motivo darebbe E_OVERRIDE_MOTIVO_OBBLIGATORIO prima della FK, e non proverebbe piu' il catalogo. La regola la collauda config/test-override-motivo-obbligatorio-v1.
-- rev 2026-11-27 (brief-db-porte-aperte-dalla-sola-guc §15, giro 10-quater): fn_imposta_override_oggetti diventa il verbo DEFINER del SUPER_ADMIN (20261126-51): gli override si scrivono da un SUPER_ADMIN di fixture (dbops.fn_pgtap_entra_come_super_admin), e il caso 1 dice DEFINER. Il permesso lo collauda config/test-porta-override-permessi-v1.
--
-- Gli override di un utente e il suo emittente attivo:
--   config.fn_imposta_override_oggetti   (20261018-46)
--   config.fn_imposta_emittente_attivo   (20261018-47)
--   Brief: brief-db-processi-accensione-per-ambiente (§5-ter.2, 2b-1 lotto 9).
--
-- ⭐ Il caso si COSTRUISCE: un operatore umano dal builder, due oggetti non
--   riservati e uno riservato dal catalogo config.area_model_overrides, due
--   emittenti dal builder.
--
-- Elenco test (plan 13):
--   forma
--    1) fn_imposta_override_oggetti e' SECURITY DEFINER (il verbo del SUPER_ADMIN)
--    2) fn_imposta_emittente_attivo e' INVOKER
--   gli override
--    3) due oggetti: due override
--    4) un elenco di uno: sostituisce, ne resta uno
--    5) elenco vuoto: nessun override
--    6) valido_dal assente: la data operativa; a null: NULL
--    7) chiave estranea in un elemento: E_CAMPO_NON_AMMESSO
--    8) un elemento che non e' un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA
--    9) un oggetto riservato: lo rifiuta la FK del catalogo (23503)
--   l'emittente attivo
--   10) la preferenza nasce
--   11) cambia emittente: la stessa riga, l'emittente nuovo
--   12) lo stesso valore tocca la riga (la storia registra la conferma)
--   13) argomento NULL: E_SCRIPT_CHIAMATA_NON_VALIDA
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(13);


CREATE OR REPLACE FUNCTION pg_temp.sqlstate_di(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    RETURN SQLSTATE;
END $$;

CREATE TEMP TABLE t_u AS
SELECT (SELECT o.auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('Override pgTAP', false) o) AS au,
       (SELECT e.emittente_fiscale_id FROM dbops.fn_pgtap_crea_emittente('PGOEA') e)  AS ef1,
       (SELECT e.emittente_fiscale_id FROM dbops.fn_pgtap_crea_emittente('PGOEB') e)  AS ef2;

CREATE TEMP TABLE t_o AS
SELECT (SELECT jsonb_agg(jsonb_build_object('app_label', x.app_label, 'model_name', x.model_name))
          FROM (SELECT a.app_label, a.model_name FROM config.area_model_overrides a
                 WHERE NOT a.riservato ORDER BY a.app_label, a.model_name LIMIT 2) x) AS due,
       (SELECT jsonb_build_object('app_label', a.app_label, 'model_name', a.model_name)
          FROM config.area_model_overrides a WHERE a.riservato ORDER BY a.app_label, a.model_name LIMIT 1) AS riservato;

-- Gli override li scrive il verbo del SUPER_ADMIN: si entra come SUPER_ADMIN di
-- fixture fino ai casi dell'emittente attivo.
CREATE TEMP TABLE t_sa AS SELECT dbops.fn_pgtap_entra_come_super_admin('override-oggetti') AS prima;

-- ============================================================
-- Forma
-- ============================================================
SELECT is((SELECT p.prosecdef FROM pg_proc p
            WHERE p.oid = 'config.fn_imposta_override_oggetti(integer, jsonb)'::regprocedure),
          true, '1. fn_imposta_override_oggetti e'' SECURITY DEFINER (il verbo del SUPER_ADMIN)');

SELECT is((SELECT p.prosecdef FROM pg_proc p
            WHERE p.oid = 'config.fn_imposta_emittente_attivo(integer, bigint)'::regprocedure),
          false, '2. fn_imposta_emittente_attivo e'' INVOKER');

-- ============================================================
-- Gli override
-- ============================================================
-- ⚠️ Ogni scrittura in un'istruzione sua: la lettura nella stessa non la vedrebbe.
CREATE OR REPLACE FUNCTION pg_temp.n_override() RETURNS int LANGUAGE sql AS $$
    SELECT count(*)::int FROM config.user_override_oggetti uoo, t_u u WHERE uoo.auth_user_id = u.au
$$;

CREATE TEMP TABLE t_n1 AS
SELECT config.fn_imposta_override_oggetti(
           u.au, (SELECT jsonb_agg(e || jsonb_build_object('livello', 'BLOCCATO', 'motivo', 'pgTAP')) FROM jsonb_array_elements(o.due) e)) AS n
  FROM t_u u, t_o o;

SELECT is(format('%s|%s', (SELECT n FROM t_n1), pg_temp.n_override()), '2|2',
          '3. due oggetti: due override (ritorna 2, la tabella ne ha 2)');

CREATE TEMP TABLE t_n2 AS
SELECT config.fn_imposta_override_oggetti(
           u.au, jsonb_build_array((o.due -> 0) || '{"livello": "LETTURA", "motivo": "pgTAP"}'::jsonb)) AS n
  FROM t_u u, t_o o;

SELECT is(format('%s|%s', (SELECT n FROM t_n2), pg_temp.n_override()), '1|1',
          '4. un elenco di uno: sostituisce, ne resta uno');

CREATE TEMP TABLE t_n3 AS
SELECT config.fn_imposta_override_oggetti(u.au, '[]'::jsonb) AS n FROM t_u u;

SELECT is(format('%s|%s', (SELECT n FROM t_n3), pg_temp.n_override()), '0|0',
          '5. elenco vuoto: nessun override');

DO $ov$
BEGIN
    PERFORM config.fn_imposta_override_oggetti(
                u.au,
                jsonb_build_array((o.due -> 0) || '{"livello": "LETTURA", "motivo": "pgTAP"}'::jsonb,
                                  (o.due -> 1) || '{"livello": "LETTURA", "motivo": "pgTAP", "valido_dal": null}'::jsonb))
       FROM t_u u, t_o o;
END
$ov$;

SELECT is(
    (SELECT string_agg(format('%s', COALESCE((uoo.valido_dal = script.fn_data_operativa())::text, 'null')), ','
                       ORDER BY uoo.app_label, uoo.model_name)
       FROM config.user_override_oggetti uoo, t_u u WHERE uoo.auth_user_id = u.au),
    'true,null',
    '6. valido_dal assente: la data operativa; a null: NULL');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT config.fn_imposta_override_oggetti((SELECT au FROM t_u),
        jsonb_build_array((SELECT due -> 0 FROM t_o) || '{"livello": "LETTURA", "auth_user_id": 1}'::jsonb))$$),
    'E_CAMPO_NON_AMMESSO',
    '7. chiave estranea in un elemento: E_CAMPO_NON_AMMESSO');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT config.fn_imposta_override_oggetti((SELECT au FROM t_u), '[1]'::jsonb)$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '8. un elemento che non e'' un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT is(
    pg_temp.sqlstate_di($$SELECT config.fn_imposta_override_oggetti((SELECT au FROM t_u),
        jsonb_build_array((SELECT riservato FROM t_o) || '{"livello": "LETTURA", "motivo": "pgTAP"}'::jsonb))$$),
    '23503',
    '9. un oggetto riservato: lo rifiuta la FK del catalogo (23503)');

-- Il contesto di prima, per i casi dell'emittente attivo.
SELECT dbops.fn_pgtap_rimetti_contesto((SELECT prima FROM t_sa));

-- ============================================================
-- L'emittente attivo
-- ============================================================
CREATE TEMP TABLE t_e AS
SELECT config.fn_imposta_emittente_attivo(u.au, u.ef1) AS r1 FROM t_u u;

SELECT is(
    (SELECT uea.emittente_fiscale_id FROM config.user_emittente_attivo uea, t_u u WHERE uea.auth_user_id = u.au),
    (SELECT ef1 FROM t_u),
    '10. la preferenza nasce');

CREATE TEMP TABLE t_e2 AS
SELECT config.fn_imposta_emittente_attivo(u.au, u.ef2) AS r2 FROM t_u u;

SELECT is(
    (SELECT format('%s|%s', e2.r2 = e.r1,
                   (SELECT uea.emittente_fiscale_id = u.ef2 FROM config.user_emittente_attivo uea WHERE uea.auth_user_id = u.au))
       FROM t_u u, t_e e, t_e2 e2),
    't|t',
    '11. cambia emittente: la stessa riga, l''emittente nuovo');

-- ⚠️ Nella stessa transazione xmin non cambia: la riga toccata si riconosce
--   dal ctid (un UPDATE scrive una versione nuova della riga).
CREATE TEMP TABLE t_x AS
SELECT uea.ctid::text AS prima FROM config.user_emittente_attivo uea, t_u u WHERE uea.auth_user_id = u.au;

DO $ea$ BEGIN PERFORM config.fn_imposta_emittente_attivo(u.au, u.ef2) FROM t_u u; END $ea$;

SELECT isnt(
    (SELECT uea.ctid::text FROM config.user_emittente_attivo uea, t_u u WHERE uea.auth_user_id = u.au),
    (SELECT prima FROM t_x),
    '12. lo stesso valore tocca la riga (la storia registra la conferma)');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT config.fn_imposta_emittente_attivo((SELECT au FROM t_u), NULL)$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '13. argomento NULL: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT * FROM finish();

ROLLBACK;
