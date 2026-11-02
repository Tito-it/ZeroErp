-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.ordini_righe_componenti + fn_ordine_riga_componenti_init
--
-- Indice test:
--   1)  Tabella esiste nello schema vendite
--   2)  Colonne obbligatorie presenti con tipo corretto
--   3)  PK pk_ordrighe_comp esiste
--   4)  FK fk_ordrighe_comp_riga (ON DELETE CASCADE) esiste
--   5)  FK fk_ordrighe_comp_articolo_componente esiste
--   6)  FK fk_ordrighe_comp_componente esiste
--   7)  UNIQUE uq_ordrighe_comp_riga_art_comp esiste
--   8)  CHECK chk_ordrighe_comp_quantita_nz: nome e definizione (quantita <> 0)
--   9)  CHECK chk_ordrighe_comp_prezzo_nonneg esiste
--   10) CHECK chk_ordrighe_comp_origine esiste
--   11) FK fk_ordrighe_comp_riga coperta da un indice
--   12) Tutti i 7 trigger registrati sulla tabella
--   13) Trigger propaga_qta registrato su ordini_righe
--   14) fn_ordine_riga_componenti_init: p_riga_id NULL -> raise
--   15) fn_ordine_riga_componenti_init: p_emittente_sr_id NULL -> raise
--   16) fn_ordine_riga_componenti_init: riga inesistente -> raise
--   17) fn_ordine_riga_componenti_init: articolo non composito -> 0
--   18) fn_ordine_riga_componenti_init: idempotenza -> 0 alla seconda chiamata
--   19) CASCADE DELETE: eliminare riga padre elimina componenti
--   20) chk_ordrighe_comp_origine: valore non ammesso -> errore CHECK
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

SELECT plan(31);

-- =========================================================
-- 1) Tabella esiste
-- =========================================================
SELECT has_table(
    'vendite', 'ordini_righe_componenti',
    '1) tabella vendite.ordini_righe_componenti esiste'
);

-- =========================================================
-- 2) Colonne chiave presenti
-- =========================================================
SELECT has_column('vendite', 'ordini_righe_componenti', 'id',                    '2a) colonna id');
SELECT has_column('vendite', 'ordini_righe_componenti', 'riga_ordine_id',        '2b) colonna riga_ordine_id');
SELECT has_column('vendite', 'ordini_righe_componenti', 'articolo_componente_id','2c) colonna articolo_componente_id');
SELECT has_column('vendite', 'ordini_righe_componenti', 'componente_id',         '2d) colonna componente_id');
SELECT has_column('vendite', 'ordini_righe_componenti', 'coeff_qta_snapshot',    '2e) colonna coeff_qta_snapshot');
SELECT has_column('vendite', 'ordini_righe_componenti', 'quantita',              '2f) colonna quantita');
SELECT has_column('vendite', 'ordini_righe_componenti', 'prezzo_unitario',       '2g) colonna prezzo_unitario');
SELECT has_column('vendite', 'ordini_righe_componenti', 'origine_prezzo',        '2h) colonna origine_prezzo');
SELECT has_column('vendite', 'ordini_righe_componenti', 'stato_approvazione_prezzo', '2i) colonna stato_approvazione_prezzo');
SELECT has_column('vendite', 'ordini_righe_componenti', 'tx_id',                 '2j) colonna tx_id');

-- =========================================================
-- 3) PK esiste
-- =========================================================
SELECT has_pk(
    'vendite', 'ordini_righe_componenti',
    '3) PK pk_ordrighe_comp esiste'
);

-- =========================================================
-- 4) FK ON DELETE CASCADE verso ordini_righe
-- =========================================================
SELECT has_fk(
    'vendite', 'ordini_righe_componenti',
    '4) FK fk_ordrighe_comp_riga esiste'
);

-- =========================================================
-- 5) FK verso articoli_componenti
-- =========================================================
SELECT col_is_fk(
    'vendite', 'ordini_righe_componenti', 'articolo_componente_id',
    '5) FK fk_ordrighe_comp_articolo_componente esiste'
);

-- =========================================================
-- 6) FK verso articoli (componente_id)
-- =========================================================
SELECT col_is_fk(
    'vendite', 'ordini_righe_componenti', 'componente_id',
    '6) FK fk_ordrighe_comp_componente esiste'
);

-- =========================================================
-- 7) UNIQUE (riga_ordine_id, articolo_componente_id)
-- =========================================================
SELECT has_unique(
    'vendite', 'ordini_righe_componenti',
    '7) UNIQUE uq_ordrighe_comp_riga_art_comp esiste'
);

-- =========================================================
-- 8) CHECK quantita <> 0
-- =========================================================
-- ⚠️ Rev. 2026-10-08 (20261008-30): il vincolo si chiama _nz, non _pos — vieta
--    lo zero, non il negativo. Prima qui c'era has_check(schema, tabella,
--    descrizione), che verifica che esista UN check qualunque: il nome stava
--    solo nella descrizione. Ora si leggono nome e definizione dal catalogo.
SELECT is(
    (SELECT pg_get_constraintdef(c.oid)
       FROM pg_constraint c
      WHERE c.conrelid = 'vendite.ordini_righe_componenti'::regclass
        AND c.conname  = 'chk_ordrighe_comp_quantita_nz'),
    'CHECK ((quantita <> (0)::numeric))',
    '8) CHECK chk_ordrighe_comp_quantita_nz: quantita <> 0'
);

-- =========================================================
-- 9) Trigger prezzo_obbligatorio registrato
--    Modello unificato (20260513-06/07): CHECK prezzo_unitario<>0 droppato,
--    sostituito da trigger condizionale (blocca solo per obbligatori).
-- =========================================================
SELECT has_trigger(
    'vendite', 'ordini_righe_componenti',
    'trg_ordrighe_comp_a10_prezzo_obbligatorio_ins_upd',
    '9) trigger prezzo_obbligatorio registrato (CHECK rimosso, modello unificato)'
);

-- =========================================================
-- 10) CHECK origine_prezzo IN (...)
-- =========================================================
SELECT col_has_check(
    'vendite', 'ordini_righe_componenti', 'origine_prezzo',
    '10) CHECK chk_ordrighe_comp_origine su origine_prezzo'
);

-- =========================================================
-- 11) FK riga_ordine_id coperta da un indice
--     L'indice dedicato ix_vendite_ordrighe_comp_riga e' stato rimosso il 2026-07-27
--     (changeSet 20260727-37): era ridondante, perche' uq_ordrighe_comp_riga_art_comp
--     ha riga_ordine_id come colonna leading e serve gia' ogni ricerca per riga,
--     ON DELETE CASCADE compreso.
--     Il test verifica ora la PROPRIETA' — la FK e' coperta — invece del nome
--     di un indice specifico: resta valido anche se l'indice coprente cambia.
-- =========================================================
SELECT ok(
    NOT EXISTS (SELECT 1 FROM dbops.vw_fk_senza_indice
                 WHERE schema_name     = 'vendite'
                   AND table_name      = 'ordini_righe_componenti'
                   AND constraint_name = 'fk_ordrighe_comp_riga'),
    '11) FK fk_ordrighe_comp_riga coperta da un indice'
);

-- =========================================================
-- 12) Trigger registrati sulla tabella (14 attesi)
--     +2 da modello unificato 20260513: prezzo_obbligatorio + guard_obbligatorio
--     +1 dal 2026-10-08 (20261008-34): trg_ordini_righe_componenti_a05_doc_bozza_ins_upd_dlt,
--        il lock «solo in bozza» (building block a livello RIGA).
-- =========================================================
SELECT is(
    (SELECT COUNT(DISTINCT trigger_name)::integer
       FROM information_schema.triggers
      WHERE event_object_schema = 'vendite'
        AND event_object_table  = 'ordini_righe_componenti'),
    14,
    '12) 14 trigger registrati su ordini_righe_componenti'
);

-- =========================================================
-- 13) Trigger propaga_qta su ordini_righe
-- =========================================================
SELECT has_trigger(
    'vendite', 'ordini_righe',
    'trg_ordini_righe_z90_propaga_qta_componenti_upd',
    '13) trigger propaga_qta registrato su ordini_righe'
);

-- =========================================================
-- 14) fn_ordine_riga_componenti_init: p_riga_id NULL -> raise
-- =========================================================
SELECT throws_like(
    $$ SELECT vendite.fn_ordine_riga_componenti_init(NULL, 1, script.fn_data_operativa()) $$,
    '%Parametro non valido%',
    '14) fn_ordine_riga_componenti_init: p_riga_id NULL -> raise E_PARAMETRO_INVALIDO'
);

-- =========================================================
-- 15) fn_ordine_riga_componenti_init: p_emittente_sr_id NULL -> raise
-- =========================================================
SELECT throws_like(
    $$ SELECT vendite.fn_ordine_riga_componenti_init(1, NULL, script.fn_data_operativa()) $$,
    '%Parametro non valido%',
    '15) fn_ordine_riga_componenti_init: p_emittente_sr_id NULL -> raise E_PARAMETRO_INVALIDO'
);

-- =========================================================
-- 16) fn_ordine_riga_componenti_init: riga inesistente -> raise
-- =========================================================
-- ⚠️ throws_like sulla frase, non throws_ok sul codice: tutti i raise di
--    script.fn_log_and_raise_error condividono SQLSTATE P0001, quindi il codice
--    non discrimina (stessa ragione di catalogo/test-guard-iva-reactivation-v1).
--    Il pattern SALTA l'id interpolato — il messaggio 900 e'
--    `Riga ordine %s non trovata.` — altrimenti si rompe al primo id diverso.
SELECT throws_like(
    $$ SELECT vendite.fn_ordine_riga_componenti_init(2147483647, 1, script.fn_data_operativa()) $$,
    '%Riga ordine %non trovata%',
    '16) fn_ordine_riga_componenti_init: riga inesistente -> raise E_ORDINE_RIGA_NON_TROVATA'
);

-- =========================================================
-- 17) fn_ordine_riga_componenti_init: articolo non composito -> 0
-- Verifica comportamento no-op su riga con articolo non composito.
-- Richiede una riga ordine esistente con articolo non composito.
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
        SELECT 1 FROM vendite.ordini_righe or_
          JOIN catalogo.articoli a ON a.id = or_.articolo_id
         WHERE NOT COALESCE(a.is_composito, FALSE)
         LIMIT 1
    )
    THEN skip('17) nessuna riga ordine con articolo non composito disponibile')
    ELSE is(
        (SELECT vendite.fn_ordine_riga_componenti_init(
            (SELECT or_.id FROM vendite.ordini_righe or_
               JOIN catalogo.articoli a ON a.id = or_.articolo_id
              WHERE NOT COALESCE(a.is_composito, FALSE)
              LIMIT 1),
            1,
            script.fn_data_operativa()
        )),
        0,
        '17) fn_ordine_riga_componenti_init: articolo non composito -> RETURN 0'
    )
END;

-- =========================================================
-- 18) Idempotenza: seconda chiamata su riga gia' inizializzata -> 0
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
        SELECT 1 FROM vendite.ordini_righe_componenti LIMIT 1
    )
    THEN skip('18) nessun componente presente per test idempotenza')
    ELSE is(
        (SELECT vendite.fn_ordine_riga_componenti_init(
            (SELECT riga_ordine_id FROM vendite.ordini_righe_componenti LIMIT 1),
            1,
            script.fn_data_operativa()
        )),
        0,
        '18) fn_ordine_riga_componenti_init: idempotenza -> 0 alla seconda chiamata'
    )
END;

-- =========================================================
-- 19) CASCADE DELETE: struttura FK CASCADE verificata da constraint DDL
-- La semantica ON DELETE CASCADE e' garantita dal DDL (fk_ordrighe_comp_riga).
-- Un test funzionale richiederebbe fixture complete; rinviato a smoke test BE.
-- =========================================================
SELECT pass('19) CASCADE DELETE: struttura FK CASCADE verificata da constraint DDL (fk_ordrighe_comp_riga)');

-- =========================================================
-- 20) CHECK origine_prezzo: valore non ammesso -> errore
-- ⚠️ Rev. 2026-10-08 — solo documenti in DRAFT: fuori bozza dal 20261008-34
--    parla prima il lock (fascia _a05_), e l'asserzione '%' passerebbe per
--    il lock invece che per la regola in esame. Brief:
--    brief-db-righe-e-componenti-le-altre-famiglie §4.
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
        SELECT 1 FROM vendite.ordini_righe r
          JOIN vendite.ordini d ON d.id = r.ordine_id
          JOIN config.stati_doc_ordini s ON s.id = d.stato_doc_ordine_id
         WHERE s.codice_interno = 'DRAFT'
    )
    THEN skip('20) nessuna riga ordine disponibile per test CHECK origine')
    ELSE throws_like(
        $q$ INSERT INTO vendite.ordini_righe_componenti (
                riga_ordine_id, articolo_componente_id, componente_id,
                coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id
            ) VALUES (
                (SELECT r.id FROM vendite.ordini_righe r
                   JOIN vendite.ordini d ON d.id = r.ordine_id
                   JOIN config.stati_doc_ordini s ON s.id = d.stato_doc_ordine_id
                  WHERE s.codice_interno = 'DRAFT'
                  ORDER BY r.id LIMIT 1),
                (SELECT id FROM catalogo.articoli_componenti LIMIT 1),
                (SELECT componente_id FROM catalogo.articoli_componenti LIMIT 1),
                1, 1, 1, 'VALORE_NON_VALIDO', (SELECT a.uom_id FROM catalogo.articoli a WHERE a.id = (SELECT componente_id FROM catalogo.articoli_componenti LIMIT 1))
            ) $q$,
        '%',
        '20) INSERT con origine_prezzo non valido bloccato (CHECK o guard BoM)'
    )
END;

-- =========================================================
-- 21) Trigger guard_pending registrato su ordini_righe_componenti
-- =========================================================
SELECT has_trigger(
    'vendite', 'ordini_righe_componenti',
    'trg_ordini_righe_componenti_a10_guard_pending_upd',
    '21) trigger guard_pending L3 registrato su ordini_righe_componenti'
);

-- =========================================================
-- 22) Guard pending: UPDATE struttura su PENDING -> raise
-- ⚠️ Rev. 2026-10-08 — solo documenti in DRAFT: fuori bozza dal 20261008-34
--    parla prima il lock (fascia _a05_), e l'asserzione '%' passerebbe per
--    il lock invece che per la regola in esame. Brief:
--    brief-db-righe-e-componenti-le-altre-famiglie §4.
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
        SELECT 1 FROM vendite.ordini_righe_componenti c
          JOIN vendite.ordini_righe r ON r.id = c.riga_ordine_id
          JOIN vendite.ordini d ON d.id = r.ordine_id
          JOIN config.stati_doc_ordini s ON s.id = d.stato_doc_ordine_id
         WHERE c.stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
           AND s.codice_interno = 'DRAFT'
    )
    THEN skip('22) nessun componente PENDING disponibile per test guard L3')
    ELSE throws_like(
        $q$
        UPDATE vendite.ordini_righe_componenti
           SET prezzo_unitario = prezzo_unitario + 0.01
         WHERE stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
           AND id = (SELECT c.id FROM vendite.ordini_righe_componenti c
                       JOIN vendite.ordini_righe r ON r.id = c.riga_ordine_id
                       JOIN vendite.ordini d ON d.id = r.ordine_id
                       JOIN config.stati_doc_ordini s ON s.id = d.stato_doc_ordine_id
                      WHERE c.stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
                        AND s.codice_interno = 'DRAFT'
                      ORDER BY c.id LIMIT 1)
        $q$,
        '%',
        '22) guard_pending blocca UPDATE struttura su componente PENDING'
    )
END;

SELECT * FROM finish();
ROLLBACK;
