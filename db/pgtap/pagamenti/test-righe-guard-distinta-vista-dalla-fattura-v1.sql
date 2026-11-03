-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: i guard delle righe contabili giudicano la distinta anche quando chi
--       scrive NON la vede —
--       pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale,
--       pagamenti.trgfn_vendite_contabili_righe_guard_contenuto (porta 2),
--       script.fn_get_contabile_stato_origine
--
-- Elenco test (plan 10):
--  1) fixture: due aziende, un super admin, cinque righe miste
--  2) ⭐ A vede le righe miste e NON le loro distinte: e' il caso
--  3) 🔴 sotto la CHIUSA di B, A non porta la riga a pronta da registrare
--  4) ...e il messaggio non mostra il numero di una distinta che A non vede
--  5) 🔴 sotto l'ANNULLATA di B, A non ritocca la riga
--  6) 🔴 sotto la MANUALE VALIDATA di B, A non cambia l'importo
--  7) il rifiuto non si allarga: sotto la BOZZA di B, A cambia l'importo
--  8) chi vede la distinta (B) riceve lo stesso rifiuto di 3, su una riga sua (RK)
--  9) il lettore e' SECURITY DEFINER, con il search_path fissato
-- 10) Cleanup
--
-- Scopo:
--  - una riga contabile si vede per DUE strade (policy
--    rls_vendite_contabili_righe_perimetro_incasso): l'emittente della
--    distinta, oppure l'emittente della fattura. La riga «mista» — sulla
--    distinta di B, abbinata alla fattura di A — il modello la ammette: la
--    scrive chi ha in perimetro tutte e due le aziende, cioe' un super admin
--    (un operatore lavora per UNA azienda: uq_user_emittenti_fiscali_auth_user),
--    e A la deve vedere per capire dove e' finito il suo incasso;
--  - 🔴 per A la distinta non c'e'. I due guard la leggevano sotto la row
--    security, non la trovavano e TACEVANO: 3, 5 e 6 passavano. Dal
--    2026-11-03 stato e origine si leggono con
--    script.fn_get_contabile_stato_origine, fuori dalla RLS;
--  - il numero della distinta resta letto sotto la RLS (4): chi non la vede
--    ne legge l'id, non il codice;
--  - 7 e 8 sono i controlli: la lettura nuova non rifiuta dove la regola non
--    rifiuta, e non cambia il rifiuto di chi la distinta la vede.
--  - ⚠️ si asserisce il CODICE (campo CONSTRAINT dell'eccezione), come in
--    test-righe-distinta-annullata-congelate-v1: i messaggi di
--    E_RIGA_CONTABILE_DISTINTA_FINALE e _ANNULLATA condividono parole;
--  - ⚠️ le distinte si INSERISCONO dirette, con l'emittente DATO: il super
--    admin non ha un'azienda sua, e la chiave di riuso di
--    fn_get_or_create_vendite_contabile potrebbe restituire una distinta gia'
--    esistente della stessa giornata.
--  - ⚠️ MUTAZIONE: con i corpi precedenti 3, 5 e 6 rispondono NESSUN_RIFIUTO,
--    ma SOLO come app: il caso esiste perche' la row security nasconde la
--    distinta. Visto come app sullo scratch il 2026-11-03, prima dell'apply:
--    rossi 3, 5, 6 e 9 (la funzione non c'era), verdi gli altri.
--  - ⚠️ Da OWNER (prova pre-apply sullo scratch, 2026-11-03) 2 e 4 sono rossi
--    per costruzione e 3, 5, 6 verdi anche senza la correzione: l'owner salta
--    la row security e la distinta la vede. Il file prova la regola solo sul
--    runner applicativo, per cui e' scritto.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⛔ LE DUE AZIENDE SI COSTRUISCONO, prima del contesto.
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Il super admin: senza azienda, come in produzione, e con tutte nel perimetro.
CREATE TEMP TABLE _admin AS
SELECT ou.auth_user_id
  FROM dbops.fn_pgtap_crea_operatore_umano('righe distinta vista dalla fattura', p_super_admin := true) ou;

-- ⚠️ 2. CONTESTO APPLICATIVO: si comincia nei panni di A, che costruisce il
--    suo cliente e la sua fattura.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondi WHERE lato = 'A')); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- Il codice e il messaggio del rifiuto
--   fn_log_and_raise_error mette il codice di dominio nel campo CONSTRAINT
--   dell'eccezione: throws_ok vede solo SQLSTATE e messaggio. Lo statement
--   fallito annulla solo se stesso.
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

CREATE FUNCTION pg_temp.messaggio_rifiuto(p_sql text)
RETURNS text
LANGUAGE plpgsql
AS $fn$
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN_RIFIUTO';
    EXCEPTION WHEN OTHERS THEN
        RETURN SQLERRM;
    END;
END;
$fn$;

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_righe_guard_distinta_vista_dalla_fattura'::text AS test_scope;

-- Il cliente di A, nei panni di A: senza terzo parametro il legame BA ->
-- emittente lo scrive il trigger verso l'emittente di chi agisce.
CREATE TEMP TABLE tmp_cli AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('righe distinta vista dalla fattura') c;

CREATE TEMP TABLE tmp_refs AS
SELECT (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'A')                  AS a_ef,
       (SELECT soggetto_ruolo_id    FROM _mondi WHERE lato = 'A')                  AS a_sr,
       (SELECT auth_user_id         FROM _mondi WHERE lato = 'A')                  AS a_user,
       (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'B')                  AS b_ef,
       (SELECT soggetto_ruolo_id    FROM _mondi WHERE lato = 'B')                  AS b_sr,
       (SELECT auth_user_id         FROM _mondi WHERE lato = 'B')                  AS b_user,
       (SELECT auth_user_id         FROM _admin)                                   AS admin_user,
       (SELECT billing_account_id FROM tmp_cli)                                    AS billing_account_id,
       (SELECT utility_id FROM tmp_cli)                                            AS utility_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1)                         AS valuta_id,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA' ORDER BY c.id LIMIT 1) AS centro_banca_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'ABBINATA' ORDER BY s.id LIMIT 1)                AS st_abbinata,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'SOSPESA'  ORDER BY s.id LIMIT 1)                AS st_sospesa,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'BOZZA'     ORDER BY s.id LIMIT 1)               AS d_bozza,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'VALIDATA'  ORDER BY s.id LIMIT 1)               AS d_validata,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'CHIUSA'    ORDER BY s.id LIMIT 1)               AS d_chiusa,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'ANNULLATA' ORDER BY s.id LIMIT 1)               AS d_annullata;

-- La fattura di A, scritta da A come la scriverebbe l'applicazione.
CREATE TEMP TABLE tmp_fattura AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, totale_a_pagare, meta)
  SELECT script.fn_pgtap_registro_fattura(r.a_sr), script.fn_data_operativa(), r.a_sr,
         r.billing_account_id, r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id, 500.00,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_refs r
  RETURNING id
)
SELECT id AS fattura_id FROM ins;

-- ⭐ Il super admin ha in perimetro tutte e due le aziende: e' chi puo'
--    scrivere la riga mista. Lavora senza un'azienda scelta.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT admin_user FROM tmp_refs)); END $ctx$;

-- Quattro distinte MANUALI di B, in BOZZA, con l'emittente DATO:
--   DC sara' CHIUSA · DA sara' ANNULLATA · DV sara' VALIDATA · DB resta in BOZZA
CREATE TEMP TABLE tmp_distinte AS
WITH ins AS (
    INSERT INTO pagamenti.vendite_contabili
        (centro_riscossione_id, data_contabile, data_registrazione,
         stato_id, origine, emittente_soggetto_ruolo_id, meta)
    SELECT r.centro_banca_id, script.fn_data_operativa(), script.fn_data_operativa(),
           r.d_bozza, 'MANUALE', r.b_sr,
           jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'et', v.et)
      FROM tmp_refs r
      CROSS JOIN (VALUES ('DC'), ('DA'), ('DV'), ('DB')) AS v(et)
    RETURNING id, codice, meta ->> 'et' AS et
)
SELECT * FROM ins;

-- Le righe MISTE: sulla distinta di B, con la fattura e il cliente di A.
--   RC SOSPESA sotto DC · RA SOSPESA sotto DA · RV ABBINATA sotto DV · RB ABBINATA sotto DB
--   RK SOSPESA sotto DC: e' la riga del test 8, separata da RC perche' un 3
--   rosso (la riga passata ad ABBINATA) non trascini l'8
CREATE TEMP TABLE tmp_righe AS
WITH ins AS (
    INSERT INTO pagamenti.vendite_contabili_righe
        (contabile_id, riferimento_ente, data_pagamento, importo,
         fattura_id, billing_account_id, stato_id, motivo_sospeso, meta)
    SELECT d.id, 'PGTAP_MISTA_' || v.et, script.fn_data_operativa(), v.importo,
           (SELECT fattura_id FROM tmp_fattura), r.billing_account_id,
           CASE v.stato WHEN 'ABB' THEN r.st_abbinata ELSE r.st_sospesa END,
           CASE WHEN v.stato = 'SOS' THEN 'da capire di chi e''' END,
           jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti), 'et', v.et)
      FROM tmp_refs r
      CROSS JOIN (VALUES ('RC', 'DC', 'SOS', 30.00::numeric),
                         ('RA', 'DA', 'SOS', 20.00::numeric),
                         ('RV', 'DV', 'ABB', 40.00::numeric),
                         ('RB', 'DB', 'ABB', 10.00::numeric),
                         ('RK', 'DC', 'SOS', 15.00::numeric)) AS v(et, dist, stato, importo)
      JOIN tmp_distinte d ON d.et = v.dist
    RETURNING id, meta ->> 'et' AS et
)
SELECT * FROM ins;

-- Le distinte di B arrivano dove servono.
UPDATE pagamenti.vendite_contabili SET stato_id = (SELECT d_validata FROM tmp_refs)
 WHERE id IN (SELECT id FROM tmp_distinte WHERE et IN ('DC', 'DV'));
UPDATE pagamenti.vendite_contabili SET stato_id = (SELECT d_chiusa FROM tmp_refs)
 WHERE id = (SELECT id FROM tmp_distinte WHERE et = 'DC');
UPDATE pagamenti.vendite_contabili SET stato_id = (SELECT d_annullata FROM tmp_refs)
 WHERE id = (SELECT id FROM tmp_distinte WHERE et = 'DA');

SELECT ok(
    (SELECT a_ef <> b_ef FROM tmp_refs)
    AND (SELECT count(*) = 5 FROM tmp_righe)
    AND (SELECT count(*) = 4 FROM tmp_distinte WHERE codice IS NOT NULL)
    AND (SELECT bool_and(c.stato_id = CASE d.et WHEN 'DC' THEN r.d_chiusa
                                                WHEN 'DA' THEN r.d_annullata
                                                WHEN 'DV' THEN r.d_validata
                                                ELSE r.d_bozza END)
           FROM tmp_distinte d
           JOIN pagamenti.vendite_contabili c ON c.id = d.id
           CROSS JOIN tmp_refs r),
    '1) fixture: due aziende, un super admin, quattro distinte di B con cinque righe miste');

-- ============================================================
-- Da qui nei panni di A
-- ============================================================
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT a_user FROM tmp_refs)); END $ctx$;

SELECT ok(
    (SELECT count(*) = 5 FROM pagamenti.vendite_contabili_righe
      WHERE id IN (SELECT id FROM tmp_righe))
    AND (SELECT count(*) = 0 FROM pagamenti.vendite_contabili
          WHERE id IN (SELECT id FROM tmp_distinte)),
    '2) A vede le cinque righe miste (dalla fattura) e nessuna delle loro distinte');

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili_righe SET stato_id = %s, motivo_sospeso = NULL WHERE id = %s$q$,
        (SELECT st_abbinata FROM tmp_refs), (SELECT id FROM tmp_righe WHERE et = 'RC'))),
    'E_RIGA_CONTABILE_DISTINTA_FINALE',
    '3) sotto la CHIUSA di B, A non porta la riga a pronta: il guard legge lo stato fuori dalla RLS');

SELECT ok(
    pg_temp.messaggio_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili_righe SET stato_id = %s, motivo_sospeso = NULL WHERE id = %s$q$,
        (SELECT st_abbinata FROM tmp_refs), (SELECT id FROM tmp_righe WHERE et = 'RC')))
      NOT LIKE '%' || (SELECT codice FROM tmp_distinte WHERE et = 'DC') || '%',
    '4) ...e il messaggio non mostra il numero di una distinta che A non vede');

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili_righe SET motivo_sospeso = 'nota di A' WHERE id = %s$q$,
        (SELECT id FROM tmp_righe WHERE et = 'RA'))),
    'E_RIGA_CONTABILE_DISTINTA_ANNULLATA',
    '5) sotto l''ANNULLATA di B, A non ritocca la riga: si legge soltanto');

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili_righe SET importo = 41.00 WHERE id = %s$q$,
        (SELECT id FROM tmp_righe WHERE et = 'RV'))),
    'E_RIGA_CONTABILE_DISTINTA_VALIDATA',
    '6) sotto la MANUALE VALIDATA di B, A non cambia l''importo: la porta 2 legge l''origine fuori dalla RLS');

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili_righe SET importo = 11.00 WHERE id = %s$q$,
        (SELECT id FROM tmp_righe WHERE et = 'RB'))),
    'NESSUN_RIFIUTO',
    '7) il rifiuto non si allarga: sotto la BOZZA di B, A cambia l''importo');

-- ============================================================
-- Il controllo: chi vede la distinta
-- ============================================================
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT b_user FROM tmp_refs)); END $ctx$;

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili_righe SET stato_id = %s, motivo_sospeso = NULL WHERE id = %s$q$,
        (SELECT st_abbinata FROM tmp_refs), (SELECT id FROM tmp_righe WHERE et = 'RK'))),
    'E_RIGA_CONTABILE_DISTINTA_FINALE',
    '8) B, che la distinta la vede, riceve lo stesso rifiuto');

-- ============================================================
-- Il lettore
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1
              FROM pg_proc p
              JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'script'
               AND p.proname = 'fn_get_contabile_stato_origine'
               AND p.prosecdef
               AND p.proconfig @> ARRAY['search_path=pg_catalog, pg_temp']),
    '9) script.fn_get_contabile_stato_origine e'' SECURITY DEFINER, con il search_path fissato');

-- ============================================================
-- Cleanup
-- ============================================================
SELECT ok(true, '10) Cleanup: la transazione viene annullata, nessun residuo');

SELECT * FROM finish();
ROLLBACK;
