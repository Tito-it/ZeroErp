-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: generazione automatica di anagrafiche.vettori.codice via
--       config.sistema_codici (riga 19, aggiunta il 2026-08-21).
--
-- ── PERCHE' ESISTE ─────────────────────────────────────────────────────
--   `anagrafiche.vettori.codice` e' NOT NULL e UNIQUE, ma fino al 2026-08-21
--   nessuno lo generava: niente trigger gen_codice sulla tabella, niente riga
--   in config.sistema_codici. Il codice doveva arrivare dal chiamante, e un
--   INSERT che lo ometteva moriva su una violazione di vincolo (23502), senza
--   nessun codice E_* a spiegarlo. Nel frattempo
--   `anagrafiche.trgfn_vettori_normalize` — un no-op — dichiarava nel suo
--   COMMENT «generazione codice demandata al sistema_codici»: un rinvio a un
--   meccanismo che per i vettori non era mai stato attivato.
--   Emerso scrivendo la doc manuale della fascia A.
--
-- ── COSA VERIFICA DAVVERO ──────────────────────────────────────────────
--   Che l'automazione generale dei codici abbia fatto il suo lavoro. Sequenza,
--   funzione e trigger NON sono scritti a mano da nessuna parte: li crea con
--   DDL dinamico script.trgfn_config_sistema_codici_sync_gen_codice quando il
--   loader del CSV inserisce la riga in config.sistema_codici. I test 2/3/4
--   sono quindi il collaudo di quell'automazione su un caso nuovo, non la
--   verifica di codice scritto a mano.
--
-- ⚠️ Questo file e' ROSSO finche' la migrazione del 2026-08-21 non e'
--    applicata. E' atteso, non e' una regressione.
--
-- Indice test (1..6):
--   Sanity configurazione:
--   1) riga 'vettori' presente e attiva in config.sistema_codici, con target
--      anagrafiche.vettori.codice
--   2) sequenza anagrafiche.vettori_codice_seq creata dall'automazione
--   3) funzione anagrafiche.trgfn_vettori_gen_codice() creata dall'automazione
--   4) trigger trg_vettori_a10_gen_codice_ins_upd creato dall'automazione
--   Comportamento:
--   5) INSERT vettore senza codice -> codice generato con pattern VET-NNNNNNN
--   6) il codice cosi' generato non e' poi modificabile (lock gia' configurato)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Contesto applicativo: il test gira come gira l'applicazione (OPERATORE +
--   RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ Vincoli DIFFERITI: qui il COMMIT non arriva mai (si chiude in ROLLBACK).
--   In testa e non in coda: in coda scatterebbero dopo il cleanup.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- 1) La riga di configurazione esiste e punta alla colonna giusta
--    E' il seed a comandare tutto il resto: se questa riga cambia target, gli
--    oggetti dei test 2/3/4 vengono distrutti e ricreati altrove
--    dall'automazione, in silenzio.
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM config.sistema_codici sc
         WHERE sc.codice_interno  = 'vettori'
           AND sc.schema_tabella  = 'anagrafiche'
           AND sc.nome_tabella    = 'vettori'
           AND sc.nome_colonna    = 'codice'
           AND sc.usa_sequenza IS TRUE
    ),
    '1) config.sistema_codici: riga vettori -> anagrafiche.vettori.codice, usa_sequenza = true'
);

-- ============================================================
-- 2) La sequenza esiste
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_sequences
         WHERE schemaname   = 'anagrafiche'
           AND sequencename = 'vettori_codice_seq'
    ),
    '2) sequenza anagrafiche.vettori_codice_seq esiste'
);

-- ============================================================
-- 3) La trigger function generata esiste
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'anagrafiche'
           AND p.proname = 'trgfn_vettori_gen_codice'
    ),
    '3) anagrafiche.trgfn_vettori_gen_codice() esiste'
);

-- ============================================================
-- 4) Il trigger esiste ed e' agganciato alla colonna codice
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c      ON c.oid = t.tgrelid
          JOIN pg_namespace n  ON n.oid = c.relnamespace
          JOIN pg_attribute a  ON a.attrelid = c.oid
                              AND a.attnum = ANY (t.tgattr)
         WHERE n.nspname = 'anagrafiche'
           AND c.relname = 'vettori'
           AND t.tgname  = 'trg_vettori_a10_gen_codice_ins_upd'
           AND a.attname = 'codice'
           AND NOT t.tgisinternal
    ),
    '4) trg_vettori_a10_gen_codice_ins_upd esiste su UPDATE OF codice'
);

-- ============================================================
-- Fixture: un soggetto nuovo con ruolo VT
--   ⚠️ Serve un ruolo VT LIBERO: uq_vettori_ruolo e' UNIQUE, quindi riusare il
--   ruolo di un vettore esistente farebbe fallire l'INSERT per un motivo che
--   non c'entra con questo test. Si crea, non si pesca.
--   ⚠️ Soggetto e ruolo in due istruzioni separate (plpgsql, non una CTE): una
--   policy che risolve il perimetro dal padre non lo troverebbe nella stessa
--   snapshot e negherebbe fail-closed.
-- ============================================================
CREATE TEMP TABLE tmp_vet_ctx (soggetto_id uuid, soggetto_ruolo_id bigint);

DO $fix$
DECLARE
    v_soggetto_id       uuid;
    v_soggetto_ruolo_id bigint;
BEGIN
    v_soggetto_id       := dbops.fn_pgtap_crea_soggetto_pg('PGTAP Vettore Gen Codice');
    v_soggetto_ruolo_id := dbops.fn_pgtap_crea_soggetto_ruolo(v_soggetto_id, 'VT');
    INSERT INTO tmp_vet_ctx (soggetto_id, soggetto_ruolo_id)
    VALUES (v_soggetto_id, v_soggetto_ruolo_id);
END
$fix$;

-- ============================================================
-- 5) INSERT senza codice -> codice generato VET-NNNNNNN
--    Il pattern verifica anche il padding a 7 cifre: la lunghezza viene da
--    config.sistema_codici, non dal codice della funzione.
-- ============================================================
-- ⚠️ `descrizione` e' NOT NULL senza default: va valorizzata, altrimenti si
--   fallisce su un vincolo che non c'entra con il codice generato.
CREATE TEMP TABLE tmp_vet_creato AS
WITH ins AS (
    INSERT INTO anagrafiche.vettori (soggetto_ruolo_id, descrizione)
    SELECT soggetto_ruolo_id, 'PGTAP Vettore Gen Codice' FROM tmp_vet_ctx
    RETURNING id, codice
)
SELECT id, codice FROM ins;

SELECT ok(
    (SELECT codice ~ '^VET-[0-9]{7}$' FROM tmp_vet_creato),
    '5) INSERT senza codice -> codice generato con pattern VET-NNNNNNN'
);

-- ============================================================
-- 6) Il codice generato non e' modificabile
--    Il lock su anagrafiche.vettori.codice era gia' configurato in
--    dbops.automation_lock_columns da gennaio: fino a oggi presidiava una
--    colonna che nessuno generava. Da ora presidia un codice vero, e questa
--    asserzione lega le due cose.
-- ============================================================
SELECT throws_like(
    format(
        $$UPDATE anagrafiche.vettori SET codice = 'VET-9999999' WHERE id = %s$$,
        (SELECT id FROM tmp_vet_creato)
    ),
    '%Impossibile modificare il valore interno della colonna%',
    '6) il codice generato non e'' modificabile (CODICE_NON_MODIFICABILE)'
);

SELECT * FROM finish();
ROLLBACK;
