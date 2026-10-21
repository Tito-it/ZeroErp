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
--       §5quinquies). Rev 2026-10-21 (20261021-24..-27, brief-db-perimetro-una-
--       volta-famiglie-residue P-1 e P-3): gli smistatori dei padri delle note
--       (fn_scope_note_ef_perimetro, fn_scope_note_magazzino_ef_perimetro) sono
--       funzioni di scope col perimetro come fn_scope_ef_perimetro, e via_coppia
--       e' uscita dalle policy: il debito del test 5 e' a zero.
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
-- ⭐ «Funzione di scope col perimetro» = fn_scope_ef_perimetro e gli
--   smistatori delle note che lo ricevono (fn_scope_note_*ef_perimetro): la
--   stessa forma, il perimetro come primo argomento in una sottoquery. Lo
--   dice la regex _perimetro qui sotto, una per tutti i test.
--   Rev 2026-10-21 (giro 5, 20261021-41): e fn_scope_email_ambito_perimetro, a
--   cui la policy passa in sottoquery le quattro risposte su chi guarda.
--   Rev 2026-10-21 (giro 4, 20261021-38): e gli smistatori delle note di
--   cliente e shop (fn_scope_note_cliente_perimetro, fn_scope_note_shop_perimetro).
--   Rev 2026-10-21 (20261021-29..-32, giro 2): anche fn_scope_sr_perimetro, la
--   forma delle vesti di CONTROPARTE (cliente, shop, fornitore): il perimetro
--   e' il soggetto dell'identita' (fn_get_identita_sr_perimetro), per riga il
--   soggetto della riga (fn_resolve_controparte_sr_id).
--
-- Elenco test (plan 6):
--  1) la derivazione non e' cieca: ci sono policy che chiamano una funzione
--     di scope col perimetro
--  2) ⭐ nessuna policy chiama piu' fn_scope_ef_whitelist( — la forma per riga
--  3) ogni chiamata a una funzione di scope col perimetro in una policy
--     riceve il perimetro in UNA sottoquery (non la forma a due, con «IS NULL»)
--  4) ⭐ il PIANO di ogni tabella con quelle policy: il perimetro in InitPlan,
--     nessuna funzione della catena nel Filter
--  5) ⭐ nessuna policy chiama un adattatore fn_scope_ef_whitelist_via_* (la
--     canonica per riga, e sotto la policy del padre) ne' uno smistatore delle
--     note che li chiama (fn_scope_note_*ef_whitelist): l'emittente per riga
--     lo da' script.fn_resolve_emittente_fiscale_id, il billing account
--     script.fn_get_ba_emittente_sr_id col perimetro in convenzione SR (giro
--     1b, 20261018-31..-33; ondata 2, 20261018-48..-51), il BA di una coppia
--     script.fn_get_ba_id_da_coppia (20261021-24..-26). Il debito dichiarato
--     e' a zero dal 2026-10-21: chi ne aggiunge uno a una policy fa rosso.
--     ⚠️ Prima le note non le vedeva: il loro nome non era fn_scope_ef_whitelist_via_*.
--  6) ⭐ le funzioni di scope di CONTROPARTE che calcolano il perimetro per riga
--     (identita', veste, veste utilizzabile a ogni riga) non stanno in nessuna
--     policy, salvo quelle DICHIARATE qui per nome: il debito dei giri
--     successivi del brief, che deve solo calare.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, e qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- La funzione di scope col perimetro, in tutte le sue forme (vedi testata).
CREATE TEMP TABLE _re AS SELECT 'fn_scope_((note_|note_magazzino_)?ef|sr|note_cliente|note_shop|email_ambito)_perimetro\('::text AS perimetro;

-- ⚠️ Il DEBITO di controparte (test 6): le funzioni di scope che calcolano
--   ancora il perimetro dell'identita' per riga, curate dai giri successivi
--   del brief. Un elenco solo, letto dai test 4 e 6: chi ne cura una la toglie
--   da qui.
CREATE TEMP TABLE _debito_controparte (nome text);
  -- Rev 2026-10-21: uscite le tre fn_scope_cliente_ownership* (giro 3,
  --   20261021-35), le tre fn_scope_shop_via_* e gli smistatori delle note di
  --   cliente e shop (giro 4, 20261021-39), fn_scope_fornitore_ownership e
  --   fn_scope_email_ambito (giro 5, 20261021-43). ⭐ Il debito e' a ZERO: la
  --   tabella resta, VUOTA, perche' i test 4 e 6 non ammettano piu' nessuno.
  --   Chi ne aggiunge uno lo fa con un INSERT qui, e con la sua ragione.

-- Le policy, con il testo di USING e WITH CHECK insieme.
CREATE TEMP TABLE _pol AS
SELECT p.polrelid AS rel, p.polname,
       coalesce(pg_get_expr(p.polqual, p.polrelid), '') || ' '
       || coalesce(pg_get_expr(p.polwithcheck, p.polrelid), '') AS testo
  FROM pg_policy p;

SELECT ok(
  (SELECT count(*) FROM _pol, _re WHERE testo ~ _re.perimetro) > 0,
  format('1) %s policy su %s tabelle chiamano una funzione di scope col perimetro (la derivazione vede)',
         (SELECT count(*) FROM _pol, _re WHERE testo ~ _re.perimetro),
         (SELECT count(DISTINCT rel) FROM _pol, _re WHERE testo ~ _re.perimetro)));

SELECT is(
  (SELECT coalesce(string_agg(rel::regclass::text || '.' || polname, ', ' ORDER BY 1), '')
     FROM _pol WHERE testo ~ 'fn_scope_ef_whitelist\('),
  '',
  '2) nessuna policy chiama fn_scope_ef_whitelist( (il perimetro per riga)');

-- Ogni occorrenza di una funzione di scope col perimetro e' seguita dalla
-- sottoquery: il catalogo stampa una sottoquery come «( SELECT».
SELECT is(
  (SELECT coalesce(string_agg(rel::regclass::text || '.' || polname, ', ' ORDER BY 1), '')
     FROM _pol, _re
    WHERE (SELECT count(*) FROM regexp_matches(testo, _re.perimetro, 'g'))
       <> (SELECT count(*) FROM regexp_matches(testo, _re.perimetro || '\( SELECT', 'g'))
       -- la forma a due sottoquery (D-3b-2c): la prima era «(SELECT (perimetro IS NULL))»
       OR testo ~ (_re.perimetro || '\( SELECT \(')),
  '',
  '3) ogni chiamata a una funzione di scope col perimetro in una policy riceve il perimetro in una sottoquery sola');

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
         WHERE x.testo ~ (SELECT perimetro FROM _re)
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
               OR bool_or(riga ~ 'Filter' AND riga ~ 'fn_get_emittenti_scope_pk_ids\(|fn_get_emittenti_scope_sr_ids\(|fn_check_user_emittente_scope\(')
               -- La catena di controparte (giro 2), salvo sulle tabelle con una
               --   policy nel debito dichiarato: li' e' ancora per riga, ed e' detto.
               OR (bool_or(riga ~ 'Filter' AND riga ~ 'fn_get_identita_sr_perimetro\(|fn_veste_utilizzabile\(')
                   AND NOT EXISTS (SELECT 1 FROM _pol p, _debito_controparte d
                                    WHERE p.rel = tabella AND p.testo ~ (d.nome || '\(')))) x),
  '',
  format('4) %s tabelle: il perimetro e'' in InitPlan e nessuna funzione della catena e'' nel Filter per riga',
         (SELECT count(DISTINCT tabella) FROM _piano)));

-- ============================================================
-- 5) Gli adattatori e gli smistatori per riga nelle policy. Il debito
--    dichiarato e' a zero dal 2026-10-21 (20261021-26): l'ultimo era
--    via_coppia, la cui chiave e' una coppia di colonne; ora la policy chiede
--    il BA a script.fn_get_ba_id_da_coppia.
-- ============================================================
SELECT is(
  (SELECT coalesce(string_agg(DISTINCT m[1], ', ' ORDER BY m[1]), '')
     FROM _pol, regexp_matches(testo, '(fn_scope_ef_whitelist_via_\w+|fn_scope_note_\w*ef_whitelist)\(', 'g') m),
  '',
  '5) nessuna policy chiama un adattatore via_* ne'' uno smistatore delle note per riga');

-- ============================================================
-- 6) Le funzioni di scope di controparte per riga. ⚠️ L'elenco e' il DEBITO
--    dei giri successivi (brief-db-perimetro-una-volta-famiglie-residue §2):
--    chi ne cura una la toglie anche da qui; una policy nuova che ne chiama
--    una fuori elenco fa rosso. La famiglia del cliente portale
--    (fn_scope_ba_ownership, _via_fattura, _via_fattura_sdi) e' uscita col
--    giro 2 (20261021-32), quella del cliente (fn_scope_cliente_ownership,
--    _via_ordine, _via_ordine_riga) col giro 3 (20261021-35), lo shop e le
--    note di cliente e shop col giro 4 (20261021-39).
-- ============================================================
SELECT is(
  (SELECT coalesce(string_agg(DISTINCT m[1], ', ' ORDER BY m[1]), '')
     FROM _pol, regexp_matches(testo,
            '(fn_scope_ba_ownership\w*|fn_scope_cliente_ownership\w*|fn_scope_shop_via_\w+|fn_scope_fornitore_ownership|fn_scope_note_cliente|fn_scope_note_shop|fn_scope_email_ambito)\(', 'g') m
    WHERE m[1] NOT IN (SELECT nome FROM _debito_controparte)),
  '',
  '6) nessuna policy chiama una funzione di scope di controparte per riga fuori dal debito dichiarato');

SELECT finish();

ROLLBACK;
