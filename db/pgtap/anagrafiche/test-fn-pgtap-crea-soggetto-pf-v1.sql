-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_soggetto_pf — il soggetto PF della fixture nasce dalle madri
-- Riferimento: brief-db-fornitore-privato-indirizzi §9.5, riga 7-bis; changeSet
--   20261116-22. Gemello di test-fn-pgtap-crea-soggetto-pg-v1.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - testata e contatto di default li scrive la madre anagrafiche.fn_crea_soggetto_pf:
--     il contatto ha il nominativo «cognome nome» che scrive la madre;
--   - gli indirizzi li scrive la madre anagrafiche.fn_crea_indirizzi_soggetto:
--     ogni tipo obbligatorio della matrice della natura ha la sua riga;
--   - i valori li decide la natura: senza natura il privato (PR); sesso solo se la
--     natura lo prevede; partita IVA se la natura la pretende; dati societari solo
--     se la natura li PRETENDE. Il caso REQUIRED su una persona fisica il seed non
--     lo ha: si COSTRUISCE dentro la transazione;
--   - una natura senza tipi obbligatori nasce senza indirizzi (costruita);
--   - una natura di persona giuridica la rifiuta la madre.
--
-- Elenco test (plan 9):
--   1) senza natura: il privato, col sesso e senza partita IVA
--   2) il contatto di default e' quello della madre (nominativo = cognome nome)
--   3) il privato: ogni tipo obbligatorio della matrice ha il suo indirizzo
--   4) il privato: nessun dato societario (la natura li vieta)
--   5) la ditta individuale: partita IVA libera, nessun dato societario (facoltativi)
--   6) la ditta individuale: ogni tipo obbligatorio della matrice ha il suo indirizzo
--   7) natura PF che pretende i dati societari (costruita): ci sono
--   8) natura senza tipi obbligatori (costruita): nessun indirizzo
--   9) una natura PG: la rifiuta la madre
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

CREATE TEMP TABLE t_ref AS
SELECT (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR') AS pr,
       (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'DI') AS di,
       (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'SC') AS sc;

-- Pg_temp: i tipi obbligatori della matrice della natura che il soggetto non ha.
CREATE FUNCTION pg_temp.obbligatori_mancanti(p_soggetto uuid) RETURNS integer
LANGUAGE sql AS $f$
    SELECT count(*)::integer
      FROM anagrafiche.soggetti s
      JOIN config.tipi_soggetto_dettaglio_tipi_indirizzo m
        ON m.tipo_soggetto_dettaglio_id = s.tipo_soggetto_dettaglio_id
       AND m.attivo AND m.obbligatorio
     WHERE s.id = p_soggetto
       AND NOT EXISTS (SELECT 1 FROM anagrafiche.indirizzi_soggetti i
                        WHERE i.soggetto_id = s.id
                          AND i.tipo_indirizzo_id = m.tipo_indirizzo_id);
$f$;

-- ============================================================
-- Il privato, senza natura
-- ============================================================
CREATE TEMP TABLE t_pr AS
SELECT dbops.fn_pgtap_crea_soggetto_pf('Rossi') AS id;

SELECT is(
    (SELECT format('%s|%s|%s', s.tipo_soggetto_dettaglio_id = r.pr, s.sesso, s.partita_iva IS NULL)
       FROM anagrafiche.soggetti s, t_ref r
      WHERE s.id = (SELECT id FROM t_pr)),
    -- format() rende il booleano come t/f.
    't|M|t',
    '1) senza natura: il privato, col sesso (la natura lo pretende) e senza partita IVA');

SELECT is(
    (SELECT string_agg(format('%s|%s|%s', c.nominativo, c.email, c.is_default), ',')
       FROM anagrafiche.contatti c
      WHERE c.soggetto_id = (SELECT id FROM t_pr)
        AND c.soggetto_ruolo_id IS NULL),
    -- format() rende il booleano come t/f.
    'Rossi pgTAP|pgtap@example.com|t',
    '2) il contatto di default e'' quello della madre: nominativo = cognome nome');

SELECT is(pg_temp.obbligatori_mancanti((SELECT id FROM t_pr)), 0,
    '3) il privato: ogni tipo obbligatorio della matrice ha il suo indirizzo');

SELECT ok(
    NOT EXISTS (SELECT 1 FROM anagrafiche.dati_societari d WHERE d.soggetto_id = (SELECT id FROM t_pr)),
    '4) il privato: nessun dato societario (la natura li vieta)');

-- ============================================================
-- La ditta individuale
-- ============================================================
CREATE TEMP TABLE t_di AS
SELECT dbops.fn_pgtap_crea_soggetto_pf('Bianchi', 'Ditta', (SELECT di FROM t_ref)) AS id;

SELECT is(
    (SELECT format('%s|%s', s.partita_iva IS NOT NULL,
                   EXISTS (SELECT 1 FROM anagrafiche.dati_societari d WHERE d.soggetto_id = s.id))
       FROM anagrafiche.soggetti s WHERE s.id = (SELECT id FROM t_di)),
    't|f',
    '5) la ditta individuale: la partita IVA che la natura pretende, nessun dato societario (facoltativi)');

SELECT is(pg_temp.obbligatori_mancanti((SELECT id FROM t_di)), 0,
    '6) la ditta individuale: ogni tipo obbligatorio della matrice ha il suo indirizzo');

-- ============================================================
-- I casi costruiti: il seed non li ha, il modello li ammette
-- ============================================================
-- 7) Una natura PF che PRETENDE i dati societari: la ditta individuale, in
--   questa transazione.
UPDATE config.tipi_soggetto_dettaglio SET dati_societari_policy = 'REQUIRED'
 WHERE id = (SELECT di FROM t_ref);

CREATE TEMP TABLE t_di_ds AS
SELECT dbops.fn_pgtap_crea_soggetto_pf('Verdi', 'Ditta', (SELECT di FROM t_ref)) AS id;

SELECT ok(
    EXISTS (SELECT 1 FROM anagrafiche.dati_societari d WHERE d.soggetto_id = (SELECT id FROM t_di_ds)),
    '7) natura PF che pretende i dati societari: ci sono');

-- 8) Una natura senza tipi obbligatori: si toglie l'obbligo alla matrice del privato.
UPDATE config.tipi_soggetto_dettaglio_tipi_indirizzo
   SET obbligatorio = false
 WHERE tipo_soggetto_dettaglio_id = (SELECT pr FROM t_ref)
   AND obbligatorio;

CREATE TEMP TABLE t_pr_senza AS
SELECT dbops.fn_pgtap_crea_soggetto_pf('Neri') AS id;

SELECT is(
    (SELECT count(*)::integer FROM anagrafiche.indirizzi_soggetti i
      WHERE i.soggetto_id = (SELECT id FROM t_pr_senza)),
    0,
    '8) natura senza tipi obbligatori: il soggetto nasce senza indirizzi (nessun ripiego)');

-- ============================================================
-- La porta sbagliata
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$SELECT dbops.fn_pgtap_crea_soggetto_pf('Societa', 'pgTAP', %s)$$, (SELECT sc FROM t_ref))),
    'E_SOGGETTO_CREAZIONE_NATURA_ERRATA',
    '9) una natura di persona giuridica: la rifiuta la madre (la PG ha il suo builder)');

SELECT * FROM finish();
ROLLBACK;
