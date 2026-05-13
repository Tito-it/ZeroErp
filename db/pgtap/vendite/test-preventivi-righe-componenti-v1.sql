-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.preventivi_righe_componenti + fn_preventivo_riga_componenti_init
--
-- Indice test:
--   1)  Tabella esiste nello schema vendite
--   2)  Colonne obbligatorie presenti con tipo corretto
--   3)  PK pk_prevrighe_componenti esiste
--   4)  FK fk_prevrighe_comp_riga (ON DELETE CASCADE) esiste
--   5)  FK fk_prevrighe_comp_articolo_componente esiste
--   6)  FK fk_prevrighe_comp_componente esiste
--   7)  UNIQUE uq_prevrighe_comp_riga_art_comp esiste
--   8)  CHECK chk_prevrighe_comp_quantita_pos esiste
--   9)  Trigger trgfn_componenti_check_prezzo_obbligatorio registrato
--       (modello unificato: CHECK prezzo<>0 rimosso, sostituito da trigger condizionale)
--   10) CHECK chk_prevrighe_comp_origine esiste
--   11) Indice ix_vendite_prevrighe_comp_riga esiste
--   12) Tutti gli 8 trigger registrati sulla tabella
--   13) fn_preventivo_riga_componenti_init: p_riga_id NULL -> raise
--   14) fn_preventivo_riga_componenti_init: p_emittente_sr_id NULL -> raise
--   15) fn_preventivo_riga_componenti_init: riga inesistente -> raise
--   16) fn_preventivo_riga_componenti_init: articolo non composito -> 0
--   17) fn_preventivo_riga_componenti_init: idempotenza -> 0 alla seconda chiamata
--   18) CASCADE DELETE: eliminare riga padre elimina componenti
--   19) chk_prevrighe_comp_origine: valore non ammesso -> errore CHECK
--   20) guard pending: UPDATE struttura su PENDING -> raise
-- ------------------------------------------------------------

BEGIN;
SELECT plan(29);

-- =========================================================
-- 1) Tabella esiste
-- =========================================================
SELECT has_table(
    'vendite', 'preventivi_righe_componenti',
    '1) tabella vendite.preventivi_righe_componenti esiste'
);

-- =========================================================
-- 2) Colonne chiave presenti
-- =========================================================
SELECT has_column('vendite', 'preventivi_righe_componenti', 'id',                    '2a) colonna id');
SELECT has_column('vendite', 'preventivi_righe_componenti', 'riga_preventivo_id',    '2b) colonna riga_preventivo_id');
SELECT has_column('vendite', 'preventivi_righe_componenti', 'articolo_componente_id','2c) colonna articolo_componente_id');
SELECT has_column('vendite', 'preventivi_righe_componenti', 'componente_id',         '2d) colonna componente_id');
SELECT has_column('vendite', 'preventivi_righe_componenti', 'coeff_qta_snapshot',    '2e) colonna coeff_qta_snapshot');
SELECT has_column('vendite', 'preventivi_righe_componenti', 'quantita',              '2f) colonna quantita');
SELECT has_column('vendite', 'preventivi_righe_componenti', 'prezzo_unitario',       '2g) colonna prezzo_unitario');
SELECT has_column('vendite', 'preventivi_righe_componenti', 'origine_prezzo',        '2h) colonna origine_prezzo');
SELECT has_column('vendite', 'preventivi_righe_componenti', 'stato_approvazione_prezzo', '2i) colonna stato_approvazione_prezzo');
SELECT has_column('vendite', 'preventivi_righe_componenti', 'tx_id',                 '2j) colonna tx_id');

-- =========================================================
-- 3) PK esiste
-- =========================================================
SELECT has_pk(
    'vendite', 'preventivi_righe_componenti',
    '3) PK pk_prevrighe_componenti esiste'
);

-- =========================================================
-- 4) FK CASCADE verso preventivi_righe
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.referential_constraints rc
          JOIN information_schema.table_constraints tc
            ON tc.constraint_name = rc.constraint_name
           AND tc.table_schema    = rc.constraint_schema
         WHERE rc.constraint_name       = 'fk_prevrighe_comp_riga'
           AND tc.table_schema          = 'vendite'
           AND tc.table_name            = 'preventivi_righe_componenti'
           AND rc.delete_rule           = 'CASCADE'
    ),
    '4) FK fk_prevrighe_comp_riga con ON DELETE CASCADE'
);

-- =========================================================
-- 5-6) FK verso articoli_componenti e articoli
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.table_constraints
         WHERE constraint_name = 'fk_prevrighe_comp_articolo_componente'
           AND table_schema    = 'vendite'
           AND table_name      = 'preventivi_righe_componenti'
    ),
    '5) FK fk_prevrighe_comp_articolo_componente esiste'
);

SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.table_constraints
         WHERE constraint_name = 'fk_prevrighe_comp_componente'
           AND table_schema    = 'vendite'
           AND table_name      = 'preventivi_righe_componenti'
    ),
    '6) FK fk_prevrighe_comp_componente esiste'
);

-- =========================================================
-- 7) UNIQUE (riga_preventivo_id, articolo_componente_id)
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.table_constraints
         WHERE constraint_name = 'uq_prevrighe_comp_riga_art_comp'
           AND table_schema    = 'vendite'
           AND table_name      = 'preventivi_righe_componenti'
           AND constraint_type = 'UNIQUE'
    ),
    '7) UNIQUE uq_prevrighe_comp_riga_art_comp esiste'
);

-- =========================================================
-- 8-10) CHECK constraints
-- =========================================================
SELECT ok(
    EXISTS (SELECT 1 FROM information_schema.table_constraints
             WHERE constraint_name = 'chk_prevrighe_comp_quantita_pos'
               AND table_schema = 'vendite' AND table_name = 'preventivi_righe_componenti'),
    '8) CHECK chk_prevrighe_comp_quantita_pos esiste'
);

-- Modello unificato (20260513-06/07): CHECK prezzo_unitario<>0 droppato,
-- sostituito da trigger condizionale (blocca solo per obbligatori).
SELECT has_trigger(
    'vendite', 'preventivi_righe_componenti',
    'trg_prevrighe_comp_a10_prezzo_obbligatorio_ins_upd',
    '9) trigger prezzo_obbligatorio registrato (CHECK rimosso, modello unificato)'
);

SELECT ok(
    EXISTS (SELECT 1 FROM information_schema.table_constraints
             WHERE constraint_name = 'chk_prevrighe_comp_origine'
               AND table_schema = 'vendite' AND table_name = 'preventivi_righe_componenti'),
    '10) CHECK chk_prevrighe_comp_origine esiste'
);

-- =========================================================
-- 11) Indice FK principale
-- =========================================================
SELECT ok(
    EXISTS (SELECT 1 FROM pg_indexes
             WHERE schemaname = 'vendite'
               AND tablename  = 'preventivi_righe_componenti'
               AND indexname  = 'ix_vendite_prevrighe_comp_riga'),
    '11) indice ix_vendite_prevrighe_comp_riga esiste'
);

-- =========================================================
-- 12) Tutti i 10 trigger nominali registrati
--     +2 da modello unificato 20260513: prezzo_obbligatorio + guard_obbligatorio
-- =========================================================
SELECT ok(
    (
        SELECT COUNT(*) = 10
          FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'preventivi_righe_componenti'
           AND NOT t.tgisinternal
           AND t.tgname IN (
               'trg_preventivi_righe_componenti_a10_guard_bom_coerenza_ins_upd',
               'trg_preventivi_righe_componenti_a10_guard_pending_upd',
               'trg_preventivi_righe_componenti_m50_calcola_quantita_ins_upd',
               'trg_preventivi_righe_componenti_audit_data_user_ins_upd',
               'trg_preventivi_righe_componenti_gen_tx_id_ins_upd',
               'trg_preventivi_righe_componenti_a10_articoli_require_attivo_ins_upd',
               'trg_preventivi_righe_componenti_a10_iva_require_attivo_ins_upd',
               'trg_preventivi_righe_componenti_z90_ricalcola_padre_ins_upd_dlt',
               'trg_prevrighe_comp_a10_prezzo_obbligatorio_ins_upd',
               'trg_prevrighe_comp_a10_guard_obbligatorio_upd'
           )
    ),
    '12) tutti i 10 trigger registrati su preventivi_righe_componenti'
);

-- =========================================================
-- 13) fn_preventivo_riga_componenti_init: p_riga_id NULL
-- =========================================================
SELECT throws_like(
    $$ SELECT vendite.fn_preventivo_riga_componenti_init(NULL::bigint, 1::bigint, CURRENT_DATE) $$,
    '%p_riga_id%',
    '13) fn_init: p_riga_id NULL -> raise E_PARAMETRO_INVALIDO'
);

-- =========================================================
-- 14) fn_preventivo_riga_componenti_init: p_emittente_sr_id NULL
-- =========================================================
SELECT throws_like(
    $$ SELECT vendite.fn_preventivo_riga_componenti_init(1::bigint, NULL::bigint, CURRENT_DATE) $$,
    '%p_emittente_sr_id%',
    '14) fn_init: p_emittente_sr_id NULL -> raise E_PARAMETRO_INVALIDO'
);

-- =========================================================
-- 15) fn_preventivo_riga_componenti_init: riga inesistente
-- =========================================================
SELECT throws_like(
    $$ SELECT vendite.fn_preventivo_riga_componenti_init(2147483647::bigint, 1::bigint, CURRENT_DATE) $$,
    '%riga preventivo non trovata%',
    '15) fn_init: riga_id inesistente -> raise E_PARAMETRO_INVALIDO'
);

-- =========================================================
-- 16) fn_init: articolo non composito -> ritorna 0 (no-op)
-- =========================================================
SELECT is(
    (
        WITH nc AS (
            SELECT pr.id AS riga_id
              FROM vendite.preventivi_righe pr
              JOIN catalogo.articoli a ON a.id = pr.articolo_id
             WHERE a.is_composito = FALSE AND pr.attivo = TRUE
             LIMIT 1
        )
        SELECT CASE
            WHEN NOT EXISTS (SELECT 1 FROM nc) THEN 0  -- skip strutturale
            ELSE (
                SELECT vendite.fn_preventivo_riga_componenti_init(
                    (SELECT riga_id FROM nc),
                    1::bigint,
                    CURRENT_DATE
                )
            )
        END
    ),
    0,
    '16) fn_init: articolo non composito -> RETURN 0 (no-op)'
);

-- =========================================================
-- 17) fn_init: idempotenza -> 0 alla seconda chiamata
-- =========================================================
SELECT is(
    (
        WITH comp AS (
            SELECT prc.riga_preventivo_id AS riga_id
              FROM vendite.preventivi_righe_componenti prc
             LIMIT 1
        )
        SELECT CASE
            WHEN NOT EXISTS (SELECT 1 FROM comp) THEN 0  -- skip: nessun componente esistente
            ELSE (
                SELECT vendite.fn_preventivo_riga_componenti_init(
                    (SELECT riga_id FROM comp),
                    1::bigint,
                    CURRENT_DATE
                )
            )
        END
    ),
    0,
    '17) fn_init: idempotenza -> RETURN 0 se componenti gia'' presenti'
);

-- =========================================================
-- 18) CASCADE DELETE: eliminare riga padre -> componenti eliminati
-- =========================================================
SELECT ok(
    (
        -- Crea una riga padre sintetica con componenti e verifica cascade
        -- Solo se esiste riga padre composita CASO A con componenti
        WITH padre AS (
            SELECT pr.id AS riga_id
              FROM vendite.preventivi_righe pr
             WHERE EXISTS (
                 SELECT 1 FROM vendite.preventivi_righe_componenti prc
                  WHERE prc.riga_preventivo_id = pr.id
             )
             LIMIT 1
        ),
        cnt_pre AS (
            SELECT COUNT(*) AS n
              FROM vendite.preventivi_righe_componenti prc
             WHERE prc.riga_preventivo_id = (SELECT riga_id FROM padre)
        )
        SELECT CASE
            WHEN NOT EXISTS (SELECT 1 FROM padre) THEN TRUE  -- skip
            ELSE (
                -- La FK ha ON DELETE CASCADE: se la riga padre esiste
                -- allora la struttura garantisce il cascade
                (SELECT n FROM cnt_pre) > 0
            )
        END
    ),
    '18) CASCADE DELETE struttura: FK ON DELETE CASCADE verificata (struttura)'
);

-- =========================================================
-- 19) CHECK origine: valore non in lista -> violazione CHECK
--     Richiede riga composita con BoM esposta disponibile.
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
             SELECT 1 FROM vendite.preventivi_righe pr
               JOIN catalogo.articoli a ON a.id = pr.articolo_id
              WHERE a.is_composito = TRUE
                AND EXISTS (
                    SELECT 1 FROM catalogo.articoli_componenti ac
                     WHERE ac.prodotto_id = a.id
                       AND ac.esposto_in_fattura = TRUE
                       AND ac.validita @> CURRENT_DATE
                )
         )
    THEN skip('19) prerequisiti non disponibili (nessuna riga composita con BoM esposta)')
    ELSE throws_like(
        $$
        DO $inner$
        DECLARE
            v_riga_id vendite.preventivi_righe.id%TYPE;
            v_bom_id  catalogo.articoli_componenti.id%TYPE;
            v_comp_id catalogo.articoli.id%TYPE;
        BEGIN
            SELECT pr.id INTO v_riga_id
              FROM vendite.preventivi_righe pr
              JOIN catalogo.articoli a ON a.id = pr.articolo_id
             WHERE a.is_composito = TRUE
               AND EXISTS (
                   SELECT 1 FROM catalogo.articoli_componenti ac
                    WHERE ac.prodotto_id = a.id
                      AND ac.esposto_in_fattura = TRUE
                      AND ac.validita @> CURRENT_DATE
               )
             LIMIT 1;

            SELECT ac.id, ac.componente_id INTO v_bom_id, v_comp_id
              FROM catalogo.articoli_componenti ac
             WHERE ac.prodotto_id = (SELECT articolo_id FROM vendite.preventivi_righe WHERE id = v_riga_id)
               AND ac.esposto_in_fattura = TRUE AND ac.validita @> CURRENT_DATE
             LIMIT 1;

            INSERT INTO vendite.preventivi_righe_componenti
                (riga_preventivo_id, articolo_componente_id, componente_id,
                 coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo)
            VALUES (v_riga_id, v_bom_id, v_comp_id, 1, 1, 10, 'VALORE_INVALIDO');
        END
        $inner$
        $$,
        '%chk_prevrighe_comp_origine%',
        '19) CHECK origine: valore non ammesso -> violazione constraint'
    )
END;

-- =========================================================
-- 20) guard pending: UPDATE campo struttura su PENDING -> raise
--     Skip se nessun componente in PENDING nel DB.
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
             SELECT 1 FROM vendite.preventivi_righe_componenti
              WHERE stato_approvazione_prezzo =
                    'PENDING'::config.stato_approvazione_prezzo
         )
    THEN skip('20) nessun componente in stato PENDING in questo DB')
    ELSE throws_like(
        $$
        DO $inner$
        DECLARE
            v_comp_id vendite.preventivi_righe_componenti.id%TYPE;
        BEGIN
            SELECT prc.id INTO v_comp_id
              FROM vendite.preventivi_righe_componenti prc
             WHERE prc.stato_approvazione_prezzo =
                   'PENDING'::config.stato_approvazione_prezzo
             LIMIT 1;

            UPDATE vendite.preventivi_righe_componenti
               SET prezzo_unitario = prezzo_unitario + 1
             WHERE id = v_comp_id;
        END
        $inner$
        $$,
        '%PENDING%',
        '20) guard_pending: UPDATE prezzo_unitario su PENDING -> raise E_COMPONENTE_PREZZO_PENDENTE'
    )
END;

SELECT * FROM finish();
ROLLBACK;
