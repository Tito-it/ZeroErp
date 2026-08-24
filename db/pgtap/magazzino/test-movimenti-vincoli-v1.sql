-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: i vincoli di coerenza di magazzino.movimenti, il ledger del magazzino.
--
-- ── PERCHE' ESISTE ─────────────────────────────────────────────────────
--   Fino al 2026-08-21 **nessun pgTAP toccava magazzino.movimenti**, e il
--   dominio e' vuoto: i suoi vincoli non erano mai stati esercitati da niente.
--   E' cosi' che chk_mag_movimenti_da_destinazione_distinti ha potuto
--   pretendere `magazzino_id_dest IS NOT NULL` — rendendo inseribile il solo
--   TRASFERIMENTO e rifiutando ogni carico o scarico semplice — senza che
--   nessuno se ne accorgesse. Corretto da 00_schema/magazzino/20260821-10.
--
--   ⭐ Il test 2 e' quello che sarebbe stato rosso prima della correzione: e'
--   la ragione di questo file, non un caso di contorno.
--
-- ⚠️ Questo file e' ROSSO finche' 20260821-10 non e' applicato.
--
-- Indice test (1..5):
--   Forma del vincolo (anti-regressione):
--   1) chk_mag_movimenti_da_destinazione_distinti NON pretende dest NOT NULL
--   Comportamento:
--   2) carico semplice, senza magazzino di destinazione -> AMMESSO
--   3) trasferimento verso un magazzino diverso -> AMMESSO
--   4) destinazione uguale all'origine -> RIFIUTATO
--   5) quantita' zero -> RIFIUTATO (chk_mag_movimenti_qta_non_zero)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Contesto applicativo: il test gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ Vincoli DIFFERITI: qui il COMMIT non arriva mai (si chiude in ROLLBACK).
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- ============================================================
-- 1) Il vincolo non pretende piu' la destinazione
--    Legge direttamente pg_constraint: intercetta la regressione anche senza
--    riuscire a inserire nulla, ed e' l'asserzione che sopravvive a un
--    cambio di fixture.
-- ============================================================
SELECT ok(
    (SELECT pg_get_constraintdef(oid) NOT LIKE '%magazzino_id_dest IS NOT NULL%'
       FROM pg_constraint
      WHERE conrelid = 'magazzino.movimenti'::regclass
        AND conname  = 'chk_mag_movimenti_da_destinazione_distinti'),
    '1) chk_mag_movimenti_da_destinazione_distinti non pretende dest NOT NULL'
);

-- ============================================================
-- Fixture: due magazzini, un articolo, una causale di carico
--   ⚠️ magazzini.indirizzo_dettaglio_id e' NOT NULL: serve un indirizzo che
--   esista gia'. E il codice non e' generato da nessun trigger — va fornito.
-- ============================================================
CREATE TEMP TABLE tmp_mov_ctx (mag_a bigint, mag_b bigint, art uuid, cau bigint);

DO $fix$
DECLARE
    v_ind  bigint;
    v_a    bigint;
    v_b    bigint;
    v_art  uuid;
    v_cau  bigint;
BEGIN
    SELECT d.id INTO v_ind
      FROM anagrafiche.indirizzi_dettaglio d ORDER BY d.id LIMIT 1;

    INSERT INTO magazzino.magazzini (codice, descrizione, indirizzo_dettaglio_id)
    VALUES ('PGTAP-MOV-A', 'Test vincoli movimenti A', v_ind) RETURNING id INTO v_a;

    INSERT INTO magazzino.magazzini (codice, descrizione, indirizzo_dettaglio_id)
    VALUES ('PGTAP-MOV-B', 'Test vincoli movimenti B', v_ind) RETURNING id INTO v_b;

    SELECT a.id INTO v_art
      FROM catalogo.articoli a WHERE a.attivo IS TRUE ORDER BY a.id LIMIT 1;

    SELECT c.id INTO v_cau
      FROM magazzino.causali c WHERE c.codice = 'CARICO_ACQ' LIMIT 1;

    INSERT INTO tmp_mov_ctx (mag_a, mag_b, art, cau) VALUES (v_a, v_b, v_art, v_cau);
END
$fix$;

-- ============================================================
-- 2) ⭐ Carico semplice: nessun magazzino di destinazione -> AMMESSO
--    E' il movimento piu' comune del magazzino, ed e' quello che il vincolo
--    difettoso rifiutava.
-- ============================================================
SELECT lives_ok(
    format(
        $$INSERT INTO magazzino.movimenti
            (articolo_id, magazzino_id, causale_id, qta, doc_schema, doc_table, doc_id)
          VALUES (%L::uuid, %s, %s, 10, 'pgtap', 'test', 1)$$,
        (SELECT art FROM tmp_mov_ctx),
        (SELECT mag_a FROM tmp_mov_ctx),
        (SELECT cau FROM tmp_mov_ctx)
    ),
    '2) carico semplice senza magazzino di destinazione -> ammesso'
);

-- ============================================================
-- 3) Trasferimento verso un magazzino diverso -> AMMESSO
-- ============================================================
SELECT lives_ok(
    format(
        $$INSERT INTO magazzino.movimenti
            (articolo_id, magazzino_id, magazzino_id_dest, causale_id, qta,
             doc_schema, doc_table, doc_id)
          VALUES (%L::uuid, %s, %s, %s, 5, 'pgtap', 'test', 2)$$,
        (SELECT art FROM tmp_mov_ctx),
        (SELECT mag_a FROM tmp_mov_ctx),
        (SELECT mag_b FROM tmp_mov_ctx),
        (SELECT cau FROM tmp_mov_ctx)
    ),
    '3) trasferimento verso magazzino diverso -> ammesso'
);

-- ============================================================
-- 4) Destinazione uguale all'origine -> RIFIUTATO
--    E' cio' che il vincolo deve davvero impedire: un trasferimento verso se
--    stesso non e' un movimento, e sdoppierebbe la giacenza.
-- ============================================================
SELECT throws_ok(
    format(
        $$INSERT INTO magazzino.movimenti
            (articolo_id, magazzino_id, magazzino_id_dest, causale_id, qta,
             doc_schema, doc_table, doc_id)
          VALUES (%L::uuid, %s, %s, %s, 5, 'pgtap', 'test', 3)$$,
        (SELECT art FROM tmp_mov_ctx),
        (SELECT mag_a FROM tmp_mov_ctx),
        (SELECT mag_a FROM tmp_mov_ctx),
        (SELECT cau FROM tmp_mov_ctx)
    ),
    '23514',
    NULL,
    '4) destinazione uguale all''origine -> rifiutato (CHECK)'
);

-- ============================================================
-- 5) Quantita' zero -> RIFIUTATO
--    chk_mag_movimenti_qta_non_zero. ⚠️ Il vincolo e' `qta <> 0`, non
--    `qta > 0`: le quantita' NEGATIVE restano ammesse, ed e' voluto — il segno
--    dello scarico vive dentro `qta`, perche' vw_giacenza somma senza guardare
--    causali.segno.
-- ============================================================
SELECT throws_ok(
    format(
        $$INSERT INTO magazzino.movimenti
            (articolo_id, magazzino_id, causale_id, qta, doc_schema, doc_table, doc_id)
          VALUES (%L::uuid, %s, %s, 0, 'pgtap', 'test', 4)$$,
        (SELECT art FROM tmp_mov_ctx),
        (SELECT mag_a FROM tmp_mov_ctx),
        (SELECT cau FROM tmp_mov_ctx)
    ),
    '23514',
    NULL,
    '5) quantita'' zero -> rifiutata (CHECK)'
);

SELECT * FROM finish();
ROLLBACK;
