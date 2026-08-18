-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Passo 3 (P-3) del cantiere «perimetro emittente»: il §2.2 di
-- anagrafiche.trgfn_billing_account_guard_normalize non confronta piu'
-- il solo codice fiscale.
-- Brief: docs/it/dev/work-in-progress/brief-db-perimetro-emittente-liste-e-gerarchia-ba.md §4, §11.1
--
-- Elenco test (plan 7):
--   0) PRECONDIZIONI: due soggetti distinti con CF + fixture creata
--   1) stesso soggetto, CF presente            -> PASSA  (nessuna regressione)
--   2) soggetti diversi, CF diversi            -> E_ID_FISCALI_DIVERSI (invariato)
--   3) * soggetti diversi, ENTRAMBI senza CF   -> E_PARENT_SOGGETTO_DIVERSO
--   4) * STESSO soggetto, senza CF             -> PASSA (il falso positivo evitato)
--   5) * padre fuori dal perimetro RLS         -> E_PARENT_NON_RAGGIUNGIBILE
--   6) padre inesistente                       -> E_PARENT_NON_RAGGIUNGIBILE
--
-- Scopo:
--  - 3 e' IL buco chiuso: `NULL IS DISTINCT FROM NULL` e' falso, quindi due BA
--    entrambi senza codice fiscale passavano anche se di soggetti diversi;
--  - 4 e' la ragione per cui il guard NON rifiuta e basta sul NULL: due BA
--    dello stesso soggetto privo di CF sono legittimi, e la versione «rifiuta
--    qualunque NULL» li avrebbe rotti;
--  - 5 e' lo scenario di §11.1: la SELECT sul padre passa dalle policy RLS
--    (la trigger function e' SECURITY INVOKER), quindi un BA di un altro
--    emittente NON viene trovato. Prima cadeva su E_ID_FISCALI_DIVERSI, con i
--    due codici fiscali IDENTICI: un messaggio che nominava la causa sbagliata.
--
-- ⚠️ NOTE DI COSTRUZIONE, entrambe pagate sul campo:
--
--  a) I test agiscono via UPDATE di `parent_account_id`, non via INSERT del
--     figlio. Il guard e' BEFORE INSERT OR UPDATE, quindi verifica lo stesso
--     ramo — ma con l'INSERT la fixture avrebbe dovuto lasciare istanze SENZA
--     satellite, e il constraint trigger differito
--     `trg_istanze_utilities_z90_require_utility_dichiarata_ins` pretende al
--     COMMIT che ogni istanza abbia almeno un BA/IDP/cliente che la referenzia.
--     Ogni istanza nasce quindi gia' con il suo BA.
--
--  b) Di conseguenza `SET CONSTRAINTS ALL IMMEDIATE` sta DOPO la fixture, non
--     in testa: l'unita' di lavoro (istanza + satellite) e' completa solo li'.
--     Messo in testa fa scattare il vincolo a meta' strada — ed e' esattamente
--     l'avvertenza del template.
--
--  c) I test 3 e 4 azzerano il codice fiscale DENTRO la transazione — e lo
--     fanno sulle colonne SORGENTE (`codice_fiscale`, `partita_iva`), perche'
--     `id_fiscale_univoco_cf_piva` e' una colonna GENERATA e non si scrive.
--     E' fixture, non bonifica: il file chiude in ROLLBACK. Si fa cosi' perche'
--     nell'istanza esiste UN solo soggetto senza CF, e un test che dipendesse
--     da quello misurerebbe la popolazione invece della regola.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- ============================================================
-- Fixture
-- ============================================================
-- Due soggetti DISTINTI, entrambi con CF, raggiungibili dall'operatore di
-- contesto (cioe' con un BA nel suo perimetro: se non li vedesse, ogni test
-- cadrebbe sul ramo «padre non raggiungibile» e misurerebbe un'altra cosa).
-- ⚠️ ORDER BY obbligatorio: senza, quale coppia esca dipende dal piano.
CREATE TEMP TABLE _t_sog ON COMMIT DROP AS
SELECT DISTINCT ON (s.id)
       s.id                 AS soggetto_id,
       ba.soggetto_ruolo_id AS soggetto_ruolo_id,
       ba.utility_id        AS utility_id,
       ba.categoria_cliente_id AS categoria_cliente_id
  FROM anagrafiche.billing_account ba
  JOIN anagrafiche.istanze_utilities iu ON iu.id = ba.istanza_utility_id
  JOIN anagrafiche.soggetti s          ON s.id  = iu.soggetto_id
 WHERE ba.utility_id IS NOT NULL
   AND s.id_fiscale_univoco_cf_piva IS NOT NULL
 ORDER BY s.id, ba.id;

CREATE TEMP TABLE _t_ref ON COMMIT DROP AS
SELECT (SELECT soggetto_id       FROM _t_sog ORDER BY soggetto_id LIMIT 1)          AS sog_a,
       (SELECT soggetto_ruolo_id FROM _t_sog ORDER BY soggetto_id LIMIT 1)          AS sr_a,
       (SELECT utility_id        FROM _t_sog ORDER BY soggetto_id LIMIT 1)          AS uti_a,
       (SELECT categoria_cliente_id FROM _t_sog ORDER BY soggetto_id LIMIT 1)       AS cat_a,
       (SELECT soggetto_id       FROM _t_sog ORDER BY soggetto_id OFFSET 1 LIMIT 1) AS sog_b,
       (SELECT soggetto_ruolo_id FROM _t_sog ORDER BY soggetto_id OFFSET 1 LIMIT 1) AS sr_b,
       (SELECT utility_id        FROM _t_sog ORDER BY soggetto_id OFFSET 1 LIMIT 1) AS uti_b,
       (SELECT categoria_cliente_id FROM _t_sog ORDER BY soggetto_id OFFSET 1 LIMIT 1) AS cat_b;

-- Un BA che l'operatore NON vede: mappato su un emittente fuori dal suo scope.
-- ⚠️ L'id si legge dalla tabella di MAPPING, non da billing_account: la RLS lo
--   nasconderebbe anche a noi, ed e' proprio quello il punto del test 5.
CREATE TEMP TABLE _t_invisibile ON COMMIT DROP AS
SELECT efba.billing_account_id AS ba_id
  FROM anagrafiche.emittenti_fiscali_billing_account efba
 WHERE efba.billing_account_id IS NOT NULL
   AND NOT (efba.emittente_soggetto_ruolo_id = ANY(
              script.fn_get_emittenti_scope_sr_ids(
                NULLIF(current_setting('app.current_user_id', true), '')::integer)))
 ORDER BY efba.billing_account_id
 LIMIT 1;

-- Tre coppie istanza+BA, tutte SENZA parent: i test lo assegnano via UPDATE.
CREATE TEMP TABLE _t_ba (etichetta text, ba_id bigint, istanza_id bigint) ON COMMIT DROP;

DO $fx$
DECLARE
    r    record;
    v_iu bigint;
    v_ba bigint;
BEGIN
    SELECT * INTO r FROM _t_ref;

    -- padre, soggetto A
    INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
    VALUES (r.sog_a, true, 'TST-P3-IU-PADRE-A') RETURNING id INTO v_iu;
    INSERT INTO anagrafiche.billing_account (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id, valido_dal)
    VALUES (v_iu, r.sr_a, r.uti_a, r.cat_a, CURRENT_DATE) RETURNING id INTO v_ba;
    INSERT INTO _t_ba VALUES ('padre_a', v_ba, v_iu);

    -- figlio, STESSO soggetto A (test 1 e 4)
    INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
    VALUES (r.sog_a, true, 'TST-P3-IU-FIGLIO-A') RETURNING id INTO v_iu;
    INSERT INTO anagrafiche.billing_account (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id, valido_dal)
    VALUES (v_iu, r.sr_a, r.uti_a, r.cat_a, CURRENT_DATE) RETURNING id INTO v_ba;
    INSERT INTO _t_ba VALUES ('figlio_a', v_ba, v_iu);

    -- figlio, soggetto B DIVERSO (test 2, 3, 5, 6)
    INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
    VALUES (r.sog_b, true, 'TST-P3-IU-FIGLIO-B') RETURNING id INTO v_iu;
    INSERT INTO anagrafiche.billing_account (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id, valido_dal)
    VALUES (v_iu, r.sr_b, r.uti_b, r.cat_b, CURRENT_DATE) RETURNING id INTO v_ba;
    INSERT INTO _t_ba VALUES ('figlio_b', v_ba, v_iu);
END
$fx$;

-- ⚠️ Qui, non in testa: vedi nota (b) nell'intestazione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT ok(
    (SELECT sog_a IS NOT NULL AND sog_b IS NOT NULL AND sog_a <> sog_b FROM _t_ref)
    AND (SELECT count(*) FROM _t_ba) = 3,
    '0. PRECONDIZIONI: due soggetti distinti con CF + fixture BA creata'
);

-- ============================================================
-- Asserzioni
-- ============================================================

-- 1) Stesso soggetto, CF presente: nessuna regressione.
SELECT lives_ok($$
    UPDATE anagrafiche.billing_account
       SET parent_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre_a')
     WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio_a')
$$, '1. stesso soggetto con CF: il figlio si aggancia (nessuna regressione)');

-- Sgancia: i test seguenti riusano la stessa riga.
-- (il guard 2.4 blocca la dissociazione solo con attivita non fatturate: qui non ce ne sono)
UPDATE anagrafiche.billing_account SET parent_account_id = NULL
 WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio_a');

-- 2) Soggetti diversi, CF diversi: il caso storico, invariato.
SELECT throws_like($$
    UPDATE anagrafiche.billing_account
       SET parent_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre_a')
     WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio_b')
$$, '%id fiscale diverso%',
    '2. soggetti diversi con CF diversi -> E_ID_FISCALI_DIVERSI (invariato)');

-- 3) * Soggetti diversi, ENTRAMBI senza CF: il buco che P-3 chiude.
--    Prima passava, perche' NULL IS DISTINCT FROM NULL e' falso.
-- ⚠️ `id_fiscale_univoco_cf_piva` e' una colonna GENERATA
--   (CASE su codice_fiscale/partita_iva): non si scrive. Si azzerano le due
--   sorgenti, e il valore generato diventa NULL di conseguenza.
-- ⚠️ Va azzerato anche `tipo_soggetto_dettaglio_id`: il guard
--   trgfn_soggetti_guard_cf_piva_obbligatori legge da
--   config.tipi_soggetto_dettaglio se CF/PIVA sono obbligatori, e NESSUN tipo
--   configurato oggi li ammette entrambi nulli — esce in testa solo se il tipo
--   non e' dichiarato. E' anche la configurazione dell'unico soggetto senza CF
--   presente nell'istanza.
UPDATE anagrafiche.soggetti
   SET tipo_soggetto_dettaglio_id = NULL, codice_fiscale = NULL, partita_iva = NULL
 WHERE id IN ((SELECT sog_a FROM _t_ref), (SELECT sog_b FROM _t_ref));

SELECT throws_like($$
    UPDATE anagrafiche.billing_account
       SET parent_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre_a')
     WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio_b')
$$, '%appartiene a un soggetto diverso%',
    '3. * soggetti diversi ENTRAMBI senza CF -> E_PARENT_SOGGETTO_DIVERSO (era il fail-open)');

-- 4) * STESSO soggetto, senza CF: deve continuare a passare.
--    E' il caso che una P-3 scritta come «rifiuta qualunque NULL» avrebbe rotto.
SELECT lives_ok($$
    UPDATE anagrafiche.billing_account
       SET parent_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre_a')
     WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio_a')
$$, '4. * STESSO soggetto senza CF: si aggancia lo stesso (nessun falso positivo)');

-- 5) * Padre fuori dal perimetro RLS: lo scenario di §11.1.
SELECT CASE WHEN EXISTS (SELECT 1 FROM _t_invisibile)
  THEN throws_like($$
        UPDATE anagrafiche.billing_account
           SET parent_account_id = (SELECT ba_id FROM _t_invisibile)
         WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio_b')
    $$, '%non rientra nel tuo perimetro%',
        '5. * padre fuori dal perimetro RLS -> E_PARENT_NON_RAGGIUNGIBILE (era E_ID_FISCALI_DIVERSI)')
  ELSE skip('5. nessun BA su un emittente fuori scope: scenario 11.1 non riproducibile qui', 1)
END;

-- 6) Padre inesistente: stesso codice, e il guard BEFORE arriva prima della FK.
SELECT throws_like($$
    UPDATE anagrafiche.billing_account
       SET parent_account_id = (SELECT COALESCE(MAX(id), 0) + 1000000 FROM anagrafiche.billing_account)
     WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio_b')
$$, '%non rientra nel tuo perimetro%',
    '6. padre inesistente -> E_PARENT_NON_RAGGIUNGIBILE (il guard BEFORE precede la FK)');

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
