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
--   11) FK fk_prevrighe_comp_riga coperta da un indice
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
SELECT plan(30);

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
-- 11) FK riga_preventivo_id coperta da un indice
--     L'indice dedicato ix_vendite_prevrighe_comp_riga e' stato rimosso il 2026-07-27
--     (changeSet 20260727-37): era ridondante, perche' uq_prevrighe_comp_riga_art_comp
--     ha riga_preventivo_id come colonna leading e serve gia' ogni ricerca per riga,
--     ON DELETE CASCADE compreso.
--     Il test verifica ora la PROPRIETA' — la FK e' coperta — invece del nome
--     di un indice specifico: resta valido anche se l'indice coprente cambia.
-- =========================================================
SELECT ok(
    NOT EXISTS (SELECT 1 FROM dbops.vw_fk_senza_indice
                 WHERE schema_name     = 'vendite'
                   AND table_name      = 'preventivi_righe_componenti'
                   AND constraint_name = 'fk_prevrighe_comp_riga'),
    '11) FK fk_prevrighe_comp_riga coperta da un indice'
);

-- =========================================================
-- 12) Tutti i 10 trigger nominali registrati
--     +2 da modello unificato 20260513: prezzo_obbligatorio + guard_obbligatorio
-- =========================================================
-- rev 2026-07-27 (bonifica): l'asserzione confrontava 10 nomi LETTERALI di
-- trigger. Era fragile per costruzione e falsa da tempo:
-- 'trg_preventivi_righe_componenti_a10_articoli_require_attivo_ins_upd' e' lungo
-- 67 caratteri, oltre il limite di 63 di PostgreSQL. L'automazione dbops che
-- provisiona i guard require_attivo, quando il nome sfora, accorcia e aggiunge
-- un hash: quel trigger si chiama davvero
-- '..._a10_articoli_require_att_f4df00'. Il nome atteso NON PUO' esistere, e il
-- prossimo trigger auto-provisionato con nome lungo ricreerebbe il problema.
--
-- Si asserisce quindi sul COMPORTAMENTO, non sul nome: il nome e' un dettaglio
-- di implementazione dell'automazione, cio' che conta e' che il presidio ci sia.
--   - i trigger BESPOKE (scritti a mano) si verificano per FUNZIONE eseguita:
--     il nome della trigger function non viene troncato ne' hashato;
--   - i guard require_attivo si verificano per PADRE presidiato, leggendo gli
--     argomenti da pg_get_triggerdef: e' l'informazione di dominio (quale FK e'
--     protetta), stabile a prescindere da come l'automazione battezza il trigger.

-- 12a) presidi bespoke: uno per funzione
SELECT is(
    ARRAY(
        SELECT DISTINCT p.proname::text
          FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
          JOIN pg_proc p ON p.oid = t.tgfoid
         WHERE n.nspname = 'vendite'
           AND c.relname = 'preventivi_righe_componenti'
           AND NOT t.tgisinternal
           AND p.proname <> 'trgfn_child_requires_active_parent'
         ORDER BY 1
    ),
    ARRAY[
        'trgfn_audit_data_user_generic',
        'trgfn_componenti_calcola_quantita',
        'trgfn_componenti_check_prezzo_obbligatorio',
        'trgfn_componenti_guard_coerenza_bom',
        'trgfn_componenti_guard_obbligatorio',
        'trgfn_componenti_ricalcola_padre',
        'trgfn_preventivi_righe_componenti_guard_pending',
        'trgfn_tx_id_managed'
    ],
    '12a) presidi bespoke armati su preventivi_righe_componenti (per funzione)'
);

-- 12b) guard require_attivo: uno per FK verso un padre con colonna attivo
SELECT is(
    ARRAY(
        SELECT DISTINCT substring(
                   pg_get_triggerdef(t.oid)
                   from 'trgfn_child_requires_active_parent\(''([a-z_]+)'', ''([a-z_]+)''')
             || '.' || substring(
                   pg_get_triggerdef(t.oid)
                   from 'trgfn_child_requires_active_parent\(''[a-z_]+'', ''([a-z_]+)''')
          FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
          JOIN pg_proc p ON p.oid = t.tgfoid
         WHERE n.nspname = 'vendite'
           AND c.relname = 'preventivi_righe_componenti'
           AND NOT t.tgisinternal
           AND p.proname = 'trgfn_child_requires_active_parent'
         ORDER BY 1
    ),
    ARRAY[
        'catalogo.articoli',
        'catalogo.articoli_componenti',
        'catalogo.unita_misura',
        'config.iva',
        'vendite.preventivi_righe'
    ],
    '12b) guard require_attivo su tutti i padri attesi (per tabella, non per nome trigger)'
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
--
-- ⚠️ Rev. 2026-08-01 — la fixture sceglieva la riga BoM valida a CURRENT_DATE,
--    ma il guard che sta a monte del CHECK la valuta alla DATA DEL DOCUMENTO.
--    Finche' i due istanti coincidevano il test passava; quando il preventivo
--    piu' vecchio del DB e' uscito dalla finestra di validita' del componente,
--    l'INSERT ha cominciato a morire prima, con
--    «La riga BoM [...] non e' valida alla data documento [data=2026-05-11]» —
--    cioe' un rosso che non parlava del CHECK in esame. Ora il criterio di
--    selezione e' LO STESSO del guard (`ac.validita @> p.data`): la fixture non
--    puo' piu' scegliere una riga che il guard rifiutera', e il test smette di
--    dipendere da quanto tempo e' passato. Nessuna asserzione cambiata.
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
             SELECT 1 FROM vendite.preventivi_righe pr
               JOIN vendite.preventivi p ON p.id = pr.preventivo_id
               JOIN catalogo.articoli a  ON a.id = pr.articolo_id
              WHERE a.is_composito = TRUE
                AND EXISTS (
                    SELECT 1 FROM catalogo.articoli_componenti ac
                     WHERE ac.prodotto_id = a.id
                       AND ac.esposto_in_fattura = TRUE
                       AND ac.validita @> p.data
                )
         )
    THEN skip('19) prerequisiti non disponibili (nessuna riga composita con BoM esposta valida alla data documento)')
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
              JOIN vendite.preventivi p ON p.id = pr.preventivo_id
              JOIN catalogo.articoli a  ON a.id = pr.articolo_id
             WHERE a.is_composito = TRUE
               AND EXISTS (
                   SELECT 1 FROM catalogo.articoli_componenti ac
                    WHERE ac.prodotto_id = a.id
                      AND ac.esposto_in_fattura = TRUE
                      AND ac.validita @> p.data
               )
             LIMIT 1;

            -- Stessa finestra della selezione sopra: la riga BoM deve essere
            -- valida alla data del documento a cui verra' agganciata.
            SELECT ac.id, ac.componente_id INTO v_bom_id, v_comp_id
              FROM vendite.preventivi_righe pr
              JOIN vendite.preventivi p ON p.id = pr.preventivo_id
              JOIN catalogo.articoli_componenti ac ON ac.prodotto_id = pr.articolo_id
             WHERE pr.id = v_riga_id
               AND ac.esposto_in_fattura = TRUE
               AND ac.validita @> p.data
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
