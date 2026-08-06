-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard MODALITA' A (brief-preventivi-ordini.md D9) sul trigger
--       vendite.trgfn_preventivi_righe_set_natura_vendita (20260609-02).
--       Un articolo la cui natura ha destinazione_tipo='CONTRATTO' (ricorrenza)
--       NON puo' essere inserito su un preventivo: blocco fail-fast
--       all'inserimento riga con E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA.
--       La ricorrenza viaggia solo su offerta->contratto.
--
-- Il blocco e' DATA-DRIVEN su config.nature_vendita.destinazione_tipo (non
-- hardcoda il codice della natura). Resta intatta la derivazione/congelamento
-- della natura dall'articolo (no override operatore).
--
-- Indice test (1..7):
--   Sanity:
--   1) SERVIZIO_RICORRENTE mappa a destinazione_tipo='CONTRATTO'
--   2) E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA registrato in messaggi_errore
--   Fixture:
--   3) preventivo DRAFT + 2 articoli distinti (ricorrente + MERCE) disponibili
--   Comportamento:
--   4) INSERT riga con articolo a natura CONTRATTO -> BLOCCO (E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA)
--   5) INSERT riga con articolo a natura MERCE -> ammessa
--   6) natura ereditata e congelata sulla riga = MERCE (no override)
--   7) UPDATE OF articolo_id verso articolo ricorrente -> BLOCCO
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

SELECT plan(7);

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
CREATE TEMP TABLE tmp_nat_refs AS
SELECT
    (SELECT ba.id FROM anagrafiche.billing_account ba
      WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      ORDER BY ba.id LIMIT 1) AS billing_account_id,
    (SELECT ba.utility_id FROM anagrafiche.billing_account ba
      WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      ORDER BY ba.id LIMIT 1) AS utility_id,
    (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
      WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
    (SELECT a.id FROM catalogo.articoli a
      WHERE a.attivo IS TRUE AND a.is_composito = FALSE
      ORDER BY a.id LIMIT 1 OFFSET 0) AS articolo_a_id,
    (SELECT a.id FROM catalogo.articoli a
      WHERE a.attivo IS TRUE AND a.is_composito = FALSE
      ORDER BY a.id LIMIT 1 OFFSET 1) AS articolo_b_id,
    (SELECT s.id FROM config.stati_doc_preventivi s
      WHERE s.codice='DRAFT' AND s.attivo IS TRUE LIMIT 1) AS stato_draft_id,
    (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
    (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
      ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
    (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
      LIMIT 1) AS iva_id,
    (SELECT id FROM config.nature_vendita WHERE codice_interno='SERVIZIO_RICORRENTE') AS natura_ric_id,
    (SELECT id FROM config.nature_vendita WHERE codice_interno='MERCE') AS natura_merce_id;

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

-- Classifica gli articoli per il test: A=ricorrente (CONTRATTO), B=MERCE.
UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_ric_id FROM tmp_nat_refs)
 WHERE id = (SELECT articolo_a_id FROM tmp_nat_refs);
UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_merce_id FROM tmp_nat_refs)
 WHERE id = (SELECT articolo_b_id FROM tmp_nat_refs);

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

SELECT * FROM finish();
ROLLBACK;
