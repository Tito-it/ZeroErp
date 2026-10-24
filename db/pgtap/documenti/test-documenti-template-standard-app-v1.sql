-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: l'applicazione LEGGE il modello standard e non lo scrive (D-2)
--   brief-db-modelli-documento-standard §4.1 Q-1, Q-2
-- ------------------------------------------------------------
-- Elenco test (plan 7):
--  1) l'app non crea uno standard                    -> E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA
--  2) l'app non trasforma un suo modello in standard -> idem (il guard parla prima del CHECK e del lock)
--  3) l'app non modifica uno standard                -> idem          (serve uno standard: skip senza seed)
--  4) l'app non aggiunge versioni a uno standard     -> idem          (skip senza seed)
--  5) l'app non cancella uno standard                -> idem          (skip senza seed)
--  6) l'app risolve lo standard per un emittente senza modelli suoi (skip senza seed)
--  7) l'app scrive i modelli del suo emittente come prima (il guard non li tocca)
--
-- Scopo:
--  - il rifiuto si prova COME L'APPLICAZIONE: da owner il guard lascia passare
--    (e' il seed). Il comportamento del modello standard e' in
--    test-documenti-template-standard-v1.sql, che gira da owner perche' deve
--    costruire gli standard.
--  - ⚠️ 3-6 hanno bisogno di uno standard che l'app non puo' costruire: lo
--    prende dal seed. Senza seed (prima della tranche dei contenuti) sono skip
--    DICHIARATI, non verdi per sottrazione; il rifiuto di 1 e 2 non dipende
--    dai dati.
-- ------------------------------------------------------------

BEGIN;

-- Un'azienda nuova col suo operatore: nessun modello suo.
CREATE TEMP TABLE _e ON COMMIT DROP AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e));
END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _k ON COMMIT DROP AS
SELECT
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')                     AS sorg,
  (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'PREVENTIVO')      AS tipo,
  (SELECT r.id FROM documenti.render_engine_documento r WHERE r.codice_interno = 'WEASYPRINT')   AS render,
  (SELECT emittente_fiscale_id FROM _e)                                                          AS e;

-- Lo standard predefinito attivo del seed per (PREVENTIVO, PREVENTIVO), se c'e'.
CREATE TEMP TABLE _std ON COMMIT DROP AS
SELECT t.id
  FROM documenti.template_documenti t, _k
 WHERE t.standard AND t.attivo AND t.is_default
   AND t.tipo_documento_output_id = _k.tipo
   AND t.sorgente_tipo_id = _k.sorg;

-- ============================================================
-- Asserzioni
-- ============================================================
SELECT throws_like(
  $$INSERT INTO documenti.template_documenti (
        tipo_documento_output_id, codice, codice_interno, descrizione,
        sorgente_tipo_id, context_builder_code, standard, is_default, attivo)
    SELECT tipo, 'PGTAP-APP-STD', 'pgtap-app-std', 'Standard dall''app', sorg,
           'PREVENTIVO', true, false, true
      FROM _k$$,
  '%non si modifica dall''applicazione%',
  '1) l''app non crea uno standard');

INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, emittente_fiscale_id, is_default, attivo)
SELECT tipo, 'PGTAP-APP-1', 'pgtap-app-1', 'Modello dell''app', sorg, 'PREVENTIVO', e, false, true
  FROM _k;

SELECT throws_like(
  $$UPDATE documenti.template_documenti
       SET standard = true, emittente_fiscale_id = NULL
     WHERE codice_interno = 'pgtap-app-1'
       AND emittente_fiscale_id = (SELECT e FROM _k)$$,
  '%non si modifica dall''applicazione%',
  '2) l''app non trasforma un suo modello in standard');

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM _std)
    THEN skip('3) senza seed degli standard non c''e'' uno standard da toccare')
    ELSE throws_like(
      $$UPDATE documenti.template_documenti SET descrizione = descrizione || ' (app)'
         WHERE id = (SELECT id FROM _std)$$,
      '%non si modifica dall''applicazione%',
      '3) l''app non modifica uno standard')
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM _std)
    THEN skip('4) senza seed degli standard non c''e'' uno standard a cui aggiungere versioni')
    ELSE throws_like(
      $$INSERT INTO documenti.template_documenti_versioni (
            template_documento_id, versione, stato, titolo, html_template,
            render_engine_id, versione_contesto)
        SELECT s.id, 999, 'BOZZA', 'bozza dall''app', '<html>app</html>', k.render, 1
          FROM _std s, _k k$$,
      '%non si modifica dall''applicazione%',
      '4) l''app non aggiunge versioni a uno standard')
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM _std)
    THEN skip('5) senza seed degli standard non c''e'' uno standard da cancellare')
    ELSE throws_like(
      $$DELETE FROM documenti.template_documenti WHERE id = (SELECT id FROM _std)$$,
      '%non si modifica dall''applicazione%',
      '5) l''app non cancella uno standard')
END;

-- 6) La lettura: l'emittente nuovo non ha modelli suoi attivi per la coppia
--    (pgtap-app-1 e' suo e attivo: lo si spegne prima).
UPDATE documenti.template_documenti SET attivo = false WHERE codice_interno = 'pgtap-app-1'
   AND emittente_fiscale_id = (SELECT e FROM _k);

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM _std)
    THEN skip('6) senza seed degli standard non c''e'' uno standard da risolvere')
    ELSE is(
      (SELECT row(r.template_documento_id, r.livello)::text
         FROM _k, documenti.fn_risolvi_template_applicabile(_k.sorg, _k.e, _k.tipo) r),
      (SELECT row(id, 'STANDARD')::text FROM _std),
      '6) l''app risolve lo standard per un emittente senza modelli suoi')
END;

SELECT lives_ok(
  $$UPDATE documenti.template_documenti SET descrizione = 'Modello dell''app (rivisto)'
     WHERE codice_interno = 'pgtap-app-1' AND emittente_fiscale_id = (SELECT e FROM _k)$$,
  '7) l''app scrive i modelli del suo emittente come prima');

SELECT * FROM finish();
ROLLBACK;
