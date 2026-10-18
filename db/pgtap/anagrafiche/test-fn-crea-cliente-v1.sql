-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la prima meta' prova il ramo SENZA sessione (il
--   provisioning, il builder da owner): nessun operatore, quindi il legame
--   BA -> emittente lo scrive il BB e non il trigger z90. Il contesto
--   operatore si apre a meta' file, per il ramo con la sessione. La lettura
--   sotto la RLS (la rilettura a istruzione finita) la provano i builder
--   riscritti, che girano come zeroerp_app in centotrenta file, e il test
--   26-27 di script/test-fn-scrivi-riga-da-jsonb-v1 sul caso costruito.
-- pgTAP test per Zero ERP
--
-- Il billing account e il cliente:
--   anagrafiche.fn_crea_billing_account   (20261018-35)
--   anagrafiche.fn_crea_cliente           (20261018-36)
--   e i due builder che diventano involucri:
--   dbops.fn_pgtap_crea_cliente_ba        (20261018-37)
--   dbops.fn_pgtap_crea_cliente           (20261018-38)
--   Brief: brief-db-processi-accensione-per-ambiente (§5-ter.2, 2b-1 lotto 5).
--
-- ⭐ Il caso si COSTRUISCE: soggetti PG dal builder, un emittente nuovo, due
--   utility diverse (la coppia istanza/utility e' unica).
-- ⭐ L'istanza vuole un satellite al commit (vincolo DIFFERITO): le scritture
--   girano DEFERRED, e SET CONSTRAINTS ALL IMMEDIATE fa da commit.
--
-- Elenco test (plan 25):
--   forma
--    1) il BB del BA e' INVOKER
--    2) la madre del cliente e' INVOKER
--   il BB del BA, senza sessione
--    3) l'istanza nasce fittizia, del soggetto del ruolo
--    4) il BA: codice generato, fatturazione_ordini al DEFAULT (CONFERMATO)
--    5) il legame chiesto e' scritto, is_default = false
--    6) senza emittente chiesto e senza sessione: nessun legame
--    7) un'istanza esistente: un secondo BA, per un'altra utility, sulla stessa
--    8) istanza esistente piu' i campi di una nuova: E_SCRIPT_CHIAMATA_NON_VALIDA
--    9) chiave estranea fra i campi del BA: E_CAMPO_NON_AMMESSO
--   10) chiave estranea fra i campi dell'istanza, col campo sul canale COLUMN
--   11) ruolo inesistente: E_SOGGETTO_RUOLO_NON_TROVATO
--   la madre del cliente
--   12) soggetto senza ruolo: ruolo CL, BA e istanza nuovi
--   13) senza stato nasce AT, attivazione alla data operativa
--   14) contatto e indirizzi obbligatori del ruolo
--   14-bis) ... e i vincoli differiti reggono (il commit)
--   15) un BA esistente: il cliente e' suo, l'istanza letta dal BA
--   16) uno stato indicato (PR) senza date: PR, nessuna attivazione
--   17) BA esistente piu' i campi di uno nuovo: E_SCRIPT_CHIAMATA_NON_VALIDA
--   18) ne' BA ne' utility: E_SCRIPT_CHIAMATA_NON_VALIDA
--   19) la fornitura fra i campi: E_CAMPO_NON_AMMESSO
--   20) un secondo cliente sullo stesso BA: uq_clienti_billing_account
--   con un operatore in sessione
--   21) il BB senza emittente chiesto: il legame lo scrive z90
--   22) un emittente chiesto diverso da quello di chi agisce: E_SCRIPT_CHIAMATA_NON_VALIDA
--   i builder
--   23) nessuno dei due scrive piu' le tabelle della catena a mano
--   24) ... e chiamano i BB
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(25);

CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

CREATE OR REPLACE FUNCTION pg_temp.colonna_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = COLUMN_NAME;
    RETURN v_c;
END $$;

CREATE OR REPLACE FUNCTION pg_temp.vincolo_violato(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN unique_violation THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

CREATE OR REPLACE FUNCTION pg_temp.corpo(p regprocedure) RETURNS text
LANGUAGE sql AS $$
    SELECT regexp_replace(p2.prosrc, '--[^\n]*', '', 'g') FROM pg_proc p2 WHERE p2.oid = p
$$;

-- Il mondo, da owner e senza sessione.
CREATE TEMP TABLE t_m AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Cliente BA pgTAP')     AS s_ba,
       dbops.fn_pgtap_crea_soggetto_pg('Cliente madre pgTAP')  AS s_madre,
       -- Utility senza PDP: con il PDP il cliente lo rifiuta trgfn_clienti_sync_pdp.
       (SELECT u.id FROM config.utilities u WHERE NOT u.richiede_pdp ORDER BY u.id LIMIT 1)          AS u1,
       (SELECT u.id FROM config.utilities u WHERE NOT u.richiede_pdp ORDER BY u.id OFFSET 1 LIMIT 1) AS u2,
       (SELECT cc.id FROM anagrafiche.categorie_clienti cc ORDER BY cc.id LIMIT 1) AS cat,
       (SELECT t.id FROM config.tipi_contatti t ORDER BY t.id LIMIT 1) AS tipo_contatto_id;

CREATE TEMP TABLE t_ef AS SELECT * FROM dbops.fn_pgtap_crea_emittente('PGCLBA');

CREATE TEMP TABLE t_sr AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(m.s_ba, 'CL') AS sr_id FROM t_m m;

-- I tipi obbligatori del cliente, dalla matrice.
CREATE TEMP TABLE t_obbl AS
SELECT trti.tipo_indirizzo_id
  FROM config.tipi_ruolo_tipi_indirizzo trti
  JOIN config.tipi_ruoli tr ON tr.id = trti.tipo_ruolo_id
 WHERE tr.codice_interno = 'CL' AND trti.attivo AND trti.obbligatorio;

-- ⚠️ DEFERRED dopo i builder: rimettono i vincoli IMMEDIATE.
SET CONSTRAINTS ALL DEFERRED;

-- Un BA senza legame (istanza nuova), un secondo sulla stessa istanza per
-- un'altra utility, e uno col legame chiesto su un'istanza sua.
-- ⚠️ Il secondo BA di un'istanza non chiede un emittente: il guard z95
--   (un'istanza ha i BA di una sola azienda) scatta all'INSERT, prima che il
--   BB scriva il legame. Senza sessione il primo BA risponde al default, e il
--   secondo pure: e' il caso che il modello ammette (limite dichiarato nel BB).
CREATE TEMP TABLE t_ba1 AS
SELECT b.*
  FROM t_m m, t_sr r,
       anagrafiche.fn_crea_billing_account(r.sr_id, m.u1, jsonb_build_object('categoria_cliente_id', m.cat)) b;

CREATE TEMP TABLE t_ba2 AS
SELECT b.*
  FROM t_m m, t_sr r, t_ba1 b1,
       anagrafiche.fn_crea_billing_account(
           r.sr_id, m.u2, jsonb_build_object('categoria_cliente_id', m.cat),
           p_istanza_utility_id := b1.istanza_utility_id) b;

CREATE TEMP TABLE t_bae AS
SELECT b.*
  FROM t_m m, t_sr r, t_ef e,
       anagrafiche.fn_crea_billing_account(
           r.sr_id, m.u1, jsonb_build_object('categoria_cliente_id', m.cat),
           p_emittente_soggetto_ruolo_id := e.soggetto_ruolo_id) b;

-- La madre: un soggetto senza ruolo, BA nuovo, contatto, un indirizzo.
CREATE TEMP TABLE t_c1 AS
SELECT c.*
  FROM t_m m,
       anagrafiche.fn_crea_cliente(
           p_soggetto_id     := m.s_madre,
           p_utility_id      := m.u1,
           p_billing_account := jsonb_build_object('categoria_cliente_id', m.cat),
           p_contatto        := jsonb_build_object('nominativo', 'Ufficio clienti',
                                                   'tipo_contatto_id', m.tipo_contatto_id),
           p_indirizzi       := jsonb_build_array(jsonb_build_object(
               'tipo_indirizzo_id',   (SELECT min(o.tipo_indirizzo_id) FROM t_obbl o),
               'indirizzo_libero',    'Via Clienti pgTAP 9',
               'stato_id',            1)
               -- rev 2026-10-18: la forma che il guard vuole per lo stato (Italia: comune e CAP)
               || (SELECT jsonb_strip_nulls(to_jsonb(frm)) FROM dbops.fn_pgtap_indirizzo_libero_forma(1) frm))) c;

-- La madre su un BA esistente (il secondo, che non ha cliente), stato PR.
CREATE TEMP TABLE t_c2 AS
SELECT c.*
  FROM t_m m, t_ba2 b,
       anagrafiche.fn_crea_cliente(
           p_soggetto_id        := m.s_ba,
           p_campi              := jsonb_build_object(
               'stato_cliente_id', (SELECT sc.id FROM config.stati_cliente sc WHERE sc.codice_interno = 'PR')),
           p_billing_account_id := b.billing_account_id) c;

-- ============================================================
-- Forma
-- ============================================================
SELECT is(
    (SELECT p.prosecdef FROM pg_proc p
      WHERE p.oid = 'anagrafiche.fn_crea_billing_account(bigint, integer, jsonb, bigint, jsonb, bigint)'::regprocedure),
    false,
    '1. il BB del BA e'' INVOKER');

SELECT is(
    (SELECT p.prosecdef FROM pg_proc p
      WHERE p.oid = 'anagrafiche.fn_crea_cliente(uuid, integer, jsonb, jsonb, jsonb, jsonb, bigint, bigint, jsonb, bigint)'::regprocedure),
    false,
    '2. la madre del cliente e'' INVOKER');

-- ============================================================
-- Il BB del BA, senza sessione
-- ============================================================
SELECT is(
    (SELECT format('%s|%s', iu.fittizia, iu.soggetto_id = m.s_ba)
       FROM t_ba1 b JOIN anagrafiche.istanze_utilities iu ON iu.id = b.istanza_utility_id, t_m m),
    't|t',
    '3. l''istanza nasce fittizia, del soggetto del ruolo');

SELECT is(
    (SELECT format('%s|%s', NULLIF(btrim(ba.codice), '') IS NOT NULL, ba.fatturazione_ordini)
       FROM t_ba1 b JOIN anagrafiche.billing_account ba ON ba.id = b.billing_account_id),
    't|CONFERMATO',
    '4. il BA: codice generato, fatturazione_ordini al DEFAULT');

SELECT is(
    (SELECT format('%s|%s', efba.emittente_soggetto_ruolo_id = e.soggetto_ruolo_id, efba.is_default)
       FROM t_bae b
       JOIN anagrafiche.emittenti_fiscali_billing_account efba ON efba.billing_account_id = b.billing_account_id,
            t_ef e),
    't|f',
    '5. il legame chiesto e'' scritto, is_default = false');

SELECT is(
    (SELECT count(*)::int
       FROM t_ba1 b
       JOIN anagrafiche.emittenti_fiscali_billing_account efba ON efba.billing_account_id = b.billing_account_id),
    0,
    '6. senza emittente chiesto e senza sessione: nessun legame');

SELECT is(
    (SELECT format('%s|%s', b2.istanza_utility_id = b1.istanza_utility_id, ba.utility_id = m.u2)
       FROM t_ba1 b1, t_ba2 b2, t_m m, anagrafiche.billing_account ba
      WHERE ba.id = b2.billing_account_id),
    't|t',
    '7. un''istanza esistente: un secondo BA, per un''altra utility, sulla stessa');

SELECT is(
    pg_temp.codice_errore($$SELECT * FROM anagrafiche.fn_crea_billing_account(
        (SELECT sr_id FROM t_sr), (SELECT u1 FROM t_m), '{}'::jsonb,
        (SELECT istanza_utility_id FROM t_ba1), '{"codice": "X"}'::jsonb)$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '8. istanza esistente piu'' i campi di una nuova: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT is(
    pg_temp.codice_errore($$SELECT * FROM anagrafiche.fn_crea_billing_account(
        (SELECT sr_id FROM t_sr), (SELECT u1 FROM t_m), '{"utility_id": 1}'::jsonb)$$),
    'E_CAMPO_NON_AMMESSO',
    '9. chiave estranea fra i campi del BA: E_CAMPO_NON_AMMESSO');

SELECT is(
    pg_temp.colonna_errore($$SELECT * FROM anagrafiche.fn_crea_billing_account(
        (SELECT sr_id FROM t_sr), (SELECT u1 FROM t_m), '{}'::jsonb, NULL,
        '{"fittizia": false}'::jsonb)$$),
    'fittizia',
    '10. chiave estranea fra i campi dell''istanza, col campo sul canale COLUMN');

SELECT is(
    pg_temp.codice_errore($$SELECT * FROM anagrafiche.fn_crea_billing_account(-1, 1)$$),
    'E_SOGGETTO_RUOLO_NON_TROVATO',
    '11. ruolo inesistente: E_SOGGETTO_RUOLO_NON_TROVATO');

-- ============================================================
-- La madre del cliente
-- ============================================================
SELECT is(
    (SELECT format('%s|%s|%s', tr.codice_interno, ba.istanza_utility_id = c.istanza_utility_id,
                   sr.soggetto_id = m.s_madre)
       FROM t_c1 c
       JOIN anagrafiche.soggetti_ruoli sr  ON sr.id = c.soggetto_ruolo_id
       JOIN config.tipi_ruoli tr           ON tr.id = sr.tipo_ruolo_id
       JOIN anagrafiche.billing_account ba ON ba.id = c.billing_account_id, t_m m),
    'CL|t|t',
    '12. soggetto senza ruolo: ruolo CL, BA e istanza nuovi');

SELECT is(
    (SELECT format('%s|%s', sc.codice_interno, cl.data_attivazione = script.fn_data_operativa())
       FROM t_c1 c
       JOIN anagrafiche.clienti cl     ON cl.id = c.cliente_id
       JOIN config.stati_cliente sc    ON sc.id = cl.stato_cliente_id),
    'AT|t',
    '13. senza stato nasce AT, attivazione alla data operativa');

SELECT is(
    (SELECT format('%s|%s',
                   (SELECT string_agg(ct.nominativo, ',') FROM anagrafiche.contatti ct
                     WHERE ct.soggetto_ruolo_id = c.soggetto_ruolo_id),
                   (SELECT count(*) FROM t_obbl o
                     WHERE EXISTS (SELECT 1 FROM anagrafiche.indirizzi i
                                    WHERE i.soggetto_ruolo_id = c.soggetto_ruolo_id
                                      AND i.tipo_indirizzo_id = o.tipo_indirizzo_id))
                   = (SELECT count(*) FROM t_obbl))
       FROM t_c1 c),
    'Ufficio clienti|t',
    '14. contatto e indirizzi obbligatori del ruolo');

SELECT lives_ok($$SET CONSTRAINTS ALL IMMEDIATE$$,
                '14-bis. ... e i vincoli differiti reggono (il commit)');

SET CONSTRAINTS ALL DEFERRED;

SELECT is(
    (SELECT format('%s|%s', c.billing_account_id = b.billing_account_id,
                   c.istanza_utility_id = b.istanza_utility_id)
       FROM t_c2 c, t_ba2 b),
    't|t',
    '15. un BA esistente: il cliente e'' suo, l''istanza letta dal BA');

SELECT is(
    (SELECT format('%s|%s', sc.codice_interno, cl.data_attivazione IS NULL)
       FROM t_c2 c
       JOIN anagrafiche.clienti cl  ON cl.id = c.cliente_id
       JOIN config.stati_cliente sc ON sc.id = cl.stato_cliente_id),
    'PR|t',
    '16. uno stato indicato (PR) senza date: PR, nessuna attivazione');

SELECT is(
    pg_temp.codice_errore($$SELECT * FROM anagrafiche.fn_crea_cliente(
        p_soggetto_id        := (SELECT s_ba FROM t_m),
        p_billing_account    := '{"codice": "X"}'::jsonb,
        p_billing_account_id := (SELECT billing_account_id FROM t_ba1))$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '17. BA esistente piu'' i campi di uno nuovo: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT is(
    pg_temp.codice_errore($$SELECT * FROM anagrafiche.fn_crea_cliente((SELECT s_ba FROM t_m))$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '18. ne'' BA ne'' utility: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT is(
    pg_temp.codice_errore($$SELECT * FROM anagrafiche.fn_crea_cliente(
        p_soggetto_id        := (SELECT s_ba FROM t_m),
        p_campi              := '{"billing_account_id": 1}'::jsonb,
        p_billing_account_id := (SELECT billing_account_id FROM t_ba1))$$),
    'E_CAMPO_NON_AMMESSO',
    '19. la fornitura fra i campi: E_CAMPO_NON_AMMESSO');

SELECT is(
    pg_temp.vincolo_violato($$SELECT * FROM anagrafiche.fn_crea_cliente(
        p_soggetto_id        := (SELECT s_ba FROM t_m),
        p_billing_account_id := (SELECT billing_account_id FROM t_ba2))$$),
    'uq_clienti_billing_account',
    '20. un secondo cliente sullo stesso BA: uq_clienti_billing_account');

-- ============================================================
-- Con un operatore in sessione
-- ============================================================
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

CREATE TEMP TABLE t_sr3 AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(dbops.fn_pgtap_crea_soggetto_pg('Cliente sessione pgTAP'), 'CL') AS sr_id;

SET CONSTRAINTS ALL DEFERRED;

CREATE TEMP TABLE t_ba3 AS
SELECT b.*
  FROM t_m m, t_sr3 r,
       anagrafiche.fn_crea_billing_account(r.sr_id, m.u1, jsonb_build_object('categoria_cliente_id', m.cat)) b;

SELECT is(
    (SELECT count(*)::int
       FROM t_ba3 b
       JOIN anagrafiche.emittenti_fiscali_billing_account efba ON efba.billing_account_id = b.billing_account_id),
    1,
    '21. il BB senza emittente chiesto: il legame lo scrive z90 verso l''emittente di chi agisce');

SELECT is(
    pg_temp.codice_errore($$SELECT * FROM anagrafiche.fn_crea_billing_account(
        (SELECT sr_id FROM t_sr3), (SELECT u2 FROM t_m),
        jsonb_build_object('categoria_cliente_id', (SELECT cat FROM t_m)),
        p_emittente_soggetto_ruolo_id := (SELECT soggetto_ruolo_id FROM t_ef))$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '22. un emittente chiesto diverso da quello di chi agisce: E_SCRIPT_CHIAMATA_NON_VALIDA');

-- ============================================================
-- I builder (sul corpo, senza commenti)
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM unnest(ARRAY['dbops.fn_pgtap_crea_cliente_ba(text, integer, bigint)'::regprocedure,
                         'dbops.fn_pgtap_crea_cliente(text, integer, bigint, character varying)'::regprocedure]) AS f
      WHERE pg_temp.corpo(f) ~* 'INSERT\s+INTO\s+anagrafiche\.'),
    0,
    '23. nessuno dei due builder scrive piu'' le tabelle della catena a mano');

SELECT ok(
    pg_temp.corpo('dbops.fn_pgtap_crea_cliente_ba(text, integer, bigint)'::regprocedure) ~ 'anagrafiche\.fn_crea_billing_account\('
    AND pg_temp.corpo('dbops.fn_pgtap_crea_cliente(text, integer, bigint, character varying)'::regprocedure) ~ 'anagrafiche\.fn_crea_cliente\(',
    '24. ... e chiamano i BB');

SELECT * FROM finish();

ROLLBACK;
