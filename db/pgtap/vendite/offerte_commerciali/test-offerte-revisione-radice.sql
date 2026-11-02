-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la catena delle revisioni di un'offerta ha un nome,
--       vendite.offerte_commerciali.revisione_radice_id (changeSet 20260927-03..-08,
--       brief-db-liste-datatable-grezze §3.2, decisione di Tid del 2026-09-27).
--
--       La radice e' l'id della rev.1: su se' stessa per la rev.1, ereditata dal
--       padre per ogni revisione successiva. La deriva il trigger BEFORE INSERT
--       trg_offerte_commerciali_a10_default_revisione_radice_ins, e dopo la
--       nascita non si muove (lock di colonna, anche su revisione_padre_id).
--
--       ⭐ Il test 7 e' quello che distingue la regola: la rev.3 deve avere la
--       radice della rev.1, non l'id del suo padre (rev.2). Un trigger che
--       copiasse il padre invece della radice del padre passerebbe il test 6 e
--       cadrebbe qui.
--
-- ⚠️ Fixture COSTRUITA (forma di script/test-fn-available-actions-offerta-v1):
--   cliente con BA da dbops.fn_pgtap_crea_cliente_ba, listino con versione
--   attiva da dbops.fn_pgtap_crea_listino, emittente del contesto operatore.
--   ⛔ La prima versione (2026-09-27) prendeva BA, emittente e listino dal DB,
--   come i fratelli della famiglia revisioni: su zeroerp_ci, costruito da zero,
--   non c'e' nessun BA e il file moriva in ERRORE_FIXTURE.
-- ⚠️ I test 11 e 12 dipendono dal trigger di lock, che lo genera l'automazione
--   (ci_apply in CI; su dev il job automations_lock_columns): se non porta
--   ancora la colonna fanno skip() dichiarato, non un verde per sottrazione.
-- rev 2026-10-26 (brief-modello-documento-vendita §13, giro 9): lo stato
--   dell'offerta dal verbo — rev.1 e rev.2 si emettono con
--   dbops.fn_pgtap_porta_a_stato invece dell'UPDATE di stato, che la porta ora
--   rifiuta.
--
-- Indice test (1..13):
--   1)  revisione_radice_id NOT NULL
--   2)  FK fk_offerte_commerciali_revisione_radice verso la tabella stessa
--   3)  Fixture costruita completa
--   4)  rev.1 (padre NULL): la radice e' la riga stessa
--   5)  rev.1 con una radice passata dal chiamante: il valore non conta
--   6)  rev.2 da fn_crea_revisione_offerta: radice = rev.1
--   7)  rev.3 (figlia della rev.2): radice = rev.1, non il padre
--   8)  vw_offerte_commerciali_lista: la catena si legge per radice (3 righe, non la 5)
--   9)  padre inesistente: E_OFFERTA_REVISIONE_PADRE_NON_TROVATO, non un 23502
--   10) revisione_padre_id e revisione_radice_id dichiarate immutabili in automation_lock_columns
--   11) il lock generato rifiuta il cambio di revisione_padre_id — skip se non generato
--   12) il lock generato rifiuta il cambio di revisione_radice_id — skip se non generato
--   13) i due codici nuovi sono a catalogo con la loro classe e una frase in italiano
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga i DEFERRABLE INITIALLY DEFERRED non
--   scatterebbero mai (il file si chiude in ROLLBACK).
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(13);

-- ============================================================
-- 1-2) Struttura
-- ============================================================
SELECT col_not_null('vendite', 'offerte_commerciali', 'revisione_radice_id',
    '1) offerte_commerciali.revisione_radice_id NOT NULL');

SELECT ok(
    EXISTS (SELECT 1 FROM pg_constraint c
             WHERE c.conname   = 'fk_offerte_commerciali_revisione_radice'
               AND c.contype   = 'f'
               AND c.conrelid  = 'vendite.offerte_commerciali'::regclass
               AND c.confrelid = 'vendite.offerte_commerciali'::regclass),
    '2) FK fk_offerte_commerciali_revisione_radice verso vendite.offerte_commerciali');

-- ============================================================
-- 3) Setup: fixture COSTRUITA (niente dal DB esistente: su zeroerp_ci non c'e')
-- ============================================================
CREATE TEMP TABLE tmp_rr_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'revisione radice',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_rr_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_rr_cli), 'revisione radice');

CREATE TEMP TABLE tmp_rr_ctx AS
SELECT
    (SELECT billing_account_id FROM tmp_rr_cli)          AS billing_account_id,
    (SELECT istanza_utility_id FROM tmp_rr_cli)          AS istanza_utility_id,
    (SELECT utility_id FROM tmp_rr_cli)                  AS utility_id,
    script.fn_pgtap_emittente_operatore()                AS emittente_fiscale_id,
    (SELECT listino_id FROM tmp_rr_listino)              AS listino_id,
    (SELECT listino_versione_id FROM tmp_rr_listino)     AS listino_versione_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')  AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA') AS stato_emessa_id;

SELECT ok(
    (SELECT ctx.billing_account_id IS NOT NULL
        AND ctx.emittente_fiscale_id IS NOT NULL
        AND ctx.listino_versione_id IS NOT NULL
        AND ctx.stato_bozza_id IS NOT NULL AND ctx.stato_emessa_id IS NOT NULL
       FROM tmp_rr_ctx ctx),
    '3) Fixture costruita: cliente con BA, listino con versione attiva, emittente del contesto operatore, stati'
);


-- ============================================================
-- 4) rev.1: la radice e' la riga stessa
-- ============================================================
CREATE TEMP TABLE tmp_rr_rev1 AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
        revisione_numero, revisione_padre_id)
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
           ctx.utility_id, ctx.listino_id, ctx.listino_versione_id,
           DATE '2097-03-01', ctx.stato_bozza_id, 1, NULL
      FROM tmp_rr_ctx ctx
    RETURNING id, revisione_radice_id)
SELECT id, revisione_radice_id FROM ins;

SELECT is(
    (SELECT revisione_radice_id FROM tmp_rr_rev1),
    (SELECT id FROM tmp_rr_rev1),
    '4) rev.1 (revisione_padre_id NULL): revisione_radice_id = id della riga stessa'
);

-- ============================================================
-- 5) Una radice passata dal chiamante non conta
-- ============================================================
CREATE TEMP TABLE tmp_rr_altra AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
        revisione_numero, revisione_padre_id, revisione_radice_id)
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
           ctx.utility_id, ctx.listino_id, ctx.listino_versione_id,
           DATE '2097-03-01', ctx.stato_bozza_id, 1, NULL,
           (SELECT id FROM tmp_rr_rev1)
      FROM tmp_rr_ctx ctx
    RETURNING id, revisione_radice_id)
SELECT id, revisione_radice_id FROM ins;

SELECT is(
    (SELECT revisione_radice_id FROM tmp_rr_altra),
    (SELECT id FROM tmp_rr_altra),
    '5) rev.1 con revisione_radice_id passata dal chiamante: vince la derivazione (se'' stessa)'
);

-- ============================================================
-- 6) rev.2 dalla madre: radice = rev.1
-- ============================================================
-- rev 2026-10-26 (giro 9): l'emissione dal verbo, non con un UPDATE di stato.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', r.id, 'EMESSA')
  FROM tmp_rr_rev1 r;

CREATE TEMP TABLE tmp_rr_rev2 AS
SELECT vendite.fn_crea_revisione_offerta((SELECT id FROM tmp_rr_rev1), 'pgtap') AS id;

SELECT is(
    (SELECT oc.revisione_radice_id FROM vendite.offerte_commerciali oc
      WHERE oc.id = (SELECT id FROM tmp_rr_rev2)),
    (SELECT id FROM tmp_rr_rev1),
    '6) rev.2 creata da fn_crea_revisione_offerta: revisione_radice_id = rev.1'
);

-- ============================================================
-- 7) rev.3: la radice della rev.1, non l'id del padre
-- ============================================================
-- rev 2026-10-26 (giro 9): l'emissione dal verbo, non con un UPDATE di stato.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', r.id, 'EMESSA')
  FROM tmp_rr_rev2 r;

CREATE TEMP TABLE tmp_rr_rev3 AS
SELECT vendite.fn_crea_revisione_offerta((SELECT id FROM tmp_rr_rev2), 'pgtap') AS id;

SELECT is(
    (SELECT oc.revisione_radice_id FROM vendite.offerte_commerciali oc
      WHERE oc.id = (SELECT id FROM tmp_rr_rev3)),
    (SELECT id FROM tmp_rr_rev1),
    '7) rev.3 (figlia della rev.2): revisione_radice_id = rev.1, non il padre'
);

-- ============================================================
-- 8) La vista di lista espone la catena
-- ============================================================
SELECT set_eq(
    $$ SELECT v.id FROM vendite.vw_offerte_commerciali_lista v
        WHERE v.revisione_radice_id = (SELECT id FROM tmp_rr_rev1) $$,
    $$ SELECT id FROM tmp_rr_rev1 UNION ALL SELECT id FROM tmp_rr_rev2
       UNION ALL SELECT id FROM tmp_rr_rev3 $$,
    '8) vw_offerte_commerciali_lista WHERE revisione_radice_id = rev.1: le tre revisioni, non l''offerta del test 5'
);

-- ============================================================
-- 9) Padre inesistente: errore dichiarato
-- ============================================================
SELECT throws_like(
    $$ INSERT INTO vendite.offerte_commerciali (
           emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
           listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id,
           revisione_numero, revisione_padre_id)
       SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
              ctx.utility_id, ctx.listino_id, ctx.listino_versione_id,
              DATE '2097-03-01', ctx.stato_bozza_id, 2, 999999999999
         FROM tmp_rr_ctx ctx $$,
    '%L''offerta da cui dovrebbe nascere la revisione non esiste o non è visibile%',
    '9) revisione_padre_id inesistente: E_OFFERTA_REVISIONE_PADRE_NON_TROVATO (non un 23502 sulla colonna)'
);

-- ============================================================
-- 10-12) La catena e' immutabile: la sede e' il lock delle colonne
-- ============================================================
SELECT is(
    (SELECT array_agg(l.column_name::text ORDER BY l.column_name)
       FROM dbops.automation_lock_columns l
      WHERE l.target_schema = 'vendite' AND l.target_table = 'offerte_commerciali'
        AND l.error_code = 'E_OFFERTA_REVISIONE_CATENA_IMMUTABILE' AND l.enabled),
    ARRAY['revisione_padre_id', 'revisione_radice_id'],
    '10) revisione_padre_id e revisione_radice_id dichiarate immutabili in automation_lock_columns'
);

-- Il trigger lo genera l'automazione: si cerca per FUNZIONE e argomenti, non per nome.
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
                  WHERE t.tgrelid = 'vendite.offerte_commerciali'::regclass AND NOT t.tgisinternal
                    AND p.proname = 'trgfn_lock_columns'
                    AND 'revisione_padre_id' = ANY (dbops.fn_trigger_argomenti(t.tgargs)))
    THEN throws_like(
        format('UPDATE vendite.offerte_commerciali SET revisione_padre_id = %s WHERE id = %s',
               (SELECT id FROM tmp_rr_altra), (SELECT id FROM tmp_rr_rev3)),
        '%La catena delle revisioni di un''offerta non si cambia (colonna revisione_padre_id)%',
        '11) il lock generato rifiuta il cambio di revisione_padre_id')
    ELSE skip('11) lock su revisione_padre_id non ancora generato (ci_apply / job automations_lock_columns): niente da misurare', 1)
END;

SELECT CASE
    WHEN EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
                  WHERE t.tgrelid = 'vendite.offerte_commerciali'::regclass AND NOT t.tgisinternal
                    AND p.proname = 'trgfn_lock_columns'
                    AND 'revisione_radice_id' = ANY (dbops.fn_trigger_argomenti(t.tgargs)))
    THEN throws_like(
        format('UPDATE vendite.offerte_commerciali SET revisione_radice_id = %s WHERE id = %s',
               (SELECT id FROM tmp_rr_altra), (SELECT id FROM tmp_rr_rev3)),
        '%La catena delle revisioni di un''offerta non si cambia (colonna revisione_radice_id)%',
        '12) il lock generato rifiuta il cambio di revisione_radice_id')
    ELSE skip('12) lock su revisione_radice_id non ancora generato (ci_apply / job automations_lock_columns): niente da misurare', 1)
END;

-- ============================================================
-- 13) I codici nuovi: classe e frase
-- ============================================================
SELECT is(
    (SELECT array_agg(c.codice || ':' || c.classe || ':' || (m.messaggio IS NOT NULL)::text
                      ORDER BY c.codice)
       FROM config.codici_errore c
       LEFT JOIN config.messaggi_errore m ON m.codice = c.codice AND m.lingua = 'it'
      WHERE c.codice IN ('E_OFFERTA_REVISIONE_CATENA_IMMUTABILE',
                         'E_OFFERTA_REVISIONE_PADRE_NON_TROVATO')),
    ARRAY['E_OFFERTA_REVISIONE_CATENA_IMMUTABILE:CONFLITTO_STATO:true',
          'E_OFFERTA_REVISIONE_PADRE_NON_TROVATO:NON_TROVATO:true'],
    '13) i due codici nuovi sono a catalogo con la loro classe e una frase in italiano'
);

SELECT * FROM finish();
ROLLBACK;
