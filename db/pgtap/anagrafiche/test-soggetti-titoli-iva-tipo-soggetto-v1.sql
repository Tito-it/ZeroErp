-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-differiti: escluso — le persone fisiche costruite qui restano SENZA
--   indirizzi e contatti completi: il soggetto del test sono i guard BEFORE ROW
--   sui titoli e sul cambio di natura, non la saga di completezza, che ha i
--   suoi test. La finestra la apre il file (DEFERRED) dopo ogni contesto.
-- pgTAP test per Zero ERP
--
-- Chi puo' essere titolare di un titolo IVA: la natura del soggetto.
--   Brief: brief-db-dati-fiscali-e-societari-del-soggetto (Parte D)
--   changeSet 20261010-88 (matrice), -89 (seed), -90 (predicati), -91 (lettori
--   DEFINER), -92 (guard sul titolo), -93 (guard sul cambio di natura),
--   -94 (guard sul ritiro di matrice).
--
-- Elenco test (plan 21):
--   struttura e predicati
--    1) seed: INTENTO e USO_INDUSTRIALE su DI, SP, SC, ENC; AGEVOLATA_104 su PR (D-2, D-3)
--    2) COOPERATIVA senza righe finche' D-4 e' aperta
--    3) i due lettori sono SECURITY DEFINER con pg_temp in coda al search_path
--    4) fn_titolo_iva_vigente sui valori: senza scadenza, scaduto ieri, scade oggi, spento
--    5) fn_titolo_iva_vigente e fn_titolo_iva_ammesso non sono STRICT
--   societa' (SC; prima delle persone: il builder chiude la finestra differita)
--    6) INTENTO vigente su una SC -> passa
--    7) AGEVOLATA_104 su una SC -> E_TITOLO_IVA_NON_AMMESSO_PER_TIPO_SOGGETTO
--    8) ... col campo 'tipo_titolo_iva_id'
--    9) AGEVOLATA_104 SCADUTO su una SC -> passa (un titolo finito non si giudica)
--   10) ... e prorogarlo (valido_al a NULL) -> rifiutato
--   11) COOPERATIVA su una SC -> rifiutato (nessuna riga = non ammesso, D-1)
--   matrice
--   12) ritirare (INTENTO, SC) con un INTENTO vigente su una SC -> E_TITOLO_IVA_AMMISSIONE_IN_USO
--   13) riscrivere la stessa riga attiva (il mirror del CSV) -> passa
--   RLS (il contesto passa a un secondo operatore e resta quello)
--   14) gemello: per l'operatore di un ALTRO emittente il titolo e' invisibile
--   15) ⭐ eppure il suo cambio di natura e' rifiutato: il lettore DEFINER lo vede
--   persone fisiche
--   16) INTENTO su un privato -> rifiutato
--   17) AGEVOLATA_104 su un privato -> passa
--   18) il privato con l'agevolazione vigente diventa ditta -> E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI
--   19) ... col campo 'tipo_soggetto_dettaglio_id'
--   20) chiuso il titolo (valido_al a ieri), il cambio passa (D-5)
--   senza natura (D-1)
--   21) un titolo su un soggetto senza natura -> E_DATO_FISCALE_SENZA_TIPO_SOGGETTO
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il test gira come l'applicazione (RLS attiva).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL DEFERRED;

SELECT plan(21);

-- Il campo del rifiuto (canale COLUMN).
CREATE OR REPLACE FUNCTION pg_temp.colonna_del_rifiuto(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_col text;
BEGIN
    EXECUTE p_sql;
    RETURN '(nessun rifiuto)';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_col = COLUMN_NAME;
    RETURN v_col;
END $f$;

CREATE TEMP TABLE _ref AS
SELECT script.fn_giorno_operativo(now())                                   AS oggi,
       (SELECT id FROM config.tipi_titolo_iva WHERE codice_interno = 'INTENTO')         AS intento,
       (SELECT id FROM config.tipi_titolo_iva WHERE codice_interno = 'AGEVOLATA_104')   AS agevolata,
       (SELECT id FROM config.tipi_titolo_iva WHERE codice_interno = 'COOPERATIVA')     AS cooperativa,
       (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'SC')      AS sc,
       (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR')      AS pr,
       (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'DI')      AS di,
       (SELECT id FROM config.iva WHERE codice_interno = 'NI35')                         AS iva_ni,
       (SELECT id FROM config.iva WHERE attivo AND aliquota_iva = 4 ORDER BY id LIMIT 1) AS iva_4;

-- Un titolo: tipo, soggetto, valido_al. L'emittente lo mette il default
-- (emittente di lavoro dell'operatore); il plafond solo dove il tipo lo ha.
CREATE OR REPLACE FUNCTION pg_temp.titolo_sql(p_soggetto uuid, p_tipo bigint, p_valido_al date)
RETURNS text LANGUAGE sql AS $f$
    SELECT format(
        'INSERT INTO anagrafiche.soggetti_titoli_iva
             (soggetto_id, tipo_titolo_iva_id, iva_id, valido_dal, valido_al, plafond, protocollo)
         VALUES (%L, %s, %s, DATE ''2026-01-01'', %L, %s, ''PGTAP-TIT-NAT'')',
        p_soggetto, p_tipo,
        CASE WHEN p_tipo = (SELECT intento FROM _ref) THEN (SELECT iva_ni FROM _ref)
             ELSE (SELECT iva_4 FROM _ref) END,
        p_valido_al,
        CASE WHEN p_tipo = (SELECT intento FROM _ref) THEN '1000.00' ELSE 'NULL' END);
$f$;

-- ============================================================
-- Struttura e predicati
-- ============================================================
SELECT results_eq(
    $$SELECT tt.codice_interno::text, tsd.codice_interno::text
        FROM config.tipi_titolo_iva_tipi_soggetto_dettaglio m
        JOIN config.tipi_titolo_iva tt          ON tt.id  = m.tipo_titolo_iva_id
        JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = m.tipo_soggetto_dettaglio_id
       WHERE m.attivo
       ORDER BY 1, 2$$,
    $$VALUES ('AGEVOLATA_104', 'PR'),
             ('INTENTO', 'DI'), ('INTENTO', 'ENC'), ('INTENTO', 'SC'), ('INTENTO', 'SP'),
             ('USO_INDUSTRIALE', 'DI'), ('USO_INDUSTRIALE', 'ENC'), ('USO_INDUSTRIALE', 'SC'),
             ('USO_INDUSTRIALE', 'SP')$$,
    '1. seed: intento e uso industriale a chi ha partita IVA, agevolazione L. 104 al solo privato');

SELECT is(
    (SELECT count(*)::int FROM config.tipi_titolo_iva_tipi_soggetto_dettaglio
      WHERE tipo_titolo_iva_id = (SELECT cooperativa FROM _ref)),
    0,
    '2. COOPERATIVA senza righe: finche'' D-4 e'' aperta non e'' ammessa su nessuno');

SELECT is(
    (SELECT count(*)::int FROM pg_catalog.pg_proc p
       JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'anagrafiche'
        AND p.proname IN ('fn_titolo_iva_non_ammesso_del_soggetto', 'fn_titolo_iva_vigente_su_natura_esiste')
        AND p.prosecdef
        AND array_to_string(p.proconfig, ',') LIKE '%search_path=pg_catalog, public, pg_temp%'),
    2,
    '3. i due lettori sono SECURITY DEFINER, con pg_temp in coda al search_path');

SELECT results_eq(
    $$VALUES (anagrafiche.fn_titolo_iva_vigente(true,  NULL::date,           DATE '2026-06-15')),
             (anagrafiche.fn_titolo_iva_vigente(true,  DATE '2026-06-14',   DATE '2026-06-15')),
             (anagrafiche.fn_titolo_iva_vigente(true,  DATE '2026-06-15',   DATE '2026-06-15')),
             (anagrafiche.fn_titolo_iva_vigente(false, NULL::date,           DATE '2026-06-15'))$$,
    $$VALUES (true), (false), (true), (false)$$,
    '4. vigente: senza scadenza si'', scaduto ieri no, scade oggi si'', spento no');

SELECT is(
    (SELECT count(*)::int FROM pg_catalog.pg_proc p
       JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'anagrafiche'
        AND p.proname IN ('fn_titolo_iva_vigente', 'fn_titolo_iva_ammesso')
        AND NOT p.proisstrict),
    2,
    '5. i due predicati non sono STRICT: il NULL ha la sua risposta');

-- ============================================================
-- Societa'. Per prime: il builder esce IMMEDIATE.
-- ============================================================
CREATE TEMP TABLE _sc AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Titoli per natura pgTAP srl') AS id;   -- default: SC
SET CONSTRAINTS ALL DEFERRED;

SELECT lives_ok(
    pg_temp.titolo_sql((SELECT id FROM _sc), (SELECT intento FROM _ref), NULL),
    '6. una dichiarazione d''intento vigente su una societa'' di capitali -> passa');

SELECT throws_like(
    pg_temp.titolo_sql((SELECT id FROM _sc), (SELECT agevolata FROM _ref), NULL),
    '%non e'' ammesso per il tipo soggetto%',
    '7. l''agevolazione L. 104 su una societa'' -> E_TITOLO_IVA_NON_AMMESSO_PER_TIPO_SOGGETTO');

SELECT is(
    pg_temp.colonna_del_rifiuto(pg_temp.titolo_sql((SELECT id FROM _sc), (SELECT agevolata FROM _ref), NULL)),
    'tipo_titolo_iva_id',
    '8. il rifiuto porta il campo ''tipo_titolo_iva_id'' (canale COLUMN)');

CREATE TEMP TABLE _scaduto (id bigint);
SELECT lives_ok(
    'WITH ins AS (' || pg_temp.titolo_sql((SELECT id FROM _sc), (SELECT agevolata FROM _ref),
                                          (SELECT oggi - 1 FROM _ref)) || ' RETURNING id)
     INSERT INTO _scaduto SELECT id FROM ins',
    '9. l''agevolazione SCADUTA ieri su una societa'' -> passa: un titolo finito non cambia aliquote');

SELECT throws_like(
    $$UPDATE anagrafiche.soggetti_titoli_iva SET valido_al = NULL WHERE id = (SELECT id FROM _scaduto)$$,
    '%non e'' ammesso per il tipo soggetto%',
    '10. ... e prorogarla la rende vigente -> rifiutato');

SELECT throws_like(
    pg_temp.titolo_sql((SELECT id FROM _sc), (SELECT cooperativa FROM _ref), NULL),
    '%non e'' ammesso per il tipo soggetto%',
    '11. COOPERATIVA su una societa'' -> rifiutato: nessuna riga di matrice = non ammesso (D-1)');

-- ============================================================
-- Matrice
-- ============================================================
SELECT throws_like(
    $$UPDATE config.tipi_titolo_iva_tipi_soggetto_dettaglio SET attivo = false
       WHERE tipo_titolo_iva_id = (SELECT intento FROM _ref)
         AND tipo_soggetto_dettaglio_id = (SELECT sc FROM _ref)$$,
    '%non si puo'' ritirare%',
    '12. ritirare (INTENTO, SC) sotto un intento vigente -> E_TITOLO_IVA_AMMISSIONE_IN_USO');

SELECT lives_ok(
    $$UPDATE config.tipi_titolo_iva_tipi_soggetto_dettaglio SET attivo = true
       WHERE tipo_titolo_iva_id = (SELECT intento FROM _ref)
         AND tipo_soggetto_dettaglio_id = (SELECT sc FROM _ref)$$,
    '13. riscrivere la stessa riga attiva, come fa il mirror del CSV -> passa');

-- ============================================================
-- RLS. Il contesto cambia qui, prima di ogni persona fisica incompleta:
-- fn_pgtap_set_contesto_operatore esce IMMEDIATE, e i guard differiti di
-- soggetti scatterebbero sulle fixture ancora a meta'. Il privato di questo
-- caso nasce quindi COMPLETO (gli indirizzi che la sua natura pretende, come
-- fa il builder delle societa'), con l'agevolazione presentata all'emittente
-- dell'operatore di default; poi si passa all'operatore di un ALTRO
-- emittente, che resta il contesto del resto del file.
-- ============================================================
CREATE TEMP TABLE _pr2 AS
SELECT anagrafiche.fn_crea_soggetto_pf(
           p_cognome := 'Titoli', p_nome := 'Altrove', p_codice_fiscale := dbops.fn_pgtap_cf_libero(),
           p_email := 'pgtap.titoli.pr2@example.com', p_sesso := 'M',
           p_tipo_soggetto_dettaglio_id := (SELECT pr FROM _ref)) AS id;

-- rev 2026-10-18: i campi della forma dallo stato (Italia: comune e CAP del catalogo)
INSERT INTO anagrafiche.indirizzi_soggetti (
    soggetto_id, tipo_indirizzo_id, indirizzo_libero, stato_id, comune_id, codice_postale_id, locality, postal_code)
SELECT (SELECT id FROM _pr2), m.tipo_indirizzo_id, 'Via pgTAP 2', 1, f.comune_id, f.codice_postale_id, f.locality, f.postal_code
  FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
 CROSS JOIN dbops.fn_pgtap_indirizzo_libero_forma(1) f
 WHERE m.tipo_soggetto_dettaglio_id = (SELECT pr FROM _ref)
   AND m.attivo AND m.obbligatorio;

DO $tit$ BEGIN
    EXECUTE pg_temp.titolo_sql((SELECT id FROM _pr2), (SELECT agevolata FROM _ref), NULL);
END $tit$;

-- La saga del privato e' completa: i differiti si verificano qui.
SET CONSTRAINTS ALL IMMEDIATE;

CREATE TEMP TABLE _op2 AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _op2)); END $ctx$;
SET CONSTRAINTS ALL DEFERRED;

SELECT is(
    (SELECT count(*)::int FROM anagrafiche.soggetti_titoli_iva WHERE soggetto_id = (SELECT id FROM _pr2)),
    0,
    '14. gemello: per l''operatore di un altro emittente il titolo e'' invisibile (RLS)');

SELECT throws_like(
    format($$UPDATE anagrafiche.soggetti
                SET tipo_soggetto_dettaglio_id = %s, partita_iva = %L
              WHERE id = %L$$,
           (SELECT di FROM _ref), dbops.fn_pgtap_piva_libera(), (SELECT id FROM _pr2)),
    '%ancora in vigore%',
    '15. eppure il suo cambio di natura e'' rifiutato: il lettore DEFINER vede sopra la RLS');

-- ============================================================
-- Persone fisiche
-- ============================================================
CREATE TEMP TABLE _pr AS
SELECT anagrafiche.fn_crea_soggetto_pf(
           p_cognome := 'Titoli', p_nome := 'Privato', p_codice_fiscale := dbops.fn_pgtap_cf_libero(),
           p_email := 'pgtap.titoli.pr@example.com', p_sesso := 'F',
           p_tipo_soggetto_dettaglio_id := (SELECT pr FROM _ref)) AS id;

SELECT throws_like(
    pg_temp.titolo_sql((SELECT id FROM _pr), (SELECT intento FROM _ref), NULL),
    '%non e'' ammesso per il tipo soggetto%',
    '16. una dichiarazione d''intento su un privato -> rifiutato (non e'' un esportatore abituale)');

CREATE TEMP TABLE _agev (id bigint);
SELECT lives_ok(
    'WITH ins AS (' || pg_temp.titolo_sql((SELECT id FROM _pr), (SELECT agevolata FROM _ref), NULL)
                    || ' RETURNING id) INSERT INTO _agev SELECT id FROM ins',
    '17. l''agevolazione L. 104 su un privato -> passa');

CREATE TEMP TABLE _diventa_di AS
SELECT format($$UPDATE anagrafiche.soggetti
                  SET tipo_soggetto_dettaglio_id = %s, partita_iva = %L
                WHERE id = %L$$,
              (SELECT di FROM _ref), dbops.fn_pgtap_piva_libera(), (SELECT id FROM _pr)) AS q;

SELECT throws_like(
    (SELECT q FROM _diventa_di),
    '%ancora in vigore%',
    '18. il privato con l''agevolazione vigente diventa ditta -> E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI');

SELECT is(
    pg_temp.colonna_del_rifiuto((SELECT q FROM _diventa_di)),
    'tipo_soggetto_dettaglio_id',
    '19. il rifiuto porta il campo ''tipo_soggetto_dettaglio_id'': e'' la natura che si e'' toccata');

UPDATE anagrafiche.soggetti_titoli_iva
   SET valido_al = (SELECT oggi - 1 FROM _ref)
 WHERE id = (SELECT id FROM _agev);

SELECT lives_ok(
    (SELECT q FROM _diventa_di),
    '20. chiuso il titolo (valido_al a ieri), il cambio di natura passa: si esce dalla validita'' (D-5)');

-- ============================================================
-- Senza natura (D-1)
-- ============================================================
CREATE TEMP TABLE _senza AS
WITH ins AS (
    INSERT INTO anagrafiche.soggetti (ragione_sociale, stato_id)
    VALUES ('Titoli pgTAP senza natura', (SELECT id FROM config.stati WHERE codice_iso2 = 'IT'))
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    pg_temp.colonna_del_rifiuto(pg_temp.titolo_sql((SELECT id FROM _senza), (SELECT intento FROM _ref), NULL)),
    'tipo_soggetto_dettaglio_id',
    '21. un titolo su un soggetto senza natura -> E_DATO_FISCALE_SENZA_TIPO_SOGGETTO');

SELECT * FROM finish();
ROLLBACK;
