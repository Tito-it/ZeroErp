-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Schema: catalogo
-- Ambito: seed automatico UoM operativa base + lock UPDATE su uom_id
--
-- Indice test (0..7):
--   1) Funzione catalogo.trgfn_articoli_seed_uom_base presente
--   2) Trigger trg_articoli_a10_seed_uom_base_ins presente
--   3) Il lock di catalogo.articoli copre `codice` e `uom_id` — cercato per
--      FUNZIONE e ARGOMENTI, mai per nome (il nome e' dell'automazione)
--   4) Setup: riferimenti FK reali disponibili
--   5) INSERT articolo crea riga is_base=true in articoli_uom_operativa
--   6) Solo UNA riga is_base=true per articolo dopo seed
--   7) UPDATE articoli.uom_id bloccato (E_CODICE_NON_MODIFICABILE, P0001)
--   8) Override GUC consente la modifica in manutenzione
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- ============================================================
-- 1) Funzione presente
-- ============================================================
SELECT has_function(
    'catalogo', 'trgfn_articoli_seed_uom_base',
    ARRAY[]::text[],
    '1) catalogo.trgfn_articoli_seed_uom_base presente'
);

-- ============================================================
-- 2) Trigger seed presente
-- ============================================================
SELECT ok(
    EXISTS(
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'catalogo'
           AND c.relname = 'articoli'
           AND t.tgname = 'trg_articoli_a10_seed_uom_base_ins'
           AND NOT t.tgisinternal
    ),
    '2) trigger trg_articoli_a10_seed_uom_base_ins presente su catalogo.articoli'
);

-- ============================================================
-- 3) Il lock c'e', e copre le DUE colonne
-- ============================================================
-- ⛔ Il NOME non si pinna: questo trigger lo genera l'automazione
--   (dbops.fn_run_automations_lock_columns) dal registro
--   dbops.automation_lock_columns, e il nome e' suo — `trg_{table}_a10_lock_-
--   columns_upd`, da un template che sta in dbops.automation_rules_tbl.
--   ⚠️ Fino al 2026-09-23 qui c'erano DUE trigger scritti A MANO
--   (trg_articoli_a10_protect_codice_upd e _protect_uom_id_upd) che il registro
--   non conosceva: oggetti che *sembravano* governati dall'automazione e non lo
--   erano. La bonifica 90_end/20260923-02 li ha portati nel registro e
--   l'automazione ne ha fatto UNO solo con entrambe le colonne. Questo test
--   asseriva il nome vecchio ed e' andato rosso **su una riparazione**: e' la
--   forma «test che pinna il sintomo», e si cura cercando cio' che conta.
-- ⭐ E adesso asserisce ENTRAMBE le colonne. Fino a ieri il lock su `codice` non
--   era pinnato da nessuno — ed e' esattamente quello che una rigenerazione
--   poteva far sparire in silenzio.
SELECT is(
    (SELECT array_agg(DISTINCT u.a ORDER BY u.a)
       FROM pg_trigger t
       JOIN pg_proc p ON p.oid = t.tgfoid,
       -- Argomenti dal building block (dal 2026-09-26): prima qui si decodificava
       -- con encode(tgargs,'escape'), che lascia un elemento vuoto in coda.
       LATERAL unnest(dbops.fn_trigger_argomenti(t.tgargs))
               WITH ORDINALITY u(a, i)
      WHERE t.tgrelid = 'catalogo.articoli'::regclass
        AND NOT t.tgisinternal
        AND p.proname = 'trgfn_lock_columns'
        AND u.i % 2 = 1),
    ARRAY['codice', 'uom_id'],
    '3) catalogo.articoli e'' lockata da script.trgfn_lock_columns su codice e uom_id'
);

-- ============================================================
-- Setup riferimenti FK reali
-- ============================================================
CREATE TEMP TABLE tmp_test_keys AS
SELECT to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS') AS ts;

CREATE TEMP TABLE tmp_refs AS
SELECT
    (SELECT id FROM catalogo.unita_misura WHERE attivo = true ORDER BY id LIMIT 1)            AS uom1_id,
    (SELECT id FROM catalogo.unita_misura WHERE attivo = true ORDER BY id LIMIT 1 OFFSET 1)   AS uom2_id,
    (SELECT id FROM vendite.articoli_gruppi WHERE attivo = true ORDER BY id LIMIT 1)          AS gruppo_id,
    (SELECT id FROM vendite.articoli_tipologie WHERE attivo = true ORDER BY id LIMIT 1)       AS tipo_id,
    (SELECT id FROM vendite.articoli_spesa WHERE attivo = true ORDER BY id LIMIT 1)           AS spesa_id,
    (SELECT id FROM config.iva WHERE attivo = true ORDER BY id LIMIT 1)                       AS iva_id;

-- ============================================================
-- 4) Setup OK
-- ============================================================
SELECT ok(
    (SELECT uom1_id   FROM tmp_refs) IS NOT NULL
    AND (SELECT uom2_id   FROM tmp_refs) IS NOT NULL
    AND (SELECT gruppo_id FROM tmp_refs) IS NOT NULL
    AND (SELECT tipo_id   FROM tmp_refs) IS NOT NULL
    AND (SELECT spesa_id  FROM tmp_refs) IS NOT NULL
    AND (SELECT iva_id    FROM tmp_refs) IS NOT NULL,
    '4) riferimenti FK reali tutti disponibili (2 UoM, gruppo, tipo, spesa, iva)'
);

-- ============================================================
-- 5) INSERT articolo crea riga is_base=true in articoli_uom_operativa
-- ============================================================
CREATE TEMP TABLE tmp_art (id uuid);

INSERT INTO catalogo.articoli (
    codice,
    descrizione,
    uom_id,
    tipo_voce_id,
    gruppo_voce_id,
    spesa_id,
    iva_id
)
SELECT
    'TEST_SEED_' || (SELECT ts FROM tmp_test_keys),
    'Articolo test seed UoM base',
    (SELECT uom1_id   FROM tmp_refs),
    (SELECT tipo_id   FROM tmp_refs),
    (SELECT gruppo_id FROM tmp_refs),
    (SELECT spesa_id  FROM tmp_refs),
    (SELECT iva_id    FROM tmp_refs)
RETURNING id;

INSERT INTO tmp_art (id)
SELECT id FROM catalogo.articoli
 WHERE codice = 'TEST_SEED_' || (SELECT ts FROM tmp_test_keys);

SELECT ok(
    EXISTS(
        SELECT 1 FROM catalogo.articoli_uom_operativa
         WHERE articolo_id = (SELECT id FROM tmp_art)
           AND uom_id      = (SELECT uom1_id FROM tmp_refs)
           AND is_base     = true
           AND factor_to_base = 1
    ),
    '5) seed AFTER INSERT: riga is_base=true creata con uom_id e factor_to_base=1'
);

-- ============================================================
-- 6) Solo UNA riga is_base=true per articolo
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM catalogo.articoli_uom_operativa
       WHERE articolo_id = (SELECT id FROM tmp_art)
         AND is_base = true),
    1,
    '6) esattamente 1 riga is_base=true per articolo dopo seed'
);

-- ============================================================
-- 7) UPDATE uom_id bloccato
-- ============================================================
-- ⚠️ Lo SQLSTATE si dichiara: `throws_ok(sql, NULL, NULL)` accetta QUALUNQUE
--   errore — anche una FK rotta dalla fixture — e passerebbe senza aver
--   misurato il lock. `P0001` e' l'errore di dominio che solleva
--   script.fn_log_and_raise_error dentro script.trgfn_lock_columns.
-- ⛔ Non si pinna la FRASE: il codice e' E_CODICE_NON_MODIFICABILE dal
--   2026-09-23 (prima CODICE_NON_MODIFICABILE, ritirato il 2026-08-05), e il
--   messaggio a catalogo e' lo stesso per entrambi — pinnarlo qui aggiungerebbe
--   una terza copia di un testo che vive in config.messaggi_errore.
SELECT throws_ok(
    format(
        'UPDATE catalogo.articoli SET uom_id = %s WHERE id = %L',
        (SELECT uom2_id FROM tmp_refs),
        (SELECT id FROM tmp_art)
    ),
    'P0001',
    NULL,
    '7) UPDATE articoli.uom_id bloccato dal trigger lock (P0001)'
);

-- ============================================================
-- 8) Override GUC consente la modifica
-- ============================================================
SET LOCAL zeroerp.allow_lock_columns_override = 'on';

SELECT lives_ok(
    format(
        'UPDATE catalogo.articoli SET uom_id = %s WHERE id = %L',
        (SELECT uom2_id FROM tmp_refs),
        (SELECT id FROM tmp_art)
    ),
    '8) GUC zeroerp.allow_lock_columns_override=on consente UPDATE uom_id'
);

RESET zeroerp.allow_lock_columns_override;

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
