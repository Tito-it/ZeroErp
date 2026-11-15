-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.contratti_righe_componenti + fn_contratto_riga_componenti_init
--
-- Indice test:
--   1)  Tabella esiste nello schema vendite
--   2)  Colonne obbligatorie presenti con tipo corretto
--   3)  PK pk_contrighe_comp esiste
--   4)  FK fk_contrighe_comp_riga (ON DELETE CASCADE) esiste
--   5)  FK fk_contrighe_comp_articolo_componente esiste
--   6)  FK fk_contrighe_comp_componente esiste
--   7)  UNIQUE uq_contrighe_comp_riga_art_comp esiste
--   8)  CHECK chk_contrighe_comp_quantita_nz: nome e definizione (quantita <> 0)
--   9)  Trigger trgfn_componenti_check_prezzo_obbligatorio registrato
--       (modello unificato: CHECK prezzo<>0 rimosso, sostituito da trigger condizionale)
--   10) CHECK chk_contrighe_comp_origine esiste
--   11) FK fk_contrighe_comp_riga coperta da un indice
--   12) Colonna quantita presente su contratti_righe (rename da quantita_fissa)
--   13) Tutti i 16 trigger registrati sulla tabella
--       (+2 da modello unificato: prezzo_obbligatorio + guard_obbligatorio)
--   14) Trigger propaga_qta registrato su contratti_righe
--   15) Trigger qta_from_operativa usa 'quantita' (non 'quantita_fissa')
--   16) fn_contratto_riga_componenti_init: p_riga_id NULL -> raise
--   17) fn_contratto_riga_componenti_init: p_emittente_sr_id NULL -> raise
--   18) fn_contratto_riga_componenti_init: riga inesistente -> raise
--   19) fn_contratto_riga_componenti_init: articolo non composito -> 0
--   20) fn_contratto_riga_componenti_init: quantita NULL -> 0 (riga a consumo, fonte non-FISSA)
--   21) fn_contratto_riga_componenti_init: idempotenza -> 0 alla seconda chiamata
--   22) CASCADE DELETE: struttura FK CASCADE verificata da constraint DDL
--   23) chk_contrighe_comp_origine: valore non ammesso -> errore CHECK
--   24) Trigger guard_pending registrato su contratti_righe_componenti
--   25) Guard pending: UPDATE struttura su PENDING -> raise
--   26) Invariante post-fix: righe FISSA con qta_operativa NOT NULL hanno quantita NOT NULL
--   27) trgfn_qta_from_operativa: short-circuit limitato a UPDATE (fix INSERT FISSA)
--   28) fn_contratto_riga_componenti_init: guard ESCLUSIONE composito -> 0,
--       nessun componente, riga padre conserva prezzo_unitario NULL
--       [skip se nessuna riga composito+ESCLUSIONE con quantita NOT NULL]
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

SELECT plan(37);

-- =========================================================
-- 1) Tabella esiste
-- =========================================================
SELECT has_table(
    'vendite', 'contratti_righe_componenti',
    '1) tabella vendite.contratti_righe_componenti esiste'
);

-- =========================================================
-- 2) Colonne chiave presenti
-- =========================================================
SELECT has_column('vendite', 'contratti_righe_componenti', 'id',                    '2a) colonna id');
SELECT has_column('vendite', 'contratti_righe_componenti', 'riga_contratto_id',     '2b) colonna riga_contratto_id');
SELECT has_column('vendite', 'contratti_righe_componenti', 'articolo_componente_id','2c) colonna articolo_componente_id');
SELECT has_column('vendite', 'contratti_righe_componenti', 'componente_id',         '2d) colonna componente_id');
SELECT has_column('vendite', 'contratti_righe_componenti', 'coeff_qta_snapshot',    '2e) colonna coeff_qta_snapshot');
SELECT has_column('vendite', 'contratti_righe_componenti', 'quantita',              '2f) colonna quantita');
SELECT has_column('vendite', 'contratti_righe_componenti', 'prezzo_unitario',       '2g) colonna prezzo_unitario');
SELECT has_column('vendite', 'contratti_righe_componenti', 'origine_prezzo',        '2h) colonna origine_prezzo');
SELECT has_column('vendite', 'contratti_righe_componenti', 'stato_approvazione_prezzo', '2i) colonna stato_approvazione_prezzo');
SELECT has_column('vendite', 'contratti_righe_componenti', 'tx_id',                 '2j) colonna tx_id');

-- =========================================================
-- 3) PK esiste
-- =========================================================
SELECT has_pk(
    'vendite', 'contratti_righe_componenti',
    '3) PK pk_contrighe_comp esiste'
);

-- =========================================================
-- 4) FK ON DELETE CASCADE verso contratti_righe
-- =========================================================
SELECT has_fk(
    'vendite', 'contratti_righe_componenti',
    '4) FK fk_contrighe_comp_riga esiste'
);

-- =========================================================
-- 5) FK verso articoli_componenti
-- =========================================================
SELECT col_is_fk(
    'vendite', 'contratti_righe_componenti', 'articolo_componente_id',
    '5) FK fk_contrighe_comp_articolo_componente esiste'
);

-- =========================================================
-- 6) FK verso articoli (componente_id)
-- =========================================================
SELECT col_is_fk(
    'vendite', 'contratti_righe_componenti', 'componente_id',
    '6) FK fk_contrighe_comp_componente esiste'
);

-- =========================================================
-- 7) UNIQUE (riga_contratto_id, articolo_componente_id)
-- =========================================================
SELECT has_unique(
    'vendite', 'contratti_righe_componenti',
    '7) UNIQUE uq_contrighe_comp_riga_art_comp esiste'
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
      WHERE c.conrelid = 'vendite.contratti_righe_componenti'::regclass
        AND c.conname  = 'chk_contrighe_comp_quantita_nz'),
    'CHECK ((quantita <> (0)::numeric))',
    '8) CHECK chk_contrighe_comp_quantita_nz: quantita <> 0'
);

-- =========================================================
-- 9) Trigger prezzo_obbligatorio registrato
--    Modello unificato (20260513-06/07): CHECK prezzo_unitario<>0 droppato,
--    sostituito da trigger condizionale (blocca solo per obbligatori).
-- =========================================================
SELECT has_trigger(
    'vendite', 'contratti_righe_componenti',
    'trg_contrighe_comp_a10_prezzo_obbligatorio_ins_upd',
    '9) trigger prezzo_obbligatorio registrato (CHECK rimosso, modello unificato)'
);

-- =========================================================
-- 10) CHECK origine_prezzo IN (...)
-- =========================================================
SELECT col_has_check(
    'vendite', 'contratti_righe_componenti', 'origine_prezzo',
    '10) CHECK chk_contrighe_comp_origine su origine_prezzo'
);

-- =========================================================
-- 11) FK riga_contratto_id coperta da un indice
--     L'indice dedicato ix_vendite_contrighe_comp_riga e' stato rimosso il 2026-07-27
--     (changeSet 20260727-37): era ridondante, perche' uq_contrighe_comp_riga_art_comp
--     ha riga_contratto_id come colonna leading e serve gia' ogni ricerca per riga,
--     ON DELETE CASCADE compreso.
--     Il test verifica ora la PROPRIETA' — la FK e' coperta — invece del nome
--     di un indice specifico: resta valido anche se l'indice coprente cambia.
-- =========================================================
SELECT ok(
    NOT EXISTS (SELECT 1 FROM dbops.vw_fk_senza_indice
                 WHERE schema_name     = 'vendite'
                   AND table_name      = 'contratti_righe_componenti'
                   AND constraint_name = 'fk_contrighe_comp_riga'),
    '11) FK fk_contrighe_comp_riga coperta da un indice'
);

-- =========================================================
-- 12) Rename quantita_fissa -> quantita su contratti_righe
-- =========================================================
SELECT has_column(
    'vendite', 'contratti_righe', 'quantita',
    '12) colonna quantita esiste su contratti_righe (rename da quantita_fissa)'
);

-- =========================================================
-- 13) Trigger registrati sulla tabella (16 attesi)
--     +2 da modello unificato 20260513: prezzo_obbligatorio, guard_obbligatorio
--     +1 dal 2026-10-05 (20261005-17): il lock «solo in bozza» a livello RIGA,
--        trg_contratti_righe_componenti_a05_doc_bozza_ins_upd_dlt
--        (brief-db-righe-esclusione-solo-non-si-vende §8.2 B3)
--     +2 dal 2026-11-13 (20261113-10, brief-db-provenienza-prezzo-segue-il-prezzo §8): la derivazione
--        della provenienza del prezzo (a20) e il guard sulla riga di listino (a10, AFTER).
-- =========================================================
SELECT is(
    (SELECT COUNT(DISTINCT trigger_name)::integer
       FROM information_schema.triggers
      WHERE event_object_schema = 'vendite'
        AND event_object_table  = 'contratti_righe_componenti'),
    16,
    '13) 16 trigger registrati su contratti_righe_componenti'
);

-- =========================================================
-- 14) Trigger propaga_qta su contratti_righe
-- =========================================================
SELECT has_trigger(
    'vendite', 'contratti_righe',
    'trg_contratti_righe_z90_propaga_qta_componenti_upd',
    '14) trigger propaga_qta registrato su contratti_righe'
);

-- =========================================================
-- 15) Trigger qta_from_operativa usa TG_ARGV 'quantita' (non 'quantita_fissa')
-- =========================================================
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'contratti_righe'
           AND t.tgname  = 'trg_contratti_righe_a10_qta_from_operativa_ins_upd'
           AND pg_get_triggerdef(t.oid) LIKE '%quantita_fissa%'
    ),
    '15) trigger qta_from_operativa non usa piu'' quantita_fissa come TG_ARGV'
);

-- =========================================================
-- 16) fn_contratto_riga_componenti_init: p_riga_id NULL -> raise
-- =========================================================
SELECT throws_like(
    $$ SELECT vendite.fn_contratto_riga_componenti_init(NULL, 1, script.fn_data_operativa()) $$,
    '%Parametro non valido%',
    '16) fn_contratto_riga_componenti_init: p_riga_id NULL -> raise E_PARAMETRO_INVALIDO'
);

-- =========================================================
-- 17) fn_contratto_riga_componenti_init: p_emittente_sr_id NULL -> raise
-- =========================================================
SELECT throws_like(
    $$ SELECT vendite.fn_contratto_riga_componenti_init(1, NULL, script.fn_data_operativa()) $$,
    '%Parametro non valido%',
    '17) fn_contratto_riga_componenti_init: p_emittente_sr_id NULL -> raise E_PARAMETRO_INVALIDO'
);

-- =========================================================
-- 18) fn_contratto_riga_componenti_init: riga inesistente -> raise
-- =========================================================
-- ⚠️ throws_like sulla frase, non throws_ok sul codice: tutti i raise di
--    script.fn_log_and_raise_error condividono SQLSTATE P0001, quindi il codice
--    non discrimina (stessa ragione di catalogo/test-guard-iva-reactivation-v1).
--    Il pattern SALTA l'id interpolato — il messaggio 897 e'
--    `Riga contratto %s non trovata.` — altrimenti si rompe al primo id diverso.
SELECT throws_like(
    $$ SELECT vendite.fn_contratto_riga_componenti_init(2147483647, 1, script.fn_data_operativa()) $$,
    '%Riga contratto %non trovata%',
    '18) fn_contratto_riga_componenti_init: riga inesistente -> raise E_CONTRATTO_RIGA_NON_TROVATA'
);

-- =========================================================
-- 19) fn_contratto_riga_componenti_init: articolo non composito -> 0
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
        SELECT 1 FROM vendite.contratti_righe cr
          JOIN catalogo.articoli a ON a.id = cr.articolo_id
         WHERE NOT COALESCE(a.is_composito, FALSE)
         LIMIT 1
    )
    THEN skip('19) nessuna riga contratto con articolo non composito disponibile')
    ELSE is(
        (SELECT vendite.fn_contratto_riga_componenti_init(
            (SELECT cr.id FROM vendite.contratti_righe cr
               JOIN catalogo.articoli a ON a.id = cr.articolo_id
              WHERE NOT COALESCE(a.is_composito, FALSE)
              LIMIT 1),
            1,
            script.fn_data_operativa()
        )),
        0,
        '19) fn_contratto_riga_componenti_init: articolo non composito -> RETURN 0'
    )
END;

-- =========================================================
-- 20) fn_contratto_riga_componenti_init: quantita NULL -> 0 (riga a consumo)
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
        SELECT 1 FROM vendite.contratti_righe
         WHERE quantita IS NULL
         LIMIT 1
    )
    THEN skip('20) nessuna riga contratto con quantita NULL disponibile')
    ELSE is(
        (SELECT vendite.fn_contratto_riga_componenti_init(
            (SELECT id FROM vendite.contratti_righe WHERE quantita IS NULL LIMIT 1),
            1,
            script.fn_data_operativa()
        )),
        0,
        '20) fn_contratto_riga_componenti_init: quantita NULL -> RETURN 0 (riga a consumo)'
    )
END;

-- =========================================================
-- 21) Idempotenza: seconda chiamata su riga gia' inizializzata -> 0
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
        SELECT 1 FROM vendite.contratti_righe_componenti LIMIT 1
    )
    THEN skip('21) nessun componente presente per test idempotenza')
    ELSE is(
        (SELECT vendite.fn_contratto_riga_componenti_init(
            (SELECT riga_contratto_id FROM vendite.contratti_righe_componenti LIMIT 1),
            1,
            script.fn_data_operativa()
        )),
        0,
        '21) fn_contratto_riga_componenti_init: idempotenza -> 0 alla seconda chiamata'
    )
END;

-- =========================================================
-- 22) CASCADE DELETE verificata da constraint DDL
-- =========================================================
SELECT pass('22) CASCADE DELETE: struttura FK CASCADE verificata da constraint DDL');

-- =========================================================
-- 23) CHECK origine_prezzo: valore non ammesso -> errore
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
        SELECT 1 FROM vendite.contratti_righe LIMIT 1
    )
    THEN skip('23) nessuna riga contratto disponibile per test CHECK origine')
    ELSE throws_like(
        $q$ INSERT INTO vendite.contratti_righe_componenti (
                riga_contratto_id, articolo_componente_id, componente_id,
                coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id
            ) VALUES (
                (SELECT id FROM vendite.contratti_righe LIMIT 1),
                (SELECT id FROM catalogo.articoli_componenti LIMIT 1),
                (SELECT componente_id FROM catalogo.articoli_componenti LIMIT 1),
                1, 1, 1, 'VALORE_NON_VALIDO', (SELECT a.uom_id FROM catalogo.articoli a WHERE a.id = (SELECT componente_id FROM catalogo.articoli_componenti LIMIT 1))
            ) $q$,
        '%',
        '23) INSERT con origine_prezzo non valido bloccato (CHECK o guard BoM)'
    )
END;

-- =========================================================
-- 24) Trigger guard_pending registrato su contratti_righe_componenti
-- =========================================================
SELECT has_trigger(
    'vendite', 'contratti_righe_componenti',
    'trg_contratti_righe_componenti_a10_guard_pending_upd',
    '24) trigger guard_pending L3 registrato su contratti_righe_componenti'
);

-- =========================================================
-- 25) Guard pending: UPDATE struttura su PENDING -> raise
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
        SELECT 1 FROM vendite.contratti_righe_componenti
         WHERE stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
         LIMIT 1
    )
    THEN skip('25) nessun componente PENDING disponibile per test guard L3')
    ELSE throws_like(
        $q$
        UPDATE vendite.contratti_righe_componenti
           SET prezzo_unitario = prezzo_unitario + 0.01
         WHERE stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
           AND id = (SELECT id FROM vendite.contratti_righe_componenti
                      WHERE stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
                      LIMIT 1)
        $q$,
        '%',
        '25) guard_pending blocca UPDATE struttura su componente PENDING'
    )
END;

-- =========================================================
-- 26) Invariante post-fix: righe FISSA con qta_operativa NOT NULL hanno quantita NOT NULL
--     (se fallisce su dati pre-fix, eseguire data fix manuale sulle righe corrotte)
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
        SELECT 1 FROM vendite.contratti_righe
         WHERE fonte_quantita_attesa = 'FISSA'
           AND qta_operativa IS NOT NULL
         LIMIT 1
    )
    THEN skip('26) nessuna riga FISSA con qta_operativa disponibile')
    ELSE ok(
        NOT EXISTS (
            SELECT 1 FROM vendite.contratti_righe
             WHERE fonte_quantita_attesa = 'FISSA'
               AND qta_operativa IS NOT NULL
               AND quantita IS NULL
        ),
        '26) invariante post-fix: riga FISSA con qta_operativa NOT NULL ha quantita NOT NULL'
    )
END;

-- =========================================================
-- 27) trgfn_qta_from_operativa: short-circuit limitato a UPDATE (fix INSERT FISSA)
--     Verifica strutturale: la funzione contiene il check TG_OP = 'UPDATE'
-- =========================================================
SELECT ok(
    (SELECT prosrc FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname = 'trgfn_qta_from_operativa')
    LIKE '%TG_OP%',
    '27) trgfn_qta_from_operativa: short-circuit contiene controllo TG_OP (fix INSERT FISSA)'
);

-- =========================================================
-- 28) Guard difensivo ESCLUSIONE: una riga contratto composita con
--     tipo_eccezione = ESCLUSIONE e quantita NOT NULL deve dare RETURN 0
--     (no-op), senza inserire componenti e senza violare il CHECK
--     chk_contrighe_prezzo_per_tipo_eccezione (prezzo padre resta NULL).
--     Senza il guard, l'init entrerebbe nel loop e il ricalcolo padre
--     (SUM figli) farebbe scattare il CHECK -> errore.
--     Data-dependent: skip se nessuna riga composito+ESCLUSIONE valida.
-- =========================================================
-- ⚠️ rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende): il caso non
--   esiste piu' per costruzione. Un'esclusione non porta quantita'
--   (chk_contrighe_esclusione_senza_dati, guard E_RIGA_ESCLUSIONE_CON_DATI), quindi
--   una riga composito+ESCLUSIONE con quantita' NOT NULL non si puo' scrivere, e
--   l'init su un'esclusione e' no-op gia' per la quantita' assente. Il test cercava
--   quella riga nei dati: oggi passerebbe solo per coincidenza. Si dichiara, non si
--   lascia verde a vuoto.
SELECT skip('28) composito+ESCLUSIONE con quantita'' NOT NULL: impossibile per costruzione dal 2026-10-04 (un''esclusione non porta quantita'')', 1);

SELECT * FROM finish();
ROLLBACK;
