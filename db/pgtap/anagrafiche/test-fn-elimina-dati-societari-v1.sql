-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-differiti: escluso — la ditta individuale costruita qui resta SENZA
--   indirizzi e contatti completi: il soggetto del test e' il verbo
--   dell'eliminazione e la check del cambio di natura, non la saga di
--   completezza, che ha i suoi test. Con IMMEDIATE i guard differiti di
--   soggetti rifiuterebbero la fixture prima dell'asserzione. La societa' nasce
--   PRIMA, dalla sua fixture (che chiude la sua finestra); la persona fisica
--   nasce dopo il DEFERRED dichiarato.
-- pgTAP test per Zero ERP
--
-- L'eliminazione manuale dei dati societari.
--   Brief: brief-db-cambio-natura-soggetto-conferma-e-pulizia §0, D-7 (Tid,
--   2026-11-14), giro 3. ChangeSet 20261114-69; codice
--   E_DATI_SOCIETARI_NON_ELIMINABILI in config/codici_errore.csv e
--   config/messaggi_errore.csv.
--
-- Elenco test (plan 14):
--   la porta
--    1) il verbo e' SECURITY DEFINER col search_path stretto
--    2) EXECUTE all'applicazione, non a PUBLIC
--    3) l'applicazione continua a non avere DELETE sulla tabella: la porta e' il verbo
--   lo storico sempre acceso (Q-10 = A)
--    3a) storicizza: DEFAULT true e NOT NULL
--    3b) la tabella e' nel registro dello storico (il flag non si spegne)
--   una societa' di capitali (i dati societari sono REQUIRED)
--    4) la check dice perche': E_DATI_SOCIETARI_NON_ELIMINABILI, col campo della natura
--    5) il verbo rifiuta con quella frase, e la riga resta
--   una ditta individuale (i dati societari sono OPTIONAL)
--    6) con i dati societari, verso un privato: il cambio di natura ha il motivo dei dati societari
--    7) la check dell'eliminazione: nessun motivo
--    8) il verbo elimina: vero
--    9) ... la riga non c'e' piu'
--   10) ... e lo storico la conserva (DELETE)
--   11) una seconda volta: falso, non e' un errore
--   12) e ora il cambio verso il privato non ha piu' quel motivo (con la P.IVA proposta vuota: nessuno)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- La porta
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM pg_proc p
             WHERE p.oid = 'anagrafiche.fn_elimina_dati_societari(uuid)'::regprocedure
               AND p.prosecdef
               AND array_to_string(p.proconfig, ',') LIKE '%search_path=pg_catalog, public, pg_temp%'),
    '1) il verbo e'' SECURITY DEFINER col search_path stretto');

SELECT ok(
    has_function_privilege('zeroerp_app', 'anagrafiche.fn_elimina_dati_societari(uuid)', 'EXECUTE')
    AND NOT EXISTS (SELECT 1 FROM pg_proc p, aclexplode(p.proacl) a
                     WHERE p.oid = 'anagrafiche.fn_elimina_dati_societari(uuid)'::regprocedure
                       AND a.grantee = 0 AND a.privilege_type = 'EXECUTE'),
    '2) EXECUTE all''applicazione, non a PUBLIC');

SELECT ok(
    NOT has_table_privilege('zeroerp_app', 'anagrafiche.dati_societari', 'DELETE'),
    '3) l''applicazione non ha DELETE su anagrafiche.dati_societari: la porta e'' il verbo');

SELECT ok(
    EXISTS (SELECT 1
              FROM pg_attribute a
              JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
             WHERE a.attrelid = 'anagrafiche.dati_societari'::regclass
               AND a.attname = 'storicizza'
               AND a.attnotnull
               AND pg_get_expr(d.adbin, d.adrelid) = 'true'),
    '3a) storicizza dei dati societari: DEFAULT true e NOT NULL');

SELECT ok(
    EXISTS (SELECT 1 FROM config.storico_set_storicizza s
             WHERE s.table_name = 'anagrafiche.dati_societari'),
    '3b) anagrafiche.dati_societari e'' nel registro dello storico: il trigger non spegne il flag');

-- ============================================================
-- Una societa' di capitali. Per prima: la fixture esce IMMEDIATE.
-- ============================================================
CREATE TEMP TABLE _ref AS
SELECT (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'SC') AS sc,
       (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'DI') AS di,
       (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR') AS pr,
       (SELECT id FROM config.forme_giuridiche WHERE codice = 'DI')               AS forma_di;

CREATE TEMP TABLE _sc AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('pgTAP elimina dati societari SC',
                                       p_tipo_soggetto_dettaglio_id := (SELECT sc FROM _ref)::integer) AS id;

SELECT is(
    (SELECT m -> 0 ->> 'codice' || '/' || (m -> 0 -> 'dettaglio' ->> 'campo')
       FROM (SELECT anagrafiche.fn_check_elimina_dati_societari((SELECT id FROM _sc)) AS m) x),
    'E_DATI_SOCIETARI_NON_ELIMINABILI/tipo_soggetto_dettaglio_id',
    '4) societa'' di capitali: la check dice perche'' (la natura li richiede), col campo della natura');

SELECT throws_like(
    format($$SELECT anagrafiche.fn_elimina_dati_societari(%L)$$, (SELECT id FROM _sc)),
    '%richiede i dati societari%',
    '5) ... e il verbo rifiuta con quella frase');

-- ============================================================
-- Una ditta individuale. La finestra differita la dichiara il file.
-- ============================================================
SET CONSTRAINTS ALL DEFERRED;

CREATE TEMP TABLE _di AS
SELECT anagrafiche.fn_crea_soggetto_pf(
           p_cognome := 'Elimina', p_nome := 'Ditta', p_codice_fiscale := dbops.fn_pgtap_cf_libero(),
           p_email := 'pgtap.elimina.ds.di@example.com', p_sesso := 'M',
           p_tipo_soggetto_dettaglio_id := (SELECT di FROM _ref),
           p_partita_iva := dbops.fn_pgtap_piva_libera()) AS id;

CREATE TEMP TABLE _ds AS
SELECT anagrafiche.fn_scrivi_dati_societari(
           p_soggetto_id := (SELECT id FROM _di), p_forma_giuridica_id := (SELECT forma_di FROM _ref),
           p_id_prov_iscri_rea := NULL, p_iscrizione_rea := NULL,
           p_capitale_sociale := NULL, p_socio_unico := NULL, p_liquidazione := NULL,
           p_destinatario_fe := NULL, p_pec_fatturazione := NULL, p_codice_sdi := NULL,
           p_data_costituzione := NULL) AS id;

SELECT ok(
    'E_CAMBIO_NATURA_CON_DATI_SOCIETARI' = ANY (
        SELECT jsonb_array_elements(anagrafiche.fn_check_cambio_natura_soggetto(
                   (SELECT id FROM _di), (SELECT pr FROM _ref), NULL, 'N', 'N')) ->> 'codice'),
    '6) la ditta coi dati societari verso un privato: il cambio ha il motivo dei dati societari');

SELECT is(
    anagrafiche.fn_check_elimina_dati_societari((SELECT id FROM _di)),
    '[]'::jsonb,
    '7) la ditta: i dati societari si possono eliminare (OPTIONAL), nessun motivo');

SELECT is(
    anagrafiche.fn_elimina_dati_societari((SELECT id FROM _di)),
    true,
    '8) il verbo elimina: vero');

SELECT ok(
    NOT EXISTS (SELECT 1 FROM anagrafiche.dati_societari d WHERE d.soggetto_id = (SELECT id FROM _di)),
    '9) ... la riga non c''e'' piu''');

SELECT ok(
    EXISTS (SELECT 1 FROM storico.dati_societari s
             WHERE s.dati_societari_id = (SELECT id FROM _ds) AND s.tipo_operazione = 3),
    '10) ... e lo storico la conserva (tipo_operazione 3, DELETE)');

SELECT is(
    anagrafiche.fn_elimina_dati_societari((SELECT id FROM _di)),
    false,
    '11) una seconda volta: falso, niente da eliminare non e'' un errore');

SELECT is(
    anagrafiche.fn_check_cambio_natura_soggetto((SELECT id FROM _di), (SELECT pr FROM _ref), NULL, 'N', 'N'),
    '[]'::jsonb,
    '12) e ora il cambio verso il privato, con la P.IVA proposta vuota, non ha piu'' motivi');

SELECT * FROM finish();

ROLLBACK;
