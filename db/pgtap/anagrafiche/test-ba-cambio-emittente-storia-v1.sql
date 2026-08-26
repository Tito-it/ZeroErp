-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: un billing account con storia non cambia emittente fiscale
-- Oggetti:
--   anagrafiche.fn_get_storia_emittente_ba()            (20260826-46)
--   anagrafiche.fn_guard_ba_cambio_emittente()          (20260826-47)
--   anagrafiche.trgfn_efba_guard_storia_emittente()     (20260826-49)
--
-- Elenco test (plan 8):
--  1) Precondizioni: riferimenti anagrafici presenti
--  2) BA appena nato: nessuna storia -> (0, 0)
--  3) BA appena nato: il cambio di emittente PASSA        [la finestra di correzione]
--  4) Dopo una commessa: la storia conta 1 commessa
--  5) Con storia: il cambio di emittente -> P0001         [il cancello]
--  6) ... e la frase nomina il cliente e i due conteggi
--  7) Emittente che non cambia davvero: PASSA             [manutenzione ordinaria]
--  8) Il trigger e' montato sui tre movimenti (INSERT/UPDATE/DELETE)
--
-- Scopo:
--  - il caso si FABBRICA (billing account nuovo, poi una commessa sopra):
--    un test che cerca fra i dati esistenti passa a vuoto in CI, dove il
--    database e' ricostruito da zero;
--  - ⭐ il 3) e il 5) sono la stessa chiamata sullo stesso cliente, prima e
--    dopo che gli sia passato del lavoro: e' la forma «b» decisa in D-1 —
--    libero finche' non c'e' storia, vietato dopo — e provarli in coppia e'
--    l'unico modo di dimostrare che la finestra di correzione esiste davvero
--    e non e' solo dichiarata;
--  - ⚠️ il guard si chiama DIRETTAMENTE, con `prima`/`dopo` espliciti: e' la
--    forma deterministica. Il percorso via trigger su due emittenti diversi
--    richiederebbe un secondo emittente fiscale nello scope dell'operatore,
--    che questa fixture non fabbrica; il montaggio del trigger e' presidiato
--    strutturalmente dall'8).
--
-- Piano: brief-db-billing-account-cambio-emittente, M5 (§6.5)
-- ------------------------------------------------------------

-- =========================================================
-- Cleanup iniziale (idempotente, FUORI dalla transazione)
-- =========================================================
DO $$
BEGIN
    DELETE FROM vendite.commesse c
     WHERE c.codice LIKE 'TST-BA-STORIA-%';

    DELETE FROM anagrafiche.emittenti_fiscali_billing_account efba
     WHERE efba.billing_account_id IN (
         SELECT ba.id FROM anagrafiche.billing_account ba
          WHERE ba.istanza_utility_id IN (
              SELECT iu.id FROM anagrafiche.istanze_utilities iu
               WHERE iu.codice LIKE 'TST-BA-STORIA-%'));

    DELETE FROM anagrafiche.billing_account ba
     WHERE ba.istanza_utility_id IN (
         SELECT iu.id FROM anagrafiche.istanze_utilities iu
          WHERE iu.codice LIKE 'TST-BA-STORIA-%');

    DELETE FROM anagrafiche.istanze_utilities iu
     WHERE iu.codice LIKE 'TST-BA-STORIA-%';
END;
$$;

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- =========================================================
-- 0) Riferimenti anagrafici, presi da un billing account esistente
-- =========================================================
-- ⚠️ ORDER BY esplicito: un LIMIT 1 senza non verifica, scommette.
CREATE TEMP TABLE tmp_refs_ba_storia AS
SELECT
    iu_ref.soggetto_id,
    ba_ref.soggetto_ruolo_id,
    ba_ref.utility_id,
    (SELECT cc.id FROM anagrafiche.categorie_clienti cc
      WHERE cc.codice_interno = 'STANDARD')          AS categoria_cliente_id,
    script.fn_pgtap_emittente_sr_operatore()         AS emittente_sr_ok,
    (SELECT sr.id
       FROM anagrafiche.soggetti_ruoli sr
      WHERE sr.id <> script.fn_pgtap_emittente_sr_operatore()
      ORDER BY sr.id
      LIMIT 1)                                       AS emittente_sr_altro
  FROM anagrafiche.billing_account ba_ref
  JOIN anagrafiche.istanze_utilities iu_ref ON iu_ref.id = ba_ref.istanza_utility_id
 WHERE ba_ref.utility_id IS NOT NULL
 ORDER BY ba_ref.id
 LIMIT 1;

SELECT ok(
    (SELECT soggetto_id IS NOT NULL
        AND soggetto_ruolo_id IS NOT NULL
        AND utility_id IS NOT NULL
        AND categoria_cliente_id IS NOT NULL
        AND emittente_sr_ok IS NOT NULL
        AND emittente_sr_altro IS NOT NULL
     FROM tmp_refs_ba_storia),
    'Precondizioni: riferimenti anagrafici presenti'
);

-- =========================================================
-- 1) Fixture: un billing account NUOVO, quindi senza storia
-- =========================================================
CREATE TEMP TABLE tmp_ids_ba_storia (billing_account_id bigint);

DO $$
DECLARE
    v_istanza_id bigint;
    v_ba_id      bigint;
    r            record;
BEGIN
    SELECT * INTO r FROM tmp_refs_ba_storia;

    -- ⭐ FINESTRA DIFFERITA: un'istanza utility e' una SAGA — un constraint
    --   trigger DEFERRABLE pretende almeno un satellite al COMMIT, e il
    --   preambolo obbligatorio (SET CONSTRAINTS ALL IMMEDIATE) lo farebbe
    --   scattare sul PRIMO insert, prima che il billing account possa
    --   esistere. Si apre la finestra, si costruisce, si richiude.
    SET CONSTRAINTS ALL DEFERRED;

    INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
    VALUES (r.soggetto_id, true, 'TST-BA-STORIA-IU-01')
    RETURNING id INTO v_istanza_id;

    -- ⭐ Il mapping verso l'emittente NON si scrive a mano: lo crea
    --   anagrafiche.trgfn_billing_account_link_ef, che aggancia il BA
    --   all'emittente dell'OPERATORE corrente. E' esattamente il percorso
    --   reale — un billing account non passa mai da uno stato «senza
    --   emittente» — ed e' anche il motivo per cui la finestra di
    --   correzione del 3) ha senso.
    INSERT INTO anagrafiche.billing_account (
        istanza_utility_id, soggetto_ruolo_id, utility_id, valido_dal,
        categoria_cliente_id
    ) VALUES (
        v_istanza_id, r.soggetto_ruolo_id, r.utility_id, CURRENT_DATE,
        r.categoria_cliente_id
    ) RETURNING id INTO v_ba_id;

    SET CONSTRAINTS ALL IMMEDIATE;

    INSERT INTO tmp_ids_ba_storia VALUES (v_ba_id);
END;
$$;

-- =========================================================
-- 2) BA appena nato: nessuna storia
-- =========================================================
SELECT is(
    (SELECT (s.n_fatture, s.n_commesse)::text
       FROM tmp_ids_ba_storia t,
            LATERAL anagrafiche.fn_get_storia_emittente_ba(t.billing_account_id) s),
    '(0,0)',
    'Un billing account appena nato non ha nessuna storia'
);

-- =========================================================
-- 3) ⭐ La FINESTRA DI CORREZIONE: senza storia il cambio passa
-- =========================================================
SELECT lives_ok(
    format(
        $q$SELECT anagrafiche.fn_guard_ba_cambio_emittente(%s, %s, %s)$q$,
        (SELECT billing_account_id FROM tmp_ids_ba_storia),
        (SELECT emittente_sr_ok    FROM tmp_refs_ba_storia),
        (SELECT emittente_sr_altro FROM tmp_refs_ba_storia)
    ),
    'Forma b: senza storia il billing account puo'' ancora cambiare emittente'
);

-- =========================================================
-- 4) Gli si attacca del lavoro: ora la storia c'e'
-- =========================================================
INSERT INTO vendite.commesse (codice, billing_account_id, utility_id)
SELECT 'TST-BA-STORIA-CMM-01', t.billing_account_id, r.utility_id
  FROM tmp_ids_ba_storia t, tmp_refs_ba_storia r;

SELECT is(
    (SELECT s.n_commesse
       FROM tmp_ids_ba_storia t,
            LATERAL anagrafiche.fn_get_storia_emittente_ba(t.billing_account_id) s),
    1::bigint,
    'La commessa appena creata entra nel conteggio della storia'
);

-- =========================================================
-- 5/6) ⛔ IL CANCELLO: con storia il cambio si blocca, e lo dice
-- =========================================================
SELECT throws_ok(
    format(
        $q$SELECT anagrafiche.fn_guard_ba_cambio_emittente(%s, %s, %s)$q$,
        (SELECT billing_account_id FROM tmp_ids_ba_storia),
        (SELECT emittente_sr_ok    FROM tmp_refs_ba_storia),
        (SELECT emittente_sr_altro FROM tmp_refs_ba_storia)
    ),
    'P0001',
    NULL,
    'Con una commessa a carico, il cambio di emittente e'' respinto'
);

-- ⚠️ La frase E' la posta in gioco: deve dire QUANTE fatture e QUANTE
--   commesse, altrimenti manda a cercare a mano cosa c'e' sotto.
SELECT throws_like(
    format(
        $q$SELECT anagrafiche.fn_guard_ba_cambio_emittente(%s, %s, %s)$q$,
        (SELECT billing_account_id FROM tmp_ids_ba_storia),
        (SELECT emittente_sr_ok    FROM tmp_refs_ba_storia),
        (SELECT emittente_sr_altro FROM tmp_refs_ba_storia)
    ),
    '%ha gi%0 fatture e 1 commesse%',
    'La frase nomina il cliente e i due conteggi'
);

-- =========================================================
-- 7) Manutenzione ordinaria: se l'emittente non cambia, non si blocca
-- =========================================================
-- E' la riga che tiene aperta la cancellazione di un mapping specifico quando
-- il gestore globale punta allo STESSO emittente: li' non si sposta nessun
-- documento, e bloccare sarebbe un falso positivo.
SELECT lives_ok(
    format(
        $q$SELECT anagrafiche.fn_guard_ba_cambio_emittente(%s, %s, %s)$q$,
        (SELECT billing_account_id FROM tmp_ids_ba_storia),
        (SELECT emittente_sr_ok    FROM tmp_refs_ba_storia),
        (SELECT emittente_sr_ok    FROM tmp_refs_ba_storia)
    ),
    'Un emittente che non cambia davvero non blocca niente, anche con storia'
);

-- =========================================================
-- 8) Il trigger e' montato, e sui TRE movimenti
-- =========================================================
-- ⚠️ Presidio strutturale: la CANCELLAZIONE e' il movimento che si dimentica,
--   ed e' proprio quello con cui il backend «sposta» un billing account
--   (DELETE + INSERT: non esiste nessun UPDATE sul mapping).
SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger t
       JOIN pg_class c     ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE NOT t.tgisinternal
        AND n.nspname = 'anagrafiche'
        AND c.relname = 'emittenti_fiscali_billing_account'
        AND t.tgname  = 'trg_emittenti_fiscali_ba_a10_guard_storia_emittente_ins_upd_dlt'
        -- 2 = BEFORE, 4 = INSERT, 8 = DELETE, 16 = UPDATE  (pg_trigger.tgtype)
        AND (t.tgtype & 2)  = 2
        AND (t.tgtype & 4)  = 4
        AND (t.tgtype & 8)  = 8
        AND (t.tgtype & 16) = 16),
    1,
    'Il guard e'' montato BEFORE su INSERT, UPDATE e DELETE'
);

SELECT * FROM finish();
ROLLBACK;
