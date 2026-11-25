-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- I verbi delle anagrafiche di magazzino:
--   magazzino.fn_aggiungi_{magazzino,ubicazione,lotto,asset}  (20261122-06)
--   magazzino.fn_modifica_{magazzino,ubicazione,lotto}        (20261122-07)
--   Brief: brief-db-magazzino-tutte-le-scritture-dal-verbo, D-M2, D-M6, D-M7.
--
-- ⭐ I casi si COSTRUISCONO: due emittenti con il loro operatore
--   (fn_pgtap_crea_emittente_operatore: tecnici, non super admin, senza
--   righe d'area, cioe' BLOCCATO ovunque). Il livello lo scrive il test
--   (dbops.fn_pgtap_concedi_livello_area, l'upsert di config.user_override_aree). Il mondo
--   di B si costruisce nel SUO contesto, il tentativo si fa in quello di A.
--
-- ⚠️ Gira come l'APPLICAZIONE. Le fixture nascono dai builder, che passano dai
--   verbi con l'area aperta per il tempo della nascita (20261122-09): il
--   livello che il test sceglie dopo non lo vedono.
--
-- Elenco test (plan 22):
--   il permesso
--    1) senza livello: fn_aggiungi_magazzino -> E_PERMESSO_NEGATO
--    2) senza livello: fn_modifica_ubicazione -> E_PERMESSO_NEGATO
--    3) LETTURA su magazzino: fn_aggiungi_lotto -> E_PERMESSO_NEGATO
--    4) sessione senza identita': E_PERMESSO_NEGATO
--   la nascita, con TUTTO
--    5) fn_aggiungi_magazzino: nasce, dell'emittente della sessione
--    6) fn_aggiungi_ubicazione nel magazzino proprio
--    7) fn_aggiungi_ubicazione nel magazzino di B: E_MAG_MAGAZZINO_NON_TROVATO
--    8) fn_aggiungi_ubicazione in un magazzino che non esiste: lo stesso codice
--    9) fn_aggiungi_lotto
--   10) fn_aggiungi_asset: emittente della sessione
--   11) fn_aggiungi_asset con un campo fuori lista: E_CAMPO_NON_AMMESSO (dal BB)
--   la modifica, con TUTTO
--   12) fn_modifica_magazzino: il delta cambia la descrizione e lascia il resto
--   13) fn_modifica_ubicazione: una chiave a null svuota il campo, le altre restano
--   14) fn_modifica_ubicazione con il magazzino sbagliato: E_MAG_UBICAZIONE_NON_TROVATA
--   15) fn_modifica_magazzino di B: E_MAG_MAGAZZINO_NON_TROVATO
--   16) fn_modifica_lotto: si disattiva
--   17) fn_modifica_lotto inesistente: E_MAG_LOTTO_NON_TROVATO
--   18) campo non modificabile (emittente_fiscale_id): E_CAMPO_NON_AMMESSO
--   19) dati che non sono un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA
--   20) delta vuoto: la riga com'era; il ritorno ha solo id e colonne modificabili
--   la forma
--   21) i sette verbi sono SECURITY DEFINER con search_path bloccato
--   22) ognuno chiama script.fn_guard_livello sul suo oggetto, a TUTTO
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(22);


CREATE OR REPLACE FUNCTION pg_temp.corpo(p regprocedure) RETURNS text
LANGUAGE sql AS $$
    SELECT regexp_replace(p2.prosrc, '--[^\n]*', '', 'g') FROM pg_proc p2 WHERE p2.oid = p
$$;

-- ============================================================
-- Fixture: B (l'altro emittente) col suo magazzino, nel suo contesto
-- ============================================================
CREATE TEMP TABLE _b AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _b)); END $ctx$;
CREATE TEMP TABLE _fb AS SELECT dbops.fn_pgtap_crea_magazzino('PGT-VAM-B', true) AS mag;

-- ============================================================
-- Fixture: A (chi agisce), nel suo contesto
-- ============================================================
CREATE TEMP TABLE _a AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _a)); END $ctx$;

CREATE TEMP TABLE _fa AS
SELECT dbops.fn_pgtap_crea_magazzino('PGT-VAM-A', true)                   AS mag,
       dbops.fn_pgtap_crea_articolo('PGT-VAM-LOTTI',   true, true,  false) AS art_lotti,
       dbops.fn_pgtap_crea_articolo('PGT-VAM-SERIALE', true, false, true)  AS art_ser,
       dbops.fn_pgtap_crea_indirizzo_dettaglio('PGT-VAM')                  AS ind,
       (SELECT t.id FROM config.tipi_ubicazione t WHERE t.attivo ORDER BY t.id LIMIT 1)  AS tipo,
       (SELECT s.id FROM config.stati_assets s WHERE s.attivo ORDER BY s.id LIMIT 1)     AS stato,
       (SELECT o.id FROM config.assets_ownership o WHERE o.attivo ORDER BY o.id LIMIT 1) AS prop,
       (SELECT emittente_fiscale_id FROM _a)                                AS ef;

-- Un'ubicazione e un lotto esistenti, da modificare (dai builder).
CREATE TEMP TABLE _ex AS
SELECT dbops.fn_pgtap_crea_ubicazione(f.mag, 'PGT-VAM-U0',
           '{"descrizione": "Corsia A", "corsia": "A"}'::jsonb, f.tipo)                AS ubi,
       dbops.fn_pgtap_crea_lotto_di_magazzino(f.art_lotti, 'PGT-VAM-L0', DATE '2026-11-01') AS lotto
  FROM _fa f;

-- Il livello d'area dell'operatore A.
-- ⭐ rev 2026-11-25 (D-L a, brief-db-porte-aperte-dalla-sola-guc): il livello d'area lo
--   da' il builder dbops.fn_pgtap_concedi_livello_area; la copia pg_temp.livello_area
--   che stava qui e' ritirata (regola del 2).

-- ============================================================
-- 1-4 Il permesso
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_magazzino('PGT-VAM-X1', 'x',
        (SELECT ind FROM _fa))$$),
    'E_PERMESSO_NEGATO',
    '1. senza livello: fn_aggiungi_magazzino -> E_PERMESSO_NEGATO');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_modifica_ubicazione((SELECT mag FROM _fa),
        (SELECT ubi FROM _ex), '{"corsia": "Z"}'::jsonb)$$),
    'E_PERMESSO_NEGATO',
    '2. senza livello: fn_modifica_ubicazione -> E_PERMESSO_NEGATO');

SELECT dbops.fn_pgtap_concedi_livello_area((SELECT auth_user_id FROM _a), 'magazzino', 'LETTURA');
SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_lotto((SELECT art_lotti FROM _fa),
        'PGT-VAM-LX', DATE '2026-11-01')$$),
    'E_PERMESSO_NEGATO',
    '3. LETTURA su magazzino: fn_aggiungi_lotto -> E_PERMESSO_NEGATO');

SELECT dbops.fn_pgtap_concedi_livello_area((SELECT auth_user_id FROM _a), 'magazzino', 'TUTTO');
SELECT set_config('app.current_user_id', '', true);
SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_lotto((SELECT art_lotti FROM _fa),
        'PGT-VAM-LY', DATE '2026-11-01')$$),
    'E_PERMESSO_NEGATO',
    '4. sessione senza identita'': E_PERMESSO_NEGATO');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _a)); END $ctx$;

-- ============================================================
-- 5-11 La nascita, con TUTTO
-- ============================================================
CREATE TEMP TABLE _nati AS
SELECT magazzino.fn_aggiungi_magazzino('PGT-VAM-M1', 'Magazzino dal verbo', f.ind,
                                       '{"usa_ubicazioni": true}'::jsonb)          AS mag,
       magazzino.fn_aggiungi_ubicazione(f.mag, 'PGT-VAM-U1', f.tipo)                AS ubi,
       magazzino.fn_aggiungi_lotto(f.art_lotti, 'PGT-VAM-L1', DATE '2026-11-02')    AS lotto,
       magazzino.fn_aggiungi_asset(f.art_ser, 'PGT-VAM-SN1', f.stato, f.prop)       AS asset
  FROM _fa f;

SELECT is((SELECT mg.emittente_fiscale_id FROM _nati n JOIN magazzino.magazzini mg ON mg.id = n.mag),
          (SELECT ef FROM _fa),
          '5. fn_aggiungi_magazzino: nasce, dell''emittente della sessione');

SELECT is((SELECT u.magazzino_id FROM _nati n JOIN magazzino.ubicazioni u ON u.id = n.ubi),
          (SELECT mag FROM _fa),
          '6. fn_aggiungi_ubicazione nel magazzino proprio');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_ubicazione((SELECT mag FROM _fb),
        'PGT-VAM-UB', (SELECT tipo FROM _fa))$$),
    'E_MAG_MAGAZZINO_NON_TROVATO',
    '7. fn_aggiungi_ubicazione nel magazzino di B: E_MAG_MAGAZZINO_NON_TROVATO');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_ubicazione(-1,
        'PGT-VAM-UN', (SELECT tipo FROM _fa))$$),
    'E_MAG_MAGAZZINO_NON_TROVATO',
    '8. fn_aggiungi_ubicazione in un magazzino che non esiste: lo stesso codice');

SELECT is((SELECT l.articolo_id FROM _nati n JOIN magazzino.lotti l ON l.id = n.lotto),
          (SELECT art_lotti FROM _fa),
          '9. fn_aggiungi_lotto');

SELECT is((SELECT a.emittente_fiscale_id FROM _nati n JOIN magazzino.assets a ON a.id = n.asset),
          (SELECT ef FROM _fa),
          '10. fn_aggiungi_asset: emittente della sessione');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_asset((SELECT art_ser FROM _fa),
        'PGT-VAM-SNX', (SELECT stato FROM _fa), (SELECT prop FROM _fa), '{"attivo": false}'::jsonb)$$),
    'E_CAMPO_NON_AMMESSO',
    '11. fn_aggiungi_asset con un campo fuori lista: E_CAMPO_NON_AMMESSO (dal BB)');

-- ============================================================
-- 12-20 La modifica, con TUTTO
-- ============================================================
SELECT magazzino.fn_modifica_magazzino((SELECT mag FROM _nati),
                                       '{"descrizione": "Magazzino rinominato"}'::jsonb);
SELECT is((SELECT format('%s|%s|%s', mg.descrizione, mg.codice, mg.usa_ubicazioni)
             FROM _nati n JOIN magazzino.magazzini mg ON mg.id = n.mag),
          'Magazzino rinominato|PGT-VAM-M1|t',
          '12. fn_modifica_magazzino: il delta cambia la descrizione e lascia il resto');

SELECT magazzino.fn_modifica_ubicazione((SELECT mag FROM _fa), (SELECT ubi FROM _ex),
                                        '{"corsia": null}'::jsonb);
SELECT is((SELECT format('%s|%s', u.corsia IS NULL, u.descrizione)
             FROM _ex e JOIN magazzino.ubicazioni u ON u.id = e.ubi),
          't|Corsia A',
          '13. fn_modifica_ubicazione: una chiave a null svuota il campo, le altre restano');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_modifica_ubicazione((SELECT mag FROM _nati),
        (SELECT ubi FROM _ex), '{"corsia": "B"}'::jsonb)$$),
    'E_MAG_UBICAZIONE_NON_TROVATA',
    '14. fn_modifica_ubicazione con il magazzino sbagliato: E_MAG_UBICAZIONE_NON_TROVATA');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_modifica_magazzino((SELECT mag FROM _fb),
        '{"descrizione": "presa"}'::jsonb)$$),
    'E_MAG_MAGAZZINO_NON_TROVATO',
    '15. fn_modifica_magazzino di B: E_MAG_MAGAZZINO_NON_TROVATO');

SELECT is((magazzino.fn_modifica_lotto((SELECT lotto FROM _ex), '{"attivo": false}'::jsonb) ->> 'attivo'),
          'false',
          '16. fn_modifica_lotto: si disattiva');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_modifica_lotto(-1, '{"attivo": false}'::jsonb)$$),
    'E_MAG_LOTTO_NON_TROVATO',
    '17. fn_modifica_lotto inesistente: E_MAG_LOTTO_NON_TROVATO');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_modifica_magazzino((SELECT mag FROM _nati),
        jsonb_build_object('emittente_fiscale_id', (SELECT emittente_fiscale_id FROM _b)))$$),
    'E_CAMPO_NON_AMMESSO',
    '18. campo non modificabile (emittente_fiscale_id): E_CAMPO_NON_AMMESSO');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_modifica_lotto((SELECT lotto FROM _nati), '[]'::jsonb)$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '19. dati che non sono un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT is(
    (SELECT array_agg(k ORDER BY k)
       FROM jsonb_object_keys(magazzino.fn_modifica_lotto((SELECT lotto FROM _nati), '{}'::jsonb)) AS k),
    ARRAY['attivo', 'codice', 'data_arrivo', 'data_scadenza', 'id', 'meta'],
    '20. delta vuoto: la riga com''era; il ritorno ha solo id e colonne modificabili');

-- ============================================================
-- 21-22 La forma
-- ============================================================
SELECT is(
    (SELECT array_agg(format('%s:%s:%s', p.proname, p.prosecdef,
                             array_to_string(p.proconfig, ',') ~ '^search_path=')
                      ORDER BY p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'magazzino'
        AND p.proname ~ '^fn_(aggiungi|modifica)_(magazzino|ubicazione|lotto|asset)$'),
    ARRAY['fn_aggiungi_asset:t:t', 'fn_aggiungi_lotto:t:t', 'fn_aggiungi_magazzino:t:t',
          'fn_aggiungi_ubicazione:t:t', 'fn_modifica_lotto:t:t', 'fn_modifica_magazzino:t:t',
          'fn_modifica_ubicazione:t:t'],
    '21. i sette verbi sono SECURITY DEFINER con search_path bloccato');

SELECT is(
    (SELECT array_agg(p.proname ORDER BY p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'magazzino'
        AND p.proname ~ '^fn_(aggiungi|modifica)_(magazzino|ubicazione|lotto|asset)$'
        AND pg_temp.corpo(p.oid::regprocedure) !~ (
                'script\.fn_guard_livello\([^;]*''magazzino'',\s*''' ||
                CASE substring(p.proname from '_(magazzino|ubicazione|lotto|asset)$')
                    WHEN 'magazzino'  THEN 'magazzini'
                    WHEN 'ubicazione' THEN 'ubicazioni'
                    WHEN 'lotto'      THEN 'lotti'
                    ELSE 'assets' END ||
                ''',\s*''TUTTO''\)')),
    NULL::name[],
    '22. ognuno chiama script.fn_guard_livello sul suo oggetto, a TUTTO');

SELECT * FROM finish();

ROLLBACK;
