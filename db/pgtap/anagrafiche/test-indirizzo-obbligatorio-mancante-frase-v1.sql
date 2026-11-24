-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- L'indirizzo obbligatorio mancante si dice per nome: il ruolo (o la natura)
-- e il tipo richiesto col suo ripiego, ognuno col codice del suo layer.
--   Brief: brief-db-fornitore-privato-indirizzi §4.3, §8.2 (6), giro 3.
--   ChangeSet 20261116-26 … -28; codici E_INDIRIZZO_OBBLIGATORIO_MANCANTE e
--   E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO in config/codici_errore.csv
--   e config/messaggi_errore.csv.
--
-- Elenco test (plan 10):
--   il building block anagrafiche.fn_nomi_tipo_indirizzo_richiesto
--    1) il solo tipo, fra caporali
--    2) tipo e ripiego, nell'ordine, separati da « / »
--    3) ripiego uguale al tipo: il solo tipo
--    4) nessuno dei due nel catalogo: NULL
--   il layer RUOLO (anagrafiche.fn_guard_indirizzi_obbligatori_ruolo)
--    5) il codice resta E_INDIRIZZO_OBBLIGATORIO_MANCANTE
--    6) la frase nomina il ruolo e il tipo, senza ripiego
--    7) ... e col ripiego
--   il layer SOGGETTO (anagrafiche.fn_guard_indirizzi_obbligatori_soggetto)
--    8) il codice e' E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO
--    9) la frase nomina la natura e il tipo, senza ripiego
--   10) ... e col ripiego
--
-- Scopo:
--  - la frase e' la posta in gioco: si asserisce intera (throws_like senza
--    jolly), composta dalle descrizioni del CATALOGO, non da letterali;
--  - la riga obbligatoria mancante la COSTRUISCE il test (SPED obbligatorio,
--    ripiego CON), sul fornitore societa' e sul privato gia' nati completi:
--    niente si appoggia alle righe di oggi della matrice. La frase la compone
--    il guard, e il test lo chiama direttamente: rev 2026-11-24 (D-T7a-1,
--    brief-db-revisione-anagrafiche §21), una riga nata dopo il titolare non
--    lo rigiudica piu' a una scrittura qualunque, e l'UPDATE che riscriveva lo
--    stesso valore non fa piu' scattare il guard.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- Fixture: cataloghi e helper
-- ============================================================
CREATE FUNCTION pg_temp.tipo(p_codice config.tipi_indirizzi.codice_interno%TYPE)
RETURNS config.tipi_indirizzi.id%TYPE LANGUAGE sql AS
$f$ SELECT id FROM config.tipi_indirizzi WHERE codice_interno = p_codice $f$;

CREATE FUNCTION pg_temp.nome(p_codice config.tipi_indirizzi.codice_interno%TYPE)
RETURNS config.tipi_indirizzi.descrizione%TYPE LANGUAGE sql AS
$f$ SELECT descrizione FROM config.tipi_indirizzi WHERE codice_interno = p_codice $f$;

CREATE FUNCTION pg_temp.natura(p_codice config.tipi_soggetto_dettaglio.codice_interno%TYPE)
RETURNS config.tipi_soggetto_dettaglio.id%TYPE LANGUAGE sql AS
$f$ SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = p_codice $f$;

-- Una riga obbligatoria della matrice del RUOLO, col ripiego dato (l'id non ha default).
CREATE FUNCTION pg_temp.obbligatorio_ruolo(
    p_tipo_ruolo config.tipi_ruolo_tipi_indirizzo.tipo_ruolo_id%TYPE,
    p_tipo       config.tipi_indirizzi.codice_interno%TYPE,
    p_ripiego    config.tipi_indirizzi.codice_interno%TYPE)
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    DELETE FROM config.tipi_ruolo_tipi_indirizzo
     WHERE tipo_ruolo_id = p_tipo_ruolo AND tipo_indirizzo_id = pg_temp.tipo(p_tipo);
    INSERT INTO config.tipi_ruolo_tipi_indirizzo
           (id, tipo_ruolo_id, tipo_indirizzo_id, obbligatorio, attivo, fallback_tipo_indirizzo_id)
    VALUES ((SELECT COALESCE(max(id), 0) + 1 FROM config.tipi_ruolo_tipi_indirizzo),
            p_tipo_ruolo, pg_temp.tipo(p_tipo), true, true, pg_temp.tipo(p_ripiego));
END $f$;

-- Una riga obbligatoria della matrice della NATURA, col ripiego dato.
CREATE FUNCTION pg_temp.obbligatorio_natura(
    p_natura  config.tipi_soggetto_dettaglio_tipi_indirizzo.tipo_soggetto_dettaglio_id%TYPE,
    p_tipo    config.tipi_indirizzi.codice_interno%TYPE,
    p_ripiego config.tipi_indirizzi.codice_interno%TYPE)
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    DELETE FROM config.tipi_soggetto_dettaglio_tipi_indirizzo
     WHERE tipo_soggetto_dettaglio_id = p_natura AND tipo_indirizzo_id = pg_temp.tipo(p_tipo);
    INSERT INTO config.tipi_soggetto_dettaglio_tipi_indirizzo
           (id, tipo_soggetto_dettaglio_id, tipo_indirizzo_id, obbligatorio, attivo, fallback_tipo_indirizzo_id)
    VALUES ((SELECT COALESCE(max(id), 0) + 1 FROM config.tipi_soggetto_dettaglio_tipi_indirizzo),
            p_natura, pg_temp.tipo(p_tipo), true, true, pg_temp.tipo(p_ripiego));
END $f$;

-- Un indirizzo libero valido per l'Italia, del tipo dato.
CREATE FUNCTION pg_temp.el(p_tipo config.tipi_indirizzi.codice_interno%TYPE, p_via text)
RETURNS jsonb LANGUAGE sql AS $f$
    SELECT jsonb_build_object('tipo_indirizzo_codice_interno', p_tipo,
                              'indirizzo_libero',              p_via,
                              'stato_id',                      script.fn_stato_id_da_iso2('IT'))
           || (SELECT jsonb_strip_nulls(to_jsonb(frm))
                 FROM dbops.fn_pgtap_indirizzo_libero_forma(script.fn_stato_id_da_iso2('IT')) frm)
$f$;

CREATE TEMP TABLE _ref ON COMMIT DROP AS
SELECT (SELECT id FROM config.tipi_ruoli WHERE codice_interno = 'FO') AS fo,
       (SELECT descrizione FROM config.tipi_ruoli WHERE codice_interno = 'FO') AS fo_nome,
       pg_temp.natura('PR') AS pr,
       (SELECT COALESCE(descrizione, codice_interno) FROM config.tipi_soggetto_dettaglio
         WHERE codice_interno = 'PR') AS pr_nome;

-- La societa' fornitore e il privato, completi: i builder richiudono da se' la
-- finestra differita del soggetto; il ruolo nasce nella finestra e la
-- richiusura lo giudica sulla matrice di oggi, prima delle righe costruite.
CREATE TEMP TABLE _s ON COMMIT DROP AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('pgTAP obbligatorio mancante societa''') AS sc,
       dbops.fn_pgtap_crea_soggetto_pf('Obbligatorio', 'Mancante', pg_temp.natura('PR')) AS pr;

SET CONSTRAINTS ALL DEFERRED;

CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT (SELECT soggetto_ruolo_id FROM anagrafiche.fn_crea_fornitore(
            s.sc, '{}'::jsonb, NULL,
            jsonb_build_array(pg_temp.el('SEDELEG', 'Via Obbligatorio pgTAP 1')))) AS sr_sc
  FROM _s s;

SET CONSTRAINTS ALL IMMEDIATE;

-- ============================================================
-- 1-4) Il building block
-- ============================================================
SELECT is(
    anagrafiche.fn_nomi_tipo_indirizzo_richiesto(pg_temp.tipo('SPED'), NULL),
    format('«%s»', pg_temp.nome('SPED')),
    '1) il solo tipo, fra caporali');

SELECT is(
    anagrafiche.fn_nomi_tipo_indirizzo_richiesto(pg_temp.tipo('SPED'), pg_temp.tipo('CON')),
    format('«%s» / «%s»', pg_temp.nome('SPED'), pg_temp.nome('CON')),
    '2) tipo e ripiego, nell''ordine, separati da « / »');

SELECT is(
    anagrafiche.fn_nomi_tipo_indirizzo_richiesto(pg_temp.tipo('SPED'), pg_temp.tipo('SPED')),
    format('«%s»', pg_temp.nome('SPED')),
    '3) ripiego uguale al tipo: il solo tipo');

SELECT is(
    anagrafiche.fn_nomi_tipo_indirizzo_richiesto(2147483647, NULL),
    NULL,
    '4) nessuno dei due nel catalogo: NULL');

-- ============================================================
-- 5-7) Il layer RUOLO: SPED obbligatorio per il fornitore
-- ============================================================
SELECT pg_temp.obbligatorio_ruolo((SELECT fo FROM _ref), 'SPED', NULL);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_guard_indirizzi_obbligatori_ruolo(%L::bigint, NULL::uuid)',
        (SELECT sr_sc FROM _f))),
    'E_INDIRIZZO_OBBLIGATORIO_MANCANTE',
    '5) il codice del layer ruolo resta E_INDIRIZZO_OBBLIGATORIO_MANCANTE');

SELECT throws_like(
    format('SELECT anagrafiche.fn_guard_indirizzi_obbligatori_ruolo(%L::bigint, NULL::uuid)',
           (SELECT sr_sc FROM _f)),
    (SELECT format('Il ruolo %s richiede l''indirizzo «%s».', fo_nome, pg_temp.nome('SPED')) FROM _ref),
    '6) la frase nomina il ruolo e il tipo, senza ripiego');

-- ⚠️ Rev 2026-11-17 (giro 4 del brief, la regola «vale il ripiego»): un ripiego
--   conta, e la frase lo nomina, solo se il ruolo e la natura lo ammettono. Il
--   fornitore non ammetteva la consegna: la riga facoltativa la ammette (la
--   societa' la ammette gia').
INSERT INTO config.tipi_ruolo_tipi_indirizzo
       (id, tipo_ruolo_id, tipo_indirizzo_id, obbligatorio, attivo)
SELECT (SELECT COALESCE(max(id), 0) + 1 FROM config.tipi_ruolo_tipi_indirizzo),
       r.fo, pg_temp.tipo('CON'), false, true
  FROM _ref r
 WHERE NOT EXISTS (SELECT 1 FROM config.tipi_ruolo_tipi_indirizzo m
                    WHERE m.tipo_ruolo_id = r.fo AND m.tipo_indirizzo_id = pg_temp.tipo('CON'));
SELECT pg_temp.obbligatorio_ruolo((SELECT fo FROM _ref), 'SPED', 'CON');

SELECT throws_like(
    format('SELECT anagrafiche.fn_guard_indirizzi_obbligatori_ruolo(%L::bigint, NULL::uuid)',
           (SELECT sr_sc FROM _f)),
    (SELECT format('Il ruolo %s richiede l''indirizzo «%s» / «%s».',
                   fo_nome, pg_temp.nome('SPED'), pg_temp.nome('CON')) FROM _ref),
    '7) ... e col ripiego');

-- ============================================================
-- 8-10) Il layer SOGGETTO: SPED obbligatorio per il privato
-- ============================================================
SELECT pg_temp.obbligatorio_natura((SELECT pr FROM _ref), 'SPED', NULL);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_guard_indirizzi_obbligatori_soggetto(%L::uuid, NULL::uuid)',
        (SELECT pr FROM _s))),
    'E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO',
    '8) il codice del layer soggetto e'' E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO');

SELECT throws_like(
    format('SELECT anagrafiche.fn_guard_indirizzi_obbligatori_soggetto(%L::uuid, NULL::uuid)',
           (SELECT pr FROM _s)),
    (SELECT format('Il tipo soggetto %s richiede l''indirizzo «%s».', pr_nome, pg_temp.nome('SPED')) FROM _ref),
    '9) la frase nomina la natura e il tipo, senza ripiego');

SELECT pg_temp.obbligatorio_natura((SELECT pr FROM _ref), 'SPED', 'CON');

SELECT throws_like(
    format('SELECT anagrafiche.fn_guard_indirizzi_obbligatori_soggetto(%L::uuid, NULL::uuid)',
           (SELECT pr FROM _s)),
    (SELECT format('Il tipo soggetto %s richiede l''indirizzo «%s» / «%s».',
                   pr_nome, pg_temp.nome('SPED'), pg_temp.nome('CON')) FROM _ref),
    '10) ... e col ripiego');

SELECT * FROM finish();
ROLLBACK;
