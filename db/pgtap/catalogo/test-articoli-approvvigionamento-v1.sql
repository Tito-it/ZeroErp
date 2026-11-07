-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test — da dove arriva un articolo: le tre colonne di approvvigionamento
--   catalogo.articoli.modo_approvvigionamento_id / gestito_a_magazzino / lead_time_giorni
--   config.modi_approvvigionamento (vocabolario, 20260913-04/-09)
--   ChangeSet: 20260913-05 (colonne), -10/-11 (backfill + DEFAULT ACQUISTO + NOT NULL),
--              -19 (vw_articoli_dettaglio). Brief:
--   brief-db-modifiche-certe-ciclo-vendita-e-articolo, sezioni 3 e 7 (P-8).
--
-- Elenco test (plan 12):
--   VOCABOLARIO
--    1) i quattro modi ci sono e sono attivi (ACQUISTO, PRODUZIONE, STOCK, NON_APPLICABILE)
--    2) ⛔ codice_interno e' immutabile: il lock generato da ci_apply rifiuta l'UPDATE
--   STRUTTURA
--    3) modo NOT NULL, gestito_a_magazzino NOT NULL, lead_time_giorni NULLABLE
--   COMPORTAMENTO — un articolo nuovo
--    4) senza modo nasce ACQUISTO (letto per codice_interno, non per id)
--    5) e nasce «non a magazzino» e senza lead time (il NULL e' un'informazione)
--    6) ⛔ lead_time_giorni negativo -> rifiutato dal CHECK (23514)
--    7) ⭐ gemello positivo: 0 passa — 0 non e' «non si applica»
--    8) ⛔ un modo inesistente -> rifiutato dalla FK (23503)
--   IL FRAMEWORK ATTIVO — cio' che nessun changeSet scrive
--    9) il require sul figlio e' montato: cercato per FUNZIONE e ARGOMENTI, non per nome
--   10) ⛔ un articolo non puo' puntare a un modo SPENTO
--   11) ⛔ un modo usato da articoli attivi non si puo' spegnere
--   LA VISTA
--   12) vw_articoli_dettaglio decodifica dalla SORGENTE: codice_interno, descrizione,
--       gestito_a_magazzino e lead_time dell'articolo di fixture coincidono con le tabelle
--
-- ────────────────────────────────────────────────────────────────
-- ⚠️ IL TEST 9 NON CERCA IL TRIGGER PER NOME, ed e' la cosa da sapere.
--   Il nome pieno — trg_articoli_a10_modi_approvvigionamento_require_attivo_ins_upd —
--   e' lungo esattamente 63 caratteri e il framework lo TRONCA E LO HASHA:
--   sul database di sviluppo si chiama
--   trg_articoli_a10_modi_approvvigionamento_require_attivo__1ad7bd. Il brief
--   e il changeSet 20260913-05 lo nominano per esteso, e si sbagliano. Un
--   presidio dinamico non si trova per nome: si trova per la funzione che
--   monta (dbops.trgfn_child_requires_active_parent) e per i suoi argomenti.
--
-- ⚠️ I TEST 2, 9, 10 E 11 DIPENDONO DA `ci_apply`. Il lock su codice_interno e
--   la coppia ATTIVO (require sul figlio, block sul padre) li genera il
--   framework delle automazioni nella SECONDA passata di Liquibase, non un
--   changeSet: su un database migrato senza --ci-apply questi quattro sono
--   rossi PER ASSENZA, non per difetto. Il test 9 lo dice esplicitamente,
--   cosi' il primo rosso non viene inseguito nel posto sbagliato.
--
-- ⚠️ GLI ARTICOLI SI COSTRUISCONO: catalogo/articoli.csv e' vuoto, quindi su
--   un database ricostruito da zero non ce n'e' nessuno. E' anche cio' che
--   rende vero il test 11 ovunque: il modo ACQUISTO e' usato almeno
--   dall'articolo di fixture.
--
-- ⚠️ IL TEST 10 HA BISOGNO DI `SET CONSTRAINTS ALL IMMEDIATE`: il require e'
--   un constraint trigger DEFERRABLE INITIALLY DEFERRED, e senza quella riga
--   scatterebbe a un COMMIT che qui non arriva mai.
--
-- Runner: applicazione (default). catalogo.articoli e config.* non hanno RLS;
--   inserire un articolo e spegnere una voce di vocabolario sono gesti che
--   l'operatore fa dal drawer e dall'amministrazione.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- VOCABOLARIO
-- ============================================================
SELECT ok(
    ARRAY['ACQUISTO', 'NON_APPLICABILE', 'PRODUZIONE', 'STOCK']::text[]
        <@ (SELECT array_agg(m.codice_interno::text ORDER BY m.codice_interno)
              FROM config.modi_approvvigionamento m
             WHERE m.attivo IS TRUE),
    '1) config.modi_approvvigionamento: i quattro modi del seed ci sono e sono attivi'
);

-- ⛔ Il lock e' implicito (la sola presenza della colonna codice_interno lo
--   provisiona, linee-guida-sql 6b) e nasce a ci_apply.
SELECT throws_like(
    $$UPDATE config.modi_approvvigionamento
         SET codice_interno = 'ACQUISTO_RINOMINATO'
       WHERE codice_interno = 'ACQUISTO'$$,
    '%Impossibile modificare il valore interno%',
    '2) codice_interno e'' immutabile: il lock generato da ci_apply rifiuta la rinomina'
);

-- ============================================================
-- STRUTTURA
-- ============================================================
SELECT is(
    (SELECT string_agg(a.attname || '=' || CASE WHEN a.attnotnull THEN 'NOT NULL' ELSE 'NULL' END,
                       ', ' ORDER BY a.attname)
       FROM pg_attribute a
      WHERE a.attrelid = 'catalogo.articoli'::regclass
        AND a.attname IN ('modo_approvvigionamento_id', 'gestito_a_magazzino', 'lead_time_giorni')),
    'gestito_a_magazzino=NOT NULL, lead_time_giorni=NULL, modo_approvvigionamento_id=NOT NULL',
    '3) le nullabilita'' sono quelle decise: modo e gestito NOT NULL, lead time NULL (brief 3.3)'
);

-- ============================================================
-- Fixture: un articolo con le sole colonne obbligatorie, senza modo
-- ============================================================
CREATE TEMP TABLE _articolo AS
WITH a AS (
    INSERT INTO catalogo.articoli (codice, descrizione, uom_id)
    SELECT 'PGTAP-APPROVV-' || substr(md5(random()::text), 1, 12),
           'Articolo pgTAP approvvigionamento',
           (SELECT um.id FROM catalogo.unita_misura um WHERE um.attivo IS TRUE ORDER BY um.id LIMIT 1)
    RETURNING id, codice
)
SELECT id AS articolo_id, codice FROM a;

-- ============================================================
-- COMPORTAMENTO — un articolo nuovo
-- ============================================================
-- Il default e' un id risolto all'apply (20260913-11): si legge per
-- codice_interno, cosi' il test non dipende da QUALE id abbia ACQUISTO.
SELECT is(
    (SELECT m.codice_interno
       FROM catalogo.articoli a
       JOIN config.modi_approvvigionamento m ON m.id = a.modo_approvvigionamento_id
      WHERE a.id = (SELECT articolo_id FROM _articolo)),
    'ACQUISTO'::varchar,
    '4) un articolo nuovo senza modo nasce ACQUISTO (decisione di Tid, 2026-09-02)'
);

SELECT is(
    (SELECT a.gestito_a_magazzino::text || '/' || COALESCE(a.lead_time_giorni::text, 'NULL')
       FROM catalogo.articoli a
      WHERE a.id = (SELECT articolo_id FROM _articolo)),
    'false/NULL',
    '5) e nasce «non a magazzino» (fail-safe) e senza lead time (NULL = non si applica)'
);

SELECT throws_ok(
    $$UPDATE catalogo.articoli SET lead_time_giorni = -1
       WHERE id = (SELECT articolo_id FROM _articolo)$$,
    '23514', NULL,
    '6) lead_time_giorni negativo: rifiutato dal CHECK'
);

SELECT lives_ok(
    $$UPDATE catalogo.articoli SET lead_time_giorni = 0
       WHERE id = (SELECT articolo_id FROM _articolo)$$,
    '7) gemello positivo: 0 passa — lo zero e'' un lead time, non «non si applica»'
);

-- Fixture per il test 12: valori non di default, cosi' la vista non puo'
-- rispondere giusto per coincidenza con i default.
UPDATE catalogo.articoli SET lead_time_giorni = 15, gestito_a_magazzino = true
 WHERE id = (SELECT articolo_id FROM _articolo);

SELECT throws_ok(
    $$UPDATE catalogo.articoli SET modo_approvvigionamento_id = -1
       WHERE id = (SELECT articolo_id FROM _articolo)$$,
    '23503', NULL,
    '8) un modo inesistente: rifiutato dalla FK fk_articoli_modi_approvvigionamento'
);

-- ============================================================
-- IL FRAMEWORK ATTIVO
-- ============================================================
-- ⚠️ Per FUNZIONE e ARGOMENTI: il nome e' hashato (vedi intestazione).
SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger t
       JOIN pg_proc p ON p.oid = t.tgfoid
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE t.tgrelid = 'catalogo.articoli'::regclass
        AND NOT t.tgisinternal
        AND n.nspname = 'dbops'
        AND p.proname = 'trgfn_child_requires_active_parent'
        AND pg_get_triggerdef(t.oid) LIKE '%''config'', ''modi_approvvigionamento'', ''attivo'', ''modo_approvvigionamento_id''%'),
    1,
    '9) il require ATTIVO su articoli -> modi_approvvigionamento e'' montato (generato da ci_apply: se manca, e'' assenza di ci_apply, non un difetto)'
);

-- Una voce SPENTA, costruita: il vocabolario e' modificabile dall'operatore.
INSERT INTO config.modi_approvvigionamento (codice_interno, codice, descrizione, attivo, ordine)
VALUES ('PGTAP_SPENTO', 'PGTAP_SPENTO', 'Modo spento di prova pgTAP', false, 990);

SELECT throws_like(
    $$UPDATE catalogo.articoli
         SET modo_approvvigionamento_id = (SELECT id FROM config.modi_approvvigionamento
                                            WHERE codice_interno = 'PGTAP_SPENTO')
       WHERE id = (SELECT articolo_id FROM _articolo)$$,
    -- la frase di E_ATTIVO_PADRE_NON_ATTIVO: padre, chiave, figlia
    '%config.modi_approvvigionamento (id = %) non è attivo%catalogo.articoli.',
    '10) un articolo non puo'' puntare a un modo spento (require sul figlio, ci_apply)'
);

SELECT throws_like(
    $$UPDATE config.modi_approvvigionamento SET attivo = false
       WHERE codice_interno = 'ACQUISTO'$$,
    '%Non si puo'' disattivare%',
    '11) un modo usato da articoli attivi non si spegne (block sul padre, ci_apply)'
);

-- ============================================================
-- LA VISTA: il valore, non la colonna
-- ============================================================
-- ⚠️ `has_column` proverebbe che la colonna esiste, non da dove viene il
--   valore: qui si confronta la vista con le tabelle sorgente sulla riga di
--   fixture (modo ACQUISTO, gestito true e lead time 15 dal test 7).
SELECT is(
    (SELECT v.modo_approvvigionamento_codice_interno || '|' || v.modo_approvvigionamento_descrizione
            || '|' || v.gestito_a_magazzino::text || '|' || v.lead_time_giorni::text
       FROM catalogo.vw_articoli_dettaglio v
      WHERE v.id = (SELECT articolo_id FROM _articolo)),
    (SELECT m.codice_interno || '|' || m.descrizione
            || '|' || a.gestito_a_magazzino::text || '|' || a.lead_time_giorni::text
       FROM catalogo.articoli a
       JOIN config.modi_approvvigionamento m ON m.id = a.modo_approvvigionamento_id
      WHERE a.id = (SELECT articolo_id FROM _articolo)),
    '12) vw_articoli_dettaglio decodifica il modo dalla sorgente e porta gestito_a_magazzino e lead_time_giorni tali e quali'
);

SELECT * FROM finish();
ROLLBACK;
