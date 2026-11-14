-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-differiti: escluso — la ditta individuale costruita qui resta SENZA
--   indirizzi e contatti completi: il soggetto del test e' il guard BEFORE ROW
--   del cambio di natura e la sua check, non la saga di completezza, che ha i
--   suoi test. Con IMMEDIATE i guard differiti di soggetti rifiuterebbero la
--   fixture prima dell'asserzione. Il builder del preventivo viene PRIMA e
--   chiude la sua finestra; la persona fisica nasce dopo il DEFERRED dichiarato.
-- pgTAP test per Zero ERP
--
-- Il cambio di natura del soggetto: la regola dei motivi e il suo guard.
--   Brief: brief-db-cambio-natura-soggetto-conferma-e-pulizia §0, D-5 … D-11
--   (Tid, 2026-11-14), giro 2. ChangeSet 20261114-60 … -68; codici e frasi in
--   config/codici_errore.csv e config/messaggi_errore.csv.
--
-- Elenco test (plan 17):
--   struttura
--    1) il guard e' montato su soggetti, BEFORE UPDATE con WHEN (per funzione)
--    2) il guard dei titoli al cambio e il suo lettore sono ritirati
--    3) il guard del cambio parla per primo fra i guard a10 di soggetti (COLLATE "C")
--    4) la check e' INVOKER; i due lettori sopra la RLS sono DEFINER col search_path stretto
--   una societa' che compare in un preventivo
--    5) fn_soggetto_primo_documento la trova: PREVENTIVO
--    6) la natura che non cambia: nessun motivo
--    7) verso un privato: solo E_CAMBIO_NATURA_ALTRA_MACRO_TIPOLOGIA (D-11)
--    8) ... e l'UPDATE e' rifiutato con quella frase
--    9) verso una natura PG senza P.IVA (fabbricata): primo motivo E_CAMBIO_NATURA_CON_DOCUMENTI (D-6)
--   10) ... e fra i motivi c'e' anche la P.IVA da togliere
--   11) ... e l'UPDATE e' rifiutato col motivo dei documenti
--   12) il picker: la natura attuale ammessa, il privato spento col motivo della famiglia
--   una ditta individuale senza documenti
--   13) fn_soggetto_primo_documento: nessuno
--   14) verso un privato con la P.IVA ancora scritta: E_CAMBIO_NATURA_PIVA_NON_APPLICABILE, campo partita_iva
--   15) ... con la P.IVA proposta vuota: nessun motivo (giudica i valori PROPOSTI)
--   16) ... ma svuotarla e' dell'amministratore: E_SOGGETTO_ID_FISCALE_IMMUTABILE
--   il predicato degli indirizzi
--   17) fn_tipo_indirizzo_ammesso_per_natura sui valori del seed e sul fallback permissivo
--
-- ⭐ Il 9-11 costruisce il caso: il seed non ha due nature della stessa
--   famiglia di cui una senza P.IVA fra le persone giuridiche, ma il modello la
--   ammette (il catalogo e' un CSV). La natura fabbricata copia SC e toglie la
--   P.IVA e con lei i dati societari (chk_tipi_soggetto_dettaglio_piva_vs_policy
--   li lega); nessuna riga di matrice degli indirizzi, quindi indirizzi liberi.
-- ⛔ NON PROVATI, e dichiarati:
--   * il motivo degli indirizzi su righe vere (8 della check): una riga di
--     matrice nel test vuole la validita' daterange del seed; qui si prova il
--     predicato sui valori (17), l'aggregazione no;
--   * titoli IVA, flag PA e split payment: li provano
--     test-soggetti-titoli-iva-tipo-soggetto-v1.sql (14-15, 18-20, anche il
--     titolo di un altro emittente) e test-soggetti-regime-pa-v1.sql (8-9);
--   * la ditta individuale che compare in un documento: nessuna fixture crea un
--     cliente persona fisica; il ramo dei documenti lo prova la societa' (9-11).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

-- ============================================================
-- Struttura
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM pg_trigger g
             WHERE g.tgrelid = 'anagrafiche.soggetti'::regclass
               AND g.tgfoid = 'anagrafiche.trgfn_soggetti_guard_cambio_natura'::regproc
               AND NOT g.tgisinternal
               AND pg_get_triggerdef(g.oid) LIKE '%BEFORE UPDATE ON anagrafiche.soggetti%'
               AND pg_get_triggerdef(g.oid) LIKE '%WHEN ((old.tipo_soggetto_dettaglio_id IS DISTINCT FROM new.tipo_soggetto_dettaglio_id))%'),
    '1) il guard del cambio e'' montato su soggetti: BEFORE UPDATE, WHEN la natura cambia');

SELECT ok(
    to_regprocedure('anagrafiche.trgfn_soggetti_guard_titoli_iva_ammessi()') IS NULL
    AND to_regprocedure('anagrafiche.fn_titolo_iva_non_ammesso_del_soggetto(uuid, bigint)') IS NULL,
    '2) il guard dei titoli al cambio e il suo lettore sono ritirati: la regola sta nella check');

SELECT is(
    (SELECT min(g.tgname::text COLLATE "C")
       FROM pg_trigger g
      WHERE g.tgrelid = 'anagrafiche.soggetti'::regclass
        AND NOT g.tgisinternal
        AND g.tgname LIKE 'trg\_soggetti\_a10\_guard\_%'),
    'trg_soggetti_a10_guard_cambio_natura_upd',
    '3) il guard del cambio parla per primo fra i guard a10 di soggetti');

SELECT is(
    (SELECT array_agg(p.proname::text || ':' || p.prosecdef::text ORDER BY p.proname)
       FROM pg_proc p
      WHERE p.pronamespace = 'anagrafiche'::regnamespace
        AND p.proname IN ('fn_check_cambio_natura_soggetto', 'fn_soggetto_primo_documento',
                          'fn_titoli_iva_non_ammessi_conta')
        AND (NOT p.prosecdef
             OR array_to_string(p.proconfig, ',') LIKE '%search_path=pg_catalog, public, pg_temp%')),
    ARRAY['fn_check_cambio_natura_soggetto:false',
          'fn_soggetto_primo_documento:true',
          'fn_titoli_iva_non_ammessi_conta:true'],
    '4) la check e'' INVOKER; i due lettori sopra la RLS sono DEFINER col search_path stretto');

-- ============================================================
-- Una societa' che compare in un preventivo. Per prima: il builder esce IMMEDIATE.
-- ============================================================
CREATE TEMP TABLE _prev AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgTAP cambio natura');

CREATE TEMP TABLE _soc AS
SELECT r.soggetto_id AS id, s.tipo_soggetto_dettaglio_id AS natura, s.partita_iva
  FROM _prev p
  JOIN anagrafiche.soggetti_ruoli r ON r.id = p.cliente_soggetto_ruolo_id
  JOIN anagrafiche.soggetti s ON s.id = r.soggetto_id;

CREATE TEMP TABLE _ref AS
SELECT (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR') AS pr,
       (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'DI') AS di,
       (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'SEDELEG')     AS sedeleg,
       (SELECT max(id) FROM config.tipi_soggetto_dettaglio) + 100000              AS pg_senza_piva;

-- La natura PG senza P.IVA: copia di SC, senza P.IVA, senza righe di matrice. Senza P.IVA
-- vuol dire anche senza dati societari: lo pretende chk_tipi_soggetto_dettaglio_piva_vs_policy.
INSERT INTO config.tipi_soggetto_dettaglio
       (id, tipo_soggetto_id, stato_iso2, codice_interno, descrizione,
        formato_cf, formato_piva, stato_id, dati_societari_policy,
        piva_obbligatoria, cf_obbligatorio, sesso_policy,
        cliente_pa_ammesso, split_payment_ammesso)
SELECT r.pg_senza_piva, sc.tipo_soggetto_id, sc.stato_iso2, 'PGTAPNPI', 'Persona giuridica pgTAP senza P.IVA',
       sc.formato_cf, 'NON_APPLICABILE', sc.stato_id, 'NONE',
       false, sc.cf_obbligatorio, sc.sesso_policy,
       sc.cliente_pa_ammesso, sc.split_payment_ammesso
  FROM config.tipi_soggetto_dettaglio sc, _ref r
 WHERE sc.codice_interno = 'SC';

CREATE OR REPLACE FUNCTION pg_temp.motivi(p_soggetto uuid, p_natura bigint, p_piva text)
RETURNS jsonb LANGUAGE sql AS $f$
    SELECT anagrafiche.fn_check_cambio_natura_soggetto(
               s.id, p_natura, p_piva, s.cliente_pa, s.split_payment)
      FROM anagrafiche.soggetti s WHERE s.id = p_soggetto;
$f$;

CREATE OR REPLACE FUNCTION pg_temp.codici(p_motivi jsonb)
RETURNS text[] LANGUAGE sql AS $f$
    SELECT COALESCE(array_agg(m ->> 'codice' ORDER BY o), '{}')
      FROM jsonb_array_elements(p_motivi) WITH ORDINALITY AS e(m, o);
$f$;

SELECT is(
    anagrafiche.fn_soggetto_primo_documento((SELECT id FROM _soc)),
    'PREVENTIVO',
    '5) fn_soggetto_primo_documento trova la societa'' nel suo preventivo');

SELECT is(
    pg_temp.motivi((SELECT id FROM _soc), (SELECT natura FROM _soc), (SELECT partita_iva FROM _soc)),
    '[]'::jsonb,
    '6) la natura che non cambia: nessun motivo');

SELECT is(
    pg_temp.codici(pg_temp.motivi((SELECT id FROM _soc), (SELECT pr FROM _ref), (SELECT partita_iva FROM _soc))),
    ARRAY['E_CAMBIO_NATURA_ALTRA_MACRO_TIPOLOGIA'],
    '7) una societa'' verso un privato: solo il motivo della famiglia (D-11), da solo');

SELECT throws_like(
    format($$UPDATE anagrafiche.soggetti SET tipo_soggetto_dettaglio_id = %s WHERE id = %L$$,
           (SELECT pr FROM _ref), (SELECT id FROM _soc)),
    '%nature di famiglie diverse%',
    '8) ... e l''UPDATE e'' rifiutato con quella frase');

SELECT is(
    (pg_temp.codici(pg_temp.motivi((SELECT id FROM _soc), (SELECT pg_senza_piva FROM _ref),
                                   (SELECT partita_iva FROM _soc))))[1],
    'E_CAMBIO_NATURA_CON_DOCUMENTI',
    '9) verso una natura PG senza P.IVA: primo motivo, i documenti (D-6: definitivo)');

SELECT ok(
    'E_CAMBIO_NATURA_PIVA_NON_APPLICABILE' = ANY (
        pg_temp.codici(pg_temp.motivi((SELECT id FROM _soc), (SELECT pg_senza_piva FROM _ref),
                                      (SELECT partita_iva FROM _soc)))),
    '10) ... e fra i motivi c''e'' anche la P.IVA da togliere (elenca tutti i motivi, D-5)');

SELECT throws_like(
    format($$UPDATE anagrafiche.soggetti SET tipo_soggetto_dettaglio_id = %s WHERE id = %L$$,
           (SELECT pg_senza_piva FROM _ref), (SELECT id FROM _soc)),
    '%compare già in un documento%',
    '11) ... e l''UPDATE e'' rifiutato col primo motivo, i documenti');

SELECT results_eq(
    format($$SELECT tipo_soggetto_dettaglio_id, ammessa, motivo_codice
               FROM anagrafiche.fn_nature_proponibili_soggetto(%L)
              WHERE tipo_soggetto_dettaglio_id IN (%s, %s)
              ORDER BY ammessa DESC$$,
           (SELECT id FROM _soc), (SELECT natura FROM _soc), (SELECT pr FROM _ref)),
    format($$VALUES (%s::bigint, true, NULL::text),
                    (%s::bigint, false, 'E_CAMBIO_NATURA_ALTRA_MACRO_TIPOLOGIA'::text)$$,
           (SELECT natura FROM _soc), (SELECT pr FROM _ref)),
    '12) il picker: la natura attuale ammessa, il privato spento col motivo della famiglia');

-- ============================================================
-- Una ditta individuale senza documenti. La finestra differita la dichiara il file.
-- ============================================================
SET CONSTRAINTS ALL DEFERRED;

CREATE TEMP TABLE _di AS
SELECT anagrafiche.fn_crea_soggetto_pf(
           p_cognome := 'Natura', p_nome := 'Ditta', p_codice_fiscale := dbops.fn_pgtap_cf_libero(),
           p_email := 'pgtap.cambio.natura.di@example.com', p_sesso := 'M',
           p_tipo_soggetto_dettaglio_id := (SELECT di FROM _ref),
           p_partita_iva := dbops.fn_pgtap_piva_libera()) AS id;

SELECT ok(
    anagrafiche.fn_soggetto_primo_documento((SELECT id FROM _di)) IS NULL,
    '13) la ditta appena nata non compare in nessun documento');

SELECT is(
    (SELECT m -> 0 ->> 'codice' || '/' || (m -> 0 -> 'dettaglio' ->> 'campo')
       FROM (SELECT pg_temp.motivi((SELECT id FROM _di), (SELECT pr FROM _ref),
                                   (SELECT partita_iva FROM anagrafiche.soggetti
                                     WHERE id = (SELECT id FROM _di))) AS m) x),
    'E_CAMBIO_NATURA_PIVA_NON_APPLICABILE/partita_iva',
    '14) ditta verso privato con la P.IVA ancora scritta: il motivo della P.IVA, col suo campo');

SELECT is(
    pg_temp.motivi((SELECT id FROM _di), (SELECT pr FROM _ref), NULL),
    '[]'::jsonb,
    '15) ... con la P.IVA proposta vuota: nessun motivo (giudica i valori proposti, non la riga)');

SELECT throws_like(
    format($$UPDATE anagrafiche.soggetti SET tipo_soggetto_dettaglio_id = %s, partita_iva = NULL
              WHERE id = %L$$,
           (SELECT pr FROM _ref), (SELECT id FROM _di)),
    '%già scritto%',
    '16) ... ma svuotare la P.IVA e'' dell''amministratore: E_SOGGETTO_ID_FISCALE_IMMUTABILE');

-- ============================================================
-- Il predicato degli indirizzi, sui valori
-- ============================================================
SELECT results_eq(
    format($$VALUES (anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(%1$s, %3$s, script.fn_data_operativa())),
                    (anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(%2$s, %3$s, script.fn_data_operativa())),
                    (anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(NULL, %3$s, script.fn_data_operativa())),
                    (anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(%4$s, %3$s, script.fn_data_operativa()))$$,
           (SELECT pr FROM _ref), (SELECT di FROM _ref), (SELECT sedeleg FROM _ref),
           (SELECT pg_senza_piva FROM _ref)),
    $$VALUES (false), (true), (true), (true)$$,
    '17) sede legale: il privato no, la ditta si''; senza natura o senza matrice, libero');

SELECT * FROM finish();

ROLLBACK;
