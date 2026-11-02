-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: framework dbops.fn_apply_chiusura_scadenze()
--       (migration 20260426-02-create-fn-apply-chiusura-scadenze).
--
-- Indice test (1..8):
--   1) Esecuzione col verbo (listini_versioni, FK sotto la porta): chiude
--      versione ATTIVA scaduta
--   2) Esecuzione col verbo (contratti, FK sotto la porta): chiude contratto
--      ATTIVO scaduto
--   3) Idempotenza: rerun della fn non chiude righe gia' chiuse (no-op)
--   4) Pre-check tabella inesistente -> raise E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA
--   5) Pre-check colonna inesistente -> raise
--   6) Pre-check codice FK inesistente -> raise
--   7) Testata sotto la porta senza verbo_chiusura -> raise
--   8) verbo_chiusura che non e' una funzione viva -> raise
--
-- rev 2026-10-28 (brief-modello-documento-vendita §16, giro 12): la versione di
--   listino ha lo stato nel vocabolario (stato_doc_listino_versione_id, FK) e la
--   porta; testate sotto la porta si chiudono col verbo dichiarato in
--   verbo_chiusura (20261028-05, -14). Test 1 e 2 dichiarano il verbo; 7 e 8
--   nuovi. ⚠️ Il ramo VARCHAR non ha piu' una testata configurata: lo coprono
--   solo i pre-check 4 e 5 (che falliscono prima dell'esecuzione).
--
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): il contratto nasce in
--   bozza e si porta avanti con dbops.fn_pgtap_porta_a_stato (prima nasceva
--   gia' ATTIVO).
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): il contratto nasce
--   da dbops.fn_pgtap_crea_contratto (madre di produzione) invece che da un
--   INSERT a mano; date 2022, listino scaduto e variazione si scrivono in bozza.
-- rev 2026-10-24 (brief-modello-documento-vendita R-2): il periodo 2022 e il
--   listino il contratto li prende dal builder; in bozza restano solo la
--   versione di listino e la variazione globale, che il builder non accetta.
--
-- Strategia fixture:
--   - Disattiva temporaneamente le righe seed di automazione_chiusura_scadenze
--     (UPDATE attivo=false; il rollback finale ripristina). Cosi' i test
--     controllano puntualmente la propria casistica senza interferenze.
--   - Per ogni test inserisce una riga config con id > 1000, esegue la fn,
--     verifica esito, poi delete (per evitare collisioni con pre-check
--     dei test successivi).
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

-- ⚠️ 2026-09-04: `dbops.automazione_chiusura_scadenze.classe` e' NOT NULL —
--   ogni bersaglio dichiara la propria natura (MANUTENZIONE|AMMINISTRAZIONE|
--   DOMINIO), perche' il framework legge le tabelle da questa configurazione e
--   una riga nuova ne cambierebbe la natura senza che nessuno se ne accorga.
--   Le fixture qui sotto usano DOMINIO: sono gli stessi bersagli del seed reale
--   (contratti e listini portano entrambi l'emittente).
SELECT plan(8);

-- Rimuove le righe seed durante il test per evitare conflitti con
-- l'UNIQUE su (schema_tabella, nome_tabella). Il ROLLBACK finale
-- ripristina lo stato originale del DB.
DELETE FROM dbops.automazione_chiusura_scadenze;

-- =============================================================
-- Setup: il mondo, il listino e il contratto — COSTRUITI
-- =============================================================
-- ⛔ 2026-09-23. Fino a oggi questo blocco CLONAVA: il listino da
--   «il primo listino esistente», il contratto da «il primo billing account
--   la cui utility non e' un'utenza». Su un database ricostruito `vendite` e
--   `anagrafiche` sono a zero, quindi le due INSERT ... SELECT inserivano
--   ZERO righe, le temp table restavano vuote e i due test rispondevano NULL:
--   il framework di chiusura non veniva esercitato affatto, e il file
--   sembrava misurare due righe di prodotto mentre misurava la presenza di
--   dati di questa macchina.
-- ⚠️ Il criterio del caso 2 — una utility che NON sia un'utenza — resta
--   quello di prima, ma diventa una precondizione COSTRUITA: si sceglie la
--   utility col criterio e ci si costruisce sopra il cliente.
CREATE TEMP TABLE tmp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('chiusura scadenze');

CREATE TEMP TABLE tmp_ctx_ba AS
SELECT c.billing_account_id, c.istanza_utility_id, c.utility_id
  FROM dbops.fn_pgtap_crea_cliente_ba(
           'chiusura scadenze',
           (SELECT u.id FROM config.utilities u
             WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu
                                WHERE tu.utility_id = u.id)
             ORDER BY u.id LIMIT 1)) c;

DO $pgtap$
BEGIN
    IF (SELECT utility_id IS NULL FROM tmp_ctx_ba) THEN
        RAISE EXCEPTION 'Seed mancante: nessuna utility senza tipi_utenze in config.utilities';
    END IF;
END
$pgtap$;

-- Listino con versione ATTIVA scaduta (da chiudere dal framework).
-- ⭐ rev 2026-09-23 (20260923-50): le due INSERT scritte qui erano la prima
--   copia della ricetta; alla seconda (script/test-fn-available-actions-
--   offerta-v1) e' nato dbops.fn_pgtap_crea_listino, e questa copia si
--   ritira nello stesso giro (regola del 2). La tipologia non e' piu' «la
--   prima per id» ma la prima AMMESSA per l'utility.
CREATE TEMP TABLE tmp_listino AS
SELECT listino_id, listino_versione_id
  FROM dbops.fn_pgtap_crea_listino(
           (SELECT utility_id FROM tmp_ctx_ba),
           'framework chiusura',
           DATE '2022-01-01', DATE '2022-12-31');

-- Contratto in modalita' A (listino + variazione globale): la modalita' C
-- pretenderebbe righe in contratti_righe con prezzo_unitario.
-- rev 2026-10-24: nasce in DRAFT (trigger della nascita) e si attiva per la
--   matrice. La versione di listino si FISSA in bozza: quella del 2022 non
--   e' in vigore oggi, e senza una versione operativa il contratto non si
--   attiva (fn_check_listino_congelabile).
-- ⭐ rev 2026-10-24 (Q-2/Q-4): la nascita la fa il builder, dalla madre di
--   produzione, sul cliente del caso 2.
-- rev 2026-10-24 (R-2): il contratto nasce DRAFT col periodo 2022 e il
--   listino scaduto dal builder. Resta del test, in bozza prima del
--   passaggio, cio' che il builder non accetta: la versione di listino (non
--   in vigore oggi) e la variazione globale (modalita' A). Poi la matrice.
CREATE TEMP TABLE tmp_contratto AS
SELECT * FROM dbops.fn_pgtap_crea_contratto(
                 'chiusura scadenze', 'DRAFT', (SELECT billing_account_id FROM tmp_ctx_ba), NULL,
                 DATE '2022-01-01', DATE '2022-12-31', NULL,
                 (SELECT listino_id FROM tmp_listino));

UPDATE vendite.contratti c
   SET listino_versione_id = l.listino_versione_id,
       tipo_variazione_globale  = 'PERCENTUALE',
       valore_variazione_globale = -10
  FROM tmp_listino l
 WHERE c.id = (SELECT contratto_id FROM tmp_contratto);

SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti', t.contratto_id, 'ATTIVO')
  FROM tmp_contratto t;

-- =============================================================
-- 1) Esecuzione VARCHAR: chiude versione listino scaduta
-- =============================================================
INSERT INTO dbops.automazione_chiusura_scadenze (
    id, schema_tabella, nome_tabella, col_stato, tipo_stato,
    col_valido_al, stato_attivo_codice, stato_chiuso_codice,
    fk_lookup_schema, fk_lookup_table, fk_lookup_codice_col, fk_lookup_id_col,
    attivo, descrizione, classe, verbo_chiusura
) VALUES (
    1001, 'vendite', 'listini_versioni', 'stato_doc_listino_versione_id', 'FK',
    'valido_al', 'ATTIVA', 'CHIUSA',
    'config', 'stati_doc_listino_versioni', 'codice_interno', 'id',
    true, 'pgtap test 1', 'DOMINIO', 'vendite.fn_chiudi_versioni_listino_scadute'
);

-- Esegui il framework.
DO $$ BEGIN PERFORM dbops.fn_apply_chiusura_scadenze(); END $$;

SELECT is(
    (SELECT s.codice_interno
       FROM vendite.listini_versioni lv
       JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
      WHERE lv.id = (SELECT listino_versione_id FROM tmp_listino)),
    'CHIUSA'::varchar,
    'Framework col verbo: versione listino scaduta passa a CHIUSA'
);

-- Disattiva la riga di config per test 2 (no double processing).
UPDATE dbops.automazione_chiusura_scadenze SET attivo = false WHERE id = 1001;

-- =============================================================
-- 2) Esecuzione FK: chiude contratto scaduto via lookup codice_interno
-- =============================================================
INSERT INTO dbops.automazione_chiusura_scadenze (
    id, schema_tabella, nome_tabella, col_stato, tipo_stato,
    col_valido_al, stato_attivo_codice, stato_chiuso_codice,
    fk_lookup_schema, fk_lookup_table, fk_lookup_codice_col, fk_lookup_id_col,
    attivo, descrizione, classe, verbo_chiusura
) VALUES (
    1002, 'vendite', 'contratti', 'stato_doc_contratto_id', 'FK',
    'valido_al', 'ATTIVO', 'CESSATO',
    'config', 'stati_doc_contratti', 'codice_interno', 'id',
    true, 'pgtap test 2', 'DOMINIO', 'vendite.fn_cessa_contratti_scaduti'
);

DO $$ BEGIN PERFORM dbops.fn_apply_chiusura_scadenze(); END $$;

SELECT is(
    (SELECT sd.codice_interno
       FROM vendite.contratti c
       JOIN config.stati_doc_contratti sd ON sd.id = c.stato_doc_contratto_id
      WHERE c.id = (SELECT contratto_id FROM tmp_contratto)),
    'CESSATO'::varchar,
    'Framework col verbo: contratto scaduto passa a CESSATO'
);

-- =============================================================
-- 3) Idempotenza: rerun non tocca righe gia' chiuse
-- =============================================================
-- Riattiva la riga test 1 per il rerun (test 2 e' gia' attiva).
UPDATE dbops.automazione_chiusura_scadenze SET attivo = true WHERE id = 1001;

DO $$
DECLARE
    v_result jsonb;
BEGIN
    v_result := dbops.fn_apply_chiusura_scadenze();
    -- Rerun deve dare 0 righe chiuse per entrambi (idempotente).
    IF (v_result->>'_total')::integer <> 0 THEN
        RAISE EXCEPTION 'rerun non idempotente: total=%', v_result->>'_total';
    END IF;
END $$;

SELECT pass('Framework e'' idempotente: rerun non tocca righe gia'' chiuse');

-- Cleanup righe config per test pre-check.
DELETE FROM dbops.automazione_chiusura_scadenze WHERE id IN (1001, 1002);

-- =============================================================
-- 4) Pre-check tabella inesistente -> raise
-- =============================================================
INSERT INTO dbops.automazione_chiusura_scadenze (
    id, schema_tabella, nome_tabella, col_stato, tipo_stato,
    col_valido_al, stato_attivo_codice, stato_chiuso_codice,
    attivo, descrizione, classe
) VALUES (
    1003, 'vendite', 'tabella_che_non_esiste_pgtap', 'stato', 'VARCHAR',
    'valido_al', 'ATTIVA', 'CHIUSA',
    true, 'pgtap test 4', 'DOMINIO'
);

SELECT throws_ok(
    $$SELECT dbops.fn_apply_chiusura_scadenze()$$,
    'P0001',
    NULL,
    'Pre-check tabella inesistente solleva E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA'
);

DELETE FROM dbops.automazione_chiusura_scadenze WHERE id = 1003;

-- =============================================================
-- 5) Pre-check colonna inesistente -> raise
-- =============================================================
INSERT INTO dbops.automazione_chiusura_scadenze (
    id, schema_tabella, nome_tabella, col_stato, tipo_stato,
    col_valido_al, stato_attivo_codice, stato_chiuso_codice,
    attivo, descrizione, classe
) VALUES (
    1004, 'vendite', 'listini_versioni', 'colonna_inesistente_pgtap', 'VARCHAR',
    'valido_al', 'ATTIVA', 'CHIUSA',
    true, 'pgtap test 5', 'DOMINIO'
);

SELECT throws_ok(
    $$SELECT dbops.fn_apply_chiusura_scadenze()$$,
    'P0001',
    NULL,
    'Pre-check colonna inesistente solleva E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA'
);

DELETE FROM dbops.automazione_chiusura_scadenze WHERE id = 1004;

-- =============================================================
-- 6) Pre-check codice FK inesistente -> raise
-- =============================================================
INSERT INTO dbops.automazione_chiusura_scadenze (
    id, schema_tabella, nome_tabella, col_stato, tipo_stato,
    col_valido_al, stato_attivo_codice, stato_chiuso_codice,
    fk_lookup_schema, fk_lookup_table, fk_lookup_codice_col, fk_lookup_id_col,
    attivo, descrizione, classe
) VALUES (
    1005, 'vendite', 'contratti', 'stato_doc_contratto_id', 'FK',
    'valido_al', 'CODICE_INESISTENTE_PGTAP', 'CESSATO',
    'config', 'stati_doc_contratti', 'codice_interno', 'id',
    true, 'pgtap test 6', 'DOMINIO'
);

SELECT throws_ok(
    $$SELECT dbops.fn_apply_chiusura_scadenze()$$,
    'P0001',
    NULL,
    'Pre-check codice FK attivo inesistente solleva E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA'
);

DELETE FROM dbops.automazione_chiusura_scadenze WHERE id = 1005;

-- =============================================================
-- 7) Testata sotto la porta senza verbo -> raise
-- =============================================================
INSERT INTO dbops.automazione_chiusura_scadenze (
    id, schema_tabella, nome_tabella, col_stato, tipo_stato,
    col_valido_al, stato_attivo_codice, stato_chiuso_codice,
    fk_lookup_schema, fk_lookup_table, fk_lookup_codice_col, fk_lookup_id_col,
    attivo, descrizione, classe
) VALUES (
    1006, 'vendite', 'listini_versioni', 'stato_doc_listino_versione_id', 'FK',
    'valido_al', 'ATTIVA', 'CHIUSA',
    'config', 'stati_doc_listino_versioni', 'codice_interno', 'id',
    true, 'pgtap test 7', 'DOMINIO'
);

SELECT throws_like(
    $$SELECT dbops.fn_apply_chiusura_scadenze()$$,
    '%non ha il verbo di chiusura%',
    'Testata sotto la porta senza verbo_chiusura: E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA'
);

-- =============================================================
-- 8) verbo_chiusura che non e' una funzione viva -> raise
-- =============================================================
UPDATE dbops.automazione_chiusura_scadenze
   SET verbo_chiusura = 'vendite.fn_pgtap_verbo_che_non_esiste'
 WHERE id = 1006;

SELECT throws_like(
    $$SELECT dbops.fn_apply_chiusura_scadenze()$$,
    '%non e'' una funzione senza argomenti%',
    'verbo_chiusura che non esiste: E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA'
);

SELECT * FROM finish();
ROLLBACK;
