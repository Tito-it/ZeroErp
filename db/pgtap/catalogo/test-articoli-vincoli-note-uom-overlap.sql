-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Schema: catalogo
-- Ambito: vincoli articoli, note, uom operativa, overlap componenti
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

SELECT plan(20);

CREATE TEMP TABLE tmp_test_keys AS
SELECT to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS') AS ts;

CREATE TEMP TABLE tmp_ids AS
SELECT
    COALESCE((SELECT MAX(id) FROM catalogo.unita_misura), 0) + 1000 AS uom_base_id,
    COALESCE((SELECT MAX(id) FROM catalogo.unita_misura), 0) + 1001 AS uom_alt_id;

CREATE TEMP TABLE tmp_fk_refs AS
SELECT
    (SELECT id FROM vendite.articoli_gruppi WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS gruppo_id,
    (SELECT id FROM vendite.articoli_tipologie WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_id,
    (SELECT id FROM vendite.articoli_spesa WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS spesa_id,
    (SELECT id FROM config.iva WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS iva_id,
    (SELECT id FROM config.lingue WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS lingua_id;

CREATE TEMP TABLE tmp_can_run AS
SELECT (
    (SELECT gruppo_id IS NOT NULL FROM tmp_fk_refs)
    AND (SELECT tipo_id IS NOT NULL FROM tmp_fk_refs)
    AND (SELECT spesa_id IS NOT NULL FROM tmp_fk_refs)
    AND (SELECT iva_id IS NOT NULL FROM tmp_fk_refs)
    AND (SELECT lingua_id IS NOT NULL FROM tmp_fk_refs)
) AS can_run;

SELECT diag(
    format(
        'Ref base: gruppo=%s tipologia=%s spesa=%s iva=%s lingua=%s (can_run=%s)',
        COALESCE((SELECT gruppo_id::text FROM tmp_fk_refs), 'NULL'),
        COALESCE((SELECT tipo_id::text FROM tmp_fk_refs), 'NULL'),
        COALESCE((SELECT spesa_id::text FROM tmp_fk_refs), 'NULL'),
        COALESCE((SELECT iva_id::text FROM tmp_fk_refs), 'NULL'),
        COALESCE((SELECT lingua_id::text FROM tmp_fk_refs), 'NULL'),
        CASE WHEN (SELECT can_run FROM tmp_can_run) THEN 'true' ELSE 'false' END
    )
);

SELECT CASE
    WHEN (SELECT gruppo_id IS NOT NULL FROM tmp_fk_refs)
    THEN ok(true, 'Riferimento vendite.articoli_gruppi disponibile')
    ELSE ok(true, 'Riferimento vendite.articoli_gruppi mancante: test dipendenti skipped')
END;

SELECT CASE
    WHEN (SELECT tipo_id IS NOT NULL FROM tmp_fk_refs)
    THEN ok(true, 'Riferimento vendite.articoli_tipologie disponibile')
    ELSE ok(true, 'Riferimento vendite.articoli_tipologie mancante: test dipendenti skipped')
END;

SELECT CASE
    WHEN (SELECT spesa_id IS NOT NULL FROM tmp_fk_refs)
    THEN ok(true, 'Riferimento vendite.articoli_spesa disponibile')
    ELSE ok(true, 'Riferimento vendite.articoli_spesa mancante: test dipendenti skipped')
END;

SELECT CASE
    WHEN (SELECT iva_id IS NOT NULL FROM tmp_fk_refs)
    THEN ok(true, 'Riferimento config.iva disponibile')
    ELSE ok(true, 'Riferimento config.iva mancante: test dipendenti skipped')
END;

SELECT CASE
    WHEN (SELECT lingua_id IS NOT NULL FROM tmp_fk_refs)
    THEN ok(true, 'Riferimento config.lingue disponibile')
    ELSE ok(true, 'Riferimento config.lingue mancante: test dipendenti skipped')
END;

CREATE TEMP TABLE tmp_uom_base (id bigint);
CREATE TEMP TABLE tmp_uom_alt (id bigint);
CREATE TEMP TABLE tmp_note_stile (id bigint);
CREATE TEMP TABLE tmp_art_base (id uuid);
CREATE TEMP TABLE tmp_art_comp (id uuid);
CREATE TEMP TABLE tmp_note (id bigint);
CREATE TEMP TABLE tmp_uom_op_base (id bigint);
CREATE TEMP TABLE tmp_art_comp_rel (id uuid);

-- =========================================================
-- 1) Inserimento unita' di misura di test
-- =========================================================
DO $$
DECLARE
  v_id bigint;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    INSERT INTO catalogo.unita_misura (
        id,
        codice,
        descrizione,
        descrizione_fattura,
        tipo_uom_id,
        attivo
    )
    VALUES (
        (SELECT uom_base_id FROM tmp_ids),
        (SELECT 'UTB' || right(ts, 6) FROM tmp_test_keys),
        'UNITA TEST BASE',
        'UNITA TEST BASE',
        (SELECT id FROM catalogo.uom_tipi WHERE codice = 'QUANTITA'),
        true
    )
    RETURNING id INTO v_id;

    INSERT INTO tmp_uom_base (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_uom_base) = 1, 'Inserita unita_misura base di test')
    ELSE ok(true, 'Inserimento unita_misura base skipped: riferimenti mancanti')
END;

DO $$
DECLARE
  v_id bigint;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    INSERT INTO catalogo.unita_misura (
        id,
        codice,
        descrizione,
        descrizione_fattura,
        tipo_uom_id,
        attivo
    )
    VALUES (
        (SELECT uom_alt_id FROM tmp_ids),
        (SELECT 'UTA' || right(ts, 6) FROM tmp_test_keys),
        'UNITA TEST ALT',
        'UNITA TEST ALT',
        (SELECT id FROM catalogo.uom_tipi WHERE codice = 'QUANTITA'),
        true
    )
    RETURNING id INTO v_id;

    INSERT INTO tmp_uom_alt (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_uom_alt) = 1, 'Inserita unita_misura alternativa di test')
    ELSE ok(true, 'Inserimento unita_misura alternativa skipped: riferimenti mancanti')
END;

-- =========================================================
-- 2) Stile nota di test
-- =========================================================
DO $$
DECLARE
  v_id bigint;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    INSERT INTO config.note_stili (
        codice,
        codice_interno,
        descrizione,
        attivo
    )
    VALUES (
        (SELECT 'NST' || right(ts, 6) FROM tmp_test_keys),
        (SELECT 'NSTI' || right(ts, 6) FROM tmp_test_keys),
        (SELECT 'STILE TEST ' || ts FROM tmp_test_keys),
        true
    )
    RETURNING id INTO v_id;

    INSERT INTO tmp_note_stile (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_note_stile) = 1, 'Creato note_stili di test')
    ELSE ok(true, 'Creazione note_stili skipped: riferimenti mancanti')
END;

-- =========================================================
-- 3) Articoli di test
-- =========================================================
DO $$
DECLARE
  v_id uuid;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    INSERT INTO catalogo.articoli (
        codice,
        descrizione,
        uom_id,
        tipo_voce_id,
        gruppo_voce_id,
        spesa_id,
        iva_id
    )
    VALUES (
        (SELECT 'ART' || right(ts, 6) FROM tmp_test_keys),
        (SELECT 'ARTICOLO TEST BASE ' || ts FROM tmp_test_keys),
        (SELECT uom_base_id FROM tmp_ids),
        (SELECT tipo_id FROM tmp_fk_refs),
        (SELECT gruppo_id FROM tmp_fk_refs),
        (SELECT spesa_id FROM tmp_fk_refs),
        (SELECT iva_id FROM tmp_fk_refs)
    )
    RETURNING id INTO v_id;

    INSERT INTO tmp_art_base (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_art_base) = 1, 'Creato articolo base di test')
    ELSE ok(true, 'Creazione articolo base skipped: riferimenti mancanti')
END;

DO $$
DECLARE
  v_id uuid;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    INSERT INTO catalogo.articoli (
        codice,
        descrizione,
        uom_id,
        tipo_voce_id,
        gruppo_voce_id,
        spesa_id,
        iva_id
    )
    VALUES (
        (SELECT 'ARC' || right(ts, 6) FROM tmp_test_keys),
        (SELECT 'ARTICOLO TEST COMP ' || ts FROM tmp_test_keys),
        (SELECT uom_base_id FROM tmp_ids),
        (SELECT tipo_id FROM tmp_fk_refs),
        (SELECT gruppo_id FROM tmp_fk_refs),
        (SELECT spesa_id FROM tmp_fk_refs),
        (SELECT iva_id FROM tmp_fk_refs)
    )
    RETURNING id INTO v_id;

    INSERT INTO tmp_art_comp (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_art_comp) = 1, 'Creato articolo componente di test')
    ELSE ok(true, 'Creazione articolo componente skipped: riferimenti mancanti')
END;

-- 🔴 REV 2026-09-20 — QUESTA ASSERZIONE ERA VERDE PER UN ERRORE CHE NON ERA IL SUO.
--   Due difetti in una riga sola: il codice «duplicato» era 'ART…' mentre
--   l'articolo creato sopra e' 'ARC…' — quindi non duplicava niente — e l'INSERT
--   ometteva `uom_id`, che e' NOT NULL, per cui la riga moriva su 23502
--   («valore nullo nella colonna uom_id») e `uq_articoli_codice` non veniva mai
--   raggiunto. Il test passava per una ragione diversa da quella che dichiarava.
--   Trovato con la sonda del discriminante impossibile ('ZZZZZ'): pgTAP stampa
--   lo SQLSTATE vero invece di accettare qualunque errore. Vedi D11 di
--   migliorie-generali-da-test-valutazione.md. Ora l'INSERT e' identico a quello
--   che riesce (stesse FK, stesso uom_id), salvo il codice: l'unica cosa che
--   questa riga puo' violare e' l'unique.
SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN throws_ok(
        $$
        INSERT INTO catalogo.articoli (
            codice,
            descrizione,
            uom_id,
            tipo_voce_id,
            gruppo_voce_id,
            spesa_id,
            iva_id
        )
        VALUES (
            (SELECT 'ARC' || right(ts, 6) FROM tmp_test_keys),
            'ARTICOLO DUPLICATO',
            (SELECT uom_base_id FROM tmp_ids),
            (SELECT tipo_id FROM tmp_fk_refs),
            (SELECT gruppo_id FROM tmp_fk_refs),
            (SELECT spesa_id FROM tmp_fk_refs),
            (SELECT iva_id FROM tmp_fk_refs)
        );
        $$,
        '23505',
        NULL,
        'Codice articolo duplicato: bloccato'
    )
    ELSE ok(true, 'Test duplicato codice skipped: riferimenti mancanti')
END;

-- =========================================================
-- 4) Note articolo
-- =========================================================
DO $$
DECLARE
  v_id bigint;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    INSERT INTO catalogo.note (
        target_tipo,
        target_id,
        anchor_tipo,
        posizione,
        seq,
        testo,
        id_stile,
        id_lingua
    )
    VALUES (
        'ARTICOLO',
        (SELECT id FROM tmp_art_base),
        'DOCUMENTO',
        'HEADER',
        10,
        (SELECT 'NOTA TEST ' || ts FROM tmp_test_keys),
        (SELECT id FROM tmp_note_stile),
        (SELECT lingua_id FROM tmp_fk_refs)
    )
    RETURNING id INTO v_id;

    INSERT INTO tmp_note (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_note) = 1, 'Creata nota per articolo')
    ELSE ok(true, 'Creazione nota skipped: riferimenti mancanti')
END;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN lives_ok(
        $$
        UPDATE catalogo.articoli
        SET note_target_tipo = 'ARTICOLO',
            note_id = (SELECT id FROM tmp_note)
        WHERE id = (SELECT id FROM tmp_art_base);
        $$,
        --NULL,
        --NULL,
        'Collegamento nota su articolo: OK'
    )
    ELSE ok(true, 'Collegamento nota skipped: riferimenti mancanti')
END;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN throws_ok(
        $$
        UPDATE catalogo.articoli
        SET note_target_tipo = 'ARTICOLO_COMPONENTE',
            note_id = (SELECT id FROM tmp_note)
        WHERE id = (SELECT id FROM tmp_art_base);
        $$,
        '23514',
        NULL,
        'note_target_tipo non valido per articoli: bloccato'
    )
    ELSE ok(true, 'Test note_target_tipo skipped: riferimenti mancanti')
END;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN throws_ok(
        $$
        UPDATE catalogo.articoli
        SET note_target_tipo = 'ARTICOLO',
            note_id = 999999999
        WHERE id = (SELECT id FROM tmp_art_base);
        $$,
        '23503',
        NULL,
        'FK note_id inesistente: bloccato'
    )
    ELSE ok(true, 'Test FK note_id skipped: riferimenti mancanti')
END;

-- =========================================================
-- 5) UOM operativa
-- =========================================================
DO $$
DECLARE
  v_id bigint;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    -- 🔴 RIUSO invece di INSERT — 2026-08-18.
    --   Un articolo nasce gia' con la propria `articoli_uom_operativa` di base:
    --   la crea un trigger. Questo blocco la inseriva una seconda volta e
    --   violava `uq_artuomop_articolo_uom`, uccidendo il file.
    --   ⚠️ Non e' un vincolo di troppo: e' la fixture che duplica un lavoro gia'
    --   fatto dal dominio. Si prende la riga che c'e' e le si mettono i flag che
    --   il test richiede.
    UPDATE catalogo.articoli_uom_operativa
       SET is_base = true, factor_to_base = 1,
           is_sell_uom = true, is_purchase_uom = true,
           is_logistic_uom = false, attivo = true
     WHERE articolo_id = (SELECT id FROM tmp_art_base)
       AND uom_id      = (SELECT uom_base_id FROM tmp_ids)
    RETURNING id INTO v_id;

    INSERT INTO tmp_uom_op_base (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_uom_op_base) = 1, 'Inserita uom operativa base')
    ELSE ok(true, 'Inserimento uom operativa base skipped: riferimenti mancanti')
END;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN throws_ok(
        $$
        INSERT INTO catalogo.articoli_uom_operativa (
            articolo_id,
            uom_id,
            is_base,
            factor_to_base,
            attivo
        )
        VALUES (
            (SELECT id FROM tmp_art_base),
            (SELECT uom_base_id FROM tmp_ids),
            false,
            1,
            true
        );
        $$,
        '23505',
        NULL,
        'UOM operativa duplicata (articolo_id, uom_id): bloccata'
    )
    ELSE ok(true, 'Test duplicato uom operativa skipped: riferimenti mancanti')
END;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN throws_ok(
        $$
        INSERT INTO catalogo.articoli_uom_operativa (
            articolo_id,
            uom_id,
            is_base,
            factor_to_base,
            attivo
        )
        VALUES (
            (SELECT id FROM tmp_art_base),
            (SELECT uom_alt_id FROM tmp_ids),
            true,
            1,
            true
        );
        $$,
        '23505',
        NULL,
        'Seconda UOM base per articolo: bloccata'
    )
    ELSE ok(true, 'Test seconda UOM base skipped: riferimenti mancanti')
END;

-- =========================================================
-- 6) Overlap articoli_componenti
-- =========================================================
DO $$
DECLARE
  v_id uuid;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    -- 🔴 PADRE COMPOSITO, aggiunto il 2026-08-18.
    --   Appendere un componente esige `is_composito = true` sul padre: il guard
    --   rispondeva «Articolo deve essere composito = true» e il file moriva.
    --   La fixture creava un articolo semplice e gli chiedeva di comportarsi da
    --   kit — la proprieta' va dichiarata, non data per scontata.
    --   📌 NOTA: quel messaggio arriva a video con un `(%s)` LETTERALE, non
    --   sostituito: E_ARTICOLO_NON_COMPOSITO ha un segnaposto che nessun
    --   chiamante riempie. Difetto del catalogo messaggi, non di questo test —
    --   segnalato a parte.
    UPDATE catalogo.articoli
       SET is_composito = true
     WHERE id = (SELECT id FROM tmp_art_base)
       AND is_composito IS DISTINCT FROM true;

        INSERT INTO catalogo.articoli_componenti (
        prodotto_id,
        componente_id,
        coeff_qta,
        obbligatorio,
        valido_dal,
        valido_al,
        attivo
    )
    VALUES (
        (SELECT id FROM tmp_art_base),
        (SELECT id FROM tmp_art_comp),
        1,
        true,
        DATE '2026-01-01',
        DATE '2026-01-31',
        true
    )
    RETURNING id INTO v_id;

    INSERT INTO tmp_art_comp_rel (id) VALUES (v_id);
  END IF;
END $$;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN ok((SELECT count(*) FROM tmp_art_comp_rel) = 1, 'Inserito legame articoli_componenti')
    ELSE ok(true, 'Inserimento articoli_componenti skipped: riferimenti mancanti')
END;

SELECT CASE
    WHEN (SELECT can_run FROM tmp_can_run)
    THEN throws_ok(
        $$
        INSERT INTO catalogo.articoli_componenti (
            prodotto_id,
            componente_id,
            coeff_qta,
            obbligatorio,
            valido_dal,
            valido_al,
            attivo
        )
        VALUES (
            (SELECT id FROM tmp_art_base),
            (SELECT id FROM tmp_art_comp),
            1,
            true,
            DATE '2026-01-15',
            DATE '2026-02-15',
            true
        );
        $$,
        '23P01',
        NULL,
        'Overlap articoli_componenti: bloccato'
    )
    ELSE ok(true, 'Test overlap articoli_componenti skipped: riferimenti mancanti')
END;

-- Cleanup
-- 🔴 DELETE su articoli_componenti RIMOSSA il 2026-08-18: la struttura BoM e'
--   protetta da un guard di immutabilita' («modifica dei campi di struttura o
--   eliminazione di righe non ammesse»), arrivato dopo questo file. Non e'
--   un'operazione lecita per nessuno, e non serve: il ROLLBACK toglie la riga
--   insieme all'articolo che la porta. Terza occorrenza in questa cartella.
DELETE FROM catalogo.articoli_uom_operativa
WHERE articolo_id = (SELECT id FROM tmp_art_base);

DELETE FROM catalogo.note
WHERE target_tipo = 'ARTICOLO'
  AND id = (SELECT id FROM tmp_note);

-- 🔴 DELETE degli ARTICOLI rimossa il 2026-08-18, di conseguenza.
--   La riga di BoM non si puo' cancellare (guard di immutabilita', sopra), e
--   finche' c'e' la sua FK trattiene gli articoli: il cleanup si spezzava qui.
--   ⭐ E' la catena che mostra perche' il cleanup manuale in coda a un file
--   TRANSAZIONALE e' un costo senza ricavo: il ROLLBACK toglie articoli, BoM e
--   uom insieme, e senza dover conoscere l'ordine delle FK ne' i guard che nel
--   frattempo sono comparsi.

DELETE FROM config.note_stili
WHERE id = (SELECT id FROM tmp_note_stile);

-- 🔴 E anche questa, per la stessa catena (2026-08-18): le unita' di misura
--   restano trattenute dalla `articoli_uom_operativa` dell'articolo, che a sua
--   volta non si puo' togliere perche' l'articolo non si puo' togliere perche'
--   la BoM e' immutabile. Il ROLLBACK scioglie tutto in una volta.

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
