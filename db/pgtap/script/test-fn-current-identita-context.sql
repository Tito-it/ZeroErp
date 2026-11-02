-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgTAP test per Zero ERP
--
-- Test: script.fn_current_identita_context
-- Riferimento: §4.7.2 WIP multi-face-auth.
--
-- Semantica attesa:
--   - Nessun GUC settato -> tutte le colonne NULL (fail-soft)
--   - GUC settati -> valori tipizzati e correttamente parseati
--   - GUC parzialmente settati -> le colonne mancanti restano NULL
--   - Stringhe vuote -> NULL (NULLIF attivo)
--
-- Indice test (1..6):
--    1. Nessun GUC settato -> 3 NULL
--    2. Tutti e 3 i GUC settati -> valori corretti
--    3. Solo current_identita_id settato -> solo quel campo valorizzato
--    4. Solo ruolo_applicativo settato -> solo quel campo valorizzato
--    5. Valori vuoti -> NULL (NULLIF comportamento atteso)
--    6. Cast tipo enum fallirebbe con valore invalido (skip: comportamento
--       atteso documentato, non testato qui)
--
-- NOTA: SET LOCAL + rollback implicito a fine transazione. NON serve
-- RESET esplicito: il ROLLBACK finale resetta tutti i SET LOCAL.
--
-- BEGIN; + rollback implicito a fine file.
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

-- ⚠️ QUESTO FILE NON USA script.fn_pgtap_set_contesto_operatore(), a differenza
-- degli altri, e non e' una dimenticanza.
-- Qui il contesto non e' lo sfondo: e' il soggetto. Il test imposta e azzera le
-- GUC da se' (SET LOCAL piu' sotto) e verifica cosa la funzione legge in ogni
-- combinazione — a partire dall'asserzione 1, «nessuna GUC settata -> tutte le
-- colonne NULL». Impostare un contesto in testa distruggerebbe la premessa
-- della prima asserzione prima ancora di cominciare.
-- Misurato: con la riga, 7 asserzioni diventano 6 verdi + 1 rossa.
-- Brief: brief-db-pgtap-runner-rls-baseline §11.

SELECT plan(7);
-- =========================================================
-- 1) Nessun GUC settato -> 3 NULL
-- =========================================================
-- Assumiamo che i 3 GUC non siano mai stati settati in questa sessione.
-- current_setting con missing_ok=true ritorna ''; NULLIF('','') = NULL.
SELECT ok(
        (
            SELECT current_identita_id IS NULL
                AND ruolo_applicativo IS NULL
                AND soggetto_ruolo_id IS NULL
            FROM script.fn_current_identita_context()
        ),
        '1. Nessun GUC settato -> tutte le colonne NULL (fail-soft)'
    );
-- =========================================================
-- 2) Tutti e 3 i GUC settati -> valori correttamente tipizzati
-- =========================================================
SET LOCAL app.current_identita_id = '42';
SET LOCAL app.ruolo_applicativo = 'OPERATORE';
SET LOCAL app.soggetto_ruolo_id = '123';
SELECT is(
        (
            SELECT current_identita_id
            FROM script.fn_current_identita_context()
        ),
        42::bigint,
        '2a. current_identita_id = 42 (bigint)'
    );
SELECT ok(
        (
            SELECT ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
            FROM script.fn_current_identita_context()
        ),
        '2b. ruolo_applicativo = OPERATORE (config.ruolo_applicativo)'
    );
-- =========================================================
-- 3) Solo current_identita_id settato -> solo quel campo valorizzato
-- =========================================================
-- Reset parziale: il SET LOCAL precedente resta attivo nella transazione.
-- Per simulare "solo 1 GUC" uso SET LOCAL a stringa vuota (simula unset).
SET LOCAL app.ruolo_applicativo = '';
SET LOCAL app.soggetto_ruolo_id = '';
SELECT ok(
        (
            SELECT current_identita_id = 42::bigint
                AND ruolo_applicativo IS NULL
                AND soggetto_ruolo_id IS NULL
            FROM script.fn_current_identita_context()
        ),
        '3. Solo current_identita_id settato, gli altri (vuoti) -> NULL'
    );
-- =========================================================
-- 4) Solo ruolo_applicativo settato
-- =========================================================
SET LOCAL app.current_identita_id = '';
SET LOCAL app.ruolo_applicativo = 'CLIENTE_PORTALE';
SET LOCAL app.soggetto_ruolo_id = '';
SELECT ok(
        (
            SELECT current_identita_id IS NULL
                AND ruolo_applicativo = 'CLIENTE_PORTALE'::config.ruolo_applicativo
                AND soggetto_ruolo_id IS NULL
            FROM script.fn_current_identita_context()
        ),
        '4. Solo ruolo_applicativo settato -> altri NULL'
    );
-- =========================================================
-- 5) Stringhe vuote su tutti -> 3 NULL (consolida NULLIF)
-- =========================================================
SET LOCAL app.current_identita_id = '';
SET LOCAL app.ruolo_applicativo = '';
SET LOCAL app.soggetto_ruolo_id = '';
SELECT ok(
        (
            SELECT current_identita_id IS NULL
                AND ruolo_applicativo IS NULL
                AND soggetto_ruolo_id IS NULL
            FROM script.fn_current_identita_context()
        ),
        '5. GUC tutti a stringa vuota -> NULLIF consolida a NULL'
    );
-- =========================================================
-- 6) Valori bigint parseabili + enum valido insieme
-- =========================================================
SET LOCAL app.current_identita_id = '9999';
SET LOCAL app.ruolo_applicativo = 'FORNITORE_PORTALE';
SET LOCAL app.soggetto_ruolo_id = '777';
SELECT ok(
        (
            SELECT current_identita_id = 9999::bigint
                AND ruolo_applicativo = 'FORNITORE_PORTALE'::config.ruolo_applicativo
                AND soggetto_ruolo_id = 777::bigint
            FROM script.fn_current_identita_context()
        ),
        '6. Tutti i 3 GUC settati con valori diversi -> tipizzati correttamente'
    );
SELECT *
FROM finish();
ROLLBACK;