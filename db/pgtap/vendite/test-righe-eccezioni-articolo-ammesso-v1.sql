-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- rev 2026-10-28 (brief-modello-documento-vendita §16, giro 12): la versione di oggi nasce in bozza
--   senza stato e si attiva dal verbo (dbops.fn_pgtap_porta_a_stato), non con un UPDATE dello stato.
--
-- Quali articoli ammette una riga d'eccezione di offerta e di contratto: la
-- stessa check per tipo di riga di preventivo, ordine e bolla, col tipo
-- d'eccezione che decide le regole (AGGIUNTA, OVERRIDE, ESCLUSIONE).
-- Brief: brief-db-articoli-ammessi-per-documento (§8.6 A-2, A-5, D-3; §9.3.3)
-- ChangeSet: 20261013-55 -> -57
--
-- ⭐ TUTTO COSTRUITO: azienda, cliente, listino con un bundle, articoli, una
--   tipologia senza erogazioni, contratti e offerta nascono qui.
-- ⚠️ rev 2026-10-21 (brief-db-offerta-emissione-ed-erogazione §I, I-D6 di Tid): un
--   kit si vende solo a quantita' fissa, quindi il bundle P di una tipologia solo
--   a consumo non ha erogazioni (SENZA_EROGAZIONE parla prima del listino, test
--   20). Il builder sceglie la prima tipologia della utility, che puo' essere solo
--   a consumo: il listino passa qui su una che ammette la FISSA.
--
-- LA FIXTURE — listino con A, B, F standalone e il bundle P (figlio F; P in
--   listino solo coi componenti); X fuori listino; S solo componente; N di una
--   tipologia che non prevede erogazioni. Contratto DRAFT e offerta BOZZA sul
--   listino; un secondo contratto DRAFT senza listino.
--
-- Elenco test (plan 20):
--  La check (script.fn_check_articolo_riga), contratto
--   1) AGGIUNTA di un articolo fuori listino: ammessa
--   2) AGGIUNTA di un articolo gia' nel listino: E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO
--   3) OVERRIDE di un articolo del listino: ammessa
--   4) OVERRIDE di un articolo fuori listino: E_RIGA_ECCEZIONE_FUORI_LISTINO (A-5)
--   5) OVERRIDE su un contratto senza listino: E_RIGA_ECCEZIONE_SENZA_LISTINO (A-5)
--   6) ESCLUSIONE di un figlio di bundle: primo motivo FIGLIO_DI_BUNDLE
--   7) ESCLUSIONE di un articolo fuori listino: E_RIGA_ECCEZIONE_FUORI_LISTINO (A-5)
--   8) AGGIUNTA di un solo componente: primo motivo SOLO_COMPONENTE (D-3)
--   9) AGGIUNTA di un articolo senza erogazioni: E_ARTICOLO_SENZA_EROGAZIONE
--  10) offerta senza tipo d'eccezione: E_PARAMETRO_INVALIDO
--  11) offerta (OFFERTA_COMMERCIALE): OVERRIDE fuori listino, stesso motivo
--  12) ordine: le regole di preventivo, ordine e bolla non cambiano (servizio)
--  Il guard (script.trgfn_righe_guard_articolo_ammesso sulle due tabelle)
--  13) contratto: INSERT di un'OVERRIDE fuori listino rifiutata
--  14) offerta: INSERT di un'AGGIUNTA gia' in listino rifiutata
--  15) contratto: INSERT dell'ESCLUSIONE di un figlio di bundle rifiutata
--  16) contratto: INSERT dell'AGGIUNTA di un solo componente rifiutata
--  17) contratto: INSERT dell'AGGIUNTA di un articolo fuori listino ammessa
--  Il ritiro
--  18) i guard «aggiunta fuori listino» ed «esclusione figlio di bundle» non ci sono piu'
--  Il bundle: sta nel listino coi suoi componenti, non in listini_righe
--  19) ESCLUSIONE del bundle P: ammessa
--  20) AGGIUNTA del bundle P: gia' nel listino
-- ------------------------------------------------------------

BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(20);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE _mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('eccezioni articolo ammesso');

-- La versione del builder nasce ATTIVA, e i componenti di un bundle non si
-- scrivono su una versione ATTIVA: la si chiude nel 2020 e quella di oggi
-- nasce qui (BOZZA, righe, ATTIVA). Stesso impianto di
-- test-righe-esclusione-solo-non-si-vende-v1.
CREATE TEMP TABLE _listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM _mondo), 'eccezioni articolo ammesso',
    '2020-01-01'::date, '2020-12-31'::date);

-- La tipologia del listino (rev 2026-10-21, I-D6): una della utility che ammette
-- la FISSA, perche' il bundle P abbia un'erogazione. Senza, la fixture muore.
UPDATE _listino
   SET tipologia_id = (
       SELECT ltu.tipologia_id
         FROM config.listini_tipologie_utilities ltu
        WHERE ltu.utility_id = (SELECT utility_id FROM _mondo)
          AND ltu.attivo
          AND EXISTS (SELECT 1 FROM config.listini_tipologie_erogazioni te
                       WHERE te.tipologia_id = ltu.tipologia_id
                         AND te.fonte_quantita_attesa = 'FISSA')
        ORDER BY ltu.tipologia_id
        LIMIT 1);
ALTER TABLE _listino ALTER COLUMN tipologia_id SET NOT NULL;
UPDATE vendite.listini l
   SET tipologia_id = t.tipologia_id
  FROM _listino t
 WHERE l.id = t.listino_id;

CREATE TEMP TABLE _ver AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
    SELECT listino_id, 'PGTAP_EAA_V2', '2021-01-01'::date FROM _listino
    RETURNING id
)
SELECT id FROM ins;

-- N: una tipologia che la utility prevede ma che non ha erogazioni. Il
-- vocabolario lo ammette (config.listini_tipologie e' gestibile): oggi non ce
-- n'e' una, quindi si costruisce.
CREATE TEMP TABLE _tip AS
WITH ins AS (
    INSERT INTO config.listini_tipologie (id, codice, descrizione, e_servizio)
    SELECT (SELECT max(id) + 1 FROM config.listini_tipologie), 'PGTAP_EAA_SENZA_EROG',
           'pgTAP: tipologia senza erogazioni', true
    RETURNING id
)
SELECT id FROM ins;
INSERT INTO config.listini_tipologie_utilities (id, utility_id, tipologia_id)
SELECT (SELECT max(id) + 1 FROM config.listini_tipologie_utilities),
       (SELECT utility_id FROM _mondo), (SELECT id FROM _tip);

-- La struttura nasce col builder: tipologia del listino per tutti tranne N
-- (quella senza erogazioni), S solo componente, P composito (il bundle).
CREATE TEMP TABLE _art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGTAP-EAA-' || v.sigla,
           p_listino_tipologia_id => CASE WHEN v.sigla = 'N' THEN (SELECT id FROM _tip)
                                          ELSE (SELECT tipologia_id FROM _listino) END,
           p_is_composito         => v.sigla = 'P',
           p_is_solo_componente   => v.sigla = 'S') AS id
  FROM (VALUES ('A'), ('B'), ('F'), ('P'), ('X'), ('S'), ('N')) AS v(sigla);

-- Scopo: id di un articolo della fixture per sigla.
CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
  SELECT id FROM _art WHERE sigla = p_sigla;
$fx$;

-- Il bundle: P (composito dalla nascita), con F come componente in distinta.
INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
VALUES (pg_temp.art('P'), pg_temp.art('F'), 1, '2020-01-01');

INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT (SELECT id FROM _ver), a.id, ar.uom_id, 100.00
  FROM _art a JOIN catalogo.articoli ar ON ar.id = a.id
 WHERE a.sigla IN ('A', 'B', 'F');

INSERT INTO vendite.listini_righe_componenti (listino_versione_id, articolo_componente_id,
       articolo_padre_id, articolo_figlio_id, prezzo, valido_dal)
SELECT (SELECT id FROM _ver), ac.id, pg_temp.art('P'), pg_temp.art('F'), 50.00, '2021-01-01'
  FROM catalogo.articoli_componenti ac
 WHERE ac.prodotto_id = pg_temp.art('P') AND ac.componente_id = pg_temp.art('F');

-- ⚠️ rev 2026-10-31 (20261031-39, D-3): la tipologia «pescata» sopra e' oggi la
--   quota fissa, e una versione con una quota fissa a canone senza periodicita'
--   non si attiva piu'. La fixture porta la versione al modello: periodicita' a
--   righe e kit, in bozza (brief-db-contratto-righe-periodiche-in-commessa §7.7).
UPDATE vendite.listini_righe SET periodicita = 'MENSILE'
 WHERE listino_versione_id = (SELECT id FROM _ver);
INSERT INTO vendite.listini_kit (listino_versione_id, articolo_padre_id, periodicita)
VALUES ((SELECT id FROM _ver), pg_temp.art('P'), 'MENSILE');

SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', (SELECT id FROM _ver), 'ATTIVA');

-- Due contratti DRAFT, col listino e senza; un'offerta BOZZA col listino.
CREATE TEMP TABLE _ctr AS
WITH ins AS (
    INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
           stato_doc_contratto_id, listino_id, valido_dal, valido_al)
    SELECT 'PGTAP-EAA-' || v.k || '-' || substr(gen_random_uuid()::text, 1, 8),
           m.billing_account_id, m.istanza_utility_id, m.utility_id,
           (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),
           CASE v.k WHEN 'L' THEN (SELECT listino_id FROM _listino) END,
           -- Periodi che non si sovrappongono: ex_contratti_no_overlap vuole un
           -- contratto solo per cliente e periodo.
           script.fn_data_operativa() + v.dopo, script.fn_data_operativa() + v.dopo + 365
      FROM _mondo m, (VALUES ('L', 0), ('0', 400)) AS v(k, dopo)
    RETURNING id, listino_id
)
SELECT id, CASE WHEN listino_id IS NULL THEN 'senza' ELSE 'con' END AS k FROM ins;

CREATE TEMP TABLE _off AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali
           (codice, emittente_fiscale_id, billing_account_id, istanza_utility_id,
            utility_id, listino_id, validita_dal, stato_doc_offerta_id)
    SELECT 'PGTAP-EAA-O-' || substr(gen_random_uuid()::text, 1, 8),
           m.emittente_fiscale_id, m.billing_account_id, m.istanza_utility_id,
           m.utility_id, (SELECT listino_id FROM _listino), script.fn_data_operativa(),
           (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'BOZZA')
      FROM _mondo m
    RETURNING id
)
SELECT id FROM ins;

-- Scopo: id del contratto 'con' o 'senza' listino.
CREATE OR REPLACE FUNCTION pg_temp.ctr(p_k text)
RETURNS bigint LANGUAGE sql STABLE AS $fx$ SELECT id FROM _ctr WHERE k = p_k; $fx$;

-- Scopo: il primo motivo (reason) della check, o 'AMMESSO'.
CREATE OR REPLACE FUNCTION pg_temp.primo(p_doc text, p_id bigint, p_sigla text, p_tipo text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT COALESCE(script.fn_check_articolo_riga(
           p_doc, p_id, pg_temp.art(p_sigla), NULL,
           p_tipo::vendite.tipo_eccezione_contratto) -> 0 ->> 'reason', 'AMMESSO');
$fx$;

-- Scopo: l'INSERT di una riga d'eccezione, come testo. ESCLUSIONE vuota;
--   AGGIUNTA e OVERRIDE coi dati di una riga che si fattura (erogazione e fonte
--   le eredita il DB dall'articolo; quantita' 1 se la fonte di default e' FISSA).
CREATE OR REPLACE FUNCTION pg_temp.ins(p_tab text, p_col text, p_id bigint, p_sigla text, p_tipo text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT CASE WHEN p_tipo = 'ESCLUSIONE' THEN format(
      $$INSERT INTO vendite.%I (%I, articolo_id, tipo_eccezione) VALUES (%s, %L, 'ESCLUSIONE')$$,
      p_tab, p_col, p_id, pg_temp.art(p_sigla))
  ELSE format(
      $$INSERT INTO vendite.%I (%I, articolo_id, tipo_eccezione, prezzo_unitario, quantita, qta_operativa, uom_operativa_id)
        SELECT %s, a.id, %L, 80.00, q.qta, q.qta, a.uom_id
          FROM catalogo.articoli a
          LEFT JOIN LATERAL (SELECT 1::numeric AS qta FROM vendite.fn_articolo_erogazioni(a.id) e
                              WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA' LIMIT 1) q ON true
         WHERE a.id = %L$$,
      p_tab, p_col, p_id, p_tipo, pg_temp.art(p_sigla))
  END;
$fx$;

-- ============================================================
-- La check (1-12)
-- ============================================================
SELECT is(pg_temp.primo('CONTRATTO', pg_temp.ctr('con'), 'X', 'AGGIUNTA'), 'AMMESSO',
    '1) contratto: AGGIUNTA di un articolo fuori listino, ammessa');
SELECT is(pg_temp.primo('CONTRATTO', pg_temp.ctr('con'), 'B', 'AGGIUNTA'), 'AGGIUNTA_GIA_IN_LISTINO',
    '2) contratto: AGGIUNTA di un articolo gia'' nel listino');
SELECT is(pg_temp.primo('CONTRATTO', pg_temp.ctr('con'), 'B', 'OVERRIDE'), 'AMMESSO',
    '3) contratto: OVERRIDE di un articolo del listino, ammessa');
SELECT is(pg_temp.primo('CONTRATTO', pg_temp.ctr('con'), 'X', 'OVERRIDE'), 'ECCEZIONE_FUORI_LISTINO',
    '4) contratto: OVERRIDE di un articolo fuori listino (A-5)');
SELECT is(pg_temp.primo('CONTRATTO', pg_temp.ctr('senza'), 'B', 'OVERRIDE'), 'ECCEZIONE_SENZA_LISTINO',
    '5) contratto senza listino: OVERRIDE (A-5)');
SELECT is(pg_temp.primo('CONTRATTO', pg_temp.ctr('con'), 'F', 'ESCLUSIONE'), 'FIGLIO_DI_BUNDLE',
    '6) contratto: ESCLUSIONE di un figlio di bundle');
SELECT is(pg_temp.primo('CONTRATTO', pg_temp.ctr('con'), 'X', 'ESCLUSIONE'), 'ECCEZIONE_FUORI_LISTINO',
    '7) contratto: ESCLUSIONE di un articolo fuori listino (A-5)');
SELECT is(pg_temp.primo('CONTRATTO', pg_temp.ctr('con'), 'S', 'AGGIUNTA'), 'SOLO_COMPONENTE',
    '8) contratto: AGGIUNTA di un solo componente (D-3)');
SELECT is(pg_temp.primo('CONTRATTO', pg_temp.ctr('con'), 'N', 'AGGIUNTA'), 'SENZA_EROGAZIONE',
    '9) contratto: AGGIUNTA di un articolo senza erogazioni');
SELECT throws_like(
    format($$SELECT script.fn_check_articolo_riga('OFFERTA_COMMERCIALE', %s, %L)$$,
           (SELECT id FROM _off), pg_temp.art('B')),
    '%p_tipo_eccezione%',
    '10) offerta senza tipo d''eccezione: E_PARAMETRO_INVALIDO');
SELECT is(pg_temp.primo('OFFERTA_COMMERCIALE', (SELECT id FROM _off), 'X', 'OVERRIDE'), 'ECCEZIONE_FUORI_LISTINO',
    '11) offerta: OVERRIDE di un articolo fuori listino (A-5)');
SELECT is(
    script.fn_check_articolo_riga('ORDINE_VENDITA', NULL, pg_temp.art('A'),
        (SELECT nv.id FROM config.nature_vendita nv WHERE nv.destinazione_tipo = 'COMMESSA' AND nv.attivo
          ORDER BY nv.id LIMIT 1)) -> 0 ->> 'reason',
    'NATURA_NON_MERCE',
    '12) ordine: la regola di preventivo, ordine e bolla non cambia');

-- ============================================================
-- Il guard (13-17)
-- ============================================================
SELECT throws_like(
    pg_temp.ins('contratti_righe', 'contratto_id', pg_temp.ctr('con'), 'X', 'OVERRIDE'),
    '%non è nel listino%',
    '13) contratto: INSERT di un''OVERRIDE fuori listino rifiutata');
SELECT throws_like(
    pg_temp.ins('offerte_commerciali_eccezioni', 'offerta_id', (SELECT id FROM _off), 'B', 'AGGIUNTA'),
    '%presente nel listino%',
    '14) offerta: INSERT di un''AGGIUNTA gia'' in listino rifiutata');
SELECT throws_like(
    pg_temp.ins('contratti_righe', 'contratto_id', pg_temp.ctr('con'), 'F', 'ESCLUSIONE'),
    '%figlio di un bundle%',
    '15) contratto: INSERT dell''ESCLUSIONE di un figlio di bundle rifiutata');
SELECT throws_like(
    pg_temp.ins('contratti_righe', 'contratto_id', pg_temp.ctr('con'), 'S', 'AGGIUNTA'),
    '%solo come componente%',
    '16) contratto: INSERT dell''AGGIUNTA di un solo componente rifiutata');
SELECT lives_ok(
    pg_temp.ins('contratti_righe', 'contratto_id', pg_temp.ctr('con'), 'X', 'AGGIUNTA'),
    '17) contratto: INSERT dell''AGGIUNTA di un articolo fuori listino ammessa');

-- ============================================================
-- Il ritiro (18)
-- ============================================================
SELECT ok(
    to_regprocedure('script.trgfn_righe_guard_aggiunta_fuori_listino()') IS NULL
    AND to_regprocedure('script.trgfn_righe_guard_esclusione_figlio_bundle()') IS NULL
    AND NOT EXISTS (SELECT 1 FROM pg_trigger
                     WHERE tgname ~ '_a10_guard_(aggiunta_fuori_listino|esclusione_figlio_bundle|escl_figlio_bundle)_'),
    '18) i guard «aggiunta fuori listino» ed «esclusione figlio di bundle» non ci sono piu''');

-- ============================================================
-- Il bundle (19-20): «nel listino» = una riga di vendite.fn_espandi_listino_versione,
-- la base su cui il drawer applica le eccezioni; il bundle ci sta coi componenti.
-- ============================================================
SELECT is(pg_temp.primo('CONTRATTO', pg_temp.ctr('con'), 'P', 'ESCLUSIONE'), 'AMMESSO',
    '19) contratto: ESCLUSIONE del bundle del listino, ammessa');
SELECT is(pg_temp.primo('CONTRATTO', pg_temp.ctr('con'), 'P', 'AGGIUNTA'), 'AGGIUNTA_GIA_IN_LISTINO',
    '20) contratto: AGGIUNTA del bundle che il listino ha gia''');

SELECT * FROM finish();
ROLLBACK;
