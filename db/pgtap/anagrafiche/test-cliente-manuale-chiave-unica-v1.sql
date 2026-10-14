-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: un cliente manuale per soggetto, utility e azienda; gli stati del
--       cliente e le loro date; la catena delle istanze fittizie.
-- Oggetti: anagrafiche.fn_clienti_stessa_chiave, anagrafiche.fn_guard_cliente_chiave_unica
--   e i tre constraint trigger che la chiamano (clienti, collegamento BA ->
--   azienda, istanze_utilities.fittizia), anagrafiche.trgfn_clienti_guard_stato_date,
--   config.transizioni_stati_cliente, anagrafiche.trgfn_clienti_set_parent_istanza,
--   script.fn_disdetta_cliente.
-- Riferimento: brief-db-cliente-manuale-uno-per-soggetto-e-utility (C-1…C-9).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - fra le istanze fittizie, due clienti con lo stesso soggetto, utility e
--     azienda (per l'installazione) e periodi sovrapposti sono un doppione,
--     e il rifiuto porta il codice del BA del cliente esistente (C-1…C-3);
--   - un'altra utility o un'altra azienda sono un'altra fornitura;
--   - un sospeso occupa la chiave; un annullato e un pre-contrattuale no, e il
--     pre-contrattuale si blocca all'attivazione (C-2, C-4);
--   - un chiuso libera la chiave dalla data di chiusura: la catena nuova
--     (istanza, BA, cliente) parte da li', collegata alla precedente (C-5, C-9);
--   - da un chiuso si va solo a CF, la data di chiusura non cambia piu', CF e'
--     terminale (C-5, C-6);
--   - ogni stato pretende la sua data (C-6);
--   - la regola tiene anche quando cambia l'azienda di un BA, la predefinita,
--     o un'istanza diventa fittizia (i movimenti 2-4);
--   - la disdetta chiude anche un sospeso (C-6).
--
-- Elenco test (plan 29):
--    0) PRECONDIZIONI: due utility senza PDP, tre aziende, la predefinita sulla terza
--    1) C1 AT dal giorno -30 sul BA1 -> vive
--    2) fn_clienti_stessa_chiave restituisce C1 col codice del BA1
--    3) * C2 AT, stessa chiave, BA2 -> E_CLIENTE_STESSA_CHIAVE
--    4) la frase del rifiuto porta il codice del BA1 (C-3)
--    5) C2 sull'altra utility -> vive
--    6) PR stessa chiave -> vive (il pre-contrattuale non blocca)
--    7) AN stessa chiave -> vive
--    8) C1 SF senza data di sospensione -> E_CLIENTE_STATO_SENZA_DATA
--    9) C1 SF con la data -> vive
--   10) * AT stessa chiave mentre C1 e' sospeso -> E_CLIENTE_STESSA_CHIAVE
--   11) C1 SF -> AT senza data di riattivazione -> E_CLIENTE_STATO_SENZA_DATA
--   12) C1 SF -> AT con la data -> vive
--   13) C1 CH senza data di chiusura -> E_CLIENTE_STATO_SENZA_DATA
--   14) C1 CH con la chiusura oggi -> vive
--   15) catena nuova: C6 AT da oggi su istanza e BA nuovi -> vive
--   16) l'istanza di C6 punta a quella di C1 (C-9)
--   17) * C1 CH -> AT -> E_CLIENTE_STATO_TRANSIZIONE_INVALIDA
--   18) * C1 cambia la data di chiusura -> E_CLIENTE_DATA_CHIUSURA_IMMUTABILE
--   19) C1 CH -> CF, stessa data -> vive
--   20) * C1 CF -> CH -> E_CLIENTE_STATO_TRANSIZIONE_INVALIDA
--   21) * il PR del test 6 si attiva mentre C6 e' attivo -> E_CLIENTE_STESSA_CHIAVE
--   22) C7 AT stessa chiave su un BA dell'altra azienda -> vive
--   23) * movimento 2: il BA di C7 torna all'azienda del mondo -> E_CLIENTE_STESSA_CHIAVE
--   24a) un cliente AT su un'istanza vera, stessa chiave -> vive
--   24) * movimento 3: un'istanza vera con un cliente AT diventa fittizia
--       -> E_CLIENTE_STESSA_CHIAVE
--   25a) il cliente del BA scollegato (sulla predefinita) -> vive
--   25) * movimento 4: un BA scollegato (sulla predefinita, la terza azienda)
--       ha un cliente AT; la predefinita va sull'azienda del mondo
--       -> E_CLIENTE_STESSA_CHIAVE
--   26) la disdetta chiude un sospeso (C2) -> stato CH con la data
--
-- ⚠️ I constraint trigger sono DEFERRABLE INITIALLY DEFERRED: con il
--   preambolo IMMEDIATE scattano a fine istruzione, cioe' dentro
--   pg_temp.esito. I casi che vogliono l'ordine libero (22, 25) aprono la
--   finestra differita e la richiudono con SET CONSTRAINTS ALL IMMEDIATE, che
--   e' il punto in cui il guard parla.
-- ⚠️ Movimento 4: lo spostamento della predefinita passa anche dal cancello
--   della storia (fn_guard_ba_gestore_globale_storia) e dai guard
--   dell'istanza e dell'albero, che guardano TUTTI i BA scollegati: un dato
--   gia' presente fuori regola fermerebbe il test con un altro codice. Stesso
--   limite di test-istanza-ba-gestore-globale-v1.
-- ⚠️ Non provato qui: il riallineamento dello stato del PDP sul periodo
--   (trgfn_clienti_sync_stato_pdp, C-8) — vuole una utility con PDP e il suo
--   punto; dichiarato nel brief.
-- ------------------------------------------------------------

BEGIN;

-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_mondo_cliente
--   (azienda e operatore propri): i BA della fixture nascono collegati a quella
--   azienda (trigger z90).

SELECT plan(29);

-- Il codice di dominio di un errore (canale CONSTRAINT su P0001); per gli
-- altri errori SQLSTATE e vincolo. NULL se non solleva.
CREATE OR REPLACE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_s text; v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    RETURN CASE WHEN v_s = 'P0001' THEN v_c ELSE v_s || ' ' || coalesce(v_c, '') END;
END $$;

-- La frase dell'errore. NULL se non solleva.
CREATE OR REPLACE FUNCTION pg_temp.frase(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    RETURN SQLERRM;
END $$;

CREATE OR REPLACE FUNCTION pg_temp.stato(p_codice text) RETURNS integer
LANGUAGE sql AS $$
    SELECT sc.id FROM config.stati_cliente sc WHERE sc.codice_interno = p_codice
$$;

-- ============================================================
-- Fixture
-- ⛔ Cio' che un builder scrive si legge in un'istruzione SEPARATA.
-- ============================================================
CREATE TEMP TABLE _t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('cliente manuale chiave');

CREATE TEMP TABLE _t_ef AS
SELECT m.emittente_soggetto_ruolo_id AS ef_mio,
       (SELECT e.soggetto_ruolo_id FROM dbops.fn_pgtap_crea_emittente() e) AS ef_altro,
       NULL::bigint AS ef_terzo
  FROM _t_mondo m;

UPDATE _t_ef SET ef_terzo = (SELECT e.soggetto_ruolo_id FROM dbops.fn_pgtap_crea_emittente() e);

-- Due utility che non chiedono un PDP (dato di catalogo).
CREATE TEMP TABLE _t_ref AS
SELECT m.cliente_soggetto_id       AS soggetto_id,
       m.cliente_soggetto_ruolo_id AS soggetto_ruolo_id,
       (SELECT u.id FROM config.utilities u WHERE u.richiede_pdp IS FALSE
         ORDER BY u.id LIMIT 1)                AS utility_1,
       (SELECT u.id FROM config.utilities u WHERE u.richiede_pdp IS FALSE
         ORDER BY u.id OFFSET 1 LIMIT 1)       AS utility_2,
       (SELECT ba.categoria_cliente_id FROM anagrafiche.billing_account ba
         WHERE ba.id = m.billing_account_id)   AS categoria_cliente_id,
       script.fn_data_operativa()              AS oggi
  FROM _t_mondo m;

-- Istanze e BA: una per cliente (la catena nuova e' istanza + BA + cliente).
-- Fittizie tranne «vera», che ha un indirizzo. Tutte nascono sull'azienda
-- del mondo; nella stessa saga (ogni istanza vuole il suo BA al COMMIT).
CREATE TEMP TABLE _t_ba (etichetta text PRIMARY KEY, ba_id bigint, istanza_id bigint, ba_codice text);

SET CONSTRAINTS ALL DEFERRED;

DO $fx$
DECLARE
    r    record;
    v_iu bigint;
    v_ba bigint;
    e    text;
    v_ut integer;
BEGIN
    SELECT * INTO r FROM _t_ref;
    FOREACH e IN ARRAY ARRAY['c1', 'c2', 'pr', 'an', 'sosp', 'c6', 'c7', 'vera', 'scollegato'] LOOP
        IF e = 'vera' THEN
            INSERT INTO anagrafiche.istanze_utilities
                   (soggetto_id, fittizia, codice, indirizzo_dettaglio_id)
            VALUES (r.soggetto_id, false, 'TST-CMK-' || upper(e),
                    dbops.fn_pgtap_crea_indirizzo_dettaglio())
            RETURNING id INTO v_iu;
        ELSE
            INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
            VALUES (r.soggetto_id, true, 'TST-CMK-' || upper(e))
            RETURNING id INTO v_iu;
        END IF;

        v_ut := CASE WHEN e = 'c2' THEN r.utility_2 ELSE r.utility_1 END;
        INSERT INTO anagrafiche.billing_account
               (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id, valido_dal)
        VALUES (v_iu, r.soggetto_ruolo_id, v_ut, r.categoria_cliente_id, r.oggi - 30)
        RETURNING id INTO v_ba;
        INSERT INTO _t_ba VALUES (e, v_ba, v_iu, NULL);
    END LOOP;
END
$fx$;

SET CONSTRAINTS ALL IMMEDIATE;

UPDATE _t_ba t
   SET ba_codice = ba.codice
  FROM anagrafiche.billing_account ba
 WHERE ba.id = t.ba_id;

-- La predefinita sulla terza azienda: i BA della fixture sono tutti
-- collegati, lo spostamento non tocca le loro chiavi.
UPDATE anagrafiche.emittenti_fiscali_billing_account
   SET emittente_soggetto_ruolo_id = (SELECT ef_terzo FROM _t_ef)
 WHERE is_default;

-- Inserisce un cliente sul BA di un'etichetta.
CREATE OR REPLACE FUNCTION pg_temp.cliente_sql(
    p_etichetta text, p_stato text, p_attivazione text, p_chiusura text DEFAULT 'NULL')
RETURNS text LANGUAGE sql AS $$
    SELECT format(
        'INSERT INTO anagrafiche.clienti (billing_account_id, istanza_utility_id, soggetto_ruolo_id, stato_cliente_id, data_attivazione, data_chiusura) '
        'VALUES (%s, %s, %s, pg_temp.stato(%L), %s, %s)',
        b.ba_id, b.istanza_id, r.soggetto_ruolo_id, p_stato, p_attivazione, p_chiusura)
      FROM _t_ba b, _t_ref r
     WHERE b.etichetta = p_etichetta
$$;

CREATE OR REPLACE FUNCTION pg_temp.cid(p_etichetta text) RETURNS bigint
LANGUAGE sql AS $$
    SELECT c.id FROM anagrafiche.clienti c
      JOIN _t_ba b ON b.ba_id = c.billing_account_id
     WHERE b.etichetta = p_etichetta
$$;

-- ============================================================
-- 0) Precondizioni
-- ============================================================
SELECT ok(
    (SELECT utility_1 IS NOT NULL AND utility_2 IS NOT NULL AND utility_1 <> utility_2 FROM _t_ref)
    AND (SELECT ef_terzo NOT IN (ef_mio, ef_altro) AND ef_mio <> ef_altro FROM _t_ef)
    AND (SELECT count(*) = 9 FROM anagrafiche.emittenti_fiscali_billing_account e
          WHERE e.billing_account_id IN (SELECT ba_id FROM _t_ba)
            AND e.emittente_soggetto_ruolo_id = (SELECT ef_mio FROM _t_ef))
    AND (SELECT d.emittente_soggetto_ruolo_id
           FROM anagrafiche.emittenti_fiscali_billing_account d WHERE d.is_default)
        = (SELECT ef_terzo FROM _t_ef),
    '0. PRECONDIZIONI: due utility senza PDP, tre aziende, nove BA sull''azienda del mondo, la predefinita sulla terza'
);

-- ============================================================
-- 1-7) La chiave
-- ============================================================
SELECT is(pg_temp.esito(pg_temp.cliente_sql('c1', 'AT', 'script.fn_data_operativa() - 30')),
          NULL, '1. C1 attivo dal giorno -30: vive');

SELECT is(
    (SELECT string_agg(k.billing_account_codice, ',')
       FROM anagrafiche.fn_clienti_stessa_chiave(
                (SELECT soggetto_ruolo_id FROM _t_ref),
                (SELECT utility_1 FROM _t_ref),
                (SELECT ef_mio FROM _t_ef)) k),
    (SELECT ba_codice FROM _t_ba WHERE etichetta = 'c1'),
    '2. fn_clienti_stessa_chiave restituisce C1, col codice del suo BA');

SELECT is(pg_temp.esito(pg_temp.cliente_sql('sosp', 'AT', 'script.fn_data_operativa() - 10')),
          'E_CLIENTE_STESSA_CHIAVE',
          '3. Un secondo cliente attivo con la stessa chiave: E_CLIENTE_STESSA_CHIAVE');

SELECT ok(
    strpos(pg_temp.frase(pg_temp.cliente_sql('sosp', 'AT', 'script.fn_data_operativa() - 10')),
           (SELECT ba_codice FROM _t_ba WHERE etichetta = 'c1')) > 0,
    '4. La frase del rifiuto porta il codice del BA del cliente esistente (C-3)');

SELECT is(pg_temp.esito(pg_temp.cliente_sql('c2', 'AT', 'script.fn_data_operativa() - 30')),
          NULL, '5. Stesso soggetto e azienda, altra utility: vive');

SELECT is(pg_temp.esito(pg_temp.cliente_sql('pr', 'PR', 'NULL')),
          NULL, '6. Un pre-contrattuale con la stessa chiave: vive (non blocca)');

SELECT is(pg_temp.esito(pg_temp.cliente_sql('an', 'AN', 'NULL')),
          NULL, '7. Un annullato con la stessa chiave: vive');

-- ============================================================
-- 8-14) Il sospeso, la riattivazione, la chiusura
-- ============================================================
SELECT is(pg_temp.esito(format(
    'UPDATE anagrafiche.clienti SET stato_cliente_id = pg_temp.stato(''SF'') WHERE id = %s',
    pg_temp.cid('c1'))),
    'E_CLIENTE_STATO_SENZA_DATA', '8. Sospeso senza data di sospensione: E_CLIENTE_STATO_SENZA_DATA');

SELECT is(pg_temp.esito(format(
    'UPDATE anagrafiche.clienti SET stato_cliente_id = pg_temp.stato(''SF''), data_sospensione = script.fn_data_operativa() - 20 WHERE id = %s',
    pg_temp.cid('c1'))),
    NULL, '9. Sospeso con la data: vive');

SELECT is(pg_temp.esito(pg_temp.cliente_sql('sosp', 'AT', 'script.fn_data_operativa() - 10')),
          'E_CLIENTE_STESSA_CHIAVE',
          '10. Un attivo con la stessa chiave mentre C1 e'' sospeso: E_CLIENTE_STESSA_CHIAVE (il sospeso occupa)');

SELECT is(pg_temp.esito(format(
    'UPDATE anagrafiche.clienti SET stato_cliente_id = pg_temp.stato(''AT'') WHERE id = %s',
    pg_temp.cid('c1'))),
    'E_CLIENTE_STATO_SENZA_DATA', '11. Riattivato senza data di riattivazione: E_CLIENTE_STATO_SENZA_DATA');

SELECT is(pg_temp.esito(format(
    'UPDATE anagrafiche.clienti SET stato_cliente_id = pg_temp.stato(''AT''), data_riattivazione = script.fn_data_operativa() - 15 WHERE id = %s',
    pg_temp.cid('c1'))),
    NULL, '12. Riattivato con la data: vive');

SELECT is(pg_temp.esito(format(
    'UPDATE anagrafiche.clienti SET stato_cliente_id = pg_temp.stato(''CH'') WHERE id = %s',
    pg_temp.cid('c1'))),
    'E_CLIENTE_STATO_SENZA_DATA', '13. Chiuso senza data di chiusura: E_CLIENTE_STATO_SENZA_DATA');

SELECT is(pg_temp.esito(format(
    'UPDATE anagrafiche.clienti SET stato_cliente_id = pg_temp.stato(''CH''), data_chiusura = script.fn_data_operativa() WHERE id = %s',
    pg_temp.cid('c1'))),
    NULL, '14. Chiuso con la chiusura oggi: vive');

-- ============================================================
-- 15-16) La catena nuova
-- ============================================================
SELECT is(pg_temp.esito(pg_temp.cliente_sql('c6', 'AT', 'script.fn_data_operativa()')),
          NULL, '15. Catena nuova: attivo da oggi su istanza e BA nuovi, vive');

SELECT is(
    (SELECT iu.parent_istanza_id FROM anagrafiche.istanze_utilities iu
      WHERE iu.id = (SELECT istanza_id FROM _t_ba WHERE etichetta = 'c6')),
    (SELECT istanza_id FROM _t_ba WHERE etichetta = 'c1'),
    '16. L''istanza della catena nuova punta a quella del cliente chiuso (C-9)');

-- ============================================================
-- 17-20) Chiuso e' finale
-- ============================================================
SELECT is(pg_temp.esito(format(
    'UPDATE anagrafiche.clienti SET stato_cliente_id = pg_temp.stato(''AT'') WHERE id = %s',
    pg_temp.cid('c1'))),
    'E_CLIENTE_STATO_TRANSIZIONE_INVALIDA', '17. Da chiuso ad attivo: E_CLIENTE_STATO_TRANSIZIONE_INVALIDA');

SELECT is(pg_temp.esito(format(
    'UPDATE anagrafiche.clienti SET data_chiusura = script.fn_data_operativa() + 5 WHERE id = %s',
    pg_temp.cid('c1'))),
    'E_CLIENTE_DATA_CHIUSURA_IMMUTABILE', '18. Un chiuso cambia la data di chiusura: E_CLIENTE_DATA_CHIUSURA_IMMUTABILE');

SELECT is(pg_temp.esito(format(
    'UPDATE anagrafiche.clienti SET stato_cliente_id = pg_temp.stato(''CF'') WHERE id = %s',
    pg_temp.cid('c1'))),
    NULL, '19. Da CH a CF, stessa data: vive');

SELECT is(pg_temp.esito(format(
    'UPDATE anagrafiche.clienti SET stato_cliente_id = pg_temp.stato(''CH'') WHERE id = %s',
    pg_temp.cid('c1'))),
    'E_CLIENTE_STATO_TRANSIZIONE_INVALIDA', '20. Da CF si esce: E_CLIENTE_STATO_TRANSIZIONE_INVALIDA');

-- ============================================================
-- 21) Il pre-contrattuale si blocca all'attivazione
-- ============================================================
SELECT is(pg_temp.esito(format(
    'UPDATE anagrafiche.clienti SET stato_cliente_id = pg_temp.stato(''AT''), data_attivazione = script.fn_data_operativa() WHERE id = %s',
    pg_temp.cid('pr'))),
    'E_CLIENTE_STESSA_CHIAVE', '21. Il pre-contrattuale si attiva mentre C6 e'' attivo: E_CLIENTE_STESSA_CHIAVE');

-- ============================================================
-- 22-23) Un'altra azienda, e il movimento 2
-- ============================================================
SET CONSTRAINTS ALL DEFERRED;
SELECT pg_temp.esito(pg_temp.cliente_sql('c7', 'AT', 'script.fn_data_operativa()'));
UPDATE anagrafiche.emittenti_fiscali_billing_account
   SET emittente_soggetto_ruolo_id = (SELECT ef_altro FROM _t_ef)
 WHERE billing_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'c7');
SELECT is(pg_temp.esito('SET CONSTRAINTS ALL IMMEDIATE'),
          NULL, '22. Stesso soggetto e utility, su un BA dell''altra azienda: vive');
SET CONSTRAINTS ALL IMMEDIATE;

SELECT is(pg_temp.esito(format(
    'UPDATE anagrafiche.emittenti_fiscali_billing_account SET emittente_soggetto_ruolo_id = %s WHERE billing_account_id = %s',
    (SELECT ef_mio FROM _t_ef), (SELECT ba_id FROM _t_ba WHERE etichetta = 'c7'))),
    'E_CLIENTE_STESSA_CHIAVE', '23. Movimento 2: il BA torna all''azienda del mondo, doppione: E_CLIENTE_STESSA_CHIAVE');

-- ============================================================
-- 24) Movimento 3: un'istanza diventa fittizia
-- ============================================================
SELECT is(pg_temp.esito(pg_temp.cliente_sql('vera', 'AT', 'script.fn_data_operativa()')),
          NULL, '24a. Un cliente attivo su un''istanza vera, stessa chiave: vive (la regola e'' fra le fittizie)');

SELECT is(pg_temp.esito(format(
    'UPDATE anagrafiche.istanze_utilities SET fittizia = true WHERE id = %s',
    (SELECT istanza_id FROM _t_ba WHERE etichetta = 'vera'))),
    'E_CLIENTE_STESSA_CHIAVE', '24. Movimento 3: l''istanza vera diventa fittizia, doppione: E_CLIENTE_STESSA_CHIAVE');

-- ============================================================
-- 25) Movimento 4: la predefinita
-- ============================================================
SET CONSTRAINTS ALL DEFERRED;
SELECT pg_temp.esito(pg_temp.cliente_sql('scollegato', 'AT', 'script.fn_data_operativa()'));
DELETE FROM anagrafiche.emittenti_fiscali_billing_account
 WHERE billing_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'scollegato');
SELECT is(pg_temp.esito('SET CONSTRAINTS ALL IMMEDIATE'),
          NULL, '25a. Il cliente del BA scollegato e'' della predefinita (la terza azienda): vive');
SET CONSTRAINTS ALL IMMEDIATE;

SELECT is(pg_temp.esito(format(
    'UPDATE anagrafiche.emittenti_fiscali_billing_account SET emittente_soggetto_ruolo_id = %s WHERE is_default',
    (SELECT ef_mio FROM _t_ef))),
    'E_CLIENTE_STESSA_CHIAVE', '25. Movimento 4: la predefinita va sull''azienda del mondo, il cliente scollegato diventa un doppione: E_CLIENTE_STESSA_CHIAVE');

-- ============================================================
-- 26) La disdetta chiude un sospeso
-- ============================================================
UPDATE anagrafiche.clienti
   SET stato_cliente_id = pg_temp.stato('SC'), data_sospensione = script.fn_data_operativa() - 5
 WHERE id = pg_temp.cid('c2');

-- ⛔ Il verbo in un'istruzione SEPARATA dalla lettura (snapshot).
SELECT script.fn_disdetta_cliente(pg_temp.cid('c2'), script.fn_data_operativa());

SELECT is(
    (SELECT sc.codice_interno || ' ' || c.data_chiusura::text
       FROM anagrafiche.clienti c
       JOIN config.stati_cliente sc ON sc.id = c.stato_cliente_id
      WHERE c.id = pg_temp.cid('c2')),
    'CH ' || script.fn_data_operativa()::text,
    '26. La disdetta chiude un sospeso (C-6)');

SELECT * FROM finish();
ROLLBACK;
