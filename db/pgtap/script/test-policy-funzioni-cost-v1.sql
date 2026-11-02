-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: ogni funzione chiamata da una policy RLS dichiara il proprio costo
--       (COST >= 1000) — changeSet 20261010-77, e cosi' ogni funzione che
--       i PIANI delle tabelle sotto RLS mostrano nel Filter (20261010-79)
--
-- ⛔ IL PUNTO DI QUESTO FILE. COST e' una proprieta' invisibile nel corpo,
--   come ROWS (20261008-21) e security_invoker: un CREATE OR REPLACE FUNCTION
--   che non la ripete la riporta al default 100, senza errore e con risultati
--   identici. Se ne accorge solo il pianificatore: col default una policy vale
--   0,25 unita' a riga mentre ne costa ~10-35 (0,16-0,56 ms, misura dbdev
--   come app del 2026-10-10), e allora valutarla su TUTTA la tabella gli
--   sembra piu' conveniente che cercare per chiave. Caso:
--   vendite.fn_partite_merce su un DDT, ~33 ms su 47 in Seq Scan sotto policy.
--
-- ⭐ L'INSIEME SI DERIVA, NON SI ELENCA. Le funzioni sotto esame sono quelle
--   nominate da `qual` o `with_check` di pg_policies, non l'elenco del
--   changeSet: una policy nuova che chiama una funzione senza COST rende
--   questo test rosso da sola, senza che nessuno aggiorni una lista.
--
-- ⚠️ LA SOGLIA E' 1000, NON 5000. La proprieta' e' «il costo dichiarato e'
--   nell'ordine di grandezza vero», non «e' scritto 5000»: chi misura e
--   dichiara un valore diverso nello stesso ordine non e' un difetto. Il
--   default (100) e qualunque valore di quell'ordine restano rossi.
--
-- ⛔ E IL TESTO NON BASTA: CONTA IL PIANO (test 4, 2026-10-10). Una funzione
--   di policy LANGUAGE sql viene INCORPORATA: nel piano non compare lei col
--   suo COST, compare cio' che chiama. Cosi' fn_check_user_emittente_scope,
--   chiamata dentro fn_scope_ef_whitelist, stava nel Filter di 69 tabelle su
--   171 al COST di default, mentre i test 1-3 erano verdi. Il test 4 ricava le
--   funzioni dai piani (EXPLAIN come app), cioe' dalla fonte che decide.
--
-- Elenco test (plan 4):
--  1) la derivazione non e' cieca: trova le funzioni di policy, e fra loro
--     la canarina script.fn_scope_ef_perimetro (fino al 2026-10-18 era
--     fn_scope_ef_whitelist_via_ddt, uscita dalle policy col giro 1b di D-3b-2)
--  2) ⭐ nessuna funzione chiamata da una policy ha COST < 1000, salvo le
--     economiche MISURATE (stesso elenco del test 4; rev 2026-10-18) — il
--     messaggio nomina le inadempienti
--  3) ogni nome trovato nelle policy risolve a una funzione (un nome che non
--     risolve uscirebbe dal test 2 senza essere misurato)
--  4) ⭐ ogni funzione nel Filter dei piani delle tabelle sotto RLS dichiara
--     COST >= 1000, oppure e' fra quelle MISURATE economiche (elenco sotto,
--     con la misura datata accanto a ciascuna)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, e qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(4);

-- I nomi di funzione che le policy chiamano, da qual e da with_check.
CREATE TEMP TABLE _nomi_policy AS
SELECT DISTINCT m[1] AS fn
  FROM pg_policies,
       regexp_matches(coalesce(qual, '') || ' ' || coalesce(with_check, ''),
                      '(fn_\w+)\s*\(', 'g') m;

-- ...e le funzioni a cui risolvono (fuori dai cataloghi di sistema).
CREATE TEMP TABLE _fn_policy AS
-- ⚠️ Schema e nome dal catalogo, non `oid::regprocedure::text`: come app lo
--   schema script sta nel search_path e il testo uscirebbe senza `script.`.
SELECT n.nspname || '.' || p.proname
         || '(' || pg_get_function_identity_arguments(p.oid) || ')' AS funzione,
       n.nspname AS sch, p.proname AS nome, p.procost
  FROM _nomi_policy x
  JOIN pg_proc p ON p.proname = x.fn
  JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname NOT IN ('pg_catalog', 'information_schema');

SELECT ok(
  (SELECT count(*) FROM _fn_policy) > 0
  AND EXISTS (SELECT 1 FROM _fn_policy
               WHERE sch = 'script' AND nome = 'fn_scope_ef_perimetro'),
  format('1) le policy nominano %s funzioni, fra cui script.fn_scope_ef_perimetro (la derivazione vede)',
         (SELECT count(*) FROM _fn_policy)));

-- ⚠️ LE ECONOMICHE MISURATE. Sono nel Filter dei piani al COST di default
--   perche' costano davvero poco: il default (0,25 unita') e' nell'ordine di
--   grandezza giusto. Ogni voce porta la sua misura; chi ne aggiunge una la
--   MISURA (ciclo da 2000 chiamate come app, contro un ciclo vuoto), non la
--   suppone. ⛔ Non e' un posto dove parcheggiare un rosso: una funzione che
--   legge tabelle sotto RLS non e' economica.
CREATE TEMP TABLE _economiche (sch text, nome text, misura text);
INSERT INTO _economiche VALUES
  ('script', 'fn_get_uo_id_for_user',           '~0,010 ms/chiamata, dbdev come app, 2026-10-10'),
  ('script', 'fn_is_super_admin_account',       '~0,010 ms/chiamata, dbdev come app, 2026-10-10'),
  -- ⭐ L'involucro di fn_is_super_admin_account (la veste di sessione, poi l'account).
  --   Nominato dalle policy delle email (20261021-43) in una sottoquery non
  --   correlata: una chiamata per istruzione, non per riga.
  ('script', 'fn_is_super_admin',               '~0,011 ms/chiamata, 20.000 in 223 ms, scratch come owner, 2026-10-21'),
  ('script', 'fn_scope_identita_processo',      '~0,008 ms/chiamata, dbdev come app, 2026-10-10'),
  ('script', 'fn_resolve_emittente_fiscale_id', '~0,007 ms/chiamata, dbdev come app, 2026-10-10 (DEFINER: niente RLS sotto)'),
  -- ⭐ Pura: confronta l'emittente col perimetro che la policy le passa gia'
  --   calcolato (una sottoquery, una volta per istruzione). E' nominata dalle
  --   policy ef_whitelist dirette, per questo vale anche per il test 2
  --   (D-3b-2c, 20261018-24).
  ('script', 'fn_scope_ef_perimetro',           '~0,0015 ms/chiamata, 20.000 righe in 26-32 ms, dbdev come app, 2026-10-18 (non legge tabelle)'),
  -- ⭐ Pura e INCORPORATA: la sorella di controparte di fn_scope_ef_perimetro
  --   (20261021-29). Nel piano resta COALESCE(soggetto = (InitPlan), false).
  ('script', 'fn_scope_sr_perimetro',           'incorporata: 20.000 righe in 1,9 ms come un filtro vuoto, scratch come owner, 2026-10-21 (non legge tabelle)'),
  -- ⭐ Pura: la regola dell'ambito delle email, con chi guarda gia' calcolato
  --   dalla policy (20261021-41). Non legge tabelle.
  ('script', 'fn_scope_email_ambito_perimetro', '~0,0044 ms/chiamata, 20.000 righe in 92 ms (filtro vuoto 3 ms), scratch come owner, 2026-10-21 (non legge tabelle)');

SELECT is(
  (SELECT coalesce(string_agg(funzione || ' = ' || procost, ', ' ORDER BY funzione), '')
     FROM _fn_policy f
    WHERE f.procost < 1000
      -- Rev 2026-10-18 (D-3b-2): anche qui le economiche MISURATE. Una
      --   funzione pura che le policy nominano e che non legge tabelle non
      --   costa 10-35 unita' a riga: dichiararle 1000 sarebbe falso.
      AND NOT EXISTS (SELECT 1 FROM _economiche e
                       WHERE e.sch = f.sch AND e.nome = f.nome)),
  '',
  '2) ogni funzione chiamata da una policy dichiara COST >= 1000 o e'' fra le economiche misurate (un CREATE OR REPLACE senza COST la riporta a 100)');

SELECT is(
  (SELECT coalesce(string_agg(x.fn, ', ' ORDER BY x.fn), '')
     FROM _nomi_policy x
    WHERE NOT EXISTS (SELECT 1 FROM pg_proc p WHERE p.proname = x.fn)),
  '',
  '3) ogni nome di funzione trovato nelle policy risolve a una funzione');

-- ============================================================
-- 4) ⭐ Le funzioni che i PIANI mostrano, non solo quelle che le policy nominano.
-- ============================================================
-- Un EXPLAIN (senza ANALYZE: non esegue niente) di SELECT * su ogni tabella
-- con RLS attiva e almeno una policy, come app: il Filter contiene la policy
-- come il pianificatore la vede, con le funzioni SQL gia' incorporate.
CREATE TEMP TABLE _righe_piano (tabella regclass, riga text);

DO $piani$
DECLARE
    v_tab  regclass;
    v_riga text;
BEGIN
    FOR v_tab IN
        SELECT c.oid::regclass
          FROM pg_class c
         WHERE c.relrowsecurity
           AND c.relkind = 'r'
           AND EXISTS (SELECT 1 FROM pg_policy pol WHERE pol.polrelid = c.oid)
           -- ⚠️ Solo le tabelle che chi esegue puo' leggere: i piani che
           --   l'applicazione paga. Uno schema senza USAGE (shop, per l'app)
           --   farebbe fallire l'EXPLAIN; il messaggio del test conta le
           --   tabelle davvero esaminate.
           AND has_schema_privilege(c.relnamespace, 'USAGE')
           AND has_table_privilege(c.oid, 'SELECT')
    LOOP
        FOR v_riga IN EXECUTE format('EXPLAIN (VERBOSE) SELECT * FROM %s', v_tab) LOOP
            INSERT INTO _righe_piano VALUES (v_tab, v_riga);
        END LOOP;
    END LOOP;
END
$piani$;

SELECT is(
  (SELECT coalesce(string_agg(DISTINCT n.nspname || '.' || p.proname || ' = ' || p.procost
                              || ' (in ' || x.n_tab || ' tabelle)', ', '), '')
     FROM (SELECT m[1] AS fn, count(DISTINCT r.tabella) AS n_tab
             FROM _righe_piano r,
                  regexp_matches(r.riga, '(fn_\w+)\(', 'g') m
            WHERE r.riga ~ 'Filter'
            GROUP BY m[1]) x
     JOIN pg_proc p ON p.proname = x.fn
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND p.procost < 1000
      AND NOT EXISTS (SELECT 1 FROM _economiche e
                       WHERE e.sch = n.nspname AND e.nome = p.proname)),
  '',
  format('4) le funzioni nel Filter dei piani di %s tabelle sotto RLS dichiarano COST >= 1000 o sono fra le economiche misurate',
         (SELECT count(DISTINCT tabella) FROM _righe_piano)));

SELECT finish();

ROLLBACK;
