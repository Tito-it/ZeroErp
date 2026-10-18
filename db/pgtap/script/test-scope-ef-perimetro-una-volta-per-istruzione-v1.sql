-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU GPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: le policy ef_whitelist dirette calcolano il perimetro dell'operatore
--       UNA volta per istruzione, non una volta per riga.
--       changeSet 20261018-16..-21, forma a una sottoquery 20261018-24..-29
--       (D-3b-2, D-3b-2c di brief-db-plancache-funzioni-con-query-incorporate
--       §5quinquies).
--
-- ⛔ IL PUNTO DI QUESTO FILE. Il perimetro (super admin, veste utilizzabile,
--   whitelist, emittente attivo) non dipende dalla riga. Con
--   script.fn_scope_ef_whitelist(utente, emittente) la canonica plpgsql lo
--   ricalcolava a ogni riga letta. Ora la policy chiama
--   script.fn_scope_ef_perimetro(perimetro, emittente) con il perimetro
--   (script.fn_get_emittenti_scope_pk_ids) in UNA SOTTOQUERY NON CORRELATA:
--   PostgreSQL la valuta una volta per istruzione (InitPlan), e per riga
--   resta la funzione di scope, pura (~1,5 µs).
--   ⭐ Rev 2026-10-18 (D-3b-2c): UNA sottoquery, non due. Con due (la forma
--   di -19, per farsi incorporare) il perimetro si calcolava due volte per
--   istruzione, e le letture di una riga pagavano il doppio.
--   Le risposte restano le stesse (lo dicono i pgTAP della canonica e
--   script/test-fn-get-emittenti-scope-pk-ids-and-parity): se ne accorge solo
--   il tempo. Per questo il presidio guarda la FORMA e il PIANO.
--
-- ⚠️ TRE MODI DI ROMPERLA SENZA ERRORE, e i test 3 e 4 li vedono:
--   - una policy che passa il perimetro come espressione e non come
--     sottoquery: torna per riga (test 3);
--   - la canonica o il perimetro chiamati per riga nel Filter (test 4);
--   - il perimetro calcolato PIU' di una volta per policy, tornando alla
--     forma a due sottoquery (test 3: la prima sottoquery e' il perimetro,
--     non un «IS NULL» su di lui).
--   ⚠️ Nel PIANO il perimetro puo' comparire piu' volte, ed e' giusto: una
--   per policy applicata. Le policy di soggetti_titoli_iva_ambiti e
--   _movimenti fanno un EXISTS sul titolo padre, che ha la sua policy.
--
-- Elenco test (plan 5):
--  1) la derivazione non e' cieca: ci sono policy che chiamano
--     fn_scope_ef_perimetro
--  2) ⭐ nessuna policy chiama piu' fn_scope_ef_whitelist( — la forma per riga
--  3) ogni chiamata a fn_scope_ef_perimetro in una policy riceve il perimetro
--     in UNA sottoquery (non la forma a due, con «IS NULL»)
--  4) ⭐ il PIANO di ogni tabella con quelle policy: il perimetro in InitPlan,
--     nessuna funzione della catena nel Filter
--  5) ⭐ nessuna policy chiama un adattatore fn_scope_ef_whitelist_via_* (la
--     canonica per riga, e sotto la policy del padre), salvo quelli
--     DICHIARATI qui per nome: un debito che deve solo calare (giro 1b,
--     20261018-31..-33, e ondata 2, 20261018-48..-51: l'emittente per riga
--     lo da' script.fn_resolve_emittente_fiscale_id; il billing account
--     script.fn_get_ba_emittente_sr_id, col perimetro in convenzione SR).
--     Resta solo via_coppia.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, e qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- Le policy, con il testo di USING e WITH CHECK insieme.
CREATE TEMP TABLE _pol AS
SELECT p.polrelid AS rel, p.polname,
       coalesce(pg_get_expr(p.polqual, p.polrelid), '') || ' '
       || coalesce(pg_get_expr(p.polwithcheck, p.polrelid), '') AS testo
  FROM pg_policy p;

SELECT ok(
  (SELECT count(*) FROM _pol WHERE testo ~ 'fn_scope_ef_perimetro\(') > 0,
  format('1) %s policy su %s tabelle chiamano fn_scope_ef_perimetro (la derivazione vede)',
         (SELECT count(*) FROM _pol WHERE testo ~ 'fn_scope_ef_perimetro\('),
         (SELECT count(DISTINCT rel) FROM _pol WHERE testo ~ 'fn_scope_ef_perimetro\(')));

SELECT is(
  (SELECT coalesce(string_agg(rel::regclass::text || '.' || polname, ', ' ORDER BY 1), '')
     FROM _pol WHERE testo ~ 'fn_scope_ef_whitelist\('),
  '',
  '2) nessuna policy chiama fn_scope_ef_whitelist( (il perimetro per riga)');

-- Ogni occorrenza di fn_scope_ef_perimetro( e' seguita dalla sottoquery: il
-- catalogo stampa una sottoquery come «( SELECT».
SELECT is(
  (SELECT coalesce(string_agg(rel::regclass::text || '.' || polname, ', ' ORDER BY 1), '')
     FROM _pol
    WHERE (SELECT count(*) FROM regexp_matches(testo, 'fn_scope_ef_perimetro\(', 'g'))
       <> (SELECT count(*) FROM regexp_matches(testo, 'fn_scope_ef_perimetro\(\( SELECT', 'g'))
       -- la forma a due sottoquery (D-3b-2c): la prima era «(SELECT (perimetro IS NULL))»
       OR testo ~ 'fn_scope_ef_perimetro\(\( SELECT \('),
  '',
  '3) ogni chiamata a fn_scope_ef_perimetro in una policy riceve il perimetro in una sottoquery sola');

-- ============================================================
-- 4) ⭐ Il PIANO. EXPLAIN (senza ANALYZE: non esegue niente) di SELECT * su
--    ogni tabella con quelle policy. Come app la policy si applica; da
--    owner no, finche' FORCE e' spento: lo si accende DENTRO la
--    transazione (linee-guida-sql §10.5), e il ROLLBACK lo spegne.
-- ============================================================
CREATE TEMP TABLE _piano (tabella regclass, riga text);

DO $piani$
DECLARE
    v_tab  regclass;
    v_riga text;
BEGIN
    FOR v_tab IN
        SELECT DISTINCT c.oid::regclass
          FROM _pol x
          JOIN pg_class c ON c.oid = x.rel
         WHERE x.testo ~ 'fn_scope_ef_perimetro\('
           -- Solo dove la RLS e' accesa: una policy inerte la vede
           --   dbops.vw_rls_perimetro_scoperto (rls/test-rls-perimetro-scoperto).
           AND c.relrowsecurity
           AND has_schema_privilege(c.relnamespace, 'USAGE')
           AND has_table_privilege(c.oid, 'SELECT')
    LOOP
        IF NOT row_security_active(v_tab)
           AND pg_has_role(current_user,
                           (SELECT relowner FROM pg_class WHERE oid = v_tab), 'MEMBER') THEN
            EXECUTE format('ALTER TABLE %s FORCE ROW LEVEL SECURITY', v_tab);
        END IF;
        FOR v_riga IN EXECUTE format('EXPLAIN (VERBOSE) SELECT * FROM %s', v_tab) LOOP
            INSERT INTO _piano VALUES (v_tab, v_riga);
        END LOOP;
    END LOOP;
END
$piani$;

SELECT is(
  (SELECT coalesce(string_agg(t::text, ', ' ORDER BY t::text), '')
     FROM (SELECT tabella AS t FROM _piano
            GROUP BY tabella
           HAVING NOT bool_or(riga ~ 'InitPlan')
               OR bool_or(riga ~ 'Filter' AND riga ~ 'fn_get_emittenti_scope_pk_ids\(|fn_get_emittenti_scope_sr_ids\(|fn_check_user_emittente_scope\(')) x),
  '',
  format('4) %s tabelle: il perimetro e'' in InitPlan e nessuna funzione della catena e'' nel Filter per riga',
         (SELECT count(DISTINCT tabella) FROM _piano)));

-- ============================================================
-- 5) Gli adattatori nelle policy. ⚠️ L'elenco e' il DEBITO dell'ondata 2
--    (brief-db-plancache-funzioni-con-query-incorporate §5quinquies): chi ne
--    toglie uno lo toglie anche da qui; chi ne aggiunge uno a una policy fa
--    rosso questo test.
-- ============================================================
SELECT is(
  (SELECT coalesce(string_agg(DISTINCT m[1], ', ' ORDER BY m[1]), '')
     FROM _pol, regexp_matches(testo, '(fn_scope_ef_whitelist_via_\w+)\(', 'g') m
    WHERE m[1] NOT IN (
        -- ⚠️ L'unico rimasto (ondata 2, 20261018-48..-51): la sua chiave e'
        --   una COPPIA di colonne (istanza, utility) e il risolutore prende
        --   un valore solo. Chiama via_efba, che e' gia' nella forma nuova.
        'fn_scope_ef_whitelist_via_coppia')),
  '',
  '5) nessuna policy chiama un adattatore via_* fuori dal debito dichiarato dell''ondata 2');

SELECT finish();

ROLLBACK;
