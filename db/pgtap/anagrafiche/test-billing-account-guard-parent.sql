-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard dissociazione parent_account_id su billing_account
-- Funzione: anagrafiche.trgfn_billing_account_guard_normalize()
-- Trigger:  trg_billing_account_guard_normalize_ins_upd
--
-- Scenario:
--   1) Precondizioni: riferimenti config presenti
--   2) Setup: crea BA padre + BA figlio + commessa + attivita_fatturabili
--   3) Rimozione parent_account_id con attivita non fatturate → FALLISCE
--   4) Attivita fatturata → rimozione parent_account_id → OK
--   5) BA figlio senza attivita → rimozione parent_account_id → OK
--
-- Nota: usa un soggetto esistente dal DB per evitare la complessita
--       di creare soggetto + contatto + indirizzi dai guard obbligatori.
-- ------------------------------------------------------------

-- =========================================================
-- Cleanup iniziale (idempotente)
-- =========================================================
DO $$
DECLARE
    l_codici_commesse text[] := ARRAY[
        'TST-GUARD-PARENT-COMM-01'
    ];
    l_codici_ba text[];
BEGIN
    -- Cleanup attivita_fatturabili (via commessa)
    DELETE FROM vendite.attivita_fatturabili af
    WHERE af.commessa_id IN (
        SELECT c.id FROM vendite.commesse c WHERE c.codice = ANY(l_codici_commesse)
    );

    -- Cleanup commesse_attivita
    DELETE FROM vendite.commesse_attivita ca
    WHERE ca.commessa_id IN (
        SELECT c.id FROM vendite.commesse c WHERE c.codice = ANY(l_codici_commesse)
    );

    -- Cleanup commesse
    DELETE FROM vendite.commesse c
    WHERE c.codice = ANY(l_codici_commesse);

    -- Cleanup billing_account (child prima del parent per FK)
    SELECT array_agg(ba.codice) INTO l_codici_ba
    FROM anagrafiche.billing_account ba
    JOIN anagrafiche.istanze_utilities iu ON iu.id = ba.istanza_utility_id
    WHERE iu.codice LIKE 'TST-GUARD-PARENT-%';

    IF l_codici_ba IS NOT NULL THEN
        -- Prima rimuovi parent_account_id dai figli (altrimenti FK blocca delete parent)
        UPDATE anagrafiche.billing_account ba
           SET parent_account_id = NULL
         WHERE ba.id IN (
            SELECT ba2.id
            FROM anagrafiche.billing_account ba2
            JOIN anagrafiche.istanze_utilities iu ON iu.id = ba2.istanza_utility_id
            WHERE iu.codice LIKE 'TST-GUARD-PARENT-%'
              AND ba2.parent_account_id IS NOT NULL
         );

        DELETE FROM anagrafiche.billing_account ba
        WHERE ba.istanza_utility_id IN (
            SELECT iu.id FROM anagrafiche.istanze_utilities iu
            WHERE iu.codice LIKE 'TST-GUARD-PARENT-%'
        );
    END IF;

    -- Cleanup istanze_utilities
    DELETE FROM anagrafiche.istanze_utilities iu
    WHERE iu.codice LIKE 'TST-GUARD-PARENT-%';
END;
$$;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⚠️ Questo file non apre una transazione propria: la riga va prima di plan().
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- =========================================================
-- 0) Precondizioni: recupera riferimenti esistenti dal DB
-- =========================================================
CREATE TEMP TABLE tmp_refs_guard_parent AS
SELECT
    iu_ref.soggetto_id,
    ba_ref.soggetto_ruolo_id,
    ba_ref.utility_id,
    (SELECT a.id
       FROM catalogo.articoli a
      WHERE a.attivo IS TRUE
      ORDER BY a.data_insert DESC NULLS LAST
      LIMIT 1) AS articolo_id,
    (SELECT u.id
       FROM catalogo.unita_misura u
      WHERE u.attivo IS TRUE
      ORDER BY u.id
      LIMIT 1) AS uom_id,
    (SELECT t.id
       FROM config.tipi_doc_fiscale t
      WHERE t.attivo IS TRUE
      ORDER BY t.id
      LIMIT 1) AS tipo_doc_fiscale_id,
    (SELECT v.id
       FROM config.valute v
      ORDER BY v.id
      LIMIT 1) AS valuta_id
FROM anagrafiche.billing_account ba_ref
JOIN anagrafiche.istanze_utilities iu_ref ON iu_ref.id = ba_ref.istanza_utility_id
WHERE ba_ref.parent_account_id IS NULL
  AND ba_ref.utility_id IS NOT NULL
ORDER BY ba_ref.id
LIMIT 1;

SELECT ok(
    (SELECT soggetto_id IS NOT NULL
        AND soggetto_ruolo_id IS NOT NULL
        AND utility_id IS NOT NULL
        AND articolo_id IS NOT NULL
        AND uom_id IS NOT NULL
        AND tipo_doc_fiscale_id IS NOT NULL
        AND valuta_id IS NOT NULL
     FROM tmp_refs_guard_parent),
    'Precondizioni: riferimenti config e anagrafiche presenti'
);

-- =========================================================
-- 1) Setup: crea istanze, BA padre, BA figli
-- =========================================================

-- 3 istanze: una per BA padre, una per BA figlio con attivita, una per BA figlio senza attivita
CREATE TEMP TABLE tmp_ids_guard (
    parent_ba_id bigint,
    child1_ba_id bigint,
    child2_ba_id bigint
);

DO $$
DECLARE
    v_soggetto_id uuid;
    v_utility_id integer;
    v_soggetto_ruolo_id bigint;
    v_parent_istanza_id bigint;
    v_child1_istanza_id bigint;
    v_child2_istanza_id bigint;
    v_parent_ba_id bigint;
    v_child1_ba_id bigint;
    v_child2_ba_id bigint;
    v_articolo_id uuid;
    v_uom_id bigint;
    v_tipo_doc_id bigint;
    v_valuta_id integer;
    v_commessa_id bigint;
    v_commessa_attivita_id bigint;
BEGIN
    SELECT soggetto_id, utility_id, soggetto_ruolo_id,
           articolo_id, uom_id, tipo_doc_fiscale_id, valuta_id
      INTO v_soggetto_id, v_utility_id, v_soggetto_ruolo_id,
           v_articolo_id, v_uom_id, v_tipo_doc_id, v_valuta_id
      FROM tmp_refs_guard_parent;

    -- Crea 3 istanze per lo stesso soggetto
    INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
    VALUES (v_soggetto_id, true, 'TST-GUARD-PARENT-IU-01')
    RETURNING id INTO v_parent_istanza_id;

    INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
    VALUES (v_soggetto_id, true, 'TST-GUARD-PARENT-IU-02')
    RETURNING id INTO v_child1_istanza_id;

    INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
    VALUES (v_soggetto_id, true, 'TST-GUARD-PARENT-IU-03')
    RETURNING id INTO v_child2_istanza_id;

    -- BA padre (stand-alone)
    INSERT INTO anagrafiche.billing_account (
        istanza_utility_id, soggetto_ruolo_id, utility_id, valido_dal
    ) VALUES (
        v_parent_istanza_id, v_soggetto_ruolo_id, v_utility_id, CURRENT_DATE
    ) RETURNING id INTO v_parent_ba_id;

    -- BA figlio 1 (con parent, avra attivita_fatturabili)
    INSERT INTO anagrafiche.billing_account (
        istanza_utility_id, soggetto_ruolo_id, utility_id, parent_account_id, valido_dal
    ) VALUES (
        v_child1_istanza_id, v_soggetto_ruolo_id, v_utility_id, v_parent_ba_id, CURRENT_DATE
    ) RETURNING id INTO v_child1_ba_id;

    -- BA figlio 2 (con parent, senza attivita)
    INSERT INTO anagrafiche.billing_account (
        istanza_utility_id, soggetto_ruolo_id, utility_id, parent_account_id, valido_dal
    ) VALUES (
        v_child2_istanza_id, v_soggetto_ruolo_id, v_utility_id, v_parent_ba_id, CURRENT_DATE
    ) RETURNING id INTO v_child2_ba_id;

    -- Commessa per BA figlio 1
    INSERT INTO vendite.commesse (
        codice, billing_account_id, utility_id
    ) VALUES (
        'TST-GUARD-PARENT-COMM-01', v_child1_ba_id, v_utility_id
    ) RETURNING id INTO v_commessa_id;

    -- Commessa attivita
    INSERT INTO vendite.commesse_attivita (
        commessa_id, segment_key, articolo_id, istanza_utility_id,
        data_attivita, uom_id, quantita,
        competenza_mese, competenza_dal, competenza_al,
        prezzo_snapshot, tipo_doc_fiscale_id, valuta_id
    ) VALUES (
        v_commessa_id, 'TST-SEG-01', v_articolo_id, v_child1_istanza_id,
        CURRENT_DATE, v_uom_id, 1,
        date_trunc('month', CURRENT_DATE)::date,
        date_trunc('month', CURRENT_DATE)::date,
        (date_trunc('month', CURRENT_DATE) + interval '1 month - 1 day')::date,
        10.00, v_tipo_doc_id, v_valuta_id
    ) RETURNING id INTO v_commessa_attivita_id;

    -- Attivita fatturabili (NON fatturata) per BA figlio 1
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id, billing_account_id, istanza_utility_id,
        data_attivita, quantita,
        competenza_mese, competenza_dal, competenza_al,
        commessa_id, commessa_attivita_id,
        tipo_doc_fiscale_id, valuta_id,
        fatturato, approvato
    ) VALUES (
        v_articolo_id, v_child1_ba_id, v_child1_istanza_id,
        CURRENT_DATE, 1,
        date_trunc('month', CURRENT_DATE)::date,
        date_trunc('month', CURRENT_DATE)::date,
        (date_trunc('month', CURRENT_DATE) + interval '1 month - 1 day')::date,
        v_commessa_id, v_commessa_attivita_id,
        v_tipo_doc_id, v_valuta_id,
        false, false
    );

    -- Salva gli ID per i test successivi
    INSERT INTO tmp_ids_guard (parent_ba_id, child1_ba_id, child2_ba_id)
    VALUES (v_parent_ba_id, v_child1_ba_id, v_child2_ba_id);
END;
$$;

SELECT ok(
    (SELECT count(*) FROM tmp_ids_guard) = 1,
    'Setup: BA padre + 2 figli + commessa + attivita creati'
);

-- =========================================================
-- 2) Verifica: BA figlio 1 ha attivita non fatturate
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
        FROM vendite.attivita_fatturabili af
        WHERE af.billing_account_id = (SELECT child1_ba_id FROM tmp_ids_guard)
          AND af.fatturato IS FALSE
    ),
    'BA figlio 1 ha attivita non fatturate'
);

-- =========================================================
-- 3) DB-02: rimozione parent con attivita non fatturate → FALLISCE
-- =========================================================
SELECT throws_ok(
    $$
      UPDATE anagrafiche.billing_account
         SET parent_account_id = NULL
       WHERE id = (SELECT child1_ba_id FROM tmp_ids_guard);
    $$,
    NULL,
    'Rimozione parent_account_id con attivita non fatturate: FALLISCE'
);

-- =========================================================
-- 4) Verifica: parent_account_id e' ancora presente (non e' stato rimosso)
-- =========================================================
SELECT ok(
    (SELECT parent_account_id IS NOT NULL
       FROM anagrafiche.billing_account
      WHERE id = (SELECT child1_ba_id FROM tmp_ids_guard)),
    'parent_account_id ancora presente dopo tentativo di rimozione fallito'
);

-- =========================================================
-- 5) DB-03: rimozione parent senza attivita → OK
-- =========================================================
SELECT lives_ok(
    $$
      UPDATE anagrafiche.billing_account
         SET parent_account_id = NULL
       WHERE id = (SELECT child2_ba_id FROM tmp_ids_guard);
    $$,
    'Rimozione parent_account_id senza attivita: OK'
);

-- =========================================================
-- 6) Dopo fatturazione, rimozione parent → OK
-- =========================================================
-- Marca tutte le attivita come fatturate, poi rimuovi parent
SELECT lives_ok(
    $$
      UPDATE vendite.attivita_fatturabili
         SET fatturato = true
       WHERE billing_account_id = (SELECT child1_ba_id FROM tmp_ids_guard);

      UPDATE anagrafiche.billing_account
         SET parent_account_id = NULL
       WHERE id = (SELECT child1_ba_id FROM tmp_ids_guard);
    $$,
    'Rimozione parent_account_id dopo fatturazione attivita: OK'
);

-- =========================================================
-- Cleanup finale
-- =========================================================
DO $$
BEGIN
    DELETE FROM vendite.attivita_fatturabili af
    WHERE af.commessa_id IN (
        SELECT c.id FROM vendite.commesse c WHERE c.codice = 'TST-GUARD-PARENT-COMM-01'
    );

    DELETE FROM vendite.commesse_attivita ca
    WHERE ca.commessa_id IN (
        SELECT c.id FROM vendite.commesse c WHERE c.codice = 'TST-GUARD-PARENT-COMM-01'
    );

    DELETE FROM vendite.commesse c
    WHERE c.codice = 'TST-GUARD-PARENT-COMM-01';

    DELETE FROM anagrafiche.billing_account ba
    WHERE ba.istanza_utility_id IN (
        SELECT iu.id FROM anagrafiche.istanze_utilities iu
        WHERE iu.codice LIKE 'TST-GUARD-PARENT-%'
    );

    DELETE FROM anagrafiche.istanze_utilities iu
    WHERE iu.codice LIKE 'TST-GUARD-PARENT-%';
END;
$$;

SELECT * FROM finish();
