-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: documenti.fn_pubblica_template_documento_versione — l'ordine delle
--       date lo giudica il guard comune, e la chiusura delle versioni
--       precedenti non dipende da p_valido_al.
-- Oggetti:
--   documenti.fn_pubblica_template_documento_versione   (rev 20260924-02)
--   script.trgfn_guard_date_validita                    (20260923-40)
--   documenti.fn_guard_versione_contesto                (20260930-18)
--   documenti.vw_template_versioni_stampabili           (20261114-02)
--   ex_template_documenti_versioni_no_overlap_pubblicata (20261114-01)
-- Brief: brief-db-guard-date-validita.md §13;
--        brief-db-documenti-versione-contesto-template.md (test 8-11, firma a 4)
--
-- Elenco test (plan 17):
--  1) date invertite -> parla il guard comune (E_DATA_AL_MINORE_DAL), non il
--     daterange della ricerca (22000) ne' il vecchio E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO
--  2) i due canali strutturati: CONSTRAINT = E_DATA_AL_MINORE_DAL, COLUMN = valido_al
--  3) il rifiuto e' atomico: la versione pubblicata prima resta PUBBLICATA e
--     aperta, la bozza resta BOZZA
--  4) pubblicazione con fine validita': la versione aperta che la precede
--     viene chiusa (versioni_obsolete = 1)
--  5) ... chiusa al giorno prima di p_valido_dal e resa OBSOLETA
--  6) una versione gia' chiusa PRIMA di p_valido_dal non si tocca
--     (versioni_obsolete = 0)
--  7) ... e resta PUBBLICATA con la sua fine
--  8) forma dichiarata 2, builder alla 1 -> E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA (rev 20260930-21)
--  9) ... e il rifiuto e' atomico: V3 pubblicata e aperta, V4 bozza
-- 10) p_versione_contesto NULL -> E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE
-- 11) forma dichiarata 2, builder alla 2 -> pubblicata (D-C4)
-- 12) il vincolo anti-overlap vale per PUBBLICATA e OBSOLETA (20261114-01)
-- 13) il registro dbops.automazione_overlap dice lo stesso predicato del vincolo
-- 14) nuova versione con partenza domani: la precedente e' OBSOLETA, chiusa a oggi
-- 15) ... e oggi stampa lei, non la nuova (20261114-02: la validita' decide)
-- 16) nuova versione con partenza oggi: stampa la nuova, la superata no
-- 17) una OBSOLETA sopra il periodo di altre versioni fuori bozza viola il vincolo
-- 18) una OBSOLETA non si modifica (Guard A1, 20261114-04)
-- 19) una OBSOLETA non torna in BOZZA
-- 20) una PUBBLICATA non torna in BOZZA
-- 21) dopo la pubblicazione la porta della chiusura e' richiusa
-- 22) senza porta una PUBBLICATA non si chiude a mano
-- 23) a porta aperta passa solo la chiusura, non un'altra colonna cambiata
--
-- ⭐ 15 e 17 sono rossi senza i due changeSet -01/-02 del 2026-11-14 (la vista
--    chiedeva PUBBLICATA, il vincolo copriva solo PUBBLICATA); 12 e 13 ne fissano
--    la forma, 16 il bordo, verde anche prima. Il controesempio da cui nascono: la
--    CI del 2026-11-14, col fuso aziendale spostato al giorno prima della
--    pubblicazione dello standard.
-- ⭐ 18, 19, 20 e 21 sono rossi senza il -04 (A1 proteggeva solo PUBBLICATA, senza
--    lo stato; la porta non esisteva). Nella corsa senza il -04 cadono anche 22 e
--    23, a cascata: il 20 riesce a riportare in BOZZA la V2 di C, e da bozza tutto
--    passa (prova del 2026-11-14 sullo scratch: senza 17/6, con 23/0). Da soli
--    sarebbero verdi anche prima: fissano che la porta non apre piu' di quanto serve. I test 4-7 e 14 provano che la
--    pubblicazione chiude come prima, ora in una scrittura sola sotto la porta.
--
-- Scopo:
--  - ⭐ i test 1-3 provano il ritiro della copia (20260924-02): la regola del
--    periodo ha una sede sola. ⚠️ Il ritiro da solo non bastava: la ricerca
--    delle versioni da chiudere costruiva daterange(p_valido_dal, p_valido_al)
--    e con le date invertite sollevava 22000 PRIMA dell'UPDATE — il test 1 lo
--    distingue perche' pretende la FRASE del guard;
--  - ⭐ i test 4-7 provano che la ricerca riscritta su [p_valido_dal, oltre)
--    chiude lo STESSO insieme di prima: una versione aperta si chiude anche
--    quando la nuova ha una fine (p_valido_al non conta), una gia' chiusa prima
--    dell'inizio della nuova no. Sono casi COSTRUITI, non una popolazione:
--    verdi anche prima della revisione, ed e' voluto — fissano l'equivalenza.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(23);

-- ============================================================
-- Fixture: un template dell'emittente di chi agisce, tre bozze
-- ============================================================
CREATE TEMP TABLE tmp_ptv_ctx AS
SELECT script.fn_pgtap_emittente_operatore()                            AS emittente_id,
       (SELECT s.id FROM config.sorgenti s
         WHERE s.codice_interno = 'PREVENTIVO')                         AS sorgente_id,
       (SELECT t.id FROM documenti.tipi_documento_output t
         WHERE t.codice_interno = 'PREVENTIVO')                         AS tipo_output_id,
       (SELECT r.id FROM documenti.render_engine_documento r
         WHERE r.codice_interno = 'WEASYPRINT')                         AS render_id;

CREATE TEMP TABLE tmp_ptv_template AS
WITH ins AS (
    INSERT INTO documenti.template_documenti (
        tipo_documento_output_id, codice, codice_interno, descrizione,
        sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
        is_default, attivo
    )
    SELECT tipo_output_id, 'PGTAP-PTV', 'PGTAP_PTV', 'Template per test pubblicazione',
           sorgente_id, 'pgtap.builder', emittente_id, false, true
      FROM tmp_ptv_ctx
    RETURNING id
)
SELECT id FROM ins;

-- ⚠️ In un'istruzione separata dal padre (guida pgTAP, «Padre e figlio»).
CREATE TEMP TABLE tmp_ptv_v AS
WITH ins AS (
    INSERT INTO documenti.template_documenti_versioni (
        template_documento_id, versione, stato, titolo, html_template, render_engine_id,
        versione_contesto
    )
    -- V1-V3 leggono la forma 1; la V4 e' preparata per la forma 2 (D-C4).
    SELECT (SELECT id FROM tmp_ptv_template), n, 'BOZZA', 'Versione ' || n, '<p>v' || n || '</p>',
           (SELECT render_id FROM tmp_ptv_ctx), CASE WHEN n = 4 THEN 2 ELSE 1 END
      FROM generate_series(1, 4) n
    RETURNING id, versione
)
SELECT id, versione FROM ins;

-- La V1 aperta dal 2026-01-01: la base su cui si pubblica dopo.
SELECT documenti.fn_pubblica_template_documento_versione(
    (SELECT id FROM tmp_ptv_v WHERE versione = 1), DATE '2026-01-01', 1, NULL);

-- ============================================================
-- 1-3) Date invertite: il guard comune, e nessuna traccia
-- ============================================================
SELECT throws_like(
    format($q$SELECT documenti.fn_pubblica_template_documento_versione(%s, DATE '2026-03-01', 1, DATE '2026-02-01')$q$,
           (SELECT id FROM tmp_ptv_v WHERE versione = 2)),
    '%è inferiore alla data dal%',
    '1) date invertite: parla il guard comune, non il daterange della ricerca ne'' il vecchio codice'
);

CREATE TEMP TABLE tmp_ptv_diag (vincolo text, campo text);

DO $diag$
DECLARE v_cst text; v_col text;
BEGIN
    BEGIN
        PERFORM documenti.fn_pubblica_template_documento_versione(
            (SELECT id FROM tmp_ptv_v WHERE versione = 2), DATE '2026-03-01', 1, DATE '2026-02-01');
        INSERT INTO tmp_ptv_diag VALUES (NULL, NULL);
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME, v_col = COLUMN_NAME;
        INSERT INTO tmp_ptv_diag VALUES (nullif(v_cst, ''), nullif(v_col, ''));
    END;
END $diag$;

SELECT is(
    (SELECT coalesce(vincolo, '-') || ' / ' || coalesce(campo, '-') FROM tmp_ptv_diag),
    'E_DATA_AL_MINORE_DAL / valido_al',
    '2) canali strutturati: il codice del guard comune e il campo valido_al'
);

SELECT is(
    (SELECT string_agg(t.versione || '=' || t.stato || '[' || coalesce(t.valido_al::text, 'aperta') || ']', ', ' ORDER BY t.versione)
       FROM documenti.template_documenti_versioni t
      WHERE t.id IN (SELECT id FROM tmp_ptv_v WHERE versione IN (1, 2))),
    '1=PUBBLICATA[aperta], 2=BOZZA[aperta]',
    '3) rifiuto atomico: la V1 resta pubblicata e aperta, la V2 resta bozza'
);

-- ============================================================
-- 4-5) Pubblicazione con una fine: la versione aperta si chiude
-- ============================================================
CREATE TEMP TABLE tmp_ptv_esito_v2 AS
SELECT * FROM documenti.fn_pubblica_template_documento_versione(
    (SELECT id FROM tmp_ptv_v WHERE versione = 2), DATE '2026-03-01', 1, DATE '2026-06-30');

SELECT is(
    (SELECT versioni_obsolete FROM tmp_ptv_esito_v2),
    1,
    '4) V2 [2026-03-01, 2026-06-30]: la V1 aperta si sovrappone e si chiude, anche se la V2 ha una fine'
);

SELECT is(
    (SELECT t.stato || '[' || t.valido_al || ']'
       FROM documenti.template_documenti_versioni t
      WHERE t.id = (SELECT id FROM tmp_ptv_v WHERE versione = 1)),
    'OBSOLETA[2026-02-28]',
    '5) la V1 e'' OBSOLETA e chiusa al giorno prima dell''inizio della V2'
);

-- ============================================================
-- 6-7) Una versione gia' chiusa prima dell'inizio della nuova non si tocca
-- ============================================================
CREATE TEMP TABLE tmp_ptv_esito_v3 AS
SELECT * FROM documenti.fn_pubblica_template_documento_versione(
    (SELECT id FROM tmp_ptv_v WHERE versione = 3), DATE '2026-08-01', 1, NULL);

SELECT is(
    (SELECT versioni_obsolete FROM tmp_ptv_esito_v3),
    0,
    '6) V3 dal 2026-08-01: la V2, chiusa il 2026-06-30, non si sovrappone e non si chiude'
);

SELECT is(
    (SELECT t.stato || '[' || t.valido_al || ']'
       FROM documenti.template_documenti_versioni t
      WHERE t.id = (SELECT id FROM tmp_ptv_v WHERE versione = 2)),
    'PUBBLICATA[2026-06-30]',
    '7) la V2 resta PUBBLICATA con la sua fine'
);

-- ============================================================
-- 8-11) Il patto versione/forma dei dati alla pubblicazione (rev 20260930-21)
-- ============================================================
-- La V4 dichiara di leggere la forma 2. Il builder (qui: il chiamante) dice
-- di produrre la forma 1: non si pubblica.
SELECT throws_like(
    format($q$SELECT documenti.fn_pubblica_template_documento_versione(%s, DATE '2026-10-01', 1, NULL)$q$,
           (SELECT id FROM tmp_ptv_v WHERE versione = 4)),
    '%legge i dati nella forma 2, ma il sistema li prepara nella forma 1%',
    '8) forma dichiarata 2, builder alla 1: E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA, con le due forme nella frase'
);

-- Il rifiuto arriva PRIMA di chiudere le versioni precedenti: niente da annullare.
SELECT is(
    (SELECT string_agg(t.versione || '=' || t.stato || '[' || coalesce(t.valido_al::text, 'aperta') || ']', ', ' ORDER BY t.versione)
       FROM documenti.template_documenti_versioni t
      WHERE t.id IN (SELECT id FROM tmp_ptv_v WHERE versione IN (3, 4))),
    '3=PUBBLICATA[aperta], 4=BOZZA[aperta]',
    '9) rifiuto atomico: la V3 resta pubblicata e aperta, la V4 resta bozza'
);

-- Senza la forma del builder il controllo non si fa: TECNICO, non un passaggio.
SELECT throws_like(
    format($q$SELECT documenti.fn_pubblica_template_documento_versione(%s, DATE '2026-10-01', NULL, NULL)$q$,
           (SELECT id FROM tmp_ptv_v WHERE versione = 4)),
    '%manca la forma dichiarata dai dati%',
    '10) p_versione_contesto NULL: E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE, non un salto del controllo'
);

-- D-C4 fino in fondo: la bozza preparata per la forma 2 si pubblica quando il
-- builder produce la 2.
CREATE TEMP TABLE tmp_ptv_esito_v4 AS
SELECT * FROM documenti.fn_pubblica_template_documento_versione(
    (SELECT id FROM tmp_ptv_v WHERE versione = 4), DATE '2026-10-01', 2, NULL);

SELECT is(
    (SELECT t.stato || '/' || t.versione_contesto
       FROM documenti.template_documenti_versioni t
      WHERE t.id = (SELECT id FROM tmp_ptv_v WHERE versione = 4)),
    'PUBBLICATA/2',
    '11) forma dichiarata 2, builder alla 2: la V4 si pubblica'
);

-- ============================================================
-- 12-17) Stampa fino alla vigilia della nuova (20261114-01, -02)
-- ============================================================
-- La stampabilita' si decide dalla validita': una versione OBSOLETA, superata da
-- una pubblicazione con decorrenza futura, stampa fino alla vigilia. Tutte le
-- date sono relative alla data operativa: il caso si costruisce, non dipende
-- dal giorno in cui gira il test.
SELECT ok(
    (SELECT pg_get_constraintdef(c.oid) LIKE '%''PUBBLICATA''%''OBSOLETA''%'
       FROM pg_constraint c
      WHERE c.conrelid = 'documenti.template_documenti_versioni'::regclass
        AND c.conname = 'ex_template_documenti_versioni_no_overlap_pubblicata'
        AND c.contype = 'x'),
    '12) ex_template_documenti_versioni_no_overlap_pubblicata: EXCLUDE su PUBBLICATA e OBSOLETA'
);

-- ⚠️ Il registro e' la sede da cui il framework ricreerebbe il vincolo: se dicesse
--    un predicato diverso, una ricreazione riaprirebbe il buco in silenzio. Si
--    confronta il SIGNIFICATO: il predicato del registro diventa il CHECK di una
--    tabella temporanea con le stesse colonne, e PostgreSQL normalizza le due
--    espressioni allo stesso modo (stessa forma di test-listino-versione-in-vigore-v1).
CREATE TEMP TABLE tmp_ptv_pred (LIKE documenti.template_documenti_versioni);
DO $pred$
BEGIN
    EXECUTE format('ALTER TABLE tmp_ptv_pred ADD CONSTRAINT chk_pred CHECK (%s)',
                   (SELECT where_predicate FROM dbops.automazione_overlap
                     WHERE target_schema = 'documenti' AND target_table = 'template_documenti_versioni'));
END $pred$;

SELECT is(
    (SELECT substring(pg_get_constraintdef(c.oid) FROM '^CHECK (.*)$')
       FROM pg_constraint c WHERE c.conname = 'chk_pred' AND c.conrelid = 'tmp_ptv_pred'::regclass),
    (SELECT substring(pg_get_constraintdef(c.oid) FROM ' WHERE (.*)$')
       FROM pg_constraint c
      WHERE c.conrelid = 'documenti.template_documenti_versioni'::regclass
        AND c.conname = 'ex_template_documenti_versioni_no_overlap_pubblicata'),
    '13) il registro overlap dice lo stesso predicato del vincolo (confronto normalizzato)'
);

-- Due modelli nuovi: B (la nuova parte domani), C (la nuova parte oggi).
CREATE TEMP TABLE tmp_ptv_tpl2 AS
WITH ins AS (
    INSERT INTO documenti.template_documenti (
        tipo_documento_output_id, codice, codice_interno, descrizione,
        sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
        is_default, attivo
    )
    SELECT tipo_output_id, 'PGTAP-PTV-' || k, 'PGTAP_PTV_' || k, 'Template per test stampabilita ' || k,
           sorgente_id, 'pgtap.builder', emittente_id, false, true
      FROM tmp_ptv_ctx, (VALUES ('B'), ('C')) x(k)
    RETURNING id, codice_interno
)
SELECT id, right(codice_interno, 1) AS k FROM ins;

-- ⚠️ In un'istruzione separata dal padre (guida pgTAP, «Padre e figlio»).
CREATE TEMP TABLE tmp_ptv_v2 AS
WITH ins AS (
    INSERT INTO documenti.template_documenti_versioni (
        template_documento_id, versione, stato, titolo, html_template, render_engine_id,
        versione_contesto
    )
    SELECT t.id, n, 'BOZZA', 'Versione ' || t.k || n, '<p>' || t.k || n || '</p>',
           (SELECT render_id FROM tmp_ptv_ctx), 1
      FROM tmp_ptv_tpl2 t, generate_series(1, 2) n
    RETURNING id, template_documento_id, versione
)
SELECT i.id, t.k, i.versione FROM ins i JOIN tmp_ptv_tpl2 t ON t.id = i.template_documento_id;

-- Scopo: la versione con cui il modello k stampa oggi (NULL se nessuna).
CREATE OR REPLACE FUNCTION pg_temp.stampa_oggi(p_k text)
RETURNS bigint LANGUAGE sql STABLE AS $fx$
  SELECT s.template_versione_id
    FROM documenti.vw_template_versioni_stampabili s
   WHERE s.template_documento_id = (SELECT id FROM tmp_ptv_tpl2 WHERE k = p_k);
$fx$;

-- B: la V1 in vigore da dieci giorni, la V2 pubblicata OGGI con partenza DOMANI.
-- C: la V1 in vigore da dieci giorni, la V2 pubblicata con partenza OGGI.
SELECT documenti.fn_pubblica_template_documento_versione(
    v.id, script.fn_data_operativa() - 10, 1, NULL)
  FROM tmp_ptv_v2 v WHERE v.versione = 1 ORDER BY v.k;
SELECT documenti.fn_pubblica_template_documento_versione(
    (SELECT id FROM tmp_ptv_v2 WHERE k = 'B' AND versione = 2), script.fn_data_operativa() + 1, 1, NULL);
SELECT documenti.fn_pubblica_template_documento_versione(
    (SELECT id FROM tmp_ptv_v2 WHERE k = 'C' AND versione = 2), script.fn_data_operativa(), 1, NULL);

-- La pubblicazione non cambia: la V1 di B e' superata, chiusa a oggi.
SELECT is(
    (SELECT t.stato || '[' || t.valido_al || ']'
       FROM documenti.template_documenti_versioni t
      WHERE t.id = (SELECT id FROM tmp_ptv_v2 WHERE k = 'B' AND versione = 1)),
    'OBSOLETA[' || script.fn_data_operativa() || ']',
    '14) B: la V1 e'' OBSOLETA e chiusa a oggi, la vigilia della V2 che parte domani'
);

-- ⭐ Il caso del difetto: prima della -02 qui non stampava niente (NON_RISOLTO).
SELECT is(
    pg_temp.stampa_oggi('B'),
    (SELECT id FROM tmp_ptv_v2 WHERE k = 'B' AND versione = 1),
    '15) B: oggi stampa la V1 OBSOLETA, valida fino a oggi, non la V2 che parte domani'
);

-- Il bordo: dal giorno di partenza stampa la nuova, e la superata no.
SELECT is(
    pg_temp.stampa_oggi('C'),
    (SELECT id FROM tmp_ptv_v2 WHERE k = 'C' AND versione = 2),
    '16) C: la V2 parte oggi e stampa lei; la V1, chiusa a ieri, non stampa piu'''
);

-- Una riga per modello per costruzione: una OBSOLETA che copre il periodo di un'altra
-- versione fuori bozza viola il vincolo. ⚠️ Con un INSERT e non con un UPDATE: dal
-- 20261114-04 l'UPDATE di una OBSOLETA lo ferma prima il Guard A1 (test 18), e qui
-- si prova il vincolo, che presidia anche le strade dove il trigger non passa.
SELECT throws_ok(
    format($q$INSERT INTO documenti.template_documenti_versioni (
                  template_documento_id, versione, stato, titolo, html_template,
                  render_engine_id, valido_dal, valido_al, versione_contesto)
              VALUES (%s, 3, 'OBSOLETA', 'Versione B3', '<p>B3</p>', %s,
                      script.fn_data_operativa(), script.fn_data_operativa() + 5, 1)$q$,
           (SELECT id FROM tmp_ptv_tpl2 WHERE k = 'B'),
           (SELECT render_id FROM tmp_ptv_ctx)),
    '23P01',
    NULL,
    '17) B: una OBSOLETA sopra il periodo di V1 e V2 viola il vincolo: per ogni data, una sola versione stampabile'
);

-- ============================================================
-- 18-23) Fuori bozza non si modifica, nemmeno superata (20261114-04)
-- ============================================================
-- ⭐ 18 e 19 sono il difetto: prima il Guard A1 proteggeva solo PUBBLICATA, e
--    lo stato non era nel suo UPDATE OF.
SELECT throws_like(
    format($q$UPDATE documenti.template_documenti_versioni
                 SET html_template = '<p>ritoccata</p>' WHERE id = %s$q$,
           (SELECT id FROM tmp_ptv_v2 WHERE k = 'B' AND versione = 1)),
    '%Una versione pubblicata di un template documentale non puo%',
    '18) B: la V1 OBSOLETA, che oggi stampa, non si modifica: E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE'
);

SELECT throws_like(
    format($q$UPDATE documenti.template_documenti_versioni
                 SET stato = 'BOZZA' WHERE id = %s$q$,
           (SELECT id FROM tmp_ptv_v2 WHERE k = 'B' AND versione = 1)),
    '%Una versione pubblicata di un template documentale non puo%',
    '19) B: la V1 OBSOLETA non torna in BOZZA (sarebbe la strada per modificarla)'
);

SELECT throws_like(
    format($q$UPDATE documenti.template_documenti_versioni
                 SET stato = 'BOZZA' WHERE id = %s$q$,
           (SELECT id FROM tmp_ptv_v2 WHERE k = 'C' AND versione = 2)),
    '%Una versione pubblicata di un template documentale non puo%',
    '20) C: la V2 PUBBLICATA non torna in BOZZA'
);

-- La porta si richiude: dopo le pubblicazioni sopra nessuno la trova aperta, e
-- senza porta la chiusura fatta a mano e' rifiutata.
SELECT is(
    current_setting('zeroerp.allow_template_versione_chiusura_override', true),
    'off',
    '21) dopo la pubblicazione la porta della chiusura e'' richiusa'
);

SELECT throws_like(
    format($q$UPDATE documenti.template_documenti_versioni
                 SET stato = 'OBSOLETA', valido_al = script.fn_data_operativa() + 30 WHERE id = %s$q$,
           (SELECT id FROM tmp_ptv_v2 WHERE k = 'C' AND versione = 2)),
    '%Una versione pubblicata di un template documentale non puo%',
    '22) C: senza porta la V2 PUBBLICATA non si chiude a mano'
);

-- A porta aperta passa SOLO la chiusura: con un'altra colonna cambiata, no.
SELECT throws_like(
    format($q$WITH porta AS (
                  SELECT set_config('zeroerp.allow_template_versione_chiusura_override', 'on', true))
              UPDATE documenti.template_documenti_versioni
                 SET stato = 'OBSOLETA', valido_al = script.fn_data_operativa() + 30,
                     html_template = '<p>di contrabbando</p>'
               WHERE id = %s AND EXISTS (SELECT 1 FROM porta)$q$,
           (SELECT id FROM tmp_ptv_v2 WHERE k = 'C' AND versione = 2)),
    '%Una versione pubblicata di un template documentale non puo%',
    '23) C: a porta aperta la chiusura con l''HTML cambiato e'' rifiutata: la porta ammette solo la chiusura'
);

SELECT * FROM finish();
ROLLBACK;
