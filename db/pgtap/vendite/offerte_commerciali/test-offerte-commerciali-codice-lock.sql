-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: immutabilita' di vendite.offerte_commerciali.codice.
--       Trigger trg_offerte_commerciali_a10_lock_columns_upd, generato
--       dall'automazione LOCK_COLUMNS (dbops.fn_run_automations_lock_columns)
--       dalla riga aggiunta il 2026-08-21 a dbops.automation_lock_columns.
--
-- ── PERCHE' ESISTE ─────────────────────────────────────────────────────
--   Fino al 2026-08-21 questa tabella aveva il gen_codice agganciato anche in
--   UPDATE ma NESSUN lock, a differenza delle sette tabelle gemelle
--   (soggetti, billing_account, fornitori, istanze_utilities, vettori,
--   contratti, pratiche). Conseguenza: un UPDATE che azzerava `codice` ne
--   faceva rigenerare uno NUOVO, consumando la sequenza, e l'offerta cambiava
--   identita' per chiunque la citasse per codice. Nessuna GUC, nessuna
--   manutenzione: bastava un UPDATE.
--   Il percorso applicativo non era esposto (`codice` non e' in
--   _OFFERTA_UPDATE_COLS del repository), l'UPDATE diretto si'.
--   Classificata da Tid come dimenticanza, non come scelta.
--
-- ⚠️ Questo file e' ROSSO finche' la migrazione del 2026-08-21 non e'
--    applicata e l'automazione LOCK_COLUMNS non e' passata: il trigger non
--    e' scritto a mano, lo genera il runner. E' atteso, non e' una regressione.
--
-- Indice test (1..6):
--   Sanity configurazione:
--   1) riga di lock configurata in dbops.automation_lock_columns
--   2) trigger trg_offerte_commerciali_a10_lock_columns_upd esiste
--   3) il trigger copre la colonna `codice` (UPDATE OF)
--   Comportamento:
--   4) UPDATE che azzera codice -> BLOCCO (e nessun codice nuovo generato)
--   5) UPDATE che riscrive codice con un valore arbitrario -> BLOCCO
--   6) UPDATE su un'altra colonna -> ammesso (il lock non e' un blocco generale)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Contesto applicativo: il test gira come gira l'applicazione (OPERATORE +
--   RLS attiva). Senza, le SELECT della fixture leggerebbero zero righe e il
--   file diventerebbe verde per sottrazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ Vincoli DIFFERITI: qui il COMMIT non arriva mai (si chiude in ROLLBACK),
--   quindi senza questa riga non verrebbero mai esercitati.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- 1) La riga di configurazione esiste (sanity sul seed)
--    E' il seed a comandare: senza questa riga il runner non genererebbe
--    nessun lock sulla colonna, e i test 4/5 fallirebbero senza dire perche'.
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM dbops.automation_lock_columns
         WHERE target_schema = 'vendite'
           AND target_table  = 'offerte_commerciali'
           AND column_name   = 'codice'
           AND enabled IS TRUE
    ),
    '1) dbops.automation_lock_columns: riga vendite.offerte_commerciali.codice attiva'
);

-- ============================================================
-- 2) Il trigger generato esiste
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c     ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'offerte_commerciali'
           AND t.tgname  = 'trg_offerte_commerciali_a10_lock_columns_upd'
           AND NOT t.tgisinternal
    ),
    '2) trg_offerte_commerciali_a10_lock_columns_upd esiste'
);

-- ============================================================
-- 3) Il trigger copre proprio la colonna `codice`
--    Non basta che esista: il runner crea UN SOLO trigger per tabella con
--    UPDATE OF sulle colonne configurate. Se un domani ne venisse aggiunta
--    un'altra senza rigenerare il trigger (l'automazione e'
--    create-if-not-exists), il trigger resterebbe quello vecchio — e questa
--    asserzione e' cio' che se ne accorgerebbe.
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c      ON c.oid = t.tgrelid
          JOIN pg_namespace n  ON n.oid = c.relnamespace
          JOIN pg_attribute a  ON a.attrelid = c.oid
                              AND a.attnum = ANY (t.tgattr)
         WHERE n.nspname = 'vendite'
           AND c.relname = 'offerte_commerciali'
           AND t.tgname  = 'trg_offerte_commerciali_a10_lock_columns_upd'
           AND a.attname = 'codice'
    ),
    '3) il trigger di lock e'' agganciato a UPDATE OF codice'
);

-- ============================================================
-- Fixture: un'offerta in BOZZA, con codice generato dal sistema_codici
-- ============================================================
-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo); fixture
--   costruito invece che preso dai dati. Cliente su una utility senza
--   tipi_utenze (evita il guard tipo/classe sui satelliti utilities), legato
--   dal z90 all'emittente di chi agisce; listino sulla stessa utility.
--   ⛔ Cio' che i builder scrivono si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_ofc_lock_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'codice lock offerte',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_ofc_lock_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_ofc_lock_cli), 'codice lock offerte');

CREATE TEMP TABLE tmp_ofc_lock_ctx AS
SELECT
    (SELECT billing_account_id FROM tmp_ofc_lock_cli) AS billing_account_id,
    (SELECT istanza_utility_id FROM tmp_ofc_lock_cli) AS istanza_utility_id,
    (SELECT utility_id FROM tmp_ofc_lock_cli) AS utility_id,
    -- ⚠️ L'emittente non si pesca, si deriva da chi agisce: le policy
    --   ef_whitelist lo pretendono.
    script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
    (SELECT listino_id FROM tmp_ofc_lock_listino) AS listino_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA') AS stato_bozza_id;

CREATE TEMP TABLE tmp_ofc_lock_id AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
           ctx.utility_id, ctx.listino_id, DATE '2093-01-01', ctx.stato_bozza_id
      FROM tmp_ofc_lock_ctx ctx
    RETURNING id, codice
)
SELECT id, codice FROM ins;

-- ============================================================
-- 4) UPDATE che azzera il codice -> BLOCCO
--    E' il caso che ha motivato il lock: senza, il gen_codice (che gira PRIMA,
--    per ordine alfabetico) ne rigenerava uno nuovo e l'UPDATE passava.
-- ============================================================
SELECT throws_like(
    format(
        'UPDATE vendite.offerte_commerciali SET codice = NULL WHERE id = %s',
        (SELECT id FROM tmp_ofc_lock_id)
    ),
    '%Impossibile modificare il valore interno della colonna%',
    '4) UPDATE che azzera codice -> bloccato (CODICE_NON_MODIFICABILE)'
);

-- ============================================================
-- 5) UPDATE che riscrive il codice con un valore arbitrario -> BLOCCO
--    Ramo diverso dal 4: qui il gen_codice non interviene affatto (il valore
--    non e' vuoto), quindi a bloccare puo' essere solo il lock.
-- ============================================================
SELECT throws_like(
    format(
        $$UPDATE vendite.offerte_commerciali SET codice = 'OFC-PGTAP-FAKE' WHERE id = %s$$,
        (SELECT id FROM tmp_ofc_lock_id)
    ),
    '%Impossibile modificare il valore interno della colonna%',
    '5) UPDATE che riscrive codice con valore arbitrario -> bloccato'
);

-- ============================================================
-- 6) UPDATE su un'altra colonna -> AMMESSO
--    Il lock e' `UPDATE OF codice`: non deve trasformarsi in un blocco
--    generale della tabella. Senza questa asserzione un lock troppo largo
--    passerebbe inosservato.
-- ============================================================
SELECT lives_ok(
    format(
        $$UPDATE vendite.offerte_commerciali SET validita_al = DATE '2093-12-31' WHERE id = %s$$,
        (SELECT id FROM tmp_ofc_lock_id)
    ),
    '6) UPDATE su un''altra colonna -> ammesso (il lock non blocca il resto)'
);

SELECT * FROM finish();
ROLLBACK;
