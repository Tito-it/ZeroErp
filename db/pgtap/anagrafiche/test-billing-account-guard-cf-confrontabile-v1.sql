-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Passo 3 (P-3) del cantiere «perimetro emittente»: il §2.2 di
-- anagrafiche.trgfn_billing_account_guard_normalize non confronta piu'
-- il solo codice fiscale.
-- Brief: brief-db-perimetro-emittente-liste-e-gerarchia-ba.md §4, §11.1
--
-- Elenco test (plan 7):
--   0) PRECONDIZIONI: due soggetti distinti con CF + fixture creata + BA altrui
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
-- ⛔ 2026-09-23: i due soggetti venivano PESCATI fra quelli che hanno «un BA
--   nel perimetro dell'operatore». Su un database ricostruito dai changelog i
--   billing account sono zero: la fixture moriva sul NOT NULL di
--   `istanze_utilities.soggetto_id`. Ora si COSTRUISCONO: due clienti, due
--   soggetti distinti, entrambi con CF per costruzione, entrambi legati
--   all'azienda di chi agisce (contesto aperto dalla riga sopra: ramo B).
CREATE TEMP TABLE _t_mondo ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('P3 soggetto A');

CREATE TEMP TABLE _t_cli_b ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('P3 soggetto B');

CREATE TEMP TABLE _t_ref ON COMMIT DROP AS
SELECT m.cliente_soggetto_id       AS sog_a,
       m.cliente_soggetto_ruolo_id AS sr_a,
       m.utility_id                AS uti_a,
       (SELECT ba.categoria_cliente_id FROM anagrafiche.billing_account ba
         WHERE ba.id = m.billing_account_id) AS cat_a,
       b.soggetto_id               AS sog_b,
       b.soggetto_ruolo_id         AS sr_b,
       b.utility_id                AS uti_b,
       (SELECT ba.categoria_cliente_id FROM anagrafiche.billing_account ba
         WHERE ba.id = b.billing_account_id) AS cat_b
  FROM _t_mondo m, _t_cli_b b;

-- Un BA che l'operatore NON vede: il cliente di un'ALTRA azienda.
-- ⭐ Si costruisce, e il ramo `skip` del test 5 sparisce: prima lo si cercava
--   fra i legami esistenti, e su un database con un'azienda sola non c'era.
--   L'ordine e' quello che il trigger z90 impone: il BA si lega all'azienda
--   di CHI AGISCE, quindi si agisce per un attimo come l'operatore dell'altra
--   azienda, e poi si torna al proprio.
-- ⚠️ L'id si legge dal builder, che lo rilegge sotto il contesto dell'ALTRO:
--   come il nostro operatore la RLS lo nasconderebbe, ed e' il punto del test 5.
CREATE TEMP TABLE _t_altra ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _t_altra));

CREATE TEMP TABLE _t_invisibile ON COMMIT DROP AS
SELECT c.billing_account_id AS ba_id
  FROM dbops.fn_pgtap_crea_cliente_ba('P3 fuori perimetro') c;

SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _t_mondo));

-- ⚠️ I builder escono IMMEDIATE, e le tre istanze qui sotto sono una saga:
--   la finestra differita si riapre DICHIARANDOLA, non si conta sul default.
SET CONSTRAINTS ALL DEFERRED;

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
    VALUES (v_iu, r.sr_a, r.uti_a, r.cat_a, script.fn_data_operativa()) RETURNING id INTO v_ba;
    INSERT INTO _t_ba VALUES ('padre_a', v_ba, v_iu);

    -- figlio, STESSO soggetto A (test 1 e 4)
    INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
    VALUES (r.sog_a, true, 'TST-P3-IU-FIGLIO-A') RETURNING id INTO v_iu;
    INSERT INTO anagrafiche.billing_account (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id, valido_dal)
    VALUES (v_iu, r.sr_a, r.uti_a, r.cat_a, script.fn_data_operativa()) RETURNING id INTO v_ba;
    INSERT INTO _t_ba VALUES ('figlio_a', v_ba, v_iu);

    -- figlio, soggetto B DIVERSO (test 2, 3, 5, 6)
    INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
    VALUES (r.sog_b, true, 'TST-P3-IU-FIGLIO-B') RETURNING id INTO v_iu;
    INSERT INTO anagrafiche.billing_account (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id, valido_dal)
    VALUES (v_iu, r.sr_b, r.uti_b, r.cat_b, script.fn_data_operativa()) RETURNING id INTO v_ba;
    INSERT INTO _t_ba VALUES ('figlio_b', v_ba, v_iu);
END
$fx$;

-- ⚠️ Qui, non in testa: vedi nota (b) nell'intestazione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT ok(
    (SELECT sog_a IS NOT NULL AND sog_b IS NOT NULL AND sog_a <> sog_b FROM _t_ref)
    AND (SELECT count(*) FROM _t_ba) = 3
    AND (SELECT ba_id IS NOT NULL FROM _t_invisibile),
    '0. PRECONDIZIONI: due soggetti distinti con CF + fixture BA creata + un BA di un''altra azienda'
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
SELECT throws_like($$
    UPDATE anagrafiche.billing_account
       SET parent_account_id = (SELECT ba_id FROM _t_invisibile)
     WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio_b')
$$, '%non rientra nel tuo perimetro%',
    '5. * padre fuori dal perimetro RLS -> E_PARENT_NON_RAGGIUNGIBILE (era E_ID_FISCALI_DIVERSI) (rosso da owner, che salta la RLS; verde come app)');

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
