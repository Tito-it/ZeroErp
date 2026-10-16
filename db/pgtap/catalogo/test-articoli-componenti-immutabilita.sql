-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: catalogo.trgfn_articoli_componenti_block_modifica_struttura
-- Riferimento: migration 20260422-01 (DB-C-1 Sprint C prereq F2-BE-12).
--
-- Contesto:
--   BoM immutabile. DELETE vietato. UPDATE dei campi di struttura
--   vietato. Ammessi solo:
--     - UPDATE valido_al (l'ordine delle date lo giudica il guard comune
--       script.trgfn_guard_date_validita, non questo trigger: 20260924-01)
--     - UPDATE campi note, meta, attivo
--     - UPDATE campi audit (gestiti da altri trigger)
--   Pattern admin: chiudi riga + inserisci nuova con valido_dal
--   successivo. L'EXCLUDE constraint ex_articoli_componenti_no_overlap
--   impedisce overlap tra versioni.
--
-- Indice test (1..18, senza 6 e 7: 16 asserzioni):
--    1. DELETE -> raise E_BOM_MODIFICA_VIETATA
--    2. UPDATE coeff_qta -> raise
--    3. UPDATE componente_id -> raise
--    4. UPDATE obbligatorio -> raise
--    5. UPDATE esposizione_in_fattura -> raise
--    6. (ritirato 2026-10-02: partecipa_qta non esiste piu', 20261002-60)
--    7. (ritirato 2026-10-02: determina_qta_padre non esiste piu', 20261002-60)
--    8. UPDATE valido_dal -> raise
--    9. UPDATE validita (daterange nativo) -> raise
--   10. UPDATE valido_al in avanti (chiusura) -> OK
--   11. UPDATE valido_al < valido_dal -> parla il guard comune
--       (E_DATA_AL_MINORE_DAL), non piu' E_BOM_VALIDO_AL_INVALIDO
--   12. UPDATE note_id -> OK
--   13. UPDATE meta -> OK
--   14. UPDATE attivo -> OK
--   15. UPDATE simultaneo valido_al + attivo -> OK
--   16. INSERT nuova riga con valido_dal successivo (no-overlap) -> OK
--   17. UPDATE valido_al = valido_dal su riga creata oggi (chiusura
--       same-day) -> OK [regressione bug 27-04-2026, drop CHECK
--       chk_articoli_componenti_valid_dates in 20260427-02]
--   18. validita riga chiusa same-day = [oggi+6, oggi+7) (range 1 giorno)
--
-- Fixture: uso articoli seed ART_TEST_BASE (prodotto) + ART_TEST_FALLBACK
-- (componente). Creo una riga BoM iniziale con valido_dal=oggi-30,
-- valido_al=oggi+30; i test di raise usano savepoint implicito di
-- throws_ok; i test OK (10, 12-15) fanno UPDATE effettivi e restano
-- visibili fino al ROLLBACK finale.
--
-- BEGIN + ROLLBACK isolamento completo.
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

SELECT plan(16);

-- =========================================================
-- Setup: riga BoM di partenza
-- =========================================================
-- ⛔ Gli articoli si COSTRUISCONO (2026-09-23). Fino a oggi questo file
--   pescava `ART_TEST_BASE` / `ART_TEST_FALLBACK`, che non stanno in nessun
--   changelog: sono due righe messe a mano su questa macchina (UUID …101 e
--   …102). Su un database ricostruito non esistono, e il file moriva nella
--   fixture — copertura zero, non parziale.
-- Il prodotto nasce is_composito=true: senza, il trigger
-- trgfn_articoli_componenti_guard_is_composito rifiuta l'INSERT.
CREATE TEMP TABLE _t_bom AS
SELECT
    dbops.fn_pgtap_crea_articolo('PGT-BOM-IMM-PRODOTTO',
                                 p_is_composito => true)   AS prodotto_id,
    dbops.fn_pgtap_crea_articolo('PGT-BOM-IMM-COMPONENTE') AS componente_id,
    (script.fn_data_operativa() - INTERVAL '30 days')::date  AS v_dal,
    (script.fn_data_operativa() + INTERVAL '30 days')::date  AS v_al;

CREATE TEMP TABLE _t_bom_riga (riga_id uuid);

WITH ins AS (
    INSERT INTO catalogo.articoli_componenti (
        prodotto_id, componente_id, coeff_qta, obbligatorio,
        esposizione_in_fattura, valido_dal, valido_al, attivo
    )
    SELECT prodotto_id, componente_id, 1, true, 'NASCOSTO', v_dal, v_al, true
      FROM _t_bom
    RETURNING id
)
INSERT INTO _t_bom_riga (riga_id)
SELECT id FROM ins;

-- =========================================================
-- 1) DELETE -> raise E_BOM_MODIFICA_VIETATA
-- =========================================================
SELECT throws_ok(
    format(
        $sql$ DELETE FROM catalogo.articoli_componenti WHERE id = %L::uuid $sql$,
        (SELECT riga_id FROM _t_bom_riga)
    ),
    NULL, NULL,
    '1. DELETE riga BoM -> raise E_BOM_MODIFICA_VIETATA'
);

-- =========================================================
-- 2) UPDATE coeff_qta -> raise
-- =========================================================
SELECT throws_ok(
    format(
        $sql$ UPDATE catalogo.articoli_componenti SET coeff_qta = 2 WHERE id = %L::uuid $sql$,
        (SELECT riga_id FROM _t_bom_riga)
    ),
    NULL, NULL,
    '2. UPDATE coeff_qta -> raise E_BOM_MODIFICA_VIETATA'
);

-- =========================================================
-- 3) UPDATE componente_id -> raise
-- =========================================================
-- Uso un secondo articolo-componente valido per evitare che il raise
-- avvenga per violazione FK invece che per il nostro trigger.
SELECT throws_ok(
    format(
        $sql$ UPDATE catalogo.articoli_componenti SET componente_id = %L::uuid WHERE id = %L::uuid $sql$,
        (SELECT prodotto_id FROM _t_bom),   -- swap (purche' sia uuid articolo valido diverso dal componente_id)
        (SELECT riga_id FROM _t_bom_riga)
    ),
    NULL, NULL,
    '3. UPDATE componente_id -> raise E_BOM_MODIFICA_VIETATA'
);

-- =========================================================
-- 4) UPDATE obbligatorio -> raise
-- =========================================================
SELECT throws_ok(
    format(
        $sql$ UPDATE catalogo.articoli_componenti SET obbligatorio = false WHERE id = %L::uuid $sql$,
        (SELECT riga_id FROM _t_bom_riga)
    ),
    NULL, NULL,
    '4. UPDATE obbligatorio -> raise E_BOM_MODIFICA_VIETATA'
);

-- =========================================================
-- 5) UPDATE esposizione_in_fattura -> raise
-- (con un valore a catalogo: la riga deve fallire per il guard, non per la FK)
-- =========================================================
SELECT throws_ok(
    format(
        $sql$ UPDATE catalogo.articoli_componenti SET esposizione_in_fattura = 'DESCRITTIVO' WHERE id = %L::uuid $sql$,
        (SELECT riga_id FROM _t_bom_riga)
    ),
    NULL, NULL,
    '5. UPDATE esposizione_in_fattura -> raise E_BOM_MODIFICA_VIETATA'
);

-- =========================================================
-- 6), 7) RITIRATI il 2026-10-02: provavano UPDATE di partecipa_qta e
-- determina_qta_padre, colonne ritirate dalla distinta (20261002-60,
-- brief-db-bom-flag-quantita-e-kit-in-fattura D-1). Numerazione degli altri
-- invariata.
-- =========================================================

-- =========================================================
-- 8) UPDATE valido_dal -> raise
-- =========================================================
SELECT throws_ok(
    format(
        $sql$ UPDATE catalogo.articoli_componenti
                 SET valido_dal = (SELECT v_dal - INTERVAL '1 day' FROM _t_bom)::date
               WHERE id = %L::uuid $sql$,
        (SELECT riga_id FROM _t_bom_riga)
    ),
    NULL, NULL,
    '8. UPDATE valido_dal -> raise E_BOM_MODIFICA_VIETATA'
);

-- =========================================================
-- 9) UPDATE validita (daterange nativo) -> raise
-- Difesa in profondita': benche' validita sia una colonna generata da
-- valido_dal/valido_al, il trigger a10 la include fra i campi
-- bloccati per simmetria.
-- =========================================================
SELECT throws_ok(
    format(
        $sql$ UPDATE catalogo.articoli_componenti
                 SET validita = daterange('2000-01-01'::date, '2001-01-01'::date, '[]')
               WHERE id = %L::uuid $sql$,
        (SELECT riga_id FROM _t_bom_riga)
    ),
    NULL, NULL,
    '9. UPDATE validita diretto -> raise E_BOM_MODIFICA_VIETATA'
);

-- =========================================================
-- 10) UPDATE valido_al in avanti (chiusura finestra) -> OK
-- Riduco la finestra chiudendo a metà: da oggi+30 a oggi+10.
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ UPDATE catalogo.articoli_componenti
                 SET valido_al = (script.fn_data_operativa() + INTERVAL '10 days')::date
               WHERE id = %L::uuid $sql$,
        (SELECT riga_id FROM _t_bom_riga)
    ),
    '10. UPDATE valido_al in avanti (chiusura finestra) -> OK'
);

-- =========================================================
-- 11) UPDATE valido_al < valido_dal -> parla il guard comune
-- valido_dal e' oggi-30; provo valido_al = oggi-60.
-- ⭐ rev 20260924-01 (brief-db-guard-date-validita §13): fino al 23-09 qui
--   rispondeva il ramo E_BOM_VALIDO_AL_INVALIDO di questo trigger, che in
--   ordine alfabetico (`…_a10_block_…` < `…_a10_date_validita_…`) precedeva il
--   guard comune. Il ramo era una copia della regola del periodo ed e'
--   ritirato: ora parla script.trgfn_guard_date_validita, come sulle altre
--   tabelle con la coppia di date. ⚠️ Prima era un throws_ok(NULL, NULL):
--   verde con QUALSIASI errore. Ora pretende la frase del guard comune.
-- =========================================================
SELECT throws_like(
    format(
        $sql$ UPDATE catalogo.articoli_componenti
                 SET valido_al = (script.fn_data_operativa() - INTERVAL '60 days')::date
               WHERE id = %L::uuid $sql$,
        (SELECT riga_id FROM _t_bom_riga)
    ),
    '%è inferiore alla data dal%',
    '11. UPDATE valido_al < valido_dal -> parla il guard comune (E_DATA_AL_MINORE_DAL)'
);

-- =========================================================
-- 12) UPDATE note_id -> OK (campo non di struttura)
-- note_id e' una FK opzionale; metto/tolgo NULL per verificare
-- che il trigger non intercetti il cambio.
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ UPDATE catalogo.articoli_componenti
                 SET note_id = NULL, note_target_tipo = NULL
               WHERE id = %L::uuid $sql$,
        (SELECT riga_id FROM _t_bom_riga)
    ),
    '12. UPDATE note_id/note_target_tipo (campi non di struttura) -> OK'
);

-- =========================================================
-- 13) UPDATE meta -> OK
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ UPDATE catalogo.articoli_componenti
                 SET meta = jsonb_build_object('test', 'pgtap')
               WHERE id = %L::uuid $sql$,
        (SELECT riga_id FROM _t_bom_riga)
    ),
    '13. UPDATE meta -> OK'
);

-- =========================================================
-- 14) UPDATE attivo -> OK (soft-off)
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ UPDATE catalogo.articoli_componenti
                 SET attivo = false
               WHERE id = %L::uuid $sql$,
        (SELECT riga_id FROM _t_bom_riga)
    ),
    '14. UPDATE attivo -> OK'
);

-- =========================================================
-- 15) UPDATE simultaneo valido_al + attivo -> OK
-- Riattivo e ristringo la finestra in una sola statement.
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ UPDATE catalogo.articoli_componenti
                 SET attivo = true,
                     valido_al = (script.fn_data_operativa() + INTERVAL '5 days')::date
               WHERE id = %L::uuid $sql$,
        (SELECT riga_id FROM _t_bom_riga)
    ),
    '15. UPDATE simultaneo valido_al + attivo -> OK'
);

-- =========================================================
-- 16) INSERT nuova riga con valido_dal successivo -> OK
-- Chiudo la riga esistente (gia' chiusa a script.fn_data_operativa()+5) e
-- inserisco una nuova riga con valido_dal successivo per verificare
-- che l'EXCLUDE constraint accetti il pattern chiudi+inserisci.
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ INSERT INTO catalogo.articoli_componenti (
                  prodotto_id, componente_id, coeff_qta,
                  obbligatorio, esposizione_in_fattura,
                  valido_dal, valido_al, attivo
              )
              SELECT prodotto_id, componente_id, 2, true, 'NASCOSTO',
                     (script.fn_data_operativa() + INTERVAL '6 days')::date,
                     NULL,
                     true
                FROM _t_bom $sql$
    ),
    '16. INSERT nuova riga con valido_dal successivo (no-overlap) -> OK'
);

-- =========================================================
-- 17) UPDATE valido_al = valido_dal su riga appena creata -> OK
-- Regressione bug 27-04-2026: il CHECK strict
-- chk_articoli_componenti_valid_dates (valido_al > valido_dal) bloccava
-- la chiusura same-day di una riga BoM appena inserita facendo cadere
-- il flow FE in errore tecnico SQLSTATE 23514. Drop del CHECK in
-- 20260427-02 (codice morto: all'epoca trgfn_set_validita, oggi il guard
-- comune delle date, gia' rifiuta < ; il daterange sotto rifiuterebbe con
-- 22000). Il trigger block_modifica_struttura ammette
-- NEW.valido_al = OLD.valido_dal (controllo strict <), quindi il pattern
-- "Chiudi riga oggi" su una riga con valido_dal=oggi passa.
-- Targeting: la riga inserita in case 16 (UNIQUE
-- prodotto_id+componente_id+valido_dal).
-- =========================================================
SELECT lives_ok(
    $sql$ UPDATE catalogo.articoli_componenti
             SET valido_al = (script.fn_data_operativa() + INTERVAL '6 days')::date
           WHERE prodotto_id   = (SELECT prodotto_id   FROM _t_bom)
             AND componente_id = (SELECT componente_id FROM _t_bom)
             AND valido_dal    = (script.fn_data_operativa() + INTERVAL '6 days')::date $sql$,
    '17. UPDATE valido_al = valido_dal su riga creata oggi (chiusura same-day) -> OK'
);

-- =========================================================
-- 18) Verifica che la canonicalizzazione daterange su [X, X] da '[]'
-- produca '[X, X+1)' (range 1 giorno) -- non degenere/empty.
-- La colonna generata validita si ricalcola a ogni UPDATE.
-- =========================================================
SELECT is(
    (SELECT validita
       FROM catalogo.articoli_componenti
      WHERE prodotto_id   = (SELECT prodotto_id   FROM _t_bom)
        AND componente_id = (SELECT componente_id FROM _t_bom)
        AND valido_dal    = (script.fn_data_operativa() + INTERVAL '6 days')::date),
    daterange(
        (script.fn_data_operativa() + INTERVAL '6 days')::date,
        (script.fn_data_operativa() + INTERVAL '7 days')::date,
        '[)'
    ),
    '18. validita riga chiusa same-day = [oggi+6, oggi+7) (range 1 giorno)'
);

SELECT * FROM finish();
ROLLBACK;
