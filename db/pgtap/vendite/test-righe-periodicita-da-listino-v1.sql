-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-11-01 (20261101-04/-05/-06, passo 4 del brief): la periodicita' sulla riga a
--   canone e' obbligatoria. Il 2 e il 3 dicevano «vuota, e si salva»: ora la riga senza
--   periodicita' si rifiuta col codice (E_RIGA_CANONE_SENZA_PERIODICITA). Il default che
--   questo file presidia non cambia: l'obbligo ha il suo pgTAP,
--   vendite/test-righe-canone-periodicita-obbligatoria-v1.
-- pgTAP test per Zero ERP
--
-- Test: la riga a canone di contratto o di offerta eredita la periodicita' dalla
--       riga di listino (script.trgfn_righe_default_periodicita_da_listino,
--       changeSet 20261029-44/-45, brief-db-contratto-righe-periodiche-in-commessa
--       §6.11, Lotto 4b). Decisioni di Tid: G-0-bis (2026-10-28), F-9 e la (b) del
--       Lotto 4b (2026-10-29): solo il default, l'obbligo entra col passaggio BE/FE.
--
-- ⭐ TUTTO COSTRUITO. Il listino e' di quota fissa (gli articoli si erogano a
--   CANONE/FISSA), costruito qui con la sequenza di dbops.fn_pgtap_crea_listino:
--   il builder prende la prima tipologia della utility, e la riga di listino deve
--   prendere la periodicita' quando la versione e' ancora in bozza.
--   A nel listino a TRIMESTRALE, B nel listino senza periodicita', X fuori listino.
--
-- Indice test (1..6):
--   1) contratto: ADESIONE a canone su A senza periodicita' -> TRIMESTRALE dal listino
--   2) contratto: OVERRIDE a canone su B (listino senza periodicita') -> non eredita, e si rifiuta
--   3) contratto: AGGIUNTA a canone su X (fuori listino) -> non eredita (F-9), e si rifiuta
--   4) offerta: ADESIONE a canone su A -> TRIMESTRALE (la gemella)
--   5) offerta: ADESIONE su B con MENSILE scritta -> MENSILE (la scelta dell'operatore vince)
--   6) la forma: i due montaggi, BEFORE INSERT OR UPDATE OF tipo_erogazione
-- ------------------------------------------------------------

BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE tmp_per_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('periodicita da listino');

CREATE TEMP TABLE tmp_per_listino AS
WITH ins AS (
    INSERT INTO vendite.listini (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP_PER_' || substr(md5(clock_timestamp()::text || random()::text), 1, 16),
           'Fixture pgTAP: periodicita da listino', m.utility_id,
           (SELECT t.id FROM config.listini_tipologie t WHERE t.codice = 'QUOTA_FISSA'),
           script.fn_pgtap_emittente_sr_operatore()
      FROM tmp_per_mondo m
    RETURNING id)
SELECT id AS listino_id FROM ins;

CREATE TEMP TABLE tmp_per_ver AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
    SELECT listino_id, 'PGTAP_V1', script.fn_data_operativa() FROM tmp_per_listino
    RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_per_art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGTAP-PER-' || v.sigla,
           p_listino_tipologia_id => (SELECT t.id FROM config.listini_tipologie t WHERE t.codice = 'QUOTA_FISSA')) AS id
  FROM (VALUES ('A'), ('B'), ('X')) AS v(sigla);

CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
    SELECT id FROM tmp_per_art WHERE sigla = p_sigla;
$fx$;

DO $fx$ BEGIN
    PERFORM dbops.fn_pgtap_listino_aggiungi_articoli((SELECT id FROM tmp_per_ver),
        ARRAY[pg_temp.art('A'), pg_temp.art('B')], 100);
END $fx$;

-- In bozza la riga di listino si scrive: A a TRIMESTRALE, B mensile.
-- ⚠️ rev 2026-10-31 (20261031-39 e -51/-52): una versione con una quota fissa a
--   canone senza periodicita' non si attiva, e fuori dalla bozza la quota non la
--   perde. L'unica strada per «una riga di listino senza periodicita'» su una
--   versione attiva e' il catalogo che cambia dopo l'attivazione: la fixture la
--   costruisce cosi' (brief-db-contratto-righe-periodiche-in-commessa §7.10).
UPDATE vendite.listini_righe
   SET periodicita = 'TRIMESTRALE'
 WHERE listino_versione_id = (SELECT id FROM tmp_per_ver) AND articolo_id = pg_temp.art('A');

-- La tipologia QUOTA_FISSA, nella transazione, non si eroga a canone: in bozza
-- la quota senza periodicita' non e' «a canone», e la versione si attiva.
UPDATE config.listini_tipologie_erogazioni SET e_default = false
 WHERE tipologia_id = (SELECT t.id FROM config.listini_tipologie t WHERE t.codice = 'QUOTA_FISSA')
   AND e_default IS TRUE;
INSERT INTO config.listini_tipologie_erogazioni (tipologia_id, tipo_erogazione, fonte_quantita_attesa, e_default)
SELECT t.id, 'UNA_TANTUM', 'FISSA', true FROM config.listini_tipologie t WHERE t.codice = 'QUOTA_FISSA';

DO $fx$ BEGIN
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni'::regclass, (SELECT id FROM tmp_per_ver), 'ATTIVA');
END $fx$;

-- Poi il catalogo torna com'era: la quota e' di nuovo un canone, senza periodicita'.
DELETE FROM config.listini_tipologie_erogazioni
 WHERE tipologia_id = (SELECT t.id FROM config.listini_tipologie t WHERE t.codice = 'QUOTA_FISSA')
   AND tipo_erogazione = 'UNA_TANTUM' AND e_default IS TRUE;
UPDATE config.listini_tipologie_erogazioni SET e_default = true
 WHERE tipologia_id = (SELECT t.id FROM config.listini_tipologie t WHERE t.codice = 'QUOTA_FISSA')
   AND tipo_erogazione = 'CANONE' AND fonte_quantita_attesa = 'FISSA';

CREATE TEMP TABLE tmp_per_ctr AS
SELECT k.contratto_id AS id
  FROM dbops.fn_pgtap_crea_contratto(
           'periodicita da listino', 'DRAFT', (SELECT billing_account_id FROM tmp_per_mondo), NULL,
           script.fn_data_operativa(), script.fn_data_operativa() + 365, NULL,
           (SELECT listino_id FROM tmp_per_listino)) k;

CREATE TEMP TABLE tmp_per_off AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali
           (codice, emittente_fiscale_id, billing_account_id, istanza_utility_id,
            utility_id, listino_id, validita_dal)
    SELECT 'PGTAP-PER-O-' || substr(gen_random_uuid()::text, 1, 8),
           m.emittente_fiscale_id, m.billing_account_id, m.istanza_utility_id,
           m.utility_id, l.listino_id, script.fn_data_operativa()
      FROM tmp_per_mondo m, tmp_per_listino l
    RETURNING id)
SELECT id FROM ins;

-- Scopo: crea una riga a canone e ne rende la periodicita' ('-' = vuota).
CREATE OR REPLACE FUNCTION pg_temp.riga(p_doc text, p_sigla text, p_tipo text,
                                        p_periodicita text DEFAULT NULL)
RETURNS text LANGUAGE plpgsql AS $fx$
DECLARE v_per text;
BEGIN
    IF p_doc = 'contratto' THEN
        INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione,
               prezzo_unitario, tipo_erogazione, fonte_quantita_attesa, qta_operativa, periodicita)
        VALUES ((SELECT id FROM tmp_per_ctr), pg_temp.art(p_sigla), p_tipo::vendite.tipo_eccezione_contratto,
                CASE WHEN p_tipo = 'ADESIONE' THEN NULL ELSE 80 END,
                'CANONE', 'FISSA', 1, p_periodicita)
        RETURNING periodicita INTO v_per;
    ELSE
        INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id, tipo_eccezione,
               prezzo_unitario, tipo_erogazione, fonte_quantita_attesa, qta_operativa, periodicita)
        VALUES ((SELECT id FROM tmp_per_off), pg_temp.art(p_sigla), p_tipo::vendite.tipo_eccezione_contratto,
                CASE WHEN p_tipo = 'ADESIONE' THEN NULL ELSE 80 END,
                'CANONE', 'FISSA', 1, p_periodicita)
        RETURNING periodicita INTO v_per;
    END IF;
    RETURN coalesce(v_per, '-');
END;
$fx$;

-- ============================================================
-- 1-5) Il default
-- ============================================================
SELECT is(pg_temp.riga('contratto', 'A', 'ADESIONE'), 'TRIMESTRALE',
    '1) contratto: ADESIONE a canone su A senza periodicita'' -> quella della riga di listino');

-- ⚠️ Sul testo del messaggio a catalogo: il 23514 del CHECK non deve passare per questo.
SELECT throws_like($$SELECT pg_temp.riga('contratto', 'B', 'OVERRIDE')$$,
    '%Manca la periodicità%',
    '2) contratto: OVERRIDE a canone su B, il listino non la dice -> non eredita, e si rifiuta (passo 4)');

SELECT throws_like($$SELECT pg_temp.riga('contratto', 'X', 'AGGIUNTA')$$,
    '%Manca la periodicità%',
    '3) contratto: AGGIUNTA a canone fuori listino -> non eredita (F-9: la scrive l''operatore), e si rifiuta');

SELECT is(pg_temp.riga('offerta', 'A', 'ADESIONE'), 'TRIMESTRALE',
    '4) offerta: ADESIONE a canone su A -> quella della riga di listino (la gemella)');

SELECT is(pg_temp.riga('offerta', 'B', 'ADESIONE', 'MENSILE'), 'MENSILE',
    '5) offerta: la periodicita'' scritta dall''operatore vince');

-- ============================================================
-- 6) La forma
-- ============================================================
-- ⚠️ Per OID, non per testo: regclass::text perde lo schema come app.
SELECT ok(
    (SELECT count(*) = 2
            AND count(DISTINCT t.tgrelid) = 2
            AND bool_and(t.tgrelid IN ('vendite.contratti_righe'::regclass,
                                       'vendite.offerte_commerciali_eccezioni'::regclass))
            AND bool_and(t.tgtype::int & 2 = 2      -- BEFORE
                         AND t.tgtype::int & 4 = 4  -- INSERT
                         AND t.tgtype::int & 16 = 16) -- UPDATE
       FROM pg_trigger t
      WHERE t.tgfoid = 'script.trgfn_righe_default_periodicita_da_listino'::regproc),
    '6) i due montaggi: BEFORE, su INSERT e su UPDATE (OF tipo_erogazione)');

SELECT * FROM finish();
ROLLBACK;
