-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vincoli e comportamenti base su vendite.attivita_fatturabili
--
-- Elenco test (1..36):
--  1-9)  Riferimenti minimi presenti (articoli, istanze utilities, sorgenti,
--        unita di misura, note_stili, sorgente id=1 con target valido,
--        billing account, tipi doc fiscale, valute)
-- 10)    Fixture: 13 attivita di commessa distinte create
-- 11-12) Quantita negativa: consentita e mantenuta
-- 13-22) Default di colonna: approvato, fatturato, sospesa,
--        lock_in_fatturazione, storicizza, uid, tipo_doc_fiscale_id,
--        valuta_id, factor_to_base, sorgente_riga
-- 23-24) Nota su vendite.note (ATTIVITA, era ATTIVITAFT fino al 2026-10-25) e presenza nella sua partizione
-- 25)    Riga da commessa: competenza_mese non al primo del mese e RESPINTA
-- 26)    CHECK competenza_dal <= competenza_al
-- 27)    Riga da commessa: competenza_mese NON derivata da posticipa_al
-- 28)    NOT NULL quantita
-- 29)    FK su articolo_id
-- 30)    Riga con sorgente_tipo_id e sorgente_uid validi
-- 31)    Unicita 1:1 su commessa_attivita_id (una AF per attivita di commessa)
-- 32-33) attivita_consumi e attivita_fatturabile che la referenzia
-- 34-36) FK inesistenti: tipo_doc_fiscale_id, valuta_id, attivita_consumi_id
--
-- ============================================================================
-- rev 2026-08-18 — bonifica baseline. Tre cose diverse, e conviene tenerle
-- distinte perche' solo la prima e' "riparare un test".
--
-- 1. RIPARATO (la gran parte). Le fixture inserivano attivita_fatturabili
--    "nude". Non e' piu' un caso possibile: commessa_id e commessa_attivita_id
--    sono NOT NULL, e prima ancora c'e' il guard a10. Il soggetto dei test —
--    default, CHECK e FK della tabella — e' vivo: era morta la scorciatoia con
--    cui la fixture ci arrivava. Ora si passa dalla commessa, come
--    l'applicazione. Modello: test-vw-dash-competenza-v1.
--
-- 2. RIVOLTATO (25 e 27). Asserivano la normalizzazione di competenza_mese.
--    trgfn_attivita_fatturabili_normalize e' commessa-aware: quando
--    commessa_attivita_id IS NOT NULL esce in testa e salta tutto il blocco
--    delle competenze. Essendo quella colonna NOT NULL, il ramo standard non
--    e' raggiungibile da NESSUN percorso — non era un test da riparare, era un
--    comportamento che non esiste piu'. Ora verificano cio' che accade davvero.
--    🔴 Il ramo standard di quella funzione e' CODICE MORTO: segnalato, non
--    rimosso qui (e' una funzione condivisa, fuori dal perimetro di un test).
--
-- 3. RITIRATO. La UNIQUE parziale su (sorgente_tipo_id, sorgente_uid) NON
--    ESISTE PIU': la chiave di unicita' si e' spostata su commessa_attivita_id
--    e il test 31 la presidia al suo posto. E vendite.attivita_fatturabili_lotti
--    e' stata DISMESSA il 2026-08-04: con lei se ne vanno l'asserzione sul
--    "lotto di alimentazione" e quella sulla FK di lotto_attivita_id.
--    🔴 lotto_attivita_id resta come COLONNA ORFANA, sia su
--    attivita_fatturabili sia su attivita_consumi: nessuna tabella padre,
--    nessuna FK, accetta qualunque numero. O torna ad avere un padre o va via.
-- ============================================================================
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

SELECT plan(36);

-- ============================================================
-- 0) Costanti e riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_af AS
SELECT
    'pgtap_attivita_fatturabili'::text AS test_scope,
    uuidv7() AS sorgente_uid_unica;

CREATE TEMP TABLE tmp_refs_af AS
-- rev 2026-08-18 (bonifica baseline): il billing account si sceglie UNA volta.
-- Prima articolo, istanza utility e billing account arrivavano da tre
-- `ORDER BY data_insert DESC LIMIT 1` indipendenti: nulla garantiva che
-- l'istanza appartenesse a quel BA.
WITH ba AS (
    SELECT b.id, b.utility_id, b.istanza_utility_id
      FROM anagrafiche.billing_account b
     WHERE b.utility_id IS NOT NULL
       AND b.istanza_utility_id IS NOT NULL
       AND b.soggetto_ruolo_id IS NOT NULL
     ORDER BY b.id
     LIMIT 1
)
SELECT
    (SELECT id FROM ba)                 AS billing_account_id,
    (SELECT utility_id FROM ba)         AS utility_id,
    (SELECT istanza_utility_id FROM ba) AS istanza_utility_id,
    (SELECT a.id
       FROM catalogo.articoli a
      WHERE a.attivo IS TRUE AND a.is_composito = FALSE
      ORDER BY a.id
      LIMIT 1) AS articolo_id,
    (SELECT s2.id
       FROM config.sorgenti s2
      WHERE s2.attivo IS TRUE
      ORDER BY s2.id
      LIMIT 1) AS sorgente_tipo_id,
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
      LIMIT 1) AS valuta_id,
    (SELECT sc.id
       FROM vendite.stati_commessa sc
      WHERE sc.attivo IS TRUE AND sc.codice_interno <> 'ANNULLATA'
      ORDER BY sc.id
      LIMIT 1) AS stato_commessa_id,
    (SELECT ef.soggetto_ruolo_id
       FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.attivo IS TRUE
      ORDER BY ef.id
      LIMIT 1) AS emittente_sr_id;

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
-- Fixture commessa (rev 2026-08-18, bonifica baseline)
--
-- Una attivita_fatturabile non esiste piu' senza la coppia commessa_id /
-- commessa_attivita_id: sono NOT NULL sulla tabella, e prima ancora c'e'
-- trg_attivita_fatturabili_a10_guard_commessa. Il soggetto di questo file —
-- default, normalizzazioni, CHECK, FK e unicita' della tabella — e' intatto:
-- era morta la scorciatoia dell'INSERT nudo con cui la fixture ci arrivava.
--
-- ⚠️ UNA attivita' di commessa PER INSERT, tredici in tutto.
-- uq_attivita_fatturabili_commessa_attivita e' una UNIQUE piena: una AF per
-- attivita' di commessa. Condividerne una farebbe scattare QUELLA unique al
-- posto di cio' che il test verifica — in particolare l'asserzione
-- sull'unicita' di (sorgente_tipo_id, sorgente_uid), che diventerebbe un
-- verde preso dall'indice sbagliato. Le valgono anche per gli INSERT che
-- devono FALLIRE: un throws_ok che incontra la unique della commessa
-- riporterebbe 23505 al posto del 23503/23514 atteso.
--
-- Modello: test-vw-dash-competenza-v1 (INSERT diretti; non serve il giro di
-- fn_get_or_create_commessa / fn_link_commessa_sorgente per una fixture).
-- ============================================================
CREATE TEMP TABLE tmp_commessa_af AS
WITH ins AS (
    INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                  emittente_soggetto_ruolo_id, stato_commessa_id)
    SELECT 'PGTAP-AF-' || substr(md5(clock_timestamp()::text), 1, 8),
           r.billing_account_id, r.utility_id, r.emittente_sr_id, r.stato_commessa_id
      FROM tmp_refs_af r
    RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_ca_af AS
WITH ins AS (
    INSERT INTO vendite.commesse_attivita (
        commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
        uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
        tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
        stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
    SELECT (SELECT id FROM tmp_commessa_af),
           'PGTAPAF' || g.n || 'X' || substr(md5(clock_timestamp()::text), 1, 10),
           r.articolo_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
           date_trunc('month', script.fn_data_operativa())::date,
           date_trunc('month', script.fn_data_operativa())::date,
           (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
           r.tipo_doc_fiscale_id, r.valuta_id, 1.000000, 'FIXED',
           -- BOZZA di proposito: righe di fixture non devono comparire nelle
           -- corsie di emissione degli altri test.
           'BOZZA', 'NON_EMESSA', (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
         ((SELECT id FROM tmp_commessa_af))::text
      FROM tmp_refs_af r, generate_series(1, 13) AS g(n)
    RETURNING id, segment_key)
SELECT substring(segment_key FROM 'PGTAPAF([0-9]+)X')::int AS slot, id AS attivita_id
  FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_ca_af),
    13,
    'Fixture: 13 attivita di commessa distinte create'
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
        commessa_id,
        commessa_attivita_id,
        data_attivita,
        quantita,
        competenza_mese,
        competenza_dal,
        competenza_al,
        tipo_doc_fiscale_id,
        valuta_id,
        meta
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        (SELECT id FROM tmp_commessa_af),
        (SELECT attivita_id FROM tmp_ca_af WHERE slot = 1),
        script.fn_data_operativa(),
        -5,
        date_trunc('month', script.fn_data_operativa())::date,
        date_trunc('month', script.fn_data_operativa())::date,
        (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
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

-- ⚠️ rev 2026-08-26: NON e' piu' un default. Dal changeSet 20260826-33
--   `fatturato` e' una colonna GENERATA su `fattura_riga_id IS NOT NULL`, e
--   qui vale false perche' l'attivita' non e' agganciata a nessuna riga di
--   fattura. L'asserzione resta identica e continua a valere; cambia il
--   PERCHE', e lasciare scritto «default» avrebbe mandato il prossimo lettore
--   a cercare un DEFAULT che non c'e' piu'.
SELECT is(
    (SELECT fatturato FROM tmp_attivita_base),
    false,
    'fatturato = false su un attivita senza riga di fattura (colonna generata)'
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
        'ATTIVITA',
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
    'Inserita nota su vendite.note (ATTIVITA)'
);

SELECT is(
    (SELECT count(*)::int
       FROM vendite.note_attivita_fatturabili n
      WHERE n.id = (SELECT id FROM tmp_note_attivita)
        AND n.target_tipo = 'ATTIVITA'),
    1,
    'Nota presente in partizione note_attivita_fatturabili'
);

-- ============================================================
-- 2) Normalizzazione competenza_mese
-- ============================================================
-- ⚠️ rev 2026-08-18 (bonifica baseline) — QUESTO TEST E' STATO RIVOLTATO,
-- non riparato, e vale la pena dire perche'.
--
-- Asseriva che il trigger normalizzasse competenza_mese al primo del mese.
-- E' vero solo nel ramo STANDARD di trgfn_attivita_fatturabili_normalize:
-- la funzione e' commessa-aware e, quando commessa_attivita_id IS NOT NULL,
-- fa RETURN NEW in testa saltando tutto il blocco delle competenze — «lo
-- snapshot CA e' gia' completo», dice il suo stesso commento.
-- Siccome commessa_attivita_id e' NOT NULL sulla tabella, quel ramo standard
-- NON E' PIU' RAGGIUNGIBILE da nessun percorso: non e' un test da riparare,
-- e' un comportamento che non esiste piu'.
-- Cio' che oggi e' vero, ed e' quello che si verifica qui: la riga deve
-- arrivare con competenza_mese GIA' al primo del mese, e se non lo e'
-- chk_attivita_competenza_mese_primo la respinge. Il normalizzatore non
-- copre piu' per chi scrive.
-- 🔴 Il ramo standard di quella funzione e' codice morto: segnalato, non
-- rimosso qui (e' una funzione condivisa, non perimetro di questo file).
SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        commessa_id,
        commessa_attivita_id,
        data_attivita,
        quantita,
        competenza_mese,
        competenza_dal,
        competenza_al,
        tipo_doc_fiscale_id,
        valuta_id,
        meta
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        (SELECT id FROM tmp_commessa_af),
        (SELECT attivita_id FROM tmp_ca_af WHERE slot = 2),
        date '2025-01-15',
        10,
        date '2025-01-20',
        date '2025-01-01',
        (date '2025-01-01' + INTERVAL '1 month - 1 day')::date,
        r.tipo_doc_fiscale_id,
        r.valuta_id,
        jsonb_build_object('test_scope', k.test_scope, 'case', 'competenza_norm')
    FROM tmp_refs_af r,
         tmp_costanti_af k;
    $$,
    '23514',
    NULL,
    'Riga da commessa: competenza_mese non al primo del mese e respinta (il normalizzatore non copre piu)'
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
        commessa_id,
        commessa_attivita_id,
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
        (SELECT id FROM tmp_commessa_af),
        (SELECT attivita_id FROM tmp_ca_af WHERE slot = 3),
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
-- ⚠️ rev 2026-08-18 (bonifica baseline) — stessa sorte del test qui sopra, e
-- stessa causa: la derivazione di competenza_mese da posticipa_al vive nel
-- ramo standard di trgfn_attivita_fatturabili_normalize, che su una riga da
-- commessa non viene mai eseguito. Su una riga da commessa competenza_mese
-- resta NULL e la colonna e' NOT NULL: e' quello che si verifica.
SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        commessa_id,
        commessa_attivita_id,
        data_attivita,
        quantita,
        posticipa_al,
        competenza_dal,
        competenza_al,
        tipo_doc_fiscale_id,
        valuta_id,
        meta
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        (SELECT id FROM tmp_commessa_af),
        (SELECT attivita_id FROM tmp_ca_af WHERE slot = 4),
        date '2025-01-10',
        1,
        date '2025-03-15',
        date '2025-03-01',
        (date '2025-03-01' + INTERVAL '1 month - 1 day')::date,
        r.tipo_doc_fiscale_id,
        r.valuta_id,
        jsonb_build_object('test_scope', k.test_scope, 'case', 'posticipo_competenza')
    FROM tmp_refs_af r,
         tmp_costanti_af k;
    $$,
    '23502',
    NULL,
    'Riga da commessa: competenza_mese NON viene derivata da posticipa_al (ramo standard non raggiunto)'
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
        commessa_id,
        commessa_attivita_id,
        data_attivita,
        quantita,
        competenza_mese,
        competenza_dal,
        competenza_al,
        tipo_doc_fiscale_id,
        valuta_id
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        (SELECT id FROM tmp_commessa_af),
        (SELECT attivita_id FROM tmp_ca_af WHERE slot = 5),
        script.fn_data_operativa(),
        NULL,
        date_trunc('month', script.fn_data_operativa())::date,
        date_trunc('month', script.fn_data_operativa())::date,
        (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
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
        commessa_id,
        commessa_attivita_id,
        data_attivita,
        quantita,
        competenza_mese,
        competenza_dal,
        competenza_al,
        tipo_doc_fiscale_id,
        valuta_id
    )
    SELECT
        uuidv7(),
        r.istanza_utility_id,
        r.billing_account_id,
        (SELECT id FROM tmp_commessa_af),
        (SELECT attivita_id FROM tmp_ca_af WHERE slot = 6),
        script.fn_data_operativa(),
        1,
        date_trunc('month', script.fn_data_operativa())::date,
        date_trunc('month', script.fn_data_operativa())::date,
        (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
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
        commessa_id,
        commessa_attivita_id,
        data_attivita,
        quantita,
        sorgente_tipo_id,
        sorgente_riga,
        sorgente_uid,
        competenza_mese,
        competenza_dal,
        competenza_al,
        tipo_doc_fiscale_id,
        valuta_id,
        meta
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        (SELECT id FROM tmp_commessa_af),
        (SELECT attivita_id FROM tmp_ca_af WHERE slot = 7),
        script.fn_data_operativa(),
        1,
        s.sorgente_tipo_id,
        CASE WHEN s.key_selector = 'id' THEN s.sorgente_riga ELSE NULL END,
        CASE WHEN s.key_selector = 'uid' THEN s.sorgente_uid ELSE k.sorgente_uid_unica END,
        date_trunc('month', script.fn_data_operativa())::date,
        date_trunc('month', script.fn_data_operativa())::date,
        (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
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

-- ⚠️ rev 2026-08-18 (bonifica baseline) — ASSERZIONE RIMPIAZZATA, non riparata.
-- Verificava la UNIQUE parziale su (sorgente_tipo_id, sorgente_uid). Quell'indice
-- NON ESISTE PIU': sulla tabella oggi ci sono solo pk, uq_..._uid e
-- uq_attivita_fatturabili_commessa_attivita. La chiave di unicita' si e'
-- spostata sulla coppia commessa/attivita' (stessa storia di
-- test-drop-uq-commesse-attivita-src-uid-partial-v1). Lasciare l'asserzione
-- com'era avrebbe presidiato un indice fantasma; toglierla e basta avrebbe
-- lasciato SENZA presidio la chiave 1:1 che oggi conta davvero. Si sposta.
SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        commessa_id,
        commessa_attivita_id,
        data_attivita,
        quantita,
        sorgente_tipo_id,
        sorgente_riga,
        sorgente_uid,
        competenza_mese,
        competenza_dal,
        competenza_al,
        tipo_doc_fiscale_id,
        valuta_id
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        (SELECT id FROM tmp_commessa_af),
        -- ⚠️ Di proposito la STESSA attivita' di commessa della riga qui
        -- sopra (slot 7): e' il duplicato che deve essere respinto.
        (SELECT attivita_id FROM tmp_ca_af WHERE slot = 7),
        script.fn_data_operativa(),
        2,
        s.sorgente_tipo_id,
        CASE WHEN s.key_selector = 'id' THEN s.sorgente_riga ELSE NULL END,
        CASE WHEN s.key_selector = 'uid' THEN s.sorgente_uid ELSE k.sorgente_uid_unica END,
        date_trunc('month', script.fn_data_operativa())::date,
        date_trunc('month', script.fn_data_operativa())::date,
        (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
        r.tipo_doc_fiscale_id,
        r.valuta_id
    FROM tmp_refs_af r,
         tmp_sorgente_cfg s,
         tmp_costanti_af k;
    $$,
    '23505',
    NULL,
    'Unicita 1:1 su commessa_attivita_id (una AF per attivita di commessa)'
);

-- ============================================================
-- 7) attivita_consumi (link)
--
-- ⚠️ rev 2026-08-18 (bonifica baseline) — RITIRATO il blocco del "lotto di
-- alimentazione". vendite.attivita_fatturabili_lotti NON ESISTE PIU': e' stata
-- dismessa il 2026-08-04 con la potatura delle attivita' di pipeline morte.
-- Il test la creava e ci si agganciava: non e' una fixture da riparare, e' un
-- oggetto che non c'e'. Con lui se ne vanno l'asserzione "Inserimento lotto
-- alimentazione" e quella sulla FK di lotto_attivita_id (vedi sotto).
-- 🔴 SEGNALAZIONE: `attivita_fatturabili.lotto_attivita_id` e
-- `attivita_consumi.lotto_attivita_id` sono rimaste come COLONNE ORFANE — la
-- tabella padre non c'e' e nessuna delle due ha piu' una FK. Non le tocco qui
-- (non e' perimetro di un file di test), ma o tornano ad avere un padre o
-- vanno via: oggi accettano qualunque numero.
-- ============================================================
CREATE TEMP TABLE tmp_attivita_consumi AS
WITH ins AS (
    INSERT INTO vendite.attivita_consumi (
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
        r.billing_account_id,
        date_trunc('month', script.fn_data_operativa())::date,
        script.fn_data_operativa() - 30,
        script.fn_data_operativa() - 1,
        100.5,
        r.uom_id,
        jsonb_build_object('test_scope', k.test_scope),
        false
    FROM tmp_refs_af r,
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
        commessa_id,
        commessa_attivita_id,
        data_attivita,
        quantita,
        competenza_mese,
        competenza_dal,
        competenza_al,
        tipo_doc_fiscale_id,
        valuta_id,
        attivita_consumi_id,
        meta
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        (SELECT id FROM tmp_commessa_af),
        (SELECT attivita_id FROM tmp_ca_af WHERE slot = 9),
        script.fn_data_operativa(),
        1,
        date_trunc('month', script.fn_data_operativa())::date,
        date_trunc('month', script.fn_data_operativa())::date,
        (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
        r.tipo_doc_fiscale_id,
        r.valuta_id,
        c.id,
        jsonb_build_object('test_scope', k.test_scope, 'case', 'link_consumi')
    FROM tmp_refs_af r,
         tmp_attivita_consumi c,
         tmp_costanti_af k
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_attivita_link),
    1,
    'Inserita attivita con link attivita_consumi'
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
        commessa_id,
        commessa_attivita_id,
        data_attivita,
        quantita,
        competenza_mese,
        competenza_dal,
        competenza_al,
        tipo_doc_fiscale_id,
        valuta_id
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        (SELECT id FROM tmp_commessa_af),
        (SELECT attivita_id FROM tmp_ca_af WHERE slot = 10),
        script.fn_data_operativa(),
        1,
        date_trunc('month', script.fn_data_operativa())::date,
        date_trunc('month', script.fn_data_operativa())::date,
        (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
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
        commessa_id,
        commessa_attivita_id,
        data_attivita,
        quantita,
        competenza_mese,
        competenza_dal,
        competenza_al,
        tipo_doc_fiscale_id,
        valuta_id
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        (SELECT id FROM tmp_commessa_af),
        (SELECT attivita_id FROM tmp_ca_af WHERE slot = 11),
        script.fn_data_operativa(),
        1,
        date_trunc('month', script.fn_data_operativa())::date,
        date_trunc('month', script.fn_data_operativa())::date,
        (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
        r.tipo_doc_fiscale_id,
        999999::integer
    FROM tmp_refs_af r;
    $$,
    '23503',
    NULL,
    'FK violation su valuta_id'
);

-- ============================================================
-- 10) FK lotto_attivita_id — ASSERZIONE RITIRATA (rev 2026-08-18)
--
-- Non c'e' piu' NESSUNA foreign key su attivita_fatturabili.lotto_attivita_id:
-- e' caduta insieme a vendite.attivita_fatturabili_lotti. Un id inventato
-- oggi viene accettato, quindi l'asserzione non poteva che essere rossa — e
-- non per un difetto della fixture. Vedi la segnalazione sulle colonne orfane
-- al punto 7.
-- ============================================================
-- 11) FK attivita_consumi_id inesistente
-- ============================================================
SELECT throws_ok(
    $$
    INSERT INTO vendite.attivita_fatturabili (
        articolo_id,
        istanza_utility_id,
        billing_account_id,
        commessa_id,
        commessa_attivita_id,
        data_attivita,
        quantita,
        competenza_mese,
        competenza_dal,
        competenza_al,
        tipo_doc_fiscale_id,
        valuta_id,
        attivita_consumi_id
    )
    SELECT
        r.articolo_id,
        r.istanza_utility_id,
        r.billing_account_id,
        (SELECT id FROM tmp_commessa_af),
        (SELECT attivita_id FROM tmp_ca_af WHERE slot = 13),
        script.fn_data_operativa(),
        1,
        date_trunc('month', script.fn_data_operativa())::date,
        date_trunc('month', script.fn_data_operativa())::date,
        (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
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
SET attivita_consumi_id = NULL
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_af);
*/
DELETE FROM vendite.attivita_fatturabili
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_af);

UPDATE vendite.attivita_consumi
SET storicizza = false
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_af);

DELETE FROM vendite.attivita_consumi
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_af);


-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
