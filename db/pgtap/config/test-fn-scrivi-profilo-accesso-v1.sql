-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il profilo di accesso e il suo legame a un'identita':
--   config.fn_scrivi_profilo_accesso                (20261018-42)
--   config.fn_lega_profilo_identita                 (20261018-43)
--   script.fn_crea_utente_tecnico, passo 6          (20261018-44)
--   anagrafiche.fn_crea_risorsa_umana_v2, binding SA (20261018-45)
--   Brief: brief-db-processi-accensione-per-ambiente (§5-ter.2, 2b-1 lotto 8).
--
-- ⭐ Il caso si COSTRUISCE: un profilo AD_HOC col codice del test, le prime
--   due aree e la prima azione dai cataloghi, due operatori umani dal builder
--   (uno super admin: il suo binding passa dalla madre riscritta).
--
-- Elenco test (plan 17):
--   forma
--    1) fn_scrivi_profilo_accesso e' INVOKER
--    2) fn_lega_profilo_identita e' INVOKER
--   il profilo
--    3) nasce AD_HOC, attivo, senza secondo fattore, con due aree e un'azione
--    4) riscritto: descrizione nuova, aree sostituite, azioni NULL invariate
--    5) aree [] = nessuna area
--    6) un campo assente in riscrittura resta com'era (secondo fattore)
--    7) un codice di un altro tipo: E_SCRIPT_CHIAMATA_NON_VALIDA
--    8) chiave estranea fra i campi: E_CAMPO_NON_AMMESSO
--   il binding
--    9) un'identita' senza profilo: legata
--   10) lo stesso profilo di nuovo: lo stesso binding (idempotente)
--   11) un altro profilo: uq_profili_accesso_bindings_identita
--   12) argomento NULL: E_SCRIPT_CHIAMATA_NON_VALIDA
--   le copie ritirate
--   13) l'operatore super admin ha il binding SUPER_ADMIN (madre riscritta)
--   14) nessuna delle due madri scrive piu' profili_accesso_bindings a mano
--   15) ... e tutte e due chiamano il BB
--   Il codice in minuscolo (20261104-35, richiesta BE brief-be-codice-maiuscolo §6)
--   16) ⭐ due chiamate col codice in minuscolo danno lo STESSO profilo: prima
--       la seconda urtava uq_profili_accesso_codice
--   17) il codice si salva normalizzato
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(17);


CREATE OR REPLACE FUNCTION pg_temp.corpo(p regprocedure) RETURNS text
LANGUAGE sql AS $$
    SELECT regexp_replace(p2.prosrc, '--[^\n]*', '', 'g') FROM pg_proc p2 WHERE p2.oid = p
$$;

CREATE TEMP TABLE t_c AS
SELECT (SELECT a.id FROM config.aree_funzionali a ORDER BY a.id LIMIT 1)          AS area1,
       (SELECT a.id FROM config.aree_funzionali a ORDER BY a.id OFFSET 1 LIMIT 1) AS area2,
       (SELECT z.id FROM config.azioni_processo z ORDER BY z.id LIMIT 1)          AS azione1;

CREATE TEMP TABLE t_p AS
SELECT config.fn_scrivi_profilo_accesso(
           'AD_HOC', 'PGTAP_PROFILO_ADHOC', 'Profilo pgTAP',
           jsonb_build_array(jsonb_build_object('area_id', c.area1, 'livello', 'LETTURA'),
                             jsonb_build_object('area_id', c.area2, 'livello', 'TUTTO')),
           jsonb_build_array(jsonb_build_object('azione_id', c.azione1, 'abilitata', true))) AS p1,
       config.fn_scrivi_profilo_accesso('AD_HOC', 'PGTAP_PROFILO_ADHOC_2', 'Profilo pgTAP 2', '[]'::jsonb) AS p2
  FROM t_c c;

CREATE TEMP TABLE t_op AS
SELECT (SELECT o.identita_id FROM dbops.fn_pgtap_crea_operatore_umano('Profilo pgTAP 1', false) o) AS id_op,
       (SELECT o.identita_id FROM dbops.fn_pgtap_crea_operatore_umano('Profilo pgTAP SA', true) o)  AS id_sa;

-- ============================================================
-- Forma
-- ============================================================
SELECT is((SELECT p.prosecdef FROM pg_proc p
            WHERE p.oid = 'config.fn_scrivi_profilo_accesso(config.tipo_profilo_accesso, character varying, text, jsonb, jsonb, jsonb)'::regprocedure),
          false, '1. fn_scrivi_profilo_accesso e'' INVOKER');

SELECT is((SELECT p.prosecdef FROM pg_proc p
            WHERE p.oid = 'config.fn_lega_profilo_identita(integer, bigint)'::regprocedure),
          false, '2. fn_lega_profilo_identita e'' INVOKER');

-- ============================================================
-- Il profilo
-- ============================================================
SELECT is(
    (SELECT format('%s|%s|%s|%s|%s', pa.tipo, pa.attivo, pa.richiede_secondo_fattore,
                   (SELECT count(*) FROM config.profili_accesso_aree a WHERE a.profilo_accesso_id = pa.id),
                   (SELECT count(*) FROM config.profili_accesso_azioni z WHERE z.profilo_accesso_id = pa.id))
       FROM t_p p JOIN config.profili_accesso pa ON pa.id = p.p1),
    'AD_HOC|t|f|2|1',
    '3. nasce AD_HOC, attivo, senza secondo fattore, con due aree e un''azione');

-- ⚠️ La scrittura in un'istruzione sua: la lettura nella stessa non la vedrebbe.
CREATE TEMP TABLE t_r AS
SELECT config.fn_scrivi_profilo_accesso('AD_HOC', 'PGTAP_PROFILO_ADHOC', 'Profilo pgTAP riscritto',
           jsonb_build_array(jsonb_build_object('area_id', c.area1, 'livello', 'BLOCCATO')),
           NULL, '{"richiede_secondo_fattore": true}'::jsonb) AS r
  FROM t_c c;

SELECT is(
    (SELECT format('%s|%s|%s|%s', x.r = p.p1, pa.descrizione,
                   (SELECT string_agg(a.livello::text, ',') FROM config.profili_accesso_aree a WHERE a.profilo_accesso_id = pa.id),
                   (SELECT count(*) FROM config.profili_accesso_azioni z WHERE z.profilo_accesso_id = pa.id))
       FROM t_r x JOIN config.profili_accesso pa ON pa.id = x.r, t_p p),
    't|Profilo pgTAP riscritto|BLOCCATO|1',
    '4. riscritto: descrizione nuova, aree sostituite, azioni NULL invariate');

SELECT is((SELECT count(*)::int FROM t_p p JOIN config.profili_accesso_aree a ON a.profilo_accesso_id = p.p2),
          0, '5. aree [] = nessuna area');

CREATE TEMP TABLE t_r2 AS
SELECT config.fn_scrivi_profilo_accesso('AD_HOC', 'PGTAP_PROFILO_ADHOC', 'Profilo pgTAP') AS r;

SELECT is(
    (SELECT pa.richiede_secondo_fattore FROM t_r2 x JOIN config.profili_accesso pa ON pa.id = x.r),
    true,
    '6. un campo assente in riscrittura resta com''era (secondo fattore)');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT config.fn_scrivi_profilo_accesso('REPARTO', 'PGTAP_PROFILO_ADHOC', 'x')$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '7. un codice di un altro tipo: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT config.fn_scrivi_profilo_accesso('AD_HOC', 'PGTAP_PROFILO_X', 'x',
        NULL, NULL, '{"tipo": "REPARTO"}'::jsonb)$$),
    'E_CAMPO_NON_AMMESSO',
    '8. chiave estranea fra i campi: E_CAMPO_NON_AMMESSO');

-- ============================================================
-- Il binding
-- ============================================================
CREATE TEMP TABLE t_b AS
SELECT config.fn_lega_profilo_identita(p.p1, o.id_op) AS b1 FROM t_p p, t_op o;

SELECT is(
    (SELECT pab.profilo_accesso_id FROM t_b b JOIN config.profili_accesso_bindings pab ON pab.id = b.b1),
    (SELECT p1 FROM t_p),
    '9. un''identita'' senza profilo: legata');

SELECT is((SELECT config.fn_lega_profilo_identita(p.p1, o.id_op) FROM t_p p, t_op o),
          (SELECT b1 FROM t_b),
          '10. lo stesso profilo di nuovo: lo stesso binding (idempotente)');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT config.fn_lega_profilo_identita((SELECT p2 FROM t_p), (SELECT id_op FROM t_op))$$),
    'uq_profili_accesso_bindings_identita',
    '11. un altro profilo: uq_profili_accesso_bindings_identita');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT config.fn_lega_profilo_identita(NULL, (SELECT id_op FROM t_op))$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '12. argomento NULL: E_SCRIPT_CHIAMATA_NON_VALIDA');

-- ============================================================
-- Le copie ritirate
-- ============================================================
SELECT is(
    (SELECT pa.tipo::text
       FROM t_op o
       JOIN config.profili_accesso_bindings pab ON pab.identita_digitale_id = o.id_sa
       JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id),
    'SUPER_ADMIN',
    '13. l''operatore super admin ha il binding SUPER_ADMIN (madre riscritta)');

CREATE TEMP TABLE t_madri AS
SELECT p.oid::regprocedure AS f
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE (n.nspname, p.proname) IN (('script', 'fn_crea_utente_tecnico'), ('anagrafiche', 'fn_crea_risorsa_umana_v2'));

SELECT is(
    (SELECT count(*)::int FROM t_madri WHERE pg_temp.corpo(f) ~* 'INSERT\s+INTO\s+config\.profili_accesso_bindings'),
    0,
    '14. nessuna delle due madri scrive piu'' profili_accesso_bindings a mano');

SELECT is(
    (SELECT count(*)::int FROM t_madri WHERE pg_temp.corpo(f) ~ 'config\.fn_lega_profilo_identita\('),
    2,
    '15. ... e tutte e due chiamano il BB');

-- ============================================================
-- Il codice in minuscolo (20261104-35)
-- ============================================================
-- ⛔ Il caso del profilo di reparto: la funzione cercava col codice grezzo,
--   il trigger CODICE_MAIUSCOLO lo salva in maiuscolo, e la seconda chiamata
--   non trovava la riga e la reinseriva. Ogni scrittura in un'istruzione sua.
CREATE TEMP TABLE t_min1 AS
SELECT config.fn_scrivi_profilo_accesso('AD_HOC', 'pgtap_profilo_minuscolo', 'Profilo pgTAP minuscolo', '[]'::jsonb) AS id;
CREATE TEMP TABLE t_min2 AS
SELECT config.fn_scrivi_profilo_accesso('AD_HOC', ' Pgtap_Profilo_Minuscolo ', 'Profilo pgTAP riscritto', '[]'::jsonb) AS id;

SELECT is((SELECT id FROM t_min2), (SELECT id FROM t_min1),
    '16. due chiamate col codice in minuscolo (e maiuscole diverse) danno lo stesso profilo');

SELECT is(
    (SELECT pa.codice::text || '|' || pa.descrizione FROM config.profili_accesso pa WHERE pa.id = (SELECT id FROM t_min1)),
    'PGTAP_PROFILO_MINUSCOLO|Profilo pgTAP riscritto',
    '17. il codice si salva normalizzato, e la seconda chiamata ha aggiornato la riga');

SELECT * FROM finish();

ROLLBACK;
