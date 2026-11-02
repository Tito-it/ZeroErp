-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard MODALITA' A (brief-preventivi-ordini.md D9) sul trigger
--       vendite.trgfn_preventivi_righe_set_natura_vendita (20260609-02).
--       ⚠️ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3a): quella
--       funzione e' ritirata. La natura la scrive script.trgfn_righe_natura_vendita
--       (_a10_natura_vendita_ins_upd), il blocco della ricorrenza e' il motivo 2 di
--       script.fn_check_articolo_riga (_a10_regole_articolo_ins_upd), stesso codice e
--       stessa frase. L'ordine «lock prima, poi natura» del test 10 vale identico.
--       Un articolo la cui natura ha destinazione_tipo='CONTRATTO' (ricorrenza)
--       NON puo' essere inserito su un preventivo: blocco fail-fast
--       all'inserimento riga con E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA.
--       La ricorrenza viaggia solo su offerta->contratto.
--
-- Il blocco e' DATA-DRIVEN su config.nature_vendita.destinazione_tipo (non
-- hardcoda il codice della natura). Resta intatta la derivazione/congelamento
-- della natura dall'articolo (no override operatore).
--
-- Indice test (1..11):
--   Sanity:
--   1) SERVIZIO_RICORRENTE mappa a destinazione_tipo='CONTRATTO'
--   2) E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA registrato in messaggi_errore
--   Fixture:
--   3) preventivo DRAFT + 3 articoli distinti (ricorrente + MERCE + una tantum) disponibili
--   Comportamento:
--   4) INSERT riga con articolo a natura CONTRATTO -> BLOCCO (E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA)
--   5) INSERT riga con articolo a natura MERCE -> ammessa
--   6) natura ereditata e congelata sulla riga = MERCE (no override)
--   7) UPDATE OF articolo_id verso articolo ricorrente -> BLOCCO
--   Lock della colonna (2026-08-21):
--   8) E_PREV_RIGA_NATURA_IMMUTABILE registrato in messaggi_errore
--   9) UPDATE della SOLA natura_vendita_id -> BLOCCO (lock di colonna)
--  10) UPDATE OF articolo_id verso articolo NON ricorrente -> ammesso
--      (il lock non deve intralciare l'ereditarieta')
--  11) ... e la natura si riallinea da sola all'articolo nuovo
--
-- ⚠️ I test 9 e 10 dipendono dal trigger trg_preventivi_righe_a10_lock_columns_upd,
--    che NON e' scritto a mano: lo genera l'automazione LOCK_COLUMNS
--    (dbops.fn_run_automations_lock_columns) dalla riga aggiunta il 2026-08-21 a
--    dbops.automation_lock_columns. Finche' quella migrazione non e' applicata e
--    l'automazione non e' passata, il test 9 e' ROSSO: e' atteso, non e' una
--    regressione.
--
-- ⚠️ Il test 10 e' il presidio dell'ORDINE ALFABETICO fra i due BEFORE ROW.
--    `trg_preventivi_righe_a10_lock_columns_upd` precede
--    `trg_preventivi_righe_a10_natura_vendita_ins_upd`, quindi il lock legge
--    la natura NON ancora riscritta dall'ereditarieta' e il cambio articolo passa.
--    Se qualcuno rinominasse i due trigger invertendone l'ordine, il lock
--    bloccherebbe anche il cambio articolo legittimo: il test 10 e' l'unica cosa
--    che se ne accorgerebbe.
--
-- Nota: il ramo "articolo a natura NULL (legacy pre-backfill)" non e' piu'
-- testabile da quando catalogo.articoli.natura_vendita_id e' NOT NULL (D3,
-- 20260609-03/04): nessun articolo puo' avere natura NULL, quindi lo stato non
-- e' rappresentabile. Il ramo NULL del trigger resta come difesa ma e'
-- irraggiungibile a regime.
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

SELECT plan(11);

-- ============================================================
-- 1) Sanity seed: SERVIZIO_RICORRENTE -> destinazione_tipo CONTRATTO
-- ============================================================
SELECT is(
    (SELECT destinazione_tipo FROM config.nature_vendita
      WHERE codice_interno='SERVIZIO_RICORRENTE'),
    'CONTRATTO',
    '1) seed: SERVIZIO_RICORRENTE -> destinazione_tipo=CONTRATTO'
);

-- ============================================================
-- 2) Codice errore registrato
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM config.messaggi_errore
            WHERE codice='E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA'),
    '2) E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA registrato'
);

-- ============================================================
-- Fixture: riferimenti + preventivo DRAFT + 2 articoli distinti
-- ============================================================
-- ⛔ rev 2026-10-13: anche il cliente e l'azienda si COSTRUISCONO. Prima si
--   pescavano il primo billing account e il primo emittente attivo: su un
--   database ricostruito non ce ne sono, e la fixture non creava il preventivo
--   (test 3 rosso, e con lui tutti quelli a valle). Il mondo apre anche il
--   contesto sull'operatore che lo ha costruito.
CREATE TEMP TABLE tmp_nat_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('natura ricorrente preventivo');

CREATE TEMP TABLE tmp_nat_refs AS
SELECT
    (SELECT m.billing_account_id FROM tmp_nat_mondo m) AS billing_account_id,
    (SELECT m.utility_id         FROM tmp_nat_mondo m) AS utility_id,
    (SELECT m.istanza_utility_id FROM tmp_nat_mondo m) AS istanza_utility_id,
    -- 🔴 rev 2026-10-13 (brief-db-articoli-ammessi-per-documento A-9): i tre
    --   articoli si COSTRUISCONO. Prima si pescavano i primi tre del catalogo
    --   per id e la fixture ne cambiava la natura: i primi per id sono gli
    --   articoli-onere del seed (00000000-…-e1), e un onere non puo' prendere
    --   la natura MERCE (catalogo.trgfn_articoli_guard_onere_natura,
    --   20261013-05). Riclassificare un articolo del seed era comunque un
    --   difetto della fixture: il mondo si costruisce, non si cerca.
    -- La natura si sceglie alla nascita: A=ricorrente (CONTRATTO), B=MERCE.
    dbops.fn_pgtap_crea_articolo('PGT-NATRIC-A', false,
        p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                                 WHERE codice_interno='SERVIZIO_RICORRENTE')) AS articolo_a_id,
    dbops.fn_pgtap_crea_articolo('PGT-NATRIC-B', false,
        p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                                 WHERE codice_interno='MERCE')) AS articolo_b_id,
    -- Terzo articolo per il test 10: serve un bersaglio di cambio articolo che
    -- NON sia ricorrente, altrimenti a bloccare sarebbe il guard MODALITA' A e
    -- non si vedrebbe se il lock lascia passare. C = una tantum (destinazione
    -- COMMESSA): il guard MODALITA' A lo lascia passare.
    dbops.fn_pgtap_crea_articolo('PGT-NATRIC-C', false,
        p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                                 WHERE codice_interno='SERVIZIO_UNA_TANTUM')) AS articolo_c_id,
    (SELECT s.id FROM config.stati_doc_preventivi s
      WHERE s.codice='DRAFT' AND s.attivo IS TRUE LIMIT 1) AS stato_draft_id,
    (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
    (SELECT m.emittente_fiscale_id FROM tmp_nat_mondo m) AS emittente_fiscale_id,
    (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
      ORDER BY i.id LIMIT 1) AS iva_id,
    (SELECT id FROM config.nature_vendita WHERE codice_interno='SERVIZIO_RICORRENTE') AS natura_ric_id,
    (SELECT id FROM config.nature_vendita WHERE codice_interno='MERCE') AS natura_merce_id,
    (SELECT id FROM config.nature_vendita WHERE codice_interno='SERVIZIO_UNA_TANTUM') AS natura_ut_id;

INSERT INTO vendite.preventivi (
    numero, rev,
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data, emittente_fiscale_id, storicizza, meta)
SELECT 'PGTAP-NAT-RIC', 0,
       r.billing_account_id, r.istanza_utility_id, r.utility_id,
       DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
       r.stato_draft_id, DATE '2080-01-01', r.emittente_fiscale_id, false,
       jsonb_build_object('test_scope','pgtap_guard_natura_ricorrente')
  FROM tmp_nat_refs r
 WHERE r.billing_account_id IS NOT NULL AND r.stato_draft_id IS NOT NULL
   AND r.articolo_a_id IS NOT NULL AND r.articolo_b_id IS NOT NULL;

SELECT ok(
    EXISTS(SELECT 1 FROM vendite.preventivi WHERE numero='PGTAP-NAT-RIC'),
    '3) fixture: preventivo DRAFT creato + 2 articoli distinti disponibili'
);

-- ============================================================
-- 4) INSERT con articolo a natura CONTRATTO -> BLOCCO
-- ============================================================
SELECT throws_like(
    format(
        $$INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
          VALUES (%s, %L::uuid, %s, 10, 1)$$,
        (SELECT id FROM vendite.preventivi WHERE numero='PGTAP-NAT-RIC'),
        (SELECT articolo_a_id FROM tmp_nat_refs),
        (SELECT iva_id FROM tmp_nat_refs)
    ),
    '%servizio ricorrente%',
    '4) INSERT articolo ricorrente -> bloccato (E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA)'
);

-- ============================================================
-- 5) INSERT con articolo a natura MERCE -> ammessa
-- ============================================================
SELECT lives_ok(
    format(
        $$INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id, prezzo_unitario, qta_operativa)
          VALUES (%s, %L::uuid, %s, 10, 1)$$,
        (SELECT id FROM vendite.preventivi WHERE numero='PGTAP-NAT-RIC'),
        (SELECT articolo_b_id FROM tmp_nat_refs),
        (SELECT iva_id FROM tmp_nat_refs)
    ),
    '5) INSERT articolo MERCE -> ammesso'
);

-- ============================================================
-- 6) natura ereditata e congelata sulla riga = MERCE
-- ============================================================
SELECT is(
    (SELECT pr.natura_vendita_id
       FROM vendite.preventivi_righe pr
       JOIN vendite.preventivi p ON p.id = pr.preventivo_id
      WHERE p.numero='PGTAP-NAT-RIC'
        AND pr.articolo_id = (SELECT articolo_b_id FROM tmp_nat_refs)
      LIMIT 1),
    (SELECT natura_merce_id FROM tmp_nat_refs),
    '6) natura derivata e congelata sulla riga = MERCE (no override)'
);

-- ============================================================
-- 7) UPDATE OF articolo_id verso articolo ricorrente -> BLOCCO
--    (la riga MERCE inserita al punto 5 cambia articolo verso quello ricorrente)
-- ============================================================
SELECT throws_like(
    format(
        $$UPDATE vendite.preventivi_righe SET articolo_id = %L::uuid
           WHERE id = (SELECT pr.id FROM vendite.preventivi_righe pr
                         JOIN vendite.preventivi p ON p.id = pr.preventivo_id
                        WHERE p.numero='PGTAP-NAT-RIC'
                          AND pr.articolo_id = %L::uuid LIMIT 1)$$,
        (SELECT articolo_a_id FROM tmp_nat_refs),
        (SELECT articolo_b_id FROM tmp_nat_refs)
    ),
    '%servizio ricorrente%',
    '7) UPDATE OF articolo_id verso ricorrente -> bloccato'
);

-- ============================================================
-- 8) Codice errore del lock registrato
--    Sanity sul seed: senza la riga in config.messaggi_errore il lock
--    solleverebbe con un segnaposto irrisolto invece che con la sua frase.
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM config.messaggi_errore
            WHERE codice='E_PREV_RIGA_NATURA_IMMUTABILE'),
    '8) E_PREV_RIGA_NATURA_IMMUTABILE registrato'
);

-- ============================================================
-- 9) UPDATE della SOLA natura_vendita_id -> BLOCCO
--    E' il buco che il lock chiude: il trigger di ereditarieta' e' agganciato a
--    UPDATE OF articolo_id, quindi un UPDATE che tocca solo questa colonna non
--    lo faceva scattare e la natura si staccava dall'articolo — aggirando anche
--    il guard MODALITA' A verificato ai punti 4 e 7.
--    Il pattern si ferma PRIMA del segnaposto %s del messaggio.
-- ============================================================
SELECT throws_like(
    format(
        $$UPDATE vendite.preventivi_righe SET natura_vendita_id = %s
           WHERE id = (SELECT pr.id FROM vendite.preventivi_righe pr
                         JOIN vendite.preventivi p ON p.id = pr.preventivo_id
                        WHERE p.numero='PGTAP-NAT-RIC'
                          AND pr.articolo_id = %L::uuid
                        ORDER BY pr.id LIMIT 1)$$,
        (SELECT natura_ric_id FROM tmp_nat_refs),
        (SELECT articolo_b_id FROM tmp_nat_refs)
    ),
    '%natura di vendita della riga non%',
    '9) UPDATE della sola natura_vendita_id -> bloccato (E_PREV_RIGA_NATURA_IMMUTABILE)'
);

-- ============================================================
-- 10) UPDATE OF articolo_id verso articolo NON ricorrente -> AMMESSO
--     Presidio dell'ordine alfabetico fra i due BEFORE ROW: il lock
--     (trg_..._a10_lock_columns_upd) gira PRIMA dell'ereditarieta'
--     (trg_..._a10_natura_vendita_ins_upd), quindi legge la natura non
--     ancora riscritta e non vede nessuna modifica. Invertire i due nomi
--     bloccherebbe il cambio articolo legittimo, e questo e' il solo test che
--     se ne accorgerebbe.
-- ============================================================
SELECT CASE
    WHEN (SELECT articolo_c_id FROM tmp_nat_refs) IS NULL
        THEN skip('10) skip: servono almeno 3 articoli semplici attivi in catalogo')
    ELSE lives_ok(
        format(
            $$UPDATE vendite.preventivi_righe SET articolo_id = %L::uuid
               WHERE id = (SELECT pr.id FROM vendite.preventivi_righe pr
                             JOIN vendite.preventivi p ON p.id = pr.preventivo_id
                            WHERE p.numero='PGTAP-NAT-RIC'
                              AND pr.articolo_id = %L::uuid
                            ORDER BY pr.id LIMIT 1)$$,
            (SELECT articolo_c_id FROM tmp_nat_refs),
            (SELECT articolo_b_id FROM tmp_nat_refs)
        ),
        '10) UPDATE OF articolo_id verso articolo non ricorrente -> ammesso col lock attivo'
    )
END;

-- ============================================================
-- 11) ... e la natura si e' riallineata da sola all'articolo nuovo
--     Il lock blocca la scrittura MANUALE, non l'ereditarieta': se questo
--     fallisse dopo un 10) verde, vorrebbe dire che il lock ha lasciato passare
--     il cambio articolo ma il trigger di ereditarieta' non ha piu' riscritto.
-- ============================================================
SELECT CASE
    WHEN (SELECT articolo_c_id FROM tmp_nat_refs) IS NULL
        THEN skip('11) skip: servono almeno 3 articoli semplici attivi in catalogo')
    ELSE is(
        (SELECT pr.natura_vendita_id
           FROM vendite.preventivi_righe pr
           JOIN vendite.preventivi p ON p.id = pr.preventivo_id
          WHERE p.numero='PGTAP-NAT-RIC'
            AND pr.articolo_id = (SELECT articolo_c_id FROM tmp_nat_refs)
          ORDER BY pr.id LIMIT 1),
        (SELECT natura_ut_id FROM tmp_nat_refs),
        '11) natura riallineata da sola all''articolo nuovo (SERVIZIO_UNA_TANTUM)'
    )
END;

SELECT * FROM finish();
ROLLBACK;
