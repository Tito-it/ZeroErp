-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: Simmetria L3 guard_pending su vendite.contratti_righe
--       Migrations: 20260518-01, 20260518-02, 20260601-02, 20260601-03
--       (20260601: guard generalizzato in script.trgfn_righe_guard_pending;
--        la funzione dedicata vendite.trgfn_contratti_righe_guard_pending
--        e' stata droppata, il trigger ripuntato al generico.)
--
-- Indice test (1..8):
--   Struttura:
--   1)  Colonne stato_approvazione_prezzo e pratica_approvazione_prezzo_id
--       presenti su contratti_righe
--   2)  Trigger trg_contratti_righe_a10_guard_pending_upd usa il generico
--       script.trgfn_righe_guard_pending
--   3)  Trigger trg_contratti_righe_a10_guard_pending_upd presente
--
--   Comportamento guard (COND: skip se fixture non creata):
--   4)  Riga stato=NULL → UPDATE prezzo_unitario OK (guard non attivo)
--   5)  Riga PENDING → UPDATE prezzo_unitario → raise E_RIGA_PREZZO_PENDENTE
--   6)  Riga PENDING → UPDATE stato_approvazione_prezzo PENDING→APPROVED → OK
--   7)  Riga PENDING → UPDATE pratica_approvazione_prezzo_id → OK
--   8)  Riga PENDING → UPDATE meta → OK
--
-- Nota: i test 4-8 saltano automaticamente se il contratto PGTAP_PND_CNT
--       non viene creato (mancanza dati prerequisito).
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

-- ============================================================
-- Setup fixture
-- ============================================================

-- BA senza tipi_utenze (evita guard tipo/classe), con emittente risolto dalla
-- stessa funzione usata dalla guard trgfn_contratti_guard_emittente_ba: cosi'
-- l'emittente_fiscale_id passato e' coerente per costruzione e il trigger
-- trgfn_contratti_default_emittente salta (GUC vuota in pgTAP).
CREATE TEMP TABLE tmp_pnd_ctx AS
SELECT
    ba.id                   AS ba_id,
    ba.istanza_utility_id,
    ba.utility_id,
    anagrafiche.fn_get_emittente_fiscale_pk(ba.id) AS emittente_fiscale_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT' LIMIT 1) AS id_draft,
    (SELECT id FROM catalogo.unita_misura WHERE attivo = TRUE ORDER BY id LIMIT 1) AS uom_id
  FROM anagrafiche.billing_account ba
 WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id)
 ORDER BY ba.id
 LIMIT 1;

-- Contratto DRAFT per i test (date 2074 per non collidere con altri pgTAP)
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al, emittente_fiscale_id)
SELECT 'PGTAP_PND_CNT', c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2074-01-01'::date, '2074-12-31'::date, c.emittente_fiscale_id
  FROM tmp_pnd_ctx c;

-- Articolo standalone (tipo_eccezione AGGIUNTA — non richiede listino)
CREATE TEMP TABLE tmp_pnd_art AS
SELECT a.id
  FROM catalogo.articoli a
 WHERE a.attivo = TRUE AND a.is_composito = FALSE
   -- rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): l'articolo
   --   sta nel PERIMETRO delle righe: senza tipologia (decide la natura, la utility del
   --   cliente non conta) e con UNA_TANTUM/FISSA ammessa, chiesto alla sede unica.
   AND a.listino_tipologia_id IS NULL
   AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                WHERE e.tipo_erogazione = 'UNA_TANTUM' AND e.fonte_quantita_attesa = 'FISSA')
 ORDER BY a.id
 LIMIT 1;

-- Riga contratto AGGIUNTA (prezzo valorizzato, qta_operativa richiesta
-- da trgfn_qta_from_operativa, tipo_eccezione richiesto NOT NULL dal refactor)
-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
INSERT INTO vendite.contratti_righe(
    contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
    tipo_erogazione)
SELECT c.id, a.id, 'AGGIUNTA', 100.00, 1.00, 'UNA_TANTUM'
  FROM vendite.contratti c, tmp_pnd_art a
 WHERE c.numero = 'PGTAP_PND_CNT';

-- ============================================================
SELECT plan(8);
-- ============================================================

-- ============================================================
-- 1) Colonne stato_approvazione_prezzo e pratica_approvazione_prezzo_id presenti
-- ============================================================
SELECT ok(
    (SELECT COUNT(*) = 2
       FROM information_schema.columns
      WHERE table_schema = 'vendite'
        AND table_name   = 'contratti_righe'
        AND column_name  IN ('stato_approvazione_prezzo', 'pratica_approvazione_prezzo_id')),
    '1) Colonne stato_approvazione_prezzo e pratica_approvazione_prezzo_id presenti'
);

-- ============================================================
-- 2) Trigger guard_pending ripuntato al generico script.trgfn_righe_guard_pending
--    (la funzione dedicata vendite.trgfn_contratti_righe_guard_pending e' droppata)
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class  c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
          JOIN pg_proc   p ON p.oid = t.tgfoid
          JOIN pg_namespace pn ON pn.oid = p.pronamespace
         WHERE n.nspname  = 'vendite'
           AND c.relname  = 'contratti_righe'
           AND t.tgname   = 'trg_contratti_righe_a10_guard_pending_upd'
           AND pn.nspname = 'script'
           AND p.proname  = 'trgfn_righe_guard_pending'
    ),
    '2) Trigger guard_pending usa il generico script.trgfn_righe_guard_pending'
);

-- ============================================================
-- 3) Trigger trg_contratti_righe_a10_guard_pending_upd presente
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'contratti_righe'
           AND t.tgname  = 'trg_contratti_righe_a10_guard_pending_upd'
           AND NOT t.tgisinternal
    ),
    '3) Trigger trg_contratti_righe_a10_guard_pending_upd presente'
);

-- ============================================================
-- 4) Riga stato=NULL → UPDATE prezzo_unitario OK
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_PND_CNT')
    THEN skip('Fixture PGTAP_PND_CNT non creata - skip', 1)
    ELSE lives_ok(
        $$UPDATE vendite.contratti_righe
             SET prezzo_unitario = 200.00
           WHERE contratto_id = (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_PND_CNT')
             AND stato_approvazione_prezzo IS NULL$$,
        '4) Riga stato=NULL → UPDATE prezzo_unitario OK (guard non attivo)'
    )
END;

-- ============================================================
-- 5) Riga PENDING → UPDATE prezzo_unitario → raise P0001
--    Setup: porta riga in PENDING via DO block (DML non ammesso in espressione SELECT)
-- ============================================================
DO $$
BEGIN
    UPDATE vendite.contratti_righe
       SET stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
     WHERE contratto_id = (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_PND_CNT');
END;
$$;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_PND_CNT')
    THEN skip('Fixture PGTAP_PND_CNT non creata - skip', 1)
    ELSE throws_ok(
        $$UPDATE vendite.contratti_righe
             SET prezzo_unitario = 999.00
           WHERE contratto_id = (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_PND_CNT')
             AND stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo$$,
        'P0001',
        NULL,
        '5) Riga PENDING → UPDATE prezzo_unitario → raise E_RIGA_PREZZO_PENDENTE'
    )
END;

-- ============================================================
-- 6) Riga PENDING → UPDATE stato PENDING→APPROVED → OK (transizione workflow)
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_PND_CNT')
    THEN skip('Fixture PGTAP_PND_CNT non creata - skip', 1)
    ELSE lives_ok(
        $$UPDATE vendite.contratti_righe
             SET stato_approvazione_prezzo = 'APPROVED'::config.stato_approvazione_prezzo
           WHERE contratto_id = (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_PND_CNT')
             AND stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo$$,
        '6) Riga PENDING → UPDATE stato→APPROVED OK (transizione workflow)'
    )
END;

-- ============================================================
-- 7) Riga PENDING → UPDATE pratica_approvazione_prezzo_id → OK
--    Dopo test 6 la riga è APPROVED: riporta in PENDING via DO block
-- ============================================================
DO $$
BEGIN
    UPDATE vendite.contratti_righe
       SET stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
     WHERE contratto_id = (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_PND_CNT');
END;
$$;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_PND_CNT')
    THEN skip('Fixture PGTAP_PND_CNT non creata - skip', 1)
    ELSE lives_ok(
        $$UPDATE vendite.contratti_righe
             SET pratica_approvazione_prezzo_id = NULL
           WHERE contratto_id = (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_PND_CNT')
             AND stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo$$,
        '7) Riga PENDING → UPDATE pratica_id OK (allowlist)'
    )
END;

-- ============================================================
-- 8) Riga PENDING → UPDATE meta → OK
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_PND_CNT')
    THEN skip('Fixture PGTAP_PND_CNT non creata - skip', 1)
    ELSE lives_ok(
        $$UPDATE vendite.contratti_righe
             SET meta = '{"note": "test pgtap"}'::jsonb
           WHERE contratto_id = (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_PND_CNT')
             AND stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo$$,
        '8) Riga PENDING → UPDATE meta OK (allowlist)'
    )
END;

SELECT * FROM finish();
ROLLBACK;
