-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: sotto una distinta ANNULLATA le righe si leggono soltanto, e l'annullo
--       e' un gesto della MANUALE —
--       pagamenti.vendite_contabili_stati.righe_lavorabili,
--       pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale (quinta mossa),
--       script.fn_check_riga_contabile_eliminabile (motivo DISTINTA_ANNULLATA),
--       pagamenti.trgfn_vendite_contabili_guard_validazione (regola 3)
--
-- Elenco test (plan 22):
--  1) la bandiera c'e': NOT NULL, default false (fail-closed)
--  2) una MANUALE in BOZZA si annulla ancora (D-4 non la tocca)
--  3) ⭐ DA_ABBINARE sotto l'annullata: -> SOSPESA rifiutata, E_RIGA_CONTABILE_DISTINTA_ANNULLATA
--  4) ...-> SCARTATA rifiutata, stesso codice
--  5) ...correggere motivo_sospeso rifiutato (D-3: ogni scrittura)
--  6) ...il DELETE rifiutato, stesso codice (dalla check, via guard_contenuto)
--  7) ...la disattivazione rifiutata, stesso codice
--  8) ...lo spostamento FUORI dall'annullata rifiutato (le quattro mosse non lo vedevano)
--  9) la check nomina UN motivo solo, DISTINTA_ANNULLATA (ELSIF: niente DISTINTA_FINALE dietro)
-- 10) ...e la riga e' rimasta esattamente com'era
-- 11) una MANUALE VALIDATA si annulla ancora
-- 12) ⭐ SOSPESA sotto la validata poi annullata: -> SCARTATA rifiutata
-- 13) ...-> DA_ABBINARE rifiutata
-- 14) ...correzione del motivo rifiutata
-- 15) le quattro mosse non cambiano: una riga NUOVA sotto l'annullata -> E_RIGA_CONTABILE_DISTINTA_FINALE
-- 16) ...e una riga SPOSTATA dentro l'annullata -> E_RIGA_CONTABILE_DISTINTA_FINALE
-- 17) il congelamento non si allarga: sotto una BOZZA il motivo si corregge
-- 18) sotto una CHIUSA le righe si lavorano ancora: SOSPESA -> SCARTATA ammessa
-- 19) ...e «Riprendi»: SCARTATA -> SOSPESA ammessa
-- 20) ...e la registrazione tardiva passa ancora (non-regressione D20-b)
-- 21) ⭐ D-4: una GENERATA non si annulla — E_CONTABILE_ANNULLO_NON_MANUALE
-- 22) ...e resta VALIDATA
--
-- Scopo:
--  - D-1/D-3 (brief-db-righe-distinta-annullata-fuori-dalle-code): sotto una
--    distinta con righe_lavorabili = false le righe si CONGELANO — nessun
--    cambio di stato, nessuna correzione, nessuna eliminazione (test 3-14);
--  - D-2: il codice e' proprio, E_RIGA_CONTABILE_DISTINTA_ANNULLATA, e arriva
--    identico dalle due porte — la quinta mossa sull'UPDATE (3-5, 8, 12-14) e
--    la check sul DELETE e sulla disattivazione (6-7, 9). ⭐ Si asserisce il
--    CODICE (campo CONSTRAINT dell'eccezione), non la frase: un throws_like
--    su «annullata» passerebbe anche col messaggio di E_RIGA_CONTABILE_DISTINTA_FINALE,
--    che quella parola la contiene;
--  - il perimetro NON si allarga: le quattro mosse d'ingresso rispondono come
--    prima (15-16), la BOZZA resta libera (17), la CHIUSA resta lavorabile —
--    scartare, riprendere, la tardiva (18-20);
--  - D-4: l'annullo e' solo della MANUALE (2, 11 ammessi; 21-22 rifiutato):
--    senza, il sync dei fondi avrebbe incontrato righe congelate;
--  - ⚠️ la fixture SI COSTRUISCE (azienda, operatore, cliente, fattura) e le
--    distinte si INSERISCONO dirette, come in test-righe-contabili-eliminazione-v1:
--    la chiave di riuso di fn_get_or_create_vendite_contabile potrebbe
--    restituire una distinta gia' esistente della stessa giornata.
--  - ⚠️ MUTAZIONE (brief §4.3), provata a mano il 2026-09-30 sullo scratch e
--    non in questo file: il runner gira come l'applicazione e non puo'
--    riscrivere il guard. Senza la quinta mossa (20260930-32) rossi 3-5, 8,
--    12-14, e a cascata 9-10 (lo spostamento dell'8 passa e la riga finisce
--    in una bozza); senza il motivo 1a della check (-31) rossi 6-7 e 9 (arriva
--    E_RIGA_CONTABILE_DISTINTA_FINALE); senza la regola 3 del guard di
--    validazione (-33) rossi 21-22.
--
-- Piano: brief-db-righe-distinta-annullata-fuori-dalle-code §4.3, §9 P-7
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione, con la RLS.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(22);

-- ============================================================
-- Il codice del rifiuto
--   fn_log_and_raise_error mette il codice di dominio nel campo CONSTRAINT
--   dell'eccezione: throws_ok vede solo SQLSTATE e messaggio, quindi serve un
--   blocco EXCEPTION. Lo statement fallito annulla solo se stesso.
-- ============================================================
CREATE FUNCTION pg_temp.codice_rifiuto(p_sql text)
RETURNS text
LANGUAGE plpgsql
AS $fn$
DECLARE
    v_codice text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN_RIFIUTO';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME;
        RETURN COALESCE(NULLIF(v_codice, ''), 'SQLSTATE ' || SQLSTATE);
    END;
END;
$fn$;

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_righe_annullata_congelate'::text AS test_scope;

CREATE TEMP TABLE tmp_cli AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('righe annullata congelate') c;

CREATE TEMP TABLE tmp_refs AS
SELECT script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id)                       AS registro_id,
       (SELECT billing_account_id FROM tmp_cli)                                      AS billing_account_id,
       (SELECT utility_id FROM tmp_cli)                                              AS utility_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1)                           AS valuta_id,
       m.soggetto_ruolo_id                                                          AS emittente_soggetto_ruolo_id,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA' ORDER BY c.id LIMIT 1) AS centro_banca_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'DA_ABBINARE' ORDER BY s.id LIMIT 1)               AS st_da_abbinare,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'ABBINATA'    ORDER BY s.id LIMIT 1)               AS st_abbinata,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'SOSPESA'     ORDER BY s.id LIMIT 1)               AS st_sospesa,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'SCARTATA'    ORDER BY s.id LIMIT 1)               AS st_scartata,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'BOZZA'       ORDER BY s.id LIMIT 1)               AS d_bozza,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'VALIDATA'    ORDER BY s.id LIMIT 1)               AS d_validata,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'ANNULLATA'   ORDER BY s.id LIMIT 1)               AS d_annullata
  FROM _mondo m;

-- La fattura dell'azienda, scritta come la scriverebbe l'applicazione.
CREATE TEMP TABLE tmp_fattura AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, totale_a_pagare, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id, 350.00,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_refs r
  RETURNING id
)
SELECT id AS fattura_id FROM ins;

-- Cinque distinte, INSERITE dirette (vedi Scopo):
--   DA  MANUALE  in BOZZA     — sara' ANNULLATA dalla BOZZA
--   DV  MANUALE  in BOZZA     — sara' VALIDATA e poi ANNULLATA
--   DC  MANUALE  in BOZZA     — sara' REGISTRATA (CHIUSA)
--   DB  MANUALE  in BOZZA     — resta in BOZZA
--   DG  GENERATA in VALIDATA  — com'e' quella del sync dei fondi
CREATE TEMP TABLE tmp_distinte AS
WITH ins AS (
    INSERT INTO pagamenti.vendite_contabili
        (centro_riscossione_id, data_contabile, data_registrazione,
         stato_id, origine, meta)
    SELECT r.centro_banca_id, script.fn_data_operativa(), script.fn_data_operativa(),
           CASE v.et WHEN 'DG' THEN r.d_validata ELSE r.d_bozza END,
           v.origine,
           jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'et', v.et)
      FROM tmp_refs r
      CROSS JOIN (VALUES ('DA', 'MANUALE'), ('DV', 'MANUALE'), ('DC', 'MANUALE'),
                         ('DB', 'MANUALE'), ('DG', 'GENERATA')) AS v(et, origine)
    RETURNING id, meta ->> 'et' AS et
)
SELECT * FROM ins;

-- Le righe:
--   RA  DA_ABBINARE sotto DA
--   RV  SOSPESA     sotto DV
--   CA  ABBINATA    sotto DC (sara' POSTATA), CS1 e CS2 SOSPESE sotto DC
--   RB  SOSPESA     sotto DB
CREATE TEMP TABLE tmp_righe AS
WITH ins AS (
    INSERT INTO pagamenti.vendite_contabili_righe
        (contabile_id, riferimento_ente, data_pagamento, importo,
         fattura_id, billing_account_id, stato_id, motivo_sospeso, meta)
    SELECT d.id, 'PGTAP_ANNC_' || v.et, script.fn_data_operativa(), v.importo,
           CASE WHEN v.stato = 'ABB' THEN (SELECT fattura_id FROM tmp_fattura) END,
           CASE WHEN v.stato = 'ABB' THEN r.billing_account_id END,
           CASE v.stato WHEN 'DAB' THEN r.st_da_abbinare
                        WHEN 'ABB' THEN r.st_abbinata
                        ELSE            r.st_sospesa END,
           CASE WHEN v.stato = 'SOS' THEN 'da capire di chi e''' END,
           jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'et', v.et)
      FROM tmp_refs r
      CROSS JOIN (VALUES ('RA',  'DA', 'DAB', 30.00::numeric),
                         ('RV',  'DV', 'SOS', 20.00::numeric),
                         ('CA',  'DC', 'ABB', 100.00::numeric),
                         ('CS1', 'DC', 'SOS', 10.00::numeric),
                         ('CS2', 'DC', 'SOS', 15.00::numeric),
                         ('RB',  'DB', 'SOS',  5.00::numeric)) AS v(et, dist, stato, importo)
      JOIN tmp_distinte d ON d.et = v.dist
    RETURNING id, meta ->> 'et' AS et
)
SELECT * FROM ins;

-- ============================================================
-- 1) La bandiera
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'pagamenti'
               AND table_name   = 'vendite_contabili_stati'
               AND column_name  = 'righe_lavorabili'
               AND data_type    = 'boolean'
               AND is_nullable  = 'NO'
               AND column_default = 'false'),
    '1) righe_lavorabili c''e'': boolean NOT NULL, default false — uno stato nuovo non apre il lavoro');

-- ============================================================
-- 2-10) DA_ABBINARE sotto una BOZZA poi annullata
-- ============================================================
SELECT lives_ok(
    format($q$UPDATE pagamenti.vendite_contabili SET stato_id = %s WHERE id = %s$q$,
           (SELECT d_annullata FROM tmp_refs), (SELECT id FROM tmp_distinte WHERE et = 'DA')),
    '2) una MANUALE in BOZZA si annulla ancora: D-4 tocca solo le non manuali');

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili_righe SET stato_id = %s, motivo_sospeso = 'x' WHERE id = %s$q$,
        (SELECT st_sospesa FROM tmp_refs), (SELECT id FROM tmp_righe WHERE et = 'RA'))),
    'E_RIGA_CONTABILE_DISTINTA_ANNULLATA',
    '3) sotto l''annullata una DA_ABBINARE non si sospende: si legge soltanto');

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili_righe SET stato_id = %s WHERE id = %s$q$,
        (SELECT st_scartata FROM tmp_refs), (SELECT id FROM tmp_righe WHERE et = 'RA'))),
    'E_RIGA_CONTABILE_DISTINTA_ANNULLATA',
    '4) ...ne'' si scarta: non c''e'' niente da dire di denaro che non e'' mai arrivato');

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili_righe SET motivo_sospeso = 'nota tardiva' WHERE id = %s$q$,
        (SELECT id FROM tmp_righe WHERE et = 'RA'))),
    'E_RIGA_CONTABILE_DISTINTA_ANNULLATA',
    '5) ...ne'' si corregge un dato (D-3: un documento annullato non si ritocca)');

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$DELETE FROM pagamenti.vendite_contabili_righe WHERE id = %s$q$,
        (SELECT id FROM tmp_righe WHERE et = 'RA'))),
    'E_RIGA_CONTABILE_DISTINTA_ANNULLATA',
    '6) ...ne'' si cancella: la check parla col codice nuovo, via guard_contenuto');

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili_righe SET attivo = false WHERE id = %s$q$,
        (SELECT id FROM tmp_righe WHERE et = 'RA'))),
    'E_RIGA_CONTABILE_DISTINTA_ANNULLATA',
    '7) ...ne'' si disattiva: stessa check, stesso codice');

-- ⭐ Le quattro mosse guardano la distinta d'ARRIVO (qui una BOZZA): tirare
--    una riga FUORI da un'annullata non lo vedevano. La quinta guarda dove sta.
SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili_righe SET contabile_id = %s WHERE id = %s$q$,
        (SELECT id FROM tmp_distinte WHERE et = 'DB'), (SELECT id FROM tmp_righe WHERE et = 'RA'))),
    'E_RIGA_CONTABILE_DISTINTA_ANNULLATA',
    '8) ...ne'' si sposta FUORI in una bozza: la quinta mossa guarda la distinta di partenza');

-- ⚠️ ELSIF: sotto l'annullata DISTINTA_FINALE non segue — sarebbe un secondo
--    rimedio, e sbagliato, nel `motivi` del contesto.
SELECT ok(
    (SELECT jsonb_array_length(m) = 1
        AND m -> 0 ->> 'codice'     = 'E_RIGA_CONTABILE_DISTINTA_ANNULLATA'
        AND m -> 0 ->> 'reason'     = 'DISTINTA_ANNULLATA'
        AND m -> 0 ->> 'reason_key' = 'pagamenti.righe.elimina_reason.distinta_annullata'
       FROM script.fn_check_riga_contabile_eliminabile((SELECT id FROM tmp_righe WHERE et = 'RA')) AS m),
    '9) la check nomina UN motivo, DISTINTA_ANNULLATA, con la sua reason_key: il cestino si spegne col perche''');

SELECT ok(
    (SELECT s.codice_interno = 'DA_ABBINARE' AND r.attivo IS TRUE AND r.motivo_sospeso IS NULL
        AND r.contabile_id = (SELECT id FROM tmp_distinte WHERE et = 'DA')
       FROM pagamenti.vendite_contabili_righe r
       JOIN pagamenti.vendite_contabili_righe_stati s ON s.id = r.stato_id
      WHERE r.id = (SELECT id FROM tmp_righe WHERE et = 'RA')),
    '10) la riga e'' rimasta esattamente com''era: stato, attivo, motivo, distinta');

-- ============================================================
-- 11-14) SOSPESA sotto una VALIDATA poi annullata
-- ============================================================
UPDATE pagamenti.vendite_contabili SET stato_id = (SELECT d_validata FROM tmp_refs)
 WHERE id = (SELECT id FROM tmp_distinte WHERE et = 'DV');

SELECT lives_ok(
    format($q$UPDATE pagamenti.vendite_contabili SET stato_id = %s WHERE id = %s$q$,
           (SELECT d_annullata FROM tmp_refs), (SELECT id FROM tmp_distinte WHERE et = 'DV')),
    '11) una MANUALE VALIDATA si annulla ancora');

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili_righe SET stato_id = %s WHERE id = %s$q$,
        (SELECT st_scartata FROM tmp_refs), (SELECT id FROM tmp_righe WHERE et = 'RV'))),
    'E_RIGA_CONTABILE_DISTINTA_ANNULLATA',
    '12) sotto la validata poi annullata una SOSPESA non si scarta');

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili_righe SET stato_id = %s, motivo_sospeso = NULL WHERE id = %s$q$,
        (SELECT st_da_abbinare FROM tmp_refs), (SELECT id FROM tmp_righe WHERE et = 'RV'))),
    'E_RIGA_CONTABILE_DISTINTA_ANNULLATA',
    '13) ...ne'' torna da abbinare');

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili_righe SET motivo_sospeso = 'motivo corretto' WHERE id = %s$q$,
        (SELECT id FROM tmp_righe WHERE et = 'RV'))),
    'E_RIGA_CONTABILE_DISTINTA_ANNULLATA',
    '14) ...ne'' si corregge il motivo');

-- ============================================================
-- 15-16) Le quattro mosse d'ingresso non cambiano
-- ============================================================
SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$INSERT INTO pagamenti.vendite_contabili_righe
               (contabile_id, riferimento_ente, data_pagamento, importo, stato_id, meta)
           VALUES (%s, 'PGTAP_ANNC_NUOVA', script.fn_data_operativa(), 1.00, %s,
                   jsonb_build_object('test_scope', %L))$q$,
        (SELECT id FROM tmp_distinte WHERE et = 'DA'), (SELECT st_da_abbinare FROM tmp_refs),
        (SELECT test_scope FROM tmp_costanti))),
    'E_RIGA_CONTABILE_DISTINTA_FINALE',
    '15) una riga NUOVA sotto l''annullata: la prima mossa, col codice di sempre');

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili_righe SET contabile_id = %s WHERE id = %s$q$,
        (SELECT id FROM tmp_distinte WHERE et = 'DA'), (SELECT id FROM tmp_righe WHERE et = 'RB'))),
    'E_RIGA_CONTABILE_DISTINTA_FINALE',
    '16) una riga SPOSTATA dentro l''annullata: la terza mossa, col codice di sempre');

-- ============================================================
-- 17) Il congelamento non si allarga
-- ============================================================
SELECT lives_ok(
    format($q$UPDATE pagamenti.vendite_contabili_righe SET motivo_sospeso = 'motivo corretto' WHERE id = %s$q$,
           (SELECT id FROM tmp_righe WHERE et = 'RB')),
    '17) sotto una BOZZA il motivo di una sospesa si corregge: il congelamento e'' solo dell''annullata');

-- ============================================================
-- 18-20) Sotto una CHIUSA le righe si lavorano ancora
-- ============================================================
UPDATE pagamenti.vendite_contabili SET stato_id = (SELECT d_validata FROM tmp_refs)
 WHERE id = (SELECT id FROM tmp_distinte WHERE et = 'DC');

CREATE TEMP TABLE tmp_posting AS
SELECT * FROM pagamenti.fn_posta_contabile((SELECT id FROM tmp_distinte WHERE et = 'DC'));

SELECT lives_ok(
    format($q$UPDATE pagamenti.vendite_contabili_righe SET stato_id = %s WHERE id = %s$q$,
           (SELECT st_scartata FROM tmp_refs), (SELECT id FROM tmp_righe WHERE et = 'CS1')),
    '18) sotto una CHIUSA una SOSPESA si scarta ancora: dire che cosa ne e'' stato del denaro');

SELECT lives_ok(
    format($q$UPDATE pagamenti.vendite_contabili_righe SET stato_id = %s WHERE id = %s$q$,
           (SELECT st_sospesa FROM tmp_refs), (SELECT id FROM tmp_righe WHERE et = 'CS1')),
    '19) ...e «Riprendi» la riporta a SOSPESA');

-- ⚠️ Il verbo in un'istruzione SEPARATA dall'asserzione.
CREATE TEMP TABLE tmp_tardiva AS
SELECT * FROM pagamenti.fn_posta_riga_tardiva(
    (SELECT id FROM tmp_righe WHERE et = 'CS2'),
    (SELECT fattura_id FROM tmp_fattura),
    (SELECT billing_account_id FROM tmp_refs));

SELECT is(
    (SELECT s.codice_interno
       FROM pagamenti.vendite_contabili_righe r
       JOIN pagamenti.vendite_contabili_righe_stati s ON s.id = r.stato_id
      WHERE r.id = (SELECT id FROM tmp_righe WHERE et = 'CS2')),
    'POSTATA',
    '20) ...e la registrazione tardiva passa ancora (D20-b): la quinta mossa non la tocca');

-- ============================================================
-- 21-22) D-4: l'annullo e' un gesto della MANUALE
-- ============================================================
SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili SET stato_id = %s WHERE id = %s$q$,
        (SELECT d_annullata FROM tmp_refs), (SELECT id FROM tmp_distinte WHERE et = 'DG'))),
    'E_CONTABILE_ANNULLO_NON_MANUALE',
    '21) una GENERATA non si annulla: la governa il giro che l''ha prodotta');

SELECT is(
    (SELECT s.codice_interno
       FROM pagamenti.vendite_contabili c
       JOIN pagamenti.vendite_contabili_stati s ON s.id = c.stato_id
      WHERE c.id = (SELECT id FROM tmp_distinte WHERE et = 'DG')),
    'VALIDATA',
    '22) ...e resta VALIDATA');

-- ⚠️ Niente cleanup: ci pensa il ROLLBACK.
SELECT * FROM finish();
ROLLBACK;
