-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Trigger: dbops.trgfn_prevent_deactivate_if_children
-- Caso: config.stati_pdp (padre) -> anagrafiche.pdp (figlio con attivo)
--
-- ⭐ Questo file e' il TESTIMONE DEL RAMO A del guard: la tabella figlia ha la
--    colonna `attivo`, quindi bloccano solo le righe ATTIVE e il rimedio e'
--    disattivarle. Dal 20260820-08 quel ramo ha un codice suo,
--    E_ATTIVO_BLOCK_CHILDREN_ACTIVE (934). Il ramo B — figlia senza colonna
--    attivo, blocca qualunque riga, rimedio toglierle, codice 125 — e'
--    presidiato da db/pgtap/vendite/test-registri-per-emittente-v1.sql (test 6).
--    Misura del 2026-08-20: 168 trigger nel ramo A, 181 nel B.
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. In testa e non in coda apposta:
--   in coda scatterebbero tutti insieme DOPO il cleanup, su righe ormai
--   cancellate. Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(13);

CREATE TEMP TABLE tmp_test_keys AS
SELECT '*$*' AS ts;

-- =========================================================
-- 0) Verifica presenza trigger BLOCK su stati_pdp
-- =========================================================
CREATE TEMP TABLE tmp_trg_block AS
SELECT EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'config'
      AND c.relname = 'stati_pdp'
      AND t.tgname ILIKE '%block_deact%'
      AND NOT t.tgisinternal
) AS has_trg;

SELECT ok(
    (SELECT has_trg FROM tmp_trg_block),
    'Trigger BLOCK presente su config.stati_pdp'
);

-- =========================================================
-- 1) Crea stato_pdp di test
-- =========================================================
WITH ins AS (
    INSERT INTO config.stati_pdp (codice_interno, codice, descrizione, attivo)
    VALUES (
        'TST_PDP_' || (SELECT ts FROM tmp_test_keys),
        'TST_PDP_' || (SELECT ts FROM tmp_test_keys),
        'Stato PDP test trgfn_prevent_deactivate_if_children',
        true
    )
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_stato_pdp
FROM ins;

SELECT ok(
    (SELECT count(*) FROM tmp_stato_pdp) = 1,
    'Creato stato_pdp di test'
);

-- =========================================================
-- 2) Disattivazione senza figli: deve passare
-- =========================================================
SELECT lives_ok(
    $$
    UPDATE config.stati_pdp
    SET attivo = false
    WHERE id = (SELECT id FROM tmp_stato_pdp);
    $$,
    'Disattivazione stato_pdp senza figli: OK'
);

SELECT is(
    (SELECT attivo FROM config.stati_pdp WHERE id = (SELECT id FROM tmp_stato_pdp)),
    false,
    'stato_pdp disattivato quando non ci sono figli'
);

-- Riattiva per il test con figlio
SELECT lives_ok(
    $$
    UPDATE config.stati_pdp
    SET attivo = true
    WHERE id = (SELECT id FROM tmp_stato_pdp);
    $$,
    'Riattivazione stato_pdp per test con figlio'
);

-- =========================================================
-- 3) Inserimento PDP figlio (se prerequisiti presenti)
-- =========================================================
-- ⚠️ L'indirizzo si FABBRICA (rev 2026-09-15). anagrafiche.indirizzi_dettaglio
--   e' dato di macchina: su un database ricostruito da zero non ce n'e' nessuno,
--   e con `SELECT … LIMIT 1` il test 6 era rosso e i test 7-12 «skipped» — il
--   testimone del ramo A non eseguiva NIENTE. Su GitHub passava per un
--   indirizzo lasciato da qualcun altro prima nella suite; su zeroerp_ci con la
--   sola cartella dbops no. config.utilities e' seed di catalogo: si puo' cercare.
CREATE TEMP TABLE tmp_pdp_base AS
SELECT
    (SELECT id FROM config.utilities ORDER BY id LIMIT 1) AS utility_id,
    dbops.fn_pgtap_crea_indirizzo_dettaglio('pdp block_deact') AS indirizzo_id;

SELECT ok(
    (SELECT utility_id IS NOT NULL AND indirizzo_id IS NOT NULL FROM tmp_pdp_base),
    'Prerequisiti presenti per inserimento PDP'
);

SELECT CASE
    WHEN (SELECT utility_id IS NOT NULL AND indirizzo_id IS NOT NULL FROM tmp_pdp_base) THEN
        lives_ok(
            $$
            INSERT INTO anagrafiche.pdp (pdp, utility_id, indirizzo_dettaglio_id, stato_pdp_id)
            SELECT
                'PDP-TST-BLOCK-' || (SELECT ts FROM tmp_test_keys),
                utility_id,
                indirizzo_id,
                (SELECT id FROM tmp_stato_pdp)
            FROM tmp_pdp_base;
            $$,
            'Inserito PDP figlio di test'
        )
    ELSE
        ok(true, 'Prerequisiti mancanti: inserimento PDP skipped')
END;

CREATE TEMP TABLE tmp_pdp_child AS
SELECT id
FROM anagrafiche.pdp
WHERE stato_pdp_id = (SELECT id FROM tmp_stato_pdp)
ORDER BY id
LIMIT 1;

-- =========================================================
-- 4) Disattivazione con figlio: deve fallire
-- =========================================================
-- ⭐ rev 2026-08-20 — il discriminante non e' piu' «un errore qualsiasi».
--    Prima era throws_ok(..., NULL, NULL, ...), che accetta QUALUNQUE
--    eccezione: sarebbe passato anche se a fallire fosse stato un permesso,
--    una FK o il guard sbagliato. Ora si asserisce la FRASE, e quella frase
--    dice due cose che prima non erano verificate da nessuno:
--      · «attive» -> il guard ha preso il ramo giusto. anagrafiche.pdp HA la
--        colonna attivo, quindi deve sollevare E_ATTIVO_BLOCK_CHILDREN_ACTIVE
--        (934) e non E_ATTIVO_BLOCK_CHILDREN_EXIST (125). Sono due codici
--        perche' i rimedi sono diversi: qui si DISATTIVANO le righe figlie
--        (ed e' esattamente quello che fa il test 5 qui sotto), nell'altro
--        ramo si TOLGONO;
--      · la frase non nomina tabelle (brief-db-revisione-dbops, S-BE-1):
--        padre e figlia stanno nel contesto del diario, e la frase e' quella
--        del catalogo per il ramo ATTIVE.
SELECT CASE
    WHEN (SELECT utility_id IS NOT NULL AND indirizzo_id IS NOT NULL FROM tmp_pdp_base) THEN
        throws_like(
            $$
            UPDATE config.stati_pdp
            SET attivo = false
            WHERE id = (SELECT id FROM tmp_stato_pdp);
            $$,
            '%ci sono ancora righe collegate attive.',
            'Disattivazione stato_pdp con figli: bloccata, col messaggio del ramo ATTIVE'
        )
    ELSE
        ok(true, 'Prerequisiti mancanti: test blocco skipped')
END;

-- =========================================================
-- 5) Disattivazione figlio e blocco sbloccato sul padre
-- =========================================================
SELECT CASE
    WHEN (SELECT count(*) FROM tmp_pdp_child) = 1 THEN
        lives_ok(
            $$
            UPDATE anagrafiche.pdp
            SET attivo = false
            WHERE id = (SELECT id FROM tmp_pdp_child);
            $$,
            'Disattivazione PDP figlio: OK'
        )
    ELSE
        ok(true, 'PDP figlio non presente: test disattivazione figlio skipped')
END;

SELECT CASE
    WHEN (SELECT count(*) FROM tmp_pdp_child) = 1 THEN
        is(
            (SELECT attivo FROM anagrafiche.pdp WHERE id = (SELECT id FROM tmp_pdp_child)),
            false,
            'PDP figlio disattivato'
        )
    ELSE
        ok(true, 'PDP figlio non presente: check attivo skipped')
END;

SELECT CASE
    WHEN (SELECT count(*) FROM tmp_pdp_child) = 1 THEN
        lives_ok(
            $$
            UPDATE config.stati_pdp
            SET attivo = false
            WHERE id = (SELECT id FROM tmp_stato_pdp);
            $$,
            'Disattivazione stato_pdp con figli disattivi: OK'
        )
    ELSE
        ok(true, 'PDP figlio non presente: test disattivazione padre skipped')
END;

SELECT CASE
    WHEN (SELECT count(*) FROM tmp_pdp_child) = 1 THEN
        is(
            (SELECT attivo FROM config.stati_pdp WHERE id = (SELECT id FROM tmp_stato_pdp)),
            false,
            'stato_pdp disattivato con figli disattivi'
        )
    ELSE
        ok(true, 'PDP figlio non presente: check attivo padre skipped')
END;

-- =========================================================
-- 13) ⛔ I DUE MESSAGGI CONDIVIDONO UNA SOLA LISTA DI VALORI.
--     La funzione sceglie fra due codici, ma li solleva con la STESSA
--     chiamata e quindi con gli STESSI valori: oggi nessuno (variadico vuoto),
--     perche' le due frasi non nominano tabelle. Se uno dei due messaggi
--     avesse piu' segnaposti dei valori passati, format() farebbe sparire
--     l'errore di dominio in un errore tecnico — cioe' il guard smetterebbe
--     di dire perche' ha bloccato, proprio mentre blocca.
--     ⚠️ Si asserisce la COPPIA e non «sono uguali»: un confronto fra due
--     valori resta vero anche se una delle due righe non esiste piu'.
-- =========================================================
SELECT is(
    (SELECT string_agg(
              ((length(m.messaggio) - length(replace(m.messaggio, '%s', ''))) / 2)::text,
              '|' ORDER BY m.codice)
       FROM config.messaggi_errore m
      WHERE m.codice IN ('E_ATTIVO_BLOCK_CHILDREN_ACTIVE', 'E_ATTIVO_BLOCK_CHILDREN_EXIST')
        AND m.lingua = 'it'),
    '0|0',
    '13) i due codici del guard hanno lo stesso numero di segnaposti (zero, come i valori che il guard passa)'
);

-- Cleanup
DELETE FROM anagrafiche.pdp
WHERE stato_pdp_id = (SELECT id FROM tmp_stato_pdp);

DELETE FROM config.stati_pdp
WHERE id = (SELECT id FROM tmp_stato_pdp);

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
