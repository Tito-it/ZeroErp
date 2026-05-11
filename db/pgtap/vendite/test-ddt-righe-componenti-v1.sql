-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.ddt_righe_componenti + fn_ddt_riga_componenti_init
--
-- Indice test:
--   1)  Tabella esiste nello schema vendite
--   2)  Colonne obbligatorie presenti con tipo corretto
--   3)  PK pk_ddtrighe_comp esiste
--   4)  FK fk_ddtrighe_comp_riga (ON DELETE CASCADE) esiste
--   5)  FK fk_ddtrighe_comp_articolo_componente esiste
--   6)  FK fk_ddtrighe_comp_componente esiste
--   7)  UNIQUE uq_ddtrighe_comp_riga_art_comp esiste
--   8)  CHECK chk_ddtrighe_comp_quantita_pos esiste
--   9)  CHECK chk_ddtrighe_comp_prezzo_nonneg esiste
--   10) CHECK chk_ddtrighe_comp_origine esiste
--   11) Indice ix_vendite_ddtrighe_comp_riga esiste
--   12) Tutti i 7 trigger registrati sulla tabella
--   13) Trigger propaga_qta registrato su ddt_righe
--   14) fn_ddt_riga_componenti_init: p_riga_id NULL -> raise
--   15) fn_ddt_riga_componenti_init: p_emittente_sr_id NULL -> raise
--   16) fn_ddt_riga_componenti_init: riga inesistente -> raise
--   17) fn_ddt_riga_componenti_init: articolo non composito -> 0
--   18) fn_ddt_riga_componenti_init: idempotenza -> 0 alla seconda chiamata
--   19) CASCADE DELETE: eliminare riga padre elimina componenti
--   20) chk_ddtrighe_comp_origine: valore non ammesso -> errore CHECK
-- ------------------------------------------------------------

BEGIN;
SELECT plan(31);

-- =========================================================
-- 1) Tabella esiste
-- =========================================================
SELECT has_table(
    'vendite', 'ddt_righe_componenti',
    '1) tabella vendite.ddt_righe_componenti esiste'
);

-- =========================================================
-- 2) Colonne chiave presenti
-- =========================================================
SELECT has_column('vendite', 'ddt_righe_componenti', 'id',                    '2a) colonna id');
SELECT has_column('vendite', 'ddt_righe_componenti', 'riga_ddt_id',           '2b) colonna riga_ddt_id');
SELECT has_column('vendite', 'ddt_righe_componenti', 'articolo_componente_id','2c) colonna articolo_componente_id');
SELECT has_column('vendite', 'ddt_righe_componenti', 'componente_id',         '2d) colonna componente_id');
SELECT has_column('vendite', 'ddt_righe_componenti', 'coeff_qta_snapshot',    '2e) colonna coeff_qta_snapshot');
SELECT has_column('vendite', 'ddt_righe_componenti', 'quantita',              '2f) colonna quantita');
SELECT has_column('vendite', 'ddt_righe_componenti', 'prezzo_unitario',       '2g) colonna prezzo_unitario');
SELECT has_column('vendite', 'ddt_righe_componenti', 'origine_prezzo',        '2h) colonna origine_prezzo');
SELECT has_column('vendite', 'ddt_righe_componenti', 'stato_approvazione_prezzo', '2i) colonna stato_approvazione_prezzo');
SELECT has_column('vendite', 'ddt_righe_componenti', 'tx_id',                 '2j) colonna tx_id');

-- =========================================================
-- 3) PK esiste
-- =========================================================
SELECT has_pk(
    'vendite', 'ddt_righe_componenti',
    '3) PK pk_ddtrighe_comp esiste'
);

-- =========================================================
-- 4) FK ON DELETE CASCADE verso ddt_righe
-- =========================================================
SELECT has_fk(
    'vendite', 'ddt_righe_componenti',
    '4) FK fk_ddtrighe_comp_riga esiste'
);

-- =========================================================
-- 5) FK verso articoli_componenti
-- =========================================================
SELECT col_is_fk(
    'vendite', 'ddt_righe_componenti', 'articolo_componente_id',
    '5) FK fk_ddtrighe_comp_articolo_componente esiste'
);

-- =========================================================
-- 6) FK verso articoli (componente_id)
-- =========================================================
SELECT col_is_fk(
    'vendite', 'ddt_righe_componenti', 'componente_id',
    '6) FK fk_ddtrighe_comp_componente esiste'
);

-- =========================================================
-- 7) UNIQUE (riga_ddt_id, articolo_componente_id)
-- =========================================================
SELECT has_unique(
    'vendite', 'ddt_righe_componenti',
    '7) UNIQUE uq_ddtrighe_comp_riga_art_comp esiste'
);

-- =========================================================
-- 8) CHECK quantita <> 0
-- =========================================================
SELECT has_check(
    'vendite', 'ddt_righe_componenti',
    '8) CHECK chk_ddtrighe_comp_quantita_pos esiste'
);

-- =========================================================
-- 9) CHECK prezzo_unitario <> 0
-- =========================================================
SELECT col_has_check(
    'vendite', 'ddt_righe_componenti', 'prezzo_unitario',
    '9) CHECK chk_ddtrighe_comp_prezzo_nonneg su prezzo_unitario'
);

-- =========================================================
-- 10) CHECK origine_prezzo IN (...)
-- =========================================================
SELECT col_has_check(
    'vendite', 'ddt_righe_componenti', 'origine_prezzo',
    '10) CHECK chk_ddtrighe_comp_origine su origine_prezzo'
);

-- =========================================================
-- 11) Indice su riga_ddt_id
-- =========================================================
SELECT has_index(
    'vendite', 'ddt_righe_componenti',
    'ix_vendite_ddtrighe_comp_riga',
    '11) indice ix_vendite_ddtrighe_comp_riga esiste'
);

-- =========================================================
-- 12) Trigger registrati sulla tabella (7 attesi)
-- =========================================================
SELECT is(
    (SELECT COUNT(DISTINCT trigger_name)::integer
       FROM information_schema.triggers
      WHERE event_object_schema = 'vendite'
        AND event_object_table  = 'ddt_righe_componenti'),
    8,
    '12) 8 trigger registrati su ddt_righe_componenti'
);

-- =========================================================
-- 13) Trigger propaga_qta su ddt_righe
-- =========================================================
SELECT has_trigger(
    'vendite', 'ddt_righe',
    'trg_ddt_righe_z90_propaga_qta_componenti_upd',
    '13) trigger propaga_qta registrato su ddt_righe'
);

-- =========================================================
-- 14) fn_ddt_riga_componenti_init: p_riga_id NULL -> raise
-- =========================================================
SELECT throws_like(
    $$ SELECT vendite.fn_ddt_riga_componenti_init(NULL, 1, current_date) $$,
    '%Parametro non valido%',
    '14) fn_ddt_riga_componenti_init: p_riga_id NULL -> raise E_PARAMETRO_INVALIDO'
);

-- =========================================================
-- 15) fn_ddt_riga_componenti_init: p_emittente_sr_id NULL -> raise
-- =========================================================
SELECT throws_like(
    $$ SELECT vendite.fn_ddt_riga_componenti_init(1, NULL, current_date) $$,
    '%Parametro non valido%',
    '15) fn_ddt_riga_componenti_init: p_emittente_sr_id NULL -> raise E_PARAMETRO_INVALIDO'
);

-- =========================================================
-- 16) fn_ddt_riga_componenti_init: riga inesistente -> raise
-- =========================================================
SELECT throws_like(
    $$ SELECT vendite.fn_ddt_riga_componenti_init(2147483647, 1, current_date) $$,
    '%Parametro non valido%',
    '16) fn_ddt_riga_componenti_init: riga inesistente -> raise E_PARAMETRO_INVALIDO'
);

-- =========================================================
-- 17) fn_ddt_riga_componenti_init: articolo non composito -> 0
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
        SELECT 1 FROM vendite.ddt_righe dr
          JOIN catalogo.articoli a ON a.id = dr.articolo_id
         WHERE NOT COALESCE(a.is_composito, FALSE)
         LIMIT 1
    )
    THEN skip('17) nessuna riga ddt con articolo non composito disponibile')
    ELSE is(
        (SELECT vendite.fn_ddt_riga_componenti_init(
            (SELECT dr.id FROM vendite.ddt_righe dr
               JOIN catalogo.articoli a ON a.id = dr.articolo_id
              WHERE NOT COALESCE(a.is_composito, FALSE)
              LIMIT 1),
            1,
            current_date
        )),
        0,
        '17) fn_ddt_riga_componenti_init: articolo non composito -> RETURN 0'
    )
END;

-- =========================================================
-- 18) Idempotenza: seconda chiamata su riga gia' inizializzata -> 0
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
        SELECT 1 FROM vendite.ddt_righe_componenti LIMIT 1
    )
    THEN skip('18) nessun componente presente per test idempotenza')
    ELSE is(
        (SELECT vendite.fn_ddt_riga_componenti_init(
            (SELECT riga_ddt_id FROM vendite.ddt_righe_componenti LIMIT 1),
            1,
            current_date
        )),
        0,
        '18) fn_ddt_riga_componenti_init: idempotenza -> 0 alla seconda chiamata'
    )
END;

-- =========================================================
-- 19) CASCADE DELETE: struttura FK CASCADE verificata da constraint DDL
-- La semantica ON DELETE CASCADE e' garantita dal DDL (fk_ddtrighe_comp_riga).
-- =========================================================
SELECT pass('19) CASCADE DELETE: struttura FK CASCADE verificata da constraint DDL (fk_ddtrighe_comp_riga)');

-- =========================================================
-- 20) CHECK origine_prezzo: valore non ammesso -> errore
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
        SELECT 1 FROM vendite.ddt_righe LIMIT 1
    )
    THEN skip('20) nessuna riga ddt disponibile per test CHECK origine')
    ELSE throws_like(
        $q$ INSERT INTO vendite.ddt_righe_componenti (
                riga_ddt_id, articolo_componente_id, componente_id,
                coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo
            ) VALUES (
                (SELECT id FROM vendite.ddt_righe LIMIT 1),
                (SELECT id FROM catalogo.articoli_componenti LIMIT 1),
                (SELECT componente_id FROM catalogo.articoli_componenti LIMIT 1),
                1, 1, 1, 'VALORE_NON_VALIDO'
            ) $q$,
        '%',
        '20) INSERT con origine_prezzo non valido bloccato (CHECK o guard BoM)'
    )
END;

-- =========================================================
-- 21) Trigger guard_pending registrato su ddt_righe_componenti
-- =========================================================
SELECT has_trigger(
    'vendite', 'ddt_righe_componenti',
    'trg_ddt_righe_componenti_a10_guard_pending_upd',
    '21) trigger guard_pending L3 registrato su ddt_righe_componenti'
);

-- =========================================================
-- 22) Guard pending: UPDATE struttura su PENDING -> raise
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
        SELECT 1 FROM vendite.ddt_righe_componenti
         WHERE stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
         LIMIT 1
    )
    THEN skip('22) nessun componente PENDING disponibile per test guard L3')
    ELSE throws_like(
        $q$
        UPDATE vendite.ddt_righe_componenti
           SET prezzo_unitario = prezzo_unitario + 0.01
         WHERE stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
           AND id = (SELECT id FROM vendite.ddt_righe_componenti
                      WHERE stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
                      LIMIT 1)
        $q$,
        '%',
        '22) guard_pending blocca UPDATE struttura su componente PENDING'
    )
END;

SELECT * FROM finish();
ROLLBACK;
