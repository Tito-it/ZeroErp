-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_soggetto_pg — il soggetto PG della fixture nasce dalle madri
-- Riferimento: brief-db-revisione-dbops D63 (giro 8, blocco 8b); changeSet
--   20261108-46.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - testata, contatto di default e dati societari li scrive la madre
--     anagrafiche.fn_crea_soggetto_pg: il contatto ha il nominativo e l'email
--     che scrive la madre, non una forma della fixture;
--   - gli indirizzi li scrive la madre anagrafiche.fn_crea_indirizzi_soggetto:
--     ogni tipo obbligatorio della matrice ha la sua riga;
--   - una natura senza tipi obbligatori nasce senza indirizzi (il guard non ne
--     pretende): il caso si COSTRUISCE togliendo l'obbligo alla matrice della
--     natura dentro la transazione, perche' il seed non ne ha una;
--   - al ritorno i vincoli sono IMMEDIATE e il soggetto e' completo.
--
-- Elenco test (plan 4):
--   1) il contatto di default e' quello della madre (nominativo = ragione sociale)
--   2) ogni tipo obbligatorio della matrice ha il suo indirizzo
--   3) i dati societari ci sono, per una natura che li pretende (REQUIRED)
--   4) natura senza tipi obbligatori: nessun indirizzo
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

-- La natura del default (3, PG con i dati societari obbligatori).
CREATE TEMP TABLE t_spg AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Soggetto PG madri pgTAP') AS id;

SELECT is(
    (SELECT string_agg(format('%s|%s|%s', c.nominativo, c.email, c.is_default), ',')
       FROM anagrafiche.contatti c
      WHERE c.soggetto_id = (SELECT id FROM t_spg)
        AND c.soggetto_ruolo_id IS NULL),
    -- format() rende il booleano come t/f.
    'Soggetto PG madri pgTAP|pgtap@example.com|t',
    '1) il contatto di default e'' quello della madre: nominativo = ragione sociale');

SELECT is(
    (SELECT count(*)::integer
       FROM anagrafiche.soggetti s
       JOIN config.tipi_soggetto_dettaglio_tipi_indirizzo m
         ON m.tipo_soggetto_dettaglio_id = s.tipo_soggetto_dettaglio_id
        AND m.attivo AND m.obbligatorio
      WHERE s.id = (SELECT id FROM t_spg)
        AND NOT EXISTS (SELECT 1 FROM anagrafiche.indirizzi_soggetti i
                         WHERE i.soggetto_id = s.id
                           AND i.tipo_indirizzo_id = m.tipo_indirizzo_id)),
    0,
    '2) ogni tipo obbligatorio della matrice ha il suo indirizzo');

SELECT ok(
    EXISTS (SELECT 1 FROM anagrafiche.dati_societari d
             WHERE d.soggetto_id = (SELECT id FROM t_spg)),
    '3) i dati societari ci sono: la natura li pretende');

-- 4) Il caso costruito: una natura PG senza tipi obbligatori. Si toglie
--   l'obbligo alla matrice della natura 4 (PG, dati societari facoltativi).
UPDATE config.tipi_soggetto_dettaglio_tipi_indirizzo
   SET obbligatorio = false
 WHERE tipo_soggetto_dettaglio_id = 4
   AND obbligatorio;

CREATE TEMP TABLE t_spg_senza AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Soggetto PG senza obbligatori pgTAP', 4) AS id;

SELECT is(
    (SELECT count(*)::integer FROM anagrafiche.indirizzi_soggetti i
      WHERE i.soggetto_id = (SELECT id FROM t_spg_senza)),
    0,
    '4) natura senza tipi obbligatori: il soggetto nasce senza indirizzi (nessun ripiego)');

SELECT * FROM finish();
ROLLBACK;
