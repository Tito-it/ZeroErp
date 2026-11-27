-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: i ruoli d'impresa — il PSP, il vettore della bolla, il gestore unico,
--       il soggetto delle specializzazioni.
-- Oggetti: anagrafiche.psp, anagrafiche.vettori, anagrafiche.gestori,
--   anagrafiche.fornitori, anagrafiche.risorse_umane, pagamenti.enti_incasso,
--   vendite.ddt (vettore_soggetto_ruolo_id),
--   anagrafiche.trgfn_psp_guard_enti_incasso_attivi,
--   pagamenti.trgfn_enti_incasso_guard_psp, vendite.trgfn_ddt_guard_vettore_attivo,
--   anagrafiche.trgfn_gestori_guard (20261126-64 … -76).
-- Riferimento: brief-db-revisione-anagrafiche §25.4, §25.7 (T8c).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - ogni specializzazione ha un solo guard di ruolo per tabella;
--   - il soggetto di una specializzazione (fornitore, vettore, gestore, PSP,
--     risorsa umana) non si cambia: E_SPECIALIZZAZIONE_SOGGETTO_IMMUTABILE;
--   - il codice del PSP lo genera il database (PSP-<7 cifre>) e non si cambia;
--     il PSP non si cancella;
--   - un PSP con canali d'incasso attivi non si spegne: E_PSP_ENTI_INCASSO_ATTIVI;
--   - un canale d'incasso acceso vuole il suo PSP acceso
--     (E_ENTE_INCASSO_PSP_SPENTO); uno spento si modifica anche col PSP spento;
--   - il vettore della bolla e' un vettore (FK verso anagrafiche.vettori); una
--     bolla che lo sceglie, o lo cambia, lo vuole acceso (E_DDT_VETTORE_NON_ATTIVO);
--     la bolla e' storia: un vettore che ha portato una bolla si spegne;
--   - il gestore e' uno solo: lo dice il guard (E_GESTORE_SINGLETON_VIOLATO) e
--     lo tiene un indice unico anche fra due scritture concorrenti;
--   - anagrafiche.gestori_utilities non esiste piu'.
--
-- Elenco test (plan 22):
--    1) nessun trigger col nome storico *_ins_upd_check_ruolo_*
--    2) nessun guard di ruolo montato due volte sulla stessa tabella
--    3) anagrafiche.gestori_utilities non c'e'
--    4) anagrafiche.gestori ha l'indice unico del singleton
--    5) i lock vivi: soggetto delle cinque specializzazioni, codice del PSP
--    6) la FK del vettore della bolla punta ad anagrafiche.vettori
--    7) la FK del vettore e' un'eccezione dell'automazione ATTIVO, col motivo
--    8) e nessun trigger ATTIVO la difende
--    9) un PSP senza codice nasce
--   10) ... col codice PSP-<7 cifre>
--   11) il codice del PSP non si cambia
--   12) il soggetto del PSP non si cambia -> E_SPECIALIZZAZIONE_SOGGETTO_IMMUTABILE
--   13) il PSP non si cancella
--   14) il PSP con un canale attivo non si spegne -> E_PSP_ENTI_INCASSO_ATTIVI
--   15) spento il canale, il PSP si spegne
--   16) il canale spento si modifica col PSP spento
--   17) il canale non si riaccende col PSP spento -> E_ENTE_INCASSO_PSP_SPENTO
--   18) il vettore che ha portato una bolla si spegne
--   19) la bolla col vettore spento si modifica, se il vettore resta quello
--   20) una bolla non sceglie un vettore spento -> E_DDT_VETTORE_NON_ATTIVO
--   21) il vettore della bolla e' un vettore: un altro ruolo -> 23503
--   22) un secondo gestore -> E_GESTORE_SINGLETON_VIOLATO
-- ------------------------------------------------------------

BEGIN;

-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_mondo_cliente
--   (azienda e operatore propri).
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(22);

-- ============================================================
-- 1-8) La forma
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger t
       JOIN pg_class c     ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'anagrafiche'
        AND NOT t.tgisinternal
        AND t.tgname LIKE 'trg\_%\_ins\_upd\_check\_ruolo\_%'),
    0,
    '1) nessun trigger col nome storico *_ins_upd_check_ruolo_*');

SELECT is(
    (SELECT count(*)::int
       FROM (SELECT t.tgrelid, t.tgfoid
               FROM pg_trigger t
               JOIN pg_proc p      ON p.oid = t.tgfoid
               JOIN pg_namespace n ON n.oid = p.pronamespace
              WHERE n.nspname = 'anagrafiche'
                AND NOT t.tgisinternal
                AND p.proname LIKE 'trgfn\_%\_guard\_ruolo%'
              GROUP BY t.tgrelid, t.tgfoid
             HAVING count(*) > 1) d),
    0,
    '2) nessun guard di ruolo montato due volte sulla stessa tabella');

SELECT hasnt_table('anagrafiche', 'gestori_utilities',
    '3) anagrafiche.gestori_utilities non c''e''');

SELECT ok(
    EXISTS (SELECT 1
              FROM pg_index i
             WHERE i.indrelid = 'anagrafiche.gestori'::regclass
               AND i.indisunique
               AND i.indexprs IS NOT NULL
               AND i.indpred IS NULL),
    '4) anagrafiche.gestori ha l''indice unico del singleton (su un''espressione costante)');

SELECT bag_eq(
    $$SELECT v.target_table::text, v.column_name, v.error_code
        FROM dbops.vw_non_editable_fields v
       WHERE v.target_schema = 'anagrafiche'
         AND v.target_table IN ('fornitori', 'vettori', 'gestori', 'psp', 'risorse_umane')
         AND v.column_name IN ('soggetto_ruolo_id', 'codice')$$,
    $$VALUES ('fornitori',     'codice',            'E_CODICE_NON_MODIFICABILE'),
             ('fornitori',     'soggetto_ruolo_id', 'E_SPECIALIZZAZIONE_SOGGETTO_IMMUTABILE'),
             ('vettori',       'codice',            'E_CODICE_NON_MODIFICABILE'),
             ('vettori',       'soggetto_ruolo_id', 'E_SPECIALIZZAZIONE_SOGGETTO_IMMUTABILE'),
             ('gestori',       'soggetto_ruolo_id', 'E_SPECIALIZZAZIONE_SOGGETTO_IMMUTABILE'),
             ('psp',           'codice',            'E_CODICE_NON_MODIFICABILE'),
             ('psp',           'soggetto_ruolo_id', 'E_SPECIALIZZAZIONE_SOGGETTO_IMMUTABILE'),
             ('risorse_umane', 'soggetto_ruolo_id', 'E_SPECIALIZZAZIONE_SOGGETTO_IMMUTABILE')$$,
    '5) i lock vivi: il soggetto delle cinque specializzazioni, il codice del PSP');

SELECT ok(
    EXISTS (SELECT 1
              FROM pg_constraint k
             WHERE k.conrelid  = 'vendite.ddt'::regclass
               AND k.contype   = 'f'
               AND k.confrelid = 'anagrafiche.vettori'::regclass
               AND k.conkey    = ARRAY[(SELECT a.attnum FROM pg_attribute a
                                         WHERE a.attrelid = 'vendite.ddt'::regclass
                                           AND a.attname  = 'vettore_soggetto_ruolo_id')]::smallint[]),
    '6) la FK del vettore della bolla punta ad anagrafiche.vettori');

SELECT is(
    (SELECT count(*)::int FROM dbops.automazione_attivo_eccezioni e
      WHERE e.schema_figlia = 'vendite' AND e.tabella_figlia = 'ddt'
        AND e.colonna_fk = 'vettore_soggetto_ruolo_id' AND btrim(e.motivo) <> ''),
    1,
    '7) la FK del vettore e'' un''eccezione dell''automazione ATTIVO, col suo motivo');

-- Il trigger si riconosce dalla funzione e dagli argomenti, mai dal nome.
SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger t
       JOIN pg_proc p      ON p.oid = t.tgfoid
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE NOT t.tgisinternal
        AND n.nspname = 'dbops'
        AND ((p.proname = 'trgfn_prevent_deactivate_if_children'
              AND t.tgrelid = 'anagrafiche.vettori'::regclass
              AND (dbops.fn_trigger_argomenti(t.tgargs))[2] = 'ddt')
          OR (p.proname = 'trgfn_child_requires_active_parent'
              AND t.tgrelid = 'vendite.ddt'::regclass
              AND (dbops.fn_trigger_argomenti(t.tgargs))[2] = 'vettori'))),
    0,
    '8) nessun trigger ATTIVO lega la bolla al vettore: la bolla e'' storia');

-- ============================================================
-- Fixture
-- ⛔ Cio' che un builder scrive si legge in un'istruzione SEPARATA.
-- ============================================================
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('ruoli impresa T8c');

CREATE TEMP TABLE _s AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(
           dbops.fn_pgtap_crea_soggetto_pg('PSP uno pgTAP T8c'), 'PSP')        AS psp1_sr,
       dbops.fn_pgtap_crea_soggetto_ruolo(
           dbops.fn_pgtap_crea_soggetto_pg('PSP due pgTAP T8c'), 'PSP')        AS psp2_sr,
       dbops.fn_pgtap_crea_soggetto_ruolo(
           dbops.fn_pgtap_crea_soggetto_pg('Vettore pgTAP T8c'), 'VT')         AS vt_sr,
       dbops.fn_pgtap_crea_soggetto_ruolo(
           dbops.fn_pgtap_crea_soggetto_pg('Secondo gestore pgTAP T8c'), 'GE') AS ge2_sr,
       dbops.fn_pgtap_crea_magazzino('PGT-T8C-MAG', false)                     AS mag;

CREATE TEMP TABLE _g AS
SELECT * FROM dbops.fn_pgtap_crea_gestore('ruoli impresa T8c');

-- Il primo PSP nasce col codice scritto: e' la fixture, non il caso.
INSERT INTO anagrafiche.psp (soggetto_ruolo_id, codice, descrizione)
SELECT psp1_sr, 'PGTAP-T8C-PSP1', 'PSP uno pgTAP T8c' FROM _s;

INSERT INTO anagrafiche.vettori (soggetto_ruolo_id, descrizione)
SELECT vt_sr, 'Vettore pgTAP T8c' FROM _s;

-- Il canale d'incasso del PSP: centro, filiale, conto di incasso dell'azienda
-- di chi agisce (come test-enti-incasso-psp), tutti costruiti.
CREATE TEMP TABLE _banca AS
SELECT * FROM dbops.fn_pgtap_crea_filiale_bancaria('ruoli impresa T8c');

CREATE TEMP TABLE _centro AS
WITH c AS (
  INSERT INTO pagamenti.centri_riscossione (codice, descrizione, is_compensazione, is_fondo_fattura, attivo)
  VALUES ('PGTAP_T8C_CENTRO', 'Centro pgTAP T8c', false, false, true)
  RETURNING id)
SELECT id FROM c;

CREATE TEMP TABLE _conto AS
WITH conto AS (
  INSERT INTO anagrafiche.conti_bancari (iban, bank_branch_id, attivo, storicizza)
  SELECT 'IT00PGTAPT8CPSPCONTO00000001', b.bank_branch_id, true, false FROM _banca b
  RETURNING id
), legame AS (
  INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
      (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, storicizza)
  SELECT script.fn_pgtap_emittente_sr_operatore(), conto.id, 'INCASSO', false, false
    FROM conto
  RETURNING id
)
SELECT id AS legame_id FROM legame;

CREATE TEMP TABLE _ente AS
WITH e AS (
  INSERT INTO pagamenti.enti_incasso
      (codice, descrizione, tipo, attivo, centro_riscossione_id, soggetto_ruolo_id,
       soggetto_ruolo_conto_bancario_id)
  SELECT 'PGTAP_T8C_ENTE', 'Canale pgTAP T8c', 'PSP', true,
         (SELECT id FROM _centro), s.psp1_sr, (SELECT legame_id FROM _conto)
    FROM _s s
  RETURNING id)
SELECT id FROM e;

-- Due bolle in bozza; la prima sceglie il vettore quando e' acceso.
CREATE TEMP TABLE _ddt AS
SELECT dbops.fn_pgtap_crea_ddt(m.billing_account_id, m.cliente_soggetto_ruolo_id,
                               'VENDITA', s.mag) AS d1,
       dbops.fn_pgtap_crea_ddt(m.billing_account_id, m.cliente_soggetto_ruolo_id,
                               'VENDITA', s.mag) AS d2
  FROM _m m CROSS JOIN _s s;

UPDATE vendite.ddt SET vettore_soggetto_ruolo_id = (SELECT vt_sr FROM _s)
 WHERE id = (SELECT d1 FROM _ddt);

-- ============================================================
-- 9-13) Il PSP: il codice, il soggetto, la cancellazione
-- ============================================================
SELECT lives_ok(
    $$INSERT INTO anagrafiche.psp (soggetto_ruolo_id, descrizione)
      SELECT psp2_sr, 'PSP due pgTAP T8c' FROM _s$$,
    '9) un PSP senza codice nasce: il codice lo genera il database');

SELECT matches(
    (SELECT p.codice::text FROM anagrafiche.psp p
      WHERE p.soggetto_ruolo_id = (SELECT psp2_sr FROM _s)),
    '^PSP-[0-9]{7}$',
    '10) ... col codice PSP-<7 cifre>');

SELECT throws_like(
    $$UPDATE anagrafiche.psp SET codice = 'PGTAP-T8C-ALTRO'
       WHERE soggetto_ruolo_id = (SELECT psp1_sr FROM _s)$$,
    '%colonna codice%',
    '11) il codice del PSP non si cambia -> E_CODICE_NON_MODIFICABILE');

SELECT throws_like(
    $$UPDATE anagrafiche.psp SET soggetto_ruolo_id = (SELECT vt_sr FROM _s)
       WHERE soggetto_ruolo_id = (SELECT psp1_sr FROM _s)$$,
    '%per sempre al suo soggetto%',
    '12) il soggetto del PSP non si cambia -> E_SPECIALIZZAZIONE_SOGGETTO_IMMUTABILE');

SELECT throws_like(
    $$DELETE FROM anagrafiche.psp WHERE soggetto_ruolo_id = (SELECT psp1_sr FROM _s)$$,
    '%Cancellazione non permessa%',
    '13) il PSP non si cancella -> E_DELETE_NOT_ALLOWED');

-- ============================================================
-- 14-17) Il PSP e i suoi canali d'incasso
-- ============================================================
SELECT throws_like(
    $$UPDATE anagrafiche.psp SET attivo = false
       WHERE soggetto_ruolo_id = (SELECT psp1_sr FROM _s)$$,
    '%canali d''incasso attivi%',
    '14) il PSP con un canale attivo non si spegne -> E_PSP_ENTI_INCASSO_ATTIVI');

SELECT lives_ok(
    $$UPDATE pagamenti.enti_incasso SET attivo = false WHERE id = (SELECT id FROM _ente);
      UPDATE anagrafiche.psp SET attivo = false
       WHERE soggetto_ruolo_id = (SELECT psp1_sr FROM _s)$$,
    '15) spento il canale, il PSP si spegne');

SELECT lives_ok(
    $$UPDATE pagamenti.enti_incasso SET descrizione = 'Canale pgTAP T8c, chiuso'
       WHERE id = (SELECT id FROM _ente)$$,
    '16) il canale spento si modifica anche col PSP spento');

SELECT throws_like(
    $$UPDATE pagamenti.enti_incasso SET attivo = true WHERE id = (SELECT id FROM _ente)$$,
    '%PSP%spento%',
    '17) il canale non si riaccende col PSP spento -> E_ENTE_INCASSO_PSP_SPENTO');

-- ============================================================
-- 18-21) Il vettore della bolla
-- ============================================================
SELECT lives_ok(
    $$UPDATE anagrafiche.vettori SET attivo = false
       WHERE soggetto_ruolo_id = (SELECT vt_sr FROM _s)$$,
    '18) il vettore che ha portato una bolla si spegne: la bolla e'' storia');

SELECT lives_ok(
    $$UPDATE vendite.ddt SET num_colli = 3 WHERE id = (SELECT d1 FROM _ddt)$$,
    '19) la bolla col vettore spento si modifica, se il vettore resta quello');

SELECT throws_like(
    $$UPDATE vendite.ddt SET vettore_soggetto_ruolo_id = (SELECT vt_sr FROM _s)
       WHERE id = (SELECT d2 FROM _ddt)$$,
    '%vettore%spento%',
    '20) una bolla non sceglie un vettore spento -> E_DDT_VETTORE_NON_ATTIVO');

SELECT throws_ok(
    $$UPDATE vendite.ddt SET vettore_soggetto_ruolo_id = (SELECT psp2_sr FROM _s)
       WHERE id = (SELECT d2 FROM _ddt)$$,
    '23503',
    NULL,
    '21) il vettore della bolla e'' un vettore: un altro ruolo lo rifiuta la FK');

-- ============================================================
-- 22) Il gestore unico
-- ============================================================
SELECT throws_like(
    $$INSERT INTO anagrafiche.gestori (soggetto_ruolo_id, descrizione, cd_prod_software, valuta_id)
      SELECT s.ge2_sr, 'Secondo gestore pgTAP', 'PGTAP',
             (SELECT g.valuta_id FROM anagrafiche.gestori g
               WHERE g.id = (SELECT gestore_id FROM _g))
        FROM _s s$$,
    '%Esiste già un record di gestore%',
    '22) un secondo gestore -> E_GESTORE_SINGLETON_VIOLATO (il guard parla prima dell''indice)');

SELECT * FROM finish();
ROLLBACK;
