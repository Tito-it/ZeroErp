-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vincoli e comportamenti base su vendite.attivita_fatturabili
--
-- Elenco test:
-- 1) Riferimento catalogo.articoli presente
-- 2) Riferimento anagrafiche.istanze_utilities presente
-- 3) Riferimento config.sorgenti presente
-- 4) Riferimento catalogo.unita_misura presente
-- 5) Riferimento anagrafiche.billing_account presente
-- 6) Riferimento config.tipi_doc_fiscale presente
-- 7) Riferimento config.valute presente
-- 8) Sorgente configurata con target valido (per guard polimorfo)
-- 9) Inserimento con quantita negativa consentito
-- 10) Quantita negativa mantenuta
-- 11) Default approvato = false
-- 12) Default fatturato = false
-- 13) Default sospesa = false
-- 14) Default lock_in_fatturazione = false
-- 15) Default storicizza = true
-- 16) Default uid valorizzato
-- 17) tipo_doc_fiscale_id valorizzato
-- 18) Default valuta_id valorizzato
-- 19) Default factor_to_base = 1
-- 20) Default sorgente_riga = 0
-- 21) Normalizzazione competenza_mese al primo del mese
-- 22) Check competenza_dal <= competenza_al
-- 23) Competenza_mese derivata da posticipa_al se NULL
-- 24) NOT NULL quantita
-- 24) FK su articolo_id
-- 25) Inserimento riga con sorgente_tipo_id e sorgente_uid/sorgente_riga validi
-- 26) Unicita parziale su (sorgente_tipo_id, sorgente_uid)
-- 27) Inserimento lotto alimentazione
-- 28) Inserimento attivita_consumi
-- 29) Inserimento attivita_fatturabili con link lotto/consumi
-- 30) FK tipo_doc_fiscale_id inesistente
-- 31) FK valuta_id inesistente
-- 32) FK lotto_attivita_id inesistente
-- 33) FK attivita_consumi_id inesistente
-- 34) Riferimento config.note_stili presente
-- 35) Inserimento nota su vendite.note (target ATTIVITAFT)
-- 36) Nota presente in partizione vendite.note_attivita_fatturabili
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. In testa e non in coda apposta:
--   in coda scatterebbero tutti insieme DOPO il cleanup, su righe ormai
--   cancellate. Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(37);

-- ============================================================
-- 0) Costanti e riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_af AS
SELECT
    'pgtap_attivita_fatturabili'::text AS test_scope,
    uuidv7() AS sorgente_uid_unica;

CREATE TEMP TABLE tmp_refs_af AS
SELECT
    (SELECT id
       FROM catalogo.articoli
      WHERE attivo IS TRUE
      ORDER BY data_insert DESC NULLS LAST
      LIMIT 1) AS articolo_id,
    (SELECT id
       FROM anagrafiche.istanze_utilities
      ORDER BY data_insert DESC NULLS LAST
      LIMIT 1) AS istanza_utility_id,
    (SELECT id
       FROM anagrafiche.billing_account
      ORDER BY data_insert DESC NULLS LAST
      LIMIT 1) AS billing_account_id,
    (SELECT utility_id
       FROM anagrafiche.billing_account
      ORDER BY data_insert DESC NULLS LAST
      LIMIT 1) AS utility_id,
    (SELECT id
       FROM config.sorgenti
      WHERE attivo IS TRUE
      ORDER BY id
      LIMIT 1) AS sorgente_tipo_id,
    (SELECT id
       FROM catalogo.unita_misura
      WHERE attivo IS TRUE
      ORDER BY id
      LIMIT 1) AS uom_id,
    (SELECT id
       FROM config.tipi_doc_fiscale
      WHERE attivo IS TRUE
      ORDER BY id
      LIMIT 1) AS tipo_doc_fiscale_id,
    (SELECT id
       FROM config.valute
      ORDER BY id
      LIMIT 1) AS valuta_id;

CREATE TEMP TABLE tmp_note_stile AS
SELECT id AS id_stile
FROM config.note_stili
WHERE attivo IS TRUE
ORDER BY id
LIMIT 1;

CREATE TEMP TABLE tmp_sorgente_cfg (
    sorgente_tipo_id bigint,
    key_selector text,
    sorgente_riga bigint,
    sorgente_uid uuid
);

SELECT ok(
    (SELECT articolo_id FROM tmp_refs_af) IS NOT NULL,
    'Riferimento catalogo.articoli presente'
);

SELECT ok(
    (SELECT istanza_utility_id FROM tmp_refs_af) IS NOT NULL,
    'Riferimento anagrafiche.istanze_utilities presente'
);

SELECT ok(
    (SELECT sorgente_tipo_id FROM tmp_refs_af) IS NOT NULL,
    'Riferimento config.sorgenti presente'
);

SELECT ok(
    (SELECT uom_id FROM tmp_refs_af) IS NOT NULL,
    'Riferimento catalogo.unita_misura presente'
);

SELECT ok(
    (SELECT id_stile FROM tmp_note_stile) IS NOT NULL,
    'Riferimento config.note_stili presente'
);

SELECT ok(
    (SELECT count(*)
       FROM config.sorgenti
      WHERE id = 1
        AND attivo IS TRUE
        AND target_table IS NOT NULL
        AND key_selector IN ('id', 'uid')) = 1,
    'Sorgente id=1 configurata con target valido'
);

SELECT ok(
    (SELECT billing_account_id IS NOT NULL FROM tmp_refs_af),
    'Riferimento billing_account presente'
);

SELECT ok(
    (SELECT tipo_doc_fiscale_id IS NOT NULL FROM tmp_refs_af),
    'Riferimento config.tipi_doc_fiscale presente'
);

SELECT ok(
    (SELECT valuta_id IS NOT NULL FROM tmp_refs_af),
    'Riferimento config.valute presente'
);

-- ============================================================
-- 1) Inserimento base con quantita negativa (ammessa)
-- ============================================================
CREATE TEMP TABLE tmp_attivita_base AS
WITH ins AS (
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        data_attivita,
        quantita,
        competenza_mese,
        tipo_doc_fiscale_id,
        valuta_id,
        meta
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        current_date,
        -5,
        date_trunc('month', current_date)::date,
        r.tipo_doc_fiscale_id,
        r.valuta_id,
        jsonb_build_object('test_scope', k.test_scope)
    FROM tmp_refs_af r,
         tmp_costanti_af k
    RETURNING
        id,
        quantita,
        approvato,
        fatturato,
        sospesa,
        lock_in_fatturazione,
        storicizza,
        uid,
        tipo_doc_fiscale_id,
        valuta_id,
        factor_to_base,
        sorgente_riga
)
SELECT * FROM ins;

INSERT INTO tmp_sorgente_cfg (sorgente_tipo_id, key_selector, sorgente_riga, sorgente_uid)
SELECT
    s.id,
    s.key_selector,
    CASE WHEN s.key_selector = 'id' THEN a.id ELSE NULL END,
    CASE WHEN s.key_selector = 'uid' THEN a.uid ELSE NULL END
FROM config.sorgenti s,
     tmp_attivita_base a
WHERE s.id = 1
  AND s.attivo IS TRUE
  AND s.key_selector IN ('id', 'uid');

SELECT is(
    (SELECT count(*)::int FROM tmp_attivita_base),
    1,
    'Inserita attivita con quantita negativa'
);

SELECT is(
    (SELECT quantita::numeric FROM tmp_attivita_base),
    -5::numeric,
    'Quantita negativa mantenuta'
);

SELECT is(
    (SELECT approvato FROM tmp_attivita_base),
    false,
    'Default approvato = false'
);

SELECT is(
    (SELECT fatturato FROM tmp_attivita_base),
    false,
    'Default fatturato = false'
);

SELECT is(
    (SELECT sospesa FROM tmp_attivita_base),
    false,
    'Default sospesa = false'
);

SELECT is(
    (SELECT lock_in_fatturazione FROM tmp_attivita_base),
    false,
    'Default lock_in_fatturazione = false'
);

SELECT is(
    (SELECT storicizza FROM tmp_attivita_base),
    true,
    'Default storicizza = true'
);

SELECT ok(
    (SELECT uid IS NOT NULL FROM tmp_attivita_base),
    'Default uid valorizzato'
);

SELECT ok(
    (SELECT tipo_doc_fiscale_id IS NOT NULL FROM tmp_attivita_base),
    'Tipo_doc_fiscale_id valorizzato'
);

SELECT ok(
    (SELECT valuta_id IS NOT NULL FROM tmp_attivita_base),
    'Default valuta_id valorizzato'
);

SELECT is(
    (SELECT factor_to_base::numeric FROM tmp_attivita_base),
    1::numeric,
    'Default factor_to_base = 1'
);

SELECT is(
    (SELECT sorgente_riga::bigint FROM tmp_attivita_base),
    0::bigint,
    'Default sorgente_riga = 0'
);

-- ============================================================
-- 1b) Note su vendite.note e partizione note_attivita_fatturabili
-- ============================================================
CREATE TEMP TABLE tmp_note_attivita AS
WITH ins AS (
    INSERT INTO vendite.note (
        target_tipo,
        target_id,
        target_riga_id,
        anchor_tipo,
        posizione,
        seq,
        testo,
        visibile,
        solo_stampa,
        meta,
        id_stile,
        id_lingua
    )
    SELECT
        'ATTIVITAFT',
        a.id,
        a.id,
        'RIGA',
        'BEFORE',
        10,
        'Nota test attivita fatturabili',
        true,
        false,
        jsonb_build_object('test_scope', k.test_scope, 'case', 'note_attivita'),
        s.id_stile,
        NULL
    FROM tmp_attivita_base a,
         tmp_costanti_af k,
         tmp_note_stile s
    RETURNING id, target_tipo
)
SELECT * FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_note_attivita),
    1,
    'Inserita nota su vendite.note (ATTIVITAFT)'
);

SELECT is(
    (SELECT count(*)::int
       FROM vendite.note_attivita_fatturabili n
      WHERE n.id = (SELECT id FROM tmp_note_attivita)
        AND n.target_tipo = 'ATTIVITAFT'),
    1,
    'Nota presente in partizione note_attivita_fatturabili'
);

-- ============================================================
-- 2) Normalizzazione competenza_mese
-- ============================================================
CREATE TEMP TABLE tmp_attivita_competenza AS
WITH ins AS (
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        data_attivita,
        quantita,
        competenza_mese,
        tipo_doc_fiscale_id,
        valuta_id,
        meta
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        date '2025-01-15',
        10,
        date '2025-01-20',
        r.tipo_doc_fiscale_id,
        r.valuta_id,
        jsonb_build_object('test_scope', k.test_scope, 'case', 'competenza_norm')
    FROM tmp_refs_af r,
         tmp_costanti_af k
    RETURNING id, competenza_mese
)
SELECT * FROM ins;

SELECT is(
    (SELECT competenza_mese FROM tmp_attivita_competenza),
    date '2025-01-01',
    'Competenza_mese normalizzata al primo del mese'
);

-- ============================================================
-- 3) Check competenza_dal <= competenza_al
-- ============================================================
SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        data_attivita,
        quantita,
        competenza_dal,
        competenza_al,
        competenza_mese,
        tipo_doc_fiscale_id,
        valuta_id
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        date '2025-02-01',
        1,
        date '2025-02-01',
        date '2025-01-31',
        date '2025-02-01',
        r.tipo_doc_fiscale_id,
        r.valuta_id
    FROM tmp_refs_af r;
    $$,
    '23514',
    NULL,
    'Check competenza_dal <= competenza_al'
);

-- ============================================================
-- 3.1) Competenza_mese derivata da posticipa_al
-- ============================================================
CREATE TEMP TABLE tmp_attivita_posticipo AS
WITH ins AS (
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        data_attivita,
        quantita,
        posticipa_al,
        tipo_doc_fiscale_id,
        valuta_id,
        meta
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        date '2025-01-10',
        1,
        date '2025-03-15',
        r.tipo_doc_fiscale_id,
        r.valuta_id,
        jsonb_build_object('test_scope', k.test_scope, 'case', 'posticipo_competenza')
    FROM tmp_refs_af r,
         tmp_costanti_af k
    RETURNING id, competenza_mese
)
SELECT * FROM ins;

SELECT is(
    (SELECT competenza_mese FROM tmp_attivita_posticipo),
    date '2025-03-01',
    'Competenza_mese derivata da posticipa_al'
);

-- ============================================================
-- 4) NOT NULL quantita
-- ============================================================
SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        data_attivita,
        quantita,
        competenza_mese,
        tipo_doc_fiscale_id,
        valuta_id
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        current_date,
        NULL,
        date_trunc('month', current_date)::date,
        r.tipo_doc_fiscale_id,
        r.valuta_id
    FROM tmp_refs_af r;
    $$,
    '23502',
    NULL,
    'Quantita NOT NULL'
);

-- ============================================================
-- 5) FK articolo_id inesistente
-- ============================================================
SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        data_attivita,
        quantita,
        competenza_mese,
        tipo_doc_fiscale_id,
        valuta_id
    )
    SELECT
        uuidv7(),
        r.istanza_utility_id,
        r.billing_account_id,
        current_date,
        1,
        date_trunc('month', current_date)::date,
        r.tipo_doc_fiscale_id,
        r.valuta_id
    FROM tmp_refs_af r;
    $$,
    '23503',
    NULL,
    'FK violation su articolo_id'
);

-- ============================================================
-- 6) Unicita parziale sorgente_tipo_id + sorgente_uid
-- ============================================================
CREATE TEMP TABLE tmp_attivita_sorgente AS
WITH ins AS (
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        data_attivita,
        quantita,
        sorgente_tipo_id,
        sorgente_riga,
        sorgente_uid,
        competenza_mese,
        tipo_doc_fiscale_id,
        valuta_id,
        meta
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        current_date,
        1,
        s.sorgente_tipo_id,
        CASE WHEN s.key_selector = 'id' THEN s.sorgente_riga ELSE NULL END,
        CASE WHEN s.key_selector = 'uid' THEN s.sorgente_uid ELSE k.sorgente_uid_unica END,
        date_trunc('month', current_date)::date,
        r.tipo_doc_fiscale_id,
        r.valuta_id,
        jsonb_build_object('test_scope', k.test_scope, 'case', 'unique_sorgente')
    FROM tmp_refs_af r,
         tmp_sorgente_cfg s,
         tmp_costanti_af k
    RETURNING id
)
SELECT * FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_attivita_sorgente),
    1,
    'Inserita riga con sorgente_tipo_id e sorgente_uid'
);

SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        data_attivita,
        quantita,
        sorgente_tipo_id,
        sorgente_riga,
        sorgente_uid,
        competenza_mese,
        tipo_doc_fiscale_id,
        valuta_id
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        current_date,
        2,
        s.sorgente_tipo_id,
        CASE WHEN s.key_selector = 'id' THEN s.sorgente_riga ELSE NULL END,
        CASE WHEN s.key_selector = 'uid' THEN s.sorgente_uid ELSE k.sorgente_uid_unica END,
        date_trunc('month', current_date)::date,
        r.tipo_doc_fiscale_id,
        r.valuta_id
    FROM tmp_refs_af r,
         tmp_sorgente_cfg s,
         tmp_costanti_af k;
    $$,
    '23505',
    NULL,
    'Unicita sorgente_tipo_id + sorgente_uid'
);

-- ============================================================
-- 7) Lotto alimentazione + attivita_consumi (link)
-- ============================================================
CREATE TEMP TABLE tmp_lotto_attivita AS
WITH ins AS (
    INSERT INTO vendite.attivita_fatturabili_lotti (
        lock_batch_id,
        codice,
        competenza_mese,
        utility_id,
        billing_account_id,
        sorgente_tipo_id,
        meta
    )
    SELECT
        uuidv7(),
        'LA-' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS'),
        date_trunc('month', current_date)::date,
        r.utility_id,
        r.billing_account_id,
        r.sorgente_tipo_id,
        jsonb_build_object('test_scope', k.test_scope)
    FROM tmp_refs_af r,
         tmp_costanti_af k
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_lotto_attivita),
    1,
    'Inserito lotto alimentazione'
);

CREATE TEMP TABLE tmp_attivita_consumi AS
WITH ins AS (
    INSERT INTO vendite.attivita_consumi (
        lotto_attivita_id,
        billing_account_id,
        competenza_mese,
        periodo_dal,
        periodo_al,
        consumo_totale,
        uom_id,
        meta,
        storicizza
    )
    SELECT
        l.id,
        r.billing_account_id,
        date_trunc('month', current_date)::date,
        current_date - 30,
        current_date - 1,
        100.5,
        r.uom_id,
        jsonb_build_object('test_scope', k.test_scope),
        false
    FROM tmp_lotto_attivita l,
         tmp_refs_af r,
         tmp_costanti_af k
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_attivita_consumi),
    1,
    'Inserita attivita_consumi'
);

CREATE TEMP TABLE tmp_attivita_link AS
WITH ins AS (
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        data_attivita,
        quantita,
        competenza_mese,
        tipo_doc_fiscale_id,
        valuta_id,
        lotto_attivita_id,
        attivita_consumi_id,
        meta
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        current_date,
        1,
        date_trunc('month', current_date)::date,
        r.tipo_doc_fiscale_id,
        r.valuta_id,
        l.id,
        c.id,
        jsonb_build_object('test_scope', k.test_scope, 'case', 'link_lotto_consumi')
    FROM tmp_refs_af r,
         tmp_lotto_attivita l,
         tmp_attivita_consumi c,
         tmp_costanti_af k
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_attivita_link),
    1,
    'Inserita attivita con link lotto/consumi'
);

-- ============================================================
-- 8) FK tipo_doc_fiscale_id inesistente
-- ============================================================
SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        data_attivita,
        quantita,
        competenza_mese,
        tipo_doc_fiscale_id,
        valuta_id
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        current_date,
        1,
        date_trunc('month', current_date)::date,
        999999999::bigint,
        r.valuta_id
    FROM tmp_refs_af r;
    $$,
    '23503',
    NULL,
    'FK violation su tipo_doc_fiscale_id'
);

-- ============================================================
-- 9) FK valuta_id inesistente
-- ============================================================
SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        data_attivita,
        quantita,
        competenza_mese,
        tipo_doc_fiscale_id,
        valuta_id
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        current_date,
        1,
        date_trunc('month', current_date)::date,
        r.tipo_doc_fiscale_id,
        999999::integer
    FROM tmp_refs_af r;
    $$,
    '23503',
    NULL,
    'FK violation su valuta_id'
);

-- ============================================================
-- 10) FK lotto_attivita_id inesistente
-- ============================================================
SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        data_attivita,
        quantita,
        competenza_mese,
        tipo_doc_fiscale_id,
        valuta_id,
        lotto_attivita_id
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        current_date,
        1,
        date_trunc('month', current_date)::date,
        r.tipo_doc_fiscale_id,
        r.valuta_id,
        999999999::bigint
    FROM tmp_refs_af r;
    $$,
    '23503',
    NULL,
    'FK violation su lotto_attivita_id'
);

-- ============================================================
-- 11) FK attivita_consumi_id inesistente
-- ============================================================
SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        data_attivita,
        quantita,
        competenza_mese,
        tipo_doc_fiscale_id,
        valuta_id,
        attivita_consumi_id
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        current_date,
        1,
        date_trunc('month', current_date)::date,
        r.tipo_doc_fiscale_id,
        r.valuta_id,
        999999999::bigint
    FROM tmp_refs_af r;
    $$,
    '23503',
    NULL,
    'FK violation su attivita_consumi_id'
);

-- Cleanup
DELETE FROM vendite.note
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_af);

/*
UPDATE vendite.attivita_fatturabili
SET attivita_consumi_id = NULL,
    lotto_attivita_id = NULL
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_af);
*/
DELETE FROM vendite.attivita_fatturabili
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_af);

UPDATE vendite.attivita_consumi
SET storicizza = false
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_af);

DELETE FROM vendite.attivita_consumi
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_af);

UPDATE vendite.attivita_fatturabili_lotti
SET storicizza = false
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_af);

DELETE FROM vendite.attivita_fatturabili_lotti
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_af);

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
