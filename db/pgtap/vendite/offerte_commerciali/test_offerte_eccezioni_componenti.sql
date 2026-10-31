-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- rev 2026-10-26 (brief-modello-documento-vendita §13, giro 9): lo stato dell'offerta si
--   cambia solo dal verbo; l'offerta COMPOSITA del test 20 arriva ad ACCETTATA con
--   dbops.fn_pgtap_porta_a_stato invece dei due UPDATE di stato.
-- rev 2026-10-28 (brief-modello-documento-vendita §16, giro 12): la versione di listino PGTAP_OCE_V2 nasce senza stato (BOZZA) e si attiva dalla fixture dbops.fn_pgtap_porta_a_stato, non con l'UPDATE dello stato.
-- Test: vendite.offerte_commerciali_eccezioni_componenti
--       + fn_offerta_eccezione_componenti_init
--       + fn_offerta_eccezione_componenti_preview
--       + fn_push_offerta_a_contratto (copia componenti rev3)
-- ------------------------------------------------------------
-- Indice test (1..26):
--  1) has_table offerte_commerciali_eccezioni_componenti
--  2) has_column eccezione_offerta_id
--  3) has_column articolo_componente_id
--  4) has_column componente_id
--  5) has_column prezzo_unitario
--  6) has_column stato_approvazione_prezzo
--  7) has_pk pk_oce_comp
--  8) FK eccezione_offerta_id ON DELETE CASCADE
--  9) UNIQUE (eccezione_offerta_id, articolo_componente_id)
-- 10) trigger count >= 10 su offerte_commerciali_eccezioni_componenti
-- 11) trigger propaga_qta registrato su offerte_commerciali_eccezioni
-- 12) fn_init guard p_eccezione_id NULL → E_PARAMETRO_INVALIDO
-- 13) fn_init guard p_emittente_sr_id NULL → E_PARAMETRO_INVALIDO
-- 14) fn_init eccezione non trovata → E_OFFERTA_ECCEZIONE_NON_TROVATA
-- 15) fn_init articolo non composito → 0
-- 16) il kit non si vende a consumo: una riga composita con una fonte a valle e'
--     fuori perimetro (I-D6, rev 2026-10-21; era «fn_init quantita NULL → 0»)
-- 17) fn_init idempotenza → 0 alla seconda chiamata [skip se no composito]
-- 18) fn_init happy path: componenti inseriti > 0   [skip se no composito]
-- 19) fn_init override: prezzo overriddato           [skip se no composito]
-- 20) fn_push copia componenti → contratti_righe_componenti [skip se no composito]
-- 21) fn_preview esiste (has_function)
-- 22) fn_preview articolo semplice → 0 righe        [skip se no ctx]
-- 23) fn_preview articolo composito → righe > 0,
--     colonne obbligatorio+esposizione_in_fattura accessibili [skip se no composito valido]
-- 24) fn_preview COUNT = COUNT componenti attivi validi
--     (nessun filtro esposto_in_fattura)              [skip se no composito valido]
-- 25) fn_preview quantita_componente = coeff_qta * quantita_padre [skip se no composito valido]
-- 26) fn_preview include componenti esposto=FALSE     [skip se nessun componente non-esposto]
-- 27) fn_init guard ESCLUSIONE composito → 0, nessun componente,
--     padre conserva prezzo_unitario NULL                [skip se no composito]
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(27);

-- ============================================================
-- FIXTURE COSTRUITA (rev 2026-10-13)
-- ============================================================
-- ⛔ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3b, A-5):
--   FIXTURE RISCRITTA, TUTTA COSTRUITA. Prima composito, semplice, cliente e
--   listino si pescavano dal database («il fixture non si ricostruisce: si
--   FILTRA»): sullo scratch e in CI non c'era niente da filtrare, e 22 test su 27
--   si saltavano (verde per sottrazione); su dbdev le OVERRIDE puntavano ad
--   articoli fuori dal listino del documento, che dal Lotto 3b sono rifiutate.
--   Ora: un cliente; un listino con la versione 2021+ (BOZZA, righe, ATTIVA) che
--   contiene il semplice S e il bundle P (componenti F1, F2 opzionali, F2
--   NASCOSTO in fattura, prezzi dei componenti a listino). Le offerte restano
--   datate 2082: la versione e' aperta, e lo e' la distinta.
--   Le erogazioni si scelgono fra quelle che P ammette (la tipologia del listino
--   dipende dalla utility): la COMPOSITA con la fonte FISSA, la CONSUMO con una
--   fonte a valle (MANUALE o LETTURE). Il semplice eredita.
--   ⚠️ rev 2026-10-21 (brief-db-offerta-emissione-ed-erogazione §I.1, I-D1 di Tid):
--   la COMPOSITA era DERIVATA_COMPONENTI con `quantita` scritta a mano — la FISSA
--   con un altro nome che il brief ha trovato. DERIVATA ritirata: FISSA, e la
--   quantita' arriva da qta_operativa come per ogni riga FISSA. E per la I-D6 dello
--   stesso giorno un kit si vende SOLO a quantita' fissa (i componenti si calcolano
--   dalla quantita' della riga): il listino passa su una tipologia della utility che
--   ammette la FISSA e una fonte a valle, perche' il builder sceglie la prima, che
--   puo' essere solo a consumo; e il test 16 prova il rifiuto del kit a consumo.
CREATE TEMP TABLE tmp_oce_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('offerte eccezioni componenti');

-- La versione del builder nasce ATTIVA, e i componenti di un bundle non si
-- scrivono su una versione ATTIVA: la si chiude nel 2020 e quella buona nasce qui.
CREATE TEMP TABLE tmp_oce_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_oce_mondo), 'offerte eccezioni componenti',
    '2020-01-01'::date, '2020-12-31'::date);

-- La tipologia del listino (rev 2026-10-21, I-D6): una della utility che ammette la
-- FISSA (il kit) e una fonte a valle (il rifiuto del test 16). Il listino e' appena
-- nato (la sola riga d'appoggio della versione 2020 del builder): la tipologia si sceglie qui. Se la utility non ne ha una, la
-- fixture muore: NOT NULL, mai uno skip.
UPDATE tmp_oce_listino t
   SET tipologia_id = (
       SELECT ltu.tipologia_id
         FROM config.listini_tipologie_utilities ltu
        WHERE ltu.utility_id = (SELECT utility_id FROM tmp_oce_mondo)
          AND ltu.attivo
          AND EXISTS (SELECT 1 FROM config.listini_tipologie_erogazioni te
                       WHERE te.tipologia_id = ltu.tipologia_id
                         AND te.fonte_quantita_attesa = 'FISSA')
          AND EXISTS (SELECT 1 FROM config.listini_tipologie_erogazioni te
                       WHERE te.tipologia_id = ltu.tipologia_id
                         AND te.fonte_quantita_attesa <> 'FISSA')
        ORDER BY ltu.tipologia_id
        LIMIT 1);
ALTER TABLE tmp_oce_listino ALTER COLUMN tipologia_id SET NOT NULL;
UPDATE vendite.listini l
   SET tipologia_id = t.tipologia_id
  FROM tmp_oce_listino t
 WHERE l.id = t.listino_id;

CREATE TEMP TABLE tmp_oce_ver AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
    SELECT listino_id, 'PGTAP_OCE_V2', '2021-01-01'::date FROM tmp_oce_listino
    RETURNING id
)
SELECT id FROM ins;

-- Struttura alla nascita: tutti nella tipologia del listino; il bundle P nasce
-- composito.
CREATE TEMP TABLE tmp_oce_art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGT-OCE-' || v.sigla, false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM tmp_oce_listino),
           p_is_composito         => v.sigla = 'P') AS id
  FROM (VALUES ('S'), ('P'), ('F1'), ('F2')) AS v(sigla);

-- Scopo: id di un articolo della fixture per sigla.
CREATE OR REPLACE FUNCTION pg_temp.oce(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
  SELECT id FROM tmp_oce_art WHERE sigla = p_sigla;
$fx$;

-- Il bundle: P composito, F1 e F2 componenti opzionali (il fallback prezzo 0 del
-- risolutore e' ammesso solo sugli opzionali), F2 NASCOSTO in fattura (test 26).
INSERT INTO catalogo.articoli_componenti
       (prodotto_id, componente_id, coeff_qta, obbligatorio, esposizione_in_fattura, valido_dal)
VALUES (pg_temp.oce('P'), pg_temp.oce('F1'), 1, false, 'VALORIZZATO', '2020-01-01'),
       (pg_temp.oce('P'), pg_temp.oce('F2'), 2, false, 'NASCOSTO',    '2020-01-01');

INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT (SELECT id FROM tmp_oce_ver), a.id, a.uom_id, 100.00
  FROM catalogo.articoli a
 WHERE a.id IN (pg_temp.oce('S'), pg_temp.oce('F1'), pg_temp.oce('F2'));

INSERT INTO vendite.listini_righe_componenti (listino_versione_id, articolo_componente_id,
       articolo_padre_id, articolo_figlio_id, prezzo, valido_dal)
SELECT (SELECT id FROM tmp_oce_ver), ac.id, ac.prodotto_id, ac.componente_id, 40.00, '2021-01-01'
  FROM catalogo.articoli_componenti ac
 WHERE ac.prodotto_id = pg_temp.oce('P');

-- ⚠️ rev 2026-10-31 (20261031-39, D-3): la tipologia «pescata» sopra e' oggi la
--   quota fissa, e una versione con una quota fissa a canone senza periodicita'
--   non si attiva piu'. La fixture porta la versione al modello: periodicita' a
--   righe e kit, in bozza (brief-db-contratto-righe-periodiche-in-commessa §7.7).
UPDATE vendite.listini_righe SET periodicita = 'MENSILE'
 WHERE listino_versione_id = (SELECT id FROM tmp_oce_ver);
INSERT INTO vendite.listini_kit (listino_versione_id, articolo_padre_id, periodicita)
VALUES ((SELECT id FROM tmp_oce_ver), pg_temp.oce('P'), 'MENSILE');

SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni'::regclass, (SELECT id FROM tmp_oce_ver), 'ATTIVA');

CREATE TEMP TABLE tmp_oce_comp AS
SELECT pg_temp.oce('P') AS articolo_composito_id;

CREATE TEMP TABLE tmp_oce_sempl AS
SELECT pg_temp.oce('S') AS articolo_semplice_id;

CREATE TEMP TABLE tmp_oce_ctx AS
SELECT
    pg_temp.oce('P')                               AS articolo_composito_id,
    pg_temp.oce('S')                               AS articolo_semplice_id,
    m.billing_account_id,
    m.istanza_utility_id,
    m.utility_id,
    m.emittente_fiscale_id,
    m.emittente_soggetto_ruolo_id                  AS emittente_sr_id,
    (SELECT listino_id FROM tmp_oce_listino)       AS listino_id,
    (SELECT id FROM tmp_oce_ver)                   AS listino_versione_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ACCETTATA') AS stato_accettata_id,
    -- rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende, R5a): le righe
    --   dell'offerta si scrivono solo in BOZZA. Le offerte nascono in BOZZA, e la
    --   COMPOSITA va in EMESSA e poi ACCETTATA solo prima del push (test 20).
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')     AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')    AS stato_emessa_id,
    -- Le erogazioni di P: la composita con la FISSA. La consumo e' una
    --   combinazione della TIPOLOGIA con una fonte a valle: il kit non la ha
    --   (I-D6), ed e' il rifiuto del test 16.
    (SELECT e.tipo_erogazione FROM vendite.fn_articolo_erogazioni(pg_temp.oce('P')) e
      WHERE e.fonte_quantita_attesa = 'FISSA' ORDER BY e.ordine LIMIT 1) AS erog_composita,
    (SELECT te.tipo_erogazione FROM config.listini_tipologie_erogazioni te
      WHERE te.tipologia_id = (SELECT tipologia_id FROM tmp_oce_listino)
        AND te.fonte_quantita_attesa <> 'FISSA' ORDER BY te.id LIMIT 1) AS erog_consumo,
    (SELECT te.fonte_quantita_attesa FROM config.listini_tipologie_erogazioni te
      WHERE te.tipologia_id = (SELECT tipologia_id FROM tmp_oce_listino)
        AND te.fonte_quantita_attesa <> 'FISSA' ORDER BY te.id LIMIT 1) AS fonte_consumo
  FROM tmp_oce_mondo m;

-- Flag: il bundle c'e' (costruito: sempre).
CREATE TEMP TABLE tmp_oce_has_composito AS
SELECT (articolo_composito_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND listino_id IS NOT NULL
        AND emittente_sr_id IS NOT NULL
        AND erog_composita IS NOT NULL) AS disponibile
  FROM tmp_oce_ctx;

-- ============================================================
-- Le offerte: eccezioni semplice + composita + consumo + esclusione
-- ============================================================
CREATE TEMP TABLE tmp_oce_ids (
    slot       text PRIMARY KEY,
    offerta_id bigint,
    eccezione_id bigint
);

-- Scopo: un'offerta in BOZZA sul listino della fixture; ritorna l'id.
CREATE OR REPLACE FUNCTION pg_temp.oce_offerta()
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO vendite.offerte_commerciali (
      emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
      listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id)
  SELECT c.emittente_fiscale_id, c.billing_account_id, c.istanza_utility_id, c.utility_id,
         c.listino_id, c.listino_versione_id, DATE '2082-01-01', c.stato_bozza_id
    FROM tmp_oce_ctx c
  RETURNING id;
$fx$;

DO $$
DECLARE
    v_ctx    record;
    v_off_id bigint;
    v_altra  bigint;
    v_ecc_id bigint;
BEGIN
    SELECT * INTO v_ctx FROM tmp_oce_ctx;
    v_off_id := pg_temp.oce_offerta();

    -- Eccezione col semplice (test 15): eredita erogazione e fonte; la quantita'
    --   c'e' se la fonte ereditata e' FISSA.
    INSERT INTO vendite.offerte_commerciali_eccezioni (
        offerta_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa)
    VALUES (v_off_id, v_ctx.articolo_semplice_id, 'OVERRIDE', 10.00,
            (SELECT 1 FROM vendite.fn_articolo_erogazioni(v_ctx.articolo_semplice_id) e
              WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA' LIMIT 1))
    RETURNING id INTO v_ecc_id;
    INSERT INTO tmp_oce_ids VALUES ('SEMPLICE', v_off_id, v_ecc_id);

    -- Eccezione col composito (test 17-19), FISSA: 2 pezzi.
    INSERT INTO vendite.offerte_commerciali_eccezioni (
        offerta_id, articolo_id, tipo_eccezione, fonte_quantita_attesa,
        prezzo_unitario, qta_operativa, tipo_erogazione)
    VALUES (v_off_id, v_ctx.articolo_composito_id, 'OVERRIDE',
            'FISSA', 0.00, 2, v_ctx.erog_composita)
    RETURNING id INTO v_ecc_id;
    INSERT INTO tmp_oce_ids VALUES ('COMPOSITA', v_off_id, v_ecc_id);

    -- Il kit a consumo (test 16): un'offerta sua, la riga si tenta nel test.
    INSERT INTO tmp_oce_ids VALUES ('CONSUMO', pg_temp.oce_offerta(), NULL);

    -- ESCLUSIONE del composito (test 27): nasce vuota (R1 del 2026-10-04), su
    --   un'offerta sua.
    v_altra := pg_temp.oce_offerta();
    INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id, tipo_eccezione)
    VALUES (v_altra, v_ctx.articolo_composito_id, 'ESCLUSIONE')
    RETURNING id INTO v_ecc_id;
    INSERT INTO tmp_oce_ids VALUES ('ESCLUSIONE', v_altra, v_ecc_id);
END;
$$;

-- ============================================================
-- TEST 1) has_table
-- ============================================================
SELECT has_table(
    'vendite',
    'offerte_commerciali_eccezioni_componenti',
    '1) tabella vendite.offerte_commerciali_eccezioni_componenti esiste'
);

-- ============================================================
-- TEST 2-6) has_column
-- ============================================================
SELECT has_column('vendite','offerte_commerciali_eccezioni_componenti',
    'eccezione_offerta_id', '2) colonna eccezione_offerta_id esiste');

SELECT has_column('vendite','offerte_commerciali_eccezioni_componenti',
    'articolo_componente_id', '3) colonna articolo_componente_id esiste');

SELECT has_column('vendite','offerte_commerciali_eccezioni_componenti',
    'componente_id', '4) colonna componente_id esiste');

SELECT has_column('vendite','offerte_commerciali_eccezioni_componenti',
    'prezzo_unitario', '5) colonna prezzo_unitario esiste');

SELECT has_column('vendite','offerte_commerciali_eccezioni_componenti',
    'stato_approvazione_prezzo', '6) colonna stato_approvazione_prezzo esiste');

-- ============================================================
-- TEST 7) has_pk
-- ============================================================
SELECT has_pk('vendite','offerte_commerciali_eccezioni_componenti',
    '7) PK pk_oce_comp esiste');

-- ============================================================
-- TEST 8) FK CASCADE verso offerte_commerciali_eccezioni
-- ============================================================
SELECT col_is_fk(
    'vendite', 'offerte_commerciali_eccezioni_componenti',
    'eccezione_offerta_id',
    '8) eccezione_offerta_id e'' FK verso offerte_commerciali_eccezioni'
);

-- ============================================================
-- TEST 9) UNIQUE (eccezione_offerta_id, articolo_componente_id)
-- ============================================================
SELECT has_unique(
    'vendite', 'offerte_commerciali_eccezioni_componenti',
    '9) UNIQUE uq_oce_comp_eccezione_art_comp esiste'
);

-- ============================================================
-- TEST 10) Trigger count >= 10 su offerte_commerciali_eccezioni_componenti
-- ============================================================
SELECT ok(
    (SELECT COUNT(*)
       FROM information_schema.triggers
      WHERE event_object_schema = 'vendite'
        AND event_object_table  = 'offerte_commerciali_eccezioni_componenti'
    ) >= 10,
    '10) almeno 10 trigger registrati su offerte_commerciali_eccezioni_componenti'
);

-- ============================================================
-- TEST 11) Trigger propaga_qta su offerte_commerciali_eccezioni
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM information_schema.triggers
         WHERE event_object_schema = 'vendite'
           AND event_object_table  = 'offerte_commerciali_eccezioni'
           AND trigger_name LIKE '%propaga_qta%'
    ),
    '11) trigger propaga_qta registrato su offerte_commerciali_eccezioni'
);

-- ============================================================
-- TEST 12) fn_init guard p_eccezione_id NULL → E_PARAMETRO_INVALIDO
-- ============================================================
SELECT throws_like(
    $$SELECT vendite.fn_offerta_eccezione_componenti_init(NULL, 1, script.fn_data_operativa())$$,
    '%Parametro non valido%',
    '12) fn_init(NULL, 1, date): guard p_eccezione_id → E_PARAMETRO_INVALIDO'
);

-- ============================================================
-- TEST 13) fn_init guard p_emittente_sr_id NULL → E_PARAMETRO_INVALIDO
-- ============================================================
SELECT throws_like(
    $$SELECT vendite.fn_offerta_eccezione_componenti_init(1, NULL, script.fn_data_operativa())$$,
    '%Parametro non valido%',
    '13) fn_init(1, NULL, date): guard p_emittente_sr_id → E_PARAMETRO_INVALIDO'
);

-- ============================================================
-- TEST 14) fn_init eccezione non trovata → E_OFFERTA_ECCEZIONE_NON_TROVATA
--
-- ⭐ AGGIORNATO IL 2026-08-24, e in meglio: il test pretendeva
--    `E_PARAMETRO_INVALIDO`, ma quel ramo ha ricevuto un codice PROPRIO —
--    `E_OFFERTA_ECCEZIONE_NON_TROVATA`, classe `NON_TROVATO` — che e' la
--    direzione in cui il progetto sta andando (il generico si sta scomponendo,
--    codice per codice). Il test blindava il codice VECCHIO, cioe' avrebbe
--    protestato contro un miglioramento.
--
-- ⚠️ E qui si asserisce il CODICE, non piu' un frammento di frase: il punto e'
--    QUALE errore, e la frase e' la cosa che cambia piu' spesso. Con
--    `throws_like('%Parametro non valido%')` un domani basterebbe riscrivere il
--    messaggio per far diventare verde un ramo sbagliato.
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.oce_codice_init(p_ecc bigint)
RETURNS text AS $fn$
-- ⚠️ `text` esplicito: e' il canale CONSTRAINT dell'eccezione, non una colonna.
DECLARE v_cod text;
BEGIN
    PERFORM vendite.fn_offerta_eccezione_componenti_init(p_ecc, 1, script.fn_data_operativa());
    RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
    RETURN COALESCE(NULLIF(v_cod, ''), 'SQLSTATE:' || SQLSTATE);
END $fn$ LANGUAGE plpgsql;

CREATE TEMP TABLE tmp_oce_cod_14 AS
SELECT pg_temp.oce_codice_init(999999999::bigint) AS codice;

SELECT is(
    (SELECT codice FROM tmp_oce_cod_14),
    'E_OFFERTA_ECCEZIONE_NON_TROVATA',
    '14) fn_init(999999999, 1, date): eccezione non trovata → E_OFFERTA_ECCEZIONE_NON_TROVATA'
);

-- ============================================================
-- TEST 15) fn_init articolo non composito → 0
-- ============================================================
SELECT CASE
    WHEN (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'SEMPLICE') IS NOT NULL
    THEN is(
        vendite.fn_offerta_eccezione_componenti_init(
            (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'SEMPLICE'),
            (SELECT emittente_sr_id FROM tmp_oce_ctx),
            script.fn_data_operativa()
        ),
        0,
        '15) fn_init su articolo non composito → 0 (no-op CASO B)'
    )
    ELSE skip('15) skip: nessun articolo semplice disponibile')
END;

-- ============================================================
-- TEST 16) il kit non si vende a consumo (I-D6, rev 2026-10-21)
-- ============================================================
-- La riga composita con una fonte a valle (la combinazione la ammette la
-- tipologia, non il kit) e' fuori dal perimetro dell'articolo. Fino al
-- 2026-10-21 nasceva, con quantita' NULL, senza componenti e con prezzo 0.
-- Il codice si legge dal canale CONSTRAINT dell'eccezione.
CREATE OR REPLACE FUNCTION pg_temp.oce_codice(p_sql text)
RETURNS text LANGUAGE plpgsql AS $fx$
DECLARE v_cst text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN ERRORE';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME;
        RETURN coalesce(nullif(v_cst, ''), '-');
    END;
END;
$fx$;

SELECT is(
    (SELECT count(*)::int FROM vendite.fn_articolo_erogazioni(pg_temp.oce('P')) e
      WHERE e.fonte_quantita_attesa <> 'FISSA')
    || ' ' ||
    pg_temp.oce_codice(format(
        $$INSERT INTO vendite.offerte_commerciali_eccezioni (
              offerta_id, articolo_id, tipo_eccezione, fonte_quantita_attesa,
              prezzo_unitario, tipo_erogazione)
          VALUES (%s, %L, 'OVERRIDE', %L, 0.00, %L)$$,
        (SELECT offerta_id FROM tmp_oce_ids WHERE slot = 'CONSUMO'),
        (SELECT articolo_composito_id FROM tmp_oce_ctx),
        (SELECT fonte_consumo FROM tmp_oce_ctx),
        (SELECT erog_consumo FROM tmp_oce_ctx))),
    '0 E_RIGA_EROGAZIONE_FUORI_PERIMETRO',
    '16) il kit non si vende a consumo: nessuna fonte a valle nel suo perimetro, la riga e'' rifiutata'
);

-- Setup: prima chiamata fn_init (popola componenti per test 17-19)
DO $$
BEGIN
    IF (SELECT disponibile FROM tmp_oce_has_composito) THEN
        PERFORM vendite.fn_offerta_eccezione_componenti_init(
            (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA'),
            (SELECT emittente_sr_id FROM tmp_oce_ctx),
            DATE '2082-01-01'
        );
    END IF;
END $$;

-- ============================================================
-- TEST 17) fn_init idempotenza → 0 alla seconda chiamata
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_oce_has_composito)
    THEN is(
        vendite.fn_offerta_eccezione_componenti_init(
            (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA'),
            (SELECT emittente_sr_id FROM tmp_oce_ctx),
            DATE '2082-01-01'
        ),
        0,
        '17) fn_init idempotenza: seconda chiamata → 0'
    )
    ELSE skip('17) skip: nessun articolo composito disponibile')
END;

-- ============================================================
-- TEST 18) fn_init happy path: componenti inseriti > 0
-- (dopo il test 17 che ha già chiamato fn_init sulla COMPOSITA)
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_oce_has_composito)
    THEN ok(
        (SELECT COUNT(*) FROM vendite.offerte_commerciali_eccezioni_componenti
          WHERE eccezione_offerta_id =
                (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA')
        ) > 0,
        '18) fn_init happy path: componenti inseriti > 0 dopo prima chiamata'
    )
    ELSE skip('18) skip: nessun articolo composito disponibile')
END;

-- Setup test 19: crea eccezione COMPOSITA-OVR e chiama fn_init con override.
-- Chiave override: componente_id::text (uuid articolo figlio) — modello unificato
-- rev 2026-05-27; nessun filtro esposto_in_fattura nella ricerca del componente.
DO $$
DECLARE
    v_ovr_ecc_id  bigint;
    v_off_id      bigint;
    v_comp_id     uuid;
BEGIN
    IF NOT (SELECT disponibile FROM tmp_oce_has_composito) THEN RETURN; END IF;

    -- ⚠️ rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende, R5b): prima
    --   era un'AGGIUNTA dello stesso articolo composito, sulla stessa offerta che ne
    --   forzava gia' il prezzo (OVERRIDE): cioe' un articolo del listino aggiunto
    --   come fuori listino, che il guard dell'aggiunta ora rifiuta anche
    --   sull'offerta. Il test prova l'override del prezzo di un componente, non il
    --   tipo di riga: diventa un OVERRIDE su un'offerta sua, in BOZZA.
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT c.emittente_fiscale_id, c.billing_account_id, c.istanza_utility_id, c.utility_id,
           c.listino_id, c.listino_versione_id, DATE '2082-01-01', c.stato_bozza_id
      FROM tmp_oce_ctx c
    RETURNING id INTO v_off_id;

    -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
    INSERT INTO vendite.offerte_commerciali_eccezioni (
        offerta_id, articolo_id, tipo_eccezione, fonte_quantita_attesa,
        prezzo_unitario, qta_operativa, tipo_erogazione
    )
    VALUES (v_off_id, (SELECT articolo_composito_id FROM tmp_oce_ctx),
            'OVERRIDE', 'FISSA', 0.00, 3, (SELECT erog_composita FROM tmp_oce_ctx))
    RETURNING id INTO v_ovr_ecc_id;

    INSERT INTO tmp_oce_ids VALUES ('COMPOSITA-OVR', v_off_id, v_ovr_ecc_id);

    -- Prende il componente_id (uuid articolo figlio) del primo componente valido.
    SELECT ac.componente_id INTO v_comp_id
      FROM catalogo.articoli_componenti ac
     WHERE ac.prodotto_id = (SELECT articolo_composito_id FROM tmp_oce_ctx)
       AND COALESCE(ac.attivo, TRUE) = TRUE
       AND ac.validita @> DATE '2082-01-01'
     ORDER BY ac.id LIMIT 1;

    PERFORM vendite.fn_offerta_eccezione_componenti_init(
        v_ovr_ecc_id,
        (SELECT emittente_sr_id FROM tmp_oce_ctx),
        DATE '2082-01-01',
        jsonb_build_object(v_comp_id::text, 99999)
    );
END $$;

-- ============================================================
-- TEST 19) fn_init override: verifica che il prezzo override sia applicato
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_oce_has_composito)
    THEN ok(
        EXISTS (
            SELECT 1
              FROM vendite.offerte_commerciali_eccezioni_componenti
             WHERE eccezione_offerta_id =
                   (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA-OVR')
               AND prezzo_unitario = 99999
               AND origine_prezzo  = 'MANUALE'
        ),
        '19) fn_init override: prezzo 99999 applicato con origine_prezzo=MANUALE'
    )
    ELSE skip('19) skip: nessun articolo composito disponibile')
END;

-- Setup test 20: esegue push offerta → contratto
DO $$
BEGIN
    IF NOT (
        (SELECT disponibile FROM tmp_oce_has_composito)
        AND (SELECT COUNT(*) FROM vendite.offerte_commerciali_eccezioni_componenti
              WHERE eccezione_offerta_id =
                    (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA')
            ) > 0
    ) THEN RETURN; END IF;

    -- rev 2026-10-04 (R5a): righe e componenti si scrivono in BOZZA; il push vuole
    -- un'offerta ACCETTATA, e ci arriva per la sua strada: BOZZA -> EMESSA -> ACCETTATA.
    --   rev 2026-10-26 (giro 9): ci arriva dal verbo, non con l'UPDATE di stato.
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali',
        (SELECT offerta_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA'), 'ACCETTATA');

    PERFORM vendite.fn_push_offerta_a_contratto(
        (SELECT offerta_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA'),
        NULL
    );
END $$;

-- ============================================================
-- TEST 20) fn_push copia componenti → contratti_righe_componenti
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_oce_has_composito)
       AND (SELECT COUNT(*) FROM vendite.offerte_commerciali_eccezioni_componenti
             WHERE eccezione_offerta_id =
                   (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA')
           ) > 0
    THEN ok(
        (SELECT COUNT(*)
           FROM vendite.contratti_righe_componenti crc
           JOIN vendite.contratti_righe cr ON cr.id = crc.riga_contratto_id
           JOIN vendite.contratti c ON c.id = cr.contratto_id
          WHERE c.offerta_id =
                (SELECT offerta_id FROM tmp_oce_ids WHERE slot = 'COMPOSITA')
        ) > 0,
        '20) fn_push rev3: contratti_righe_componenti copiati dal push offerta→contratto'
    )
    ELSE skip('20) skip: componenti offerta non disponibili per test push')
END;

-- ============================================================
-- Setup test 21-26: fn_offerta_eccezione_componenti_preview
-- Context separato: richiede componenti validi per script.fn_data_operativa().
-- ============================================================
CREATE TEMP TABLE tmp_preview_ctx AS
SELECT
    ctx.articolo_composito_id,
    ctx.articolo_semplice_id,
    ctx.billing_account_id,
    ctx.utility_id,
    ctx.emittente_sr_id,
    a.uom_id   AS composito_uom_id,
    as_.uom_id AS semplice_uom_id,
    -- disponibile = true solo se tutti i dati presenti E almeno
    -- un componente attivo valido per script.fn_data_operativa()
    (ctx.articolo_composito_id IS NOT NULL
     AND ctx.billing_account_id IS NOT NULL
     AND ctx.emittente_sr_id IS NOT NULL
     AND EXISTS (
         SELECT 1 FROM catalogo.articoli_componenti ac
          WHERE ac.prodotto_id = ctx.articolo_composito_id
            AND COALESCE(ac.attivo, TRUE) = TRUE
            AND ac.validita @> script.fn_data_operativa()
     )) AS disponibile
  FROM tmp_oce_ctx ctx
  LEFT JOIN catalogo.articoli a   ON a.id   = ctx.articolo_composito_id
  LEFT JOIN catalogo.articoli as_ ON as_.id = ctx.articolo_semplice_id;

-- ============================================================
-- TEST 21) fn_preview esiste (has_function)
-- ============================================================
SELECT has_function(
    'vendite',
    'fn_offerta_eccezione_componenti_preview',
    '21) vendite.fn_offerta_eccezione_componenti_preview esiste'
);

-- ============================================================
-- TEST 22) fn_preview articolo semplice → 0 righe
-- ============================================================
SELECT CASE
    WHEN (SELECT billing_account_id IS NOT NULL
               AND articolo_semplice_id IS NOT NULL
            FROM tmp_preview_ctx)
    THEN is(
        (SELECT COUNT(*) FROM vendite.fn_offerta_eccezione_componenti_preview(
            (SELECT articolo_semplice_id FROM tmp_preview_ctx),
            (SELECT semplice_uom_id      FROM tmp_preview_ctx),
            1,
            script.fn_data_operativa(),
            (SELECT billing_account_id   FROM tmp_preview_ctx),
            (SELECT utility_id           FROM tmp_preview_ctx),
            (SELECT emittente_sr_id      FROM tmp_preview_ctx),
            NULL
        )),
        0::bigint,
        '22) fn_preview articolo semplice → 0 righe (nessun componente BoM)'
    )
    ELSE skip('22) skip: articolo semplice o billing context non disponibile')
END;

-- ============================================================
-- TEST 23) fn_preview articolo composito → righe > 0
--          (obbligatorio + esposizione_in_fattura accessibili nella proiezione)
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_preview_ctx)
    THEN ok(
        (SELECT COUNT(*) FROM vendite.fn_offerta_eccezione_componenti_preview(
            (SELECT articolo_composito_id FROM tmp_preview_ctx),
            (SELECT composito_uom_id      FROM tmp_preview_ctx),
            2,
            script.fn_data_operativa(),
            (SELECT billing_account_id    FROM tmp_preview_ctx),
            (SELECT utility_id            FROM tmp_preview_ctx),
            (SELECT emittente_sr_id       FROM tmp_preview_ctx),
            NULL
        ) p
        -- IS NOT DISTINCT FROM sé stesso è tautologia: se le colonne non
        -- esistessero nella RETURNS TABLE, la query fallirebbe qui
        WHERE p.obbligatorio IS NOT DISTINCT FROM p.obbligatorio
          AND p.esposizione_in_fattura IS NOT DISTINCT FROM p.esposizione_in_fattura
        ) > 0,
        '23) fn_preview articolo composito: righe > 0, colonne obbligatorio+esposizione_in_fattura accessibili'
    )
    ELSE skip('23) skip: articolo composito con componenti validi per script.fn_data_operativa() non disponibile')
END;

-- ============================================================
-- TEST 24) COUNT preview = COUNT componenti attivi validi
--          (nessun filtro esposto_in_fattura → modello unificato)
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_preview_ctx)
    THEN is(
        (SELECT COUNT(*) FROM vendite.fn_offerta_eccezione_componenti_preview(
            (SELECT articolo_composito_id FROM tmp_preview_ctx),
            (SELECT composito_uom_id      FROM tmp_preview_ctx),
            2,
            script.fn_data_operativa(),
            (SELECT billing_account_id    FROM tmp_preview_ctx),
            (SELECT utility_id            FROM tmp_preview_ctx),
            (SELECT emittente_sr_id       FROM tmp_preview_ctx),
            NULL
        )),
        (SELECT COUNT(*)
           FROM catalogo.articoli_componenti ac
          WHERE ac.prodotto_id = (SELECT articolo_composito_id FROM tmp_preview_ctx)
            AND COALESCE(ac.attivo, TRUE) = TRUE
            AND ac.validita @> script.fn_data_operativa()),
        '24) fn_preview COUNT = COUNT componenti attivi validi (nessun filtro esposto_in_fattura)'
    )
    ELSE skip('24) skip: articolo composito con componenti validi per script.fn_data_operativa() non disponibile')
END;

-- ============================================================
-- TEST 25) quantita_componente = coeff_qta_snapshot * p_quantita_padre
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_preview_ctx)
    THEN ok(
        NOT EXISTS (
            SELECT 1
              FROM vendite.fn_offerta_eccezione_componenti_preview(
                  (SELECT articolo_composito_id FROM tmp_preview_ctx),
                  (SELECT composito_uom_id      FROM tmp_preview_ctx),
                  2,
                  script.fn_data_operativa(),
                  (SELECT billing_account_id    FROM tmp_preview_ctx),
                  (SELECT utility_id            FROM tmp_preview_ctx),
                  (SELECT emittente_sr_id       FROM tmp_preview_ctx),
                  NULL
              ) p
             WHERE p.quantita_componente IS DISTINCT FROM (p.coeff_qta_snapshot * 2)
        ),
        '25) fn_preview quantita_componente = coeff_qta_snapshot * 2 (p_quantita_padre) per ogni riga'
    )
    ELSE skip('25) skip: articolo composito con componenti validi per script.fn_data_operativa() non disponibile')
END;

-- ============================================================
-- TEST 26) fn_preview include componenti NASCOSTI
--          (verifica rimozione del vecchio filtro AND esposto_in_fattura=TRUE;
--          dal 2026-10-01 il booleano false e' esposizione_in_fattura = NASCOSTO)
-- ============================================================
SELECT CASE
    WHEN (SELECT disponibile FROM tmp_preview_ctx)
       AND EXISTS (
           SELECT 1 FROM catalogo.articoli_componenti ac
            WHERE ac.prodotto_id = (SELECT articolo_composito_id FROM tmp_preview_ctx)
              AND ac.esposizione_in_fattura = 'NASCOSTO'
              AND COALESCE(ac.attivo, TRUE) = TRUE
              AND ac.validita @> script.fn_data_operativa()
       )
    THEN ok(
        EXISTS (
            SELECT 1
              FROM vendite.fn_offerta_eccezione_componenti_preview(
                  (SELECT articolo_composito_id FROM tmp_preview_ctx),
                  (SELECT composito_uom_id      FROM tmp_preview_ctx),
                  2,
                  script.fn_data_operativa(),
                  (SELECT billing_account_id    FROM tmp_preview_ctx),
                  (SELECT utility_id            FROM tmp_preview_ctx),
                  (SELECT emittente_sr_id       FROM tmp_preview_ctx),
                  NULL
              ) p
             WHERE p.esposizione_in_fattura = 'NASCOSTO'
        ),
        '26) fn_preview include componenti NASCOSTI (filtro AND esposto=TRUE rimosso)'
    )
    ELSE skip('26) skip: nessun componente NASCOSTO valido per script.fn_data_operativa()')
END;

-- ============================================================
-- TEST 27) fn_init guard difensivo: ESCLUSIONE su articolo composito
--          → ritorna 0, NESSUN componente inserito, e la riga padre
--          conserva prezzo_unitario IS NULL (nessuna violazione del
--          CHECK chk_offerte_eccezioni_prezzo_per_tipo_eccezione).
-- ============================================================
SELECT CASE
    WHEN (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'ESCLUSIONE') IS NOT NULL
    THEN is(
        (
            -- la fn deve ritornare 0 (no-op) senza sollevare il CHECK
            SELECT vendite.fn_offerta_eccezione_componenti_init(
                (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'ESCLUSIONE'),
                (SELECT emittente_sr_id FROM tmp_oce_ctx),
                DATE '2082-01-01'
            )
        )
        -- 0 componenti inseriti
        + (SELECT COUNT(*)::integer FROM vendite.offerte_commerciali_eccezioni_componenti
            WHERE eccezione_offerta_id =
                  (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'ESCLUSIONE'))
        -- prezzo padre ancora NULL → +0; se non NULL questo termine sarebbe 1000
        + (SELECT CASE WHEN prezzo_unitario IS NULL THEN 0 ELSE 1000 END
             FROM vendite.offerte_commerciali_eccezioni
            WHERE id = (SELECT eccezione_id FROM tmp_oce_ids WHERE slot = 'ESCLUSIONE')),
        0,
        '27) fn_init ESCLUSIONE composito → 0, nessun componente, prezzo padre NULL'
    )
    ELSE skip('27) skip: nessuna eccezione ESCLUSIONE composita disponibile')
END;

SELECT * FROM finish();
ROLLBACK;
