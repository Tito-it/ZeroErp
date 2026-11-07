-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: una commessa non aggrega sorgenti di emittenti diversi (H4)
-- Oggetti:
--   script.fn_get_sorgente_emittente_sr_id()                  (20260826-50)
--   vendite.fn_check_commessa_sorgente_emittente_omogeneo()   (20260826-44)
--   vendite.trgfn_commesse_sorgenti_guard_emittente()         (20260826-45)
--
-- Elenco test (plan 7):
--  1) Precondizioni: BA dell'operatore + sorgente COMMESSA a catalogo
--  2) Il risolutore risponde l'emittente giusto
--  3) Il risolutore e' FAIL-CLOSED su una chiave che non risolve
--  4) Il check risponde true per una sorgente dello stesso billing account
--  5) Il collegamento reale passa (via vendite.fn_link_commessa_sorgente)
--  6) ⭐ Il guard nuovo scatta DOPO il guard polimorfo
--  7) Il ponte testuale del risolutore non c'e' piu': la chiave passa dalle
--     colonne del modello (rev 2026-11-07, brief-db-sorgente-documento-e-riga
--     giro C.2; la forma canonica del testo la controlla il BB della porta,
--     script/test-guard-sorgente-polimorfa-testuale-v1 22-24)
--
-- ⚠️ rev 2026-11-07 (giro C.2): risolutore, check e guard prendono il documento
--   con le colonne del modello (tipo, sorgente_id, sorgente_uid). La commessa
--   sorgente e' un tipo a chiave id: sorgente_id = l'id, sorgente_uid NULL.
--
-- Scopo:
--  - la sorgente si fabbrica con il tipo COMMESSA (target vendite.commesse,
--    key_selector = 'id'), che e' la fixture ROOT gia' in uso negli altri
--    file di questo dominio: costruire un preventivo o un ordine solo per
--    avere una sorgente vorrebbe dire trascinarsi dietro i loro guard;
--  - ⭐ il 6) e' un presidio sull'ORDINE DEI NOMI, e non e' pedanteria: i
--    BEFORE ROW scattano in ordine alfabetico, e se un giorno qualcuno
--    rinominasse il guard nuovo in `...a10_guard_emittente_...` girerebbe
--    PRIMA di quello che verifica l'esistenza del documento, e proverebbe a
--    risolvere il billing account di un documento fantasma — restituendo il
--    proprio errore al posto di uno piu' preciso. E' l'unico posto in cui
--    quel cambiamento si vedrebbe.
--
-- Piano: brief-db-emittente-commessa-invariante, L8 (§7.8)
-- ------------------------------------------------------------

-- =========================================================
-- Cleanup iniziale (idempotente, FUORI dalla transazione)
-- =========================================================
DO $$
BEGIN
    DELETE FROM vendite.commesse_sorgenti cs
     WHERE cs.commessa_id IN (
         SELECT c.id FROM vendite.commesse c WHERE c.codice LIKE 'TST-SORG-EMITT-%');

    DELETE FROM vendite.commesse c
     WHERE c.codice LIKE 'TST-SORG-EMITT-%';
END;
$$;

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- =========================================================
-- 0) Riferimenti
-- =========================================================
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba, BA gia' legato all'azienda di chi
--   agisce: uno su cui l'operatore SCRIVE davvero). Prima si pescava con
--   LIMIT 1, e su un database ricostruito da zero non c'era.
CREATE TEMP TABLE tmp_cli_sorg_emitt AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('sorgente emittente omogeneo');

CREATE TEMP TABLE tmp_refs_sorg_emitt AS
SELECT
    c.billing_account_id AS billing_account_id,
    c.utility_id         AS utility_id,
    (SELECT s.id FROM config.sorgenti s
      WHERE s.codice_interno = 'COMMESSA' AND s.attivo IS TRUE) AS sorgente_tipo_id
  FROM tmp_cli_sorg_emitt c;

SELECT ok(
    (SELECT billing_account_id IS NOT NULL
        AND utility_id IS NOT NULL
        AND sorgente_tipo_id IS NOT NULL
     FROM tmp_refs_sorg_emitt),
    'Precondizioni: billing account dell''operatore + sorgente COMMESSA a catalogo'
);

-- =========================================================
-- 1) Fixture: due commesse sullo stesso billing account.
--    La prima fara' da SORGENTE della seconda.
-- =========================================================
-- rev 2026-10-27 (lotto 4 di D7): le due commesse le apre la madre
--   (dbops.fn_pgtap_crea_commessa sul BA costruito), non piu' due INSERT
--   a mano: sono fixture, non il caso sotto test.
CREATE TEMP TABLE tmp_ids_sorg_emitt AS
SELECT
    (SELECT c.commessa_id FROM dbops.fn_pgtap_crea_commessa(
         'sorg emitt root', NULL,
         (SELECT billing_account_id FROM tmp_refs_sorg_emitt)) c) AS root_id,
    (SELECT c.commessa_id FROM dbops.fn_pgtap_crea_commessa(
         'sorg emitt dest', NULL,
         (SELECT billing_account_id FROM tmp_refs_sorg_emitt)) c) AS dest_id;

-- =========================================================
-- 2) Il risolutore dice CHI EMETTE il documento
-- =========================================================
-- ⭐ Su una sorgente di tipo COMMESSA il risolutore prende la STRADA 1:
--   la colonna emittente_soggetto_ruolo_id c'e' gia', quindi e' una copia
--   e non una traduzione. Le altre due strade (emittente_fiscale_id dei
--   documenti, billing account delle attivita') sono esercitate dai
--   percorsi reali del push.
SELECT is(
    (SELECT script.fn_get_sorgente_emittente_sr_id(r.sorgente_tipo_id, t.root_id, NULL::uuid)
       FROM tmp_refs_sorg_emitt r, tmp_ids_sorg_emitt t),
    (SELECT c.emittente_soggetto_ruolo_id
       FROM vendite.commesse c, tmp_ids_sorg_emitt t WHERE c.id = t.root_id),
    'Il risolutore restituisce l''emittente del documento sorgente'
);

-- =========================================================
-- 3) ⛔ FAIL-CLOSED: una chiave che non risolve e' un errore, non un NULL
-- =========================================================
-- Un risolutore che rispondesse NULL farebbe passare il confronto a valle e
-- trasformerebbe il guard in un no-op: e' il difetto che si sta chiudendo,
-- non un dettaglio difensivo.
SELECT throws_ok(
    format(
        $q$SELECT script.fn_get_sorgente_emittente_sr_id(%s, 999999999999, NULL::uuid)$q$,
        (SELECT sorgente_tipo_id FROM tmp_refs_sorg_emitt)
    ),
    'P0001',
    NULL,
    'Il risolutore e'' fail-closed su un documento che non esiste'
);

-- =========================================================
-- 4) Il check: stesso billing account -> omogeneo
-- =========================================================
SELECT ok(
    (SELECT vendite.fn_check_commessa_sorgente_emittente_omogeneo(
                t.dest_id, r.sorgente_tipo_id, t.root_id, NULL::uuid)
       FROM tmp_refs_sorg_emitt r, tmp_ids_sorg_emitt t),
    'Sorgente dello stesso billing account: il check dice omogeneo'
);

-- =========================================================
-- 5) Il percorso reale: il collegamento passa
-- =========================================================
-- ⚠️ Il verbo va chiamato in un'istruzione SEPARATA dall'asserzione.
SELECT lives_ok(
    format(
        $q$SELECT vendite.fn_link_commessa_sorgente(%s, %s, '%s')$q$,
        (SELECT dest_id          FROM tmp_ids_sorg_emitt),
        (SELECT sorgente_tipo_id FROM tmp_refs_sorg_emitt),
        (SELECT root_id          FROM tmp_ids_sorg_emitt)
    ),
    'Collegare una sorgente dello stesso emittente passa dal guard nuovo'
);

-- =========================================================
-- 6) ⭐ L'ORDINE DEI DUE GUARD, che e' una decisione e non un caso
-- =========================================================
-- I BEFORE ROW scattano in ordine ALFABETICO. Il guard polimorfo verifica che
-- il documento ESISTA e deve parlare per primo; il nostro, che deve risolverne
-- il billing account, viene dopo. Se qualcuno rinominasse il secondo, questa
-- asserzione e' l'unico posto in cui il cambiamento si vedrebbe.
SELECT ok(
    (SELECT count(*) = 2
       FROM pg_trigger t
       JOIN pg_class c     ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE NOT t.tgisinternal
        AND n.nspname = 'vendite'
        AND c.relname = 'commesse_sorgenti'
        AND t.tgname IN ('trg_commesse_sorgenti_a10_guard_sorgente_ins_upd',
                         'trg_commesse_sorgenti_a10_guard_sorgente_omogeneita_ins_upd'))
    AND 'trg_commesse_sorgenti_a10_guard_sorgente_ins_upd'
      < 'trg_commesse_sorgenti_a10_guard_sorgente_omogeneita_ins_upd',
    'Il guard di omogeneita'' scatta DOPO quello che verifica l''esistenza del documento'
);


-- =========================================================
-- 7) Il ponte testuale non c'e' piu' (giro C.2)
-- =========================================================
-- Il risolutore aveva una porta testuale per chi teneva la chiave del link come
-- testo canonico. Il link tiene le colonne del modello, i due chiamanti le
-- passano, e la porta si e' ritirata: la forma canonica del testo resta un
-- compito del BB della porta del link.
SELECT ok(
    to_regprocedure('script.fn_get_sorgente_emittente_sr_id(bigint,text)') IS NULL,
    'Il risolutore dell''emittente non ha piu'' la porta testuale (bigint, text)'
);

SELECT * FROM finish();
ROLLBACK;
