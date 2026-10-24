-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: come si eroga una riga di contratto o di offerta lo dice l'ARTICOLO.
--       Giro B3 (+B4) del brief brief-db-offerta-emissione-ed-erogazione (§B, §C.5,
--       §C.7, §C.9), changeSet 20261007-60 … -65. Decisioni di Tid del 2026-10-07:
--       B-R2 (la riga eredita), B-R3/B-D4 (il perimetro e' la tipologia dell'articolo,
--       dentro la utility), B-D1 (senza tipologia decide la natura), B-D5
--       (DERIVATA_COMPONENTI sul composito), B-D6 (le righe gia' scritte restano).
--       ⚠️ rev 2026-10-21 (§I, decisioni I-D1 e I-D6 di Tid; changeSet 20261021-48,
--       -55): DERIVATA_COMPONENTI ritirata (B-D5 superata) e il composito si eroga
--       solo con la FISSA (test 3, 21). B-D6 e' superata dal §H: la porta SUPER_ADMIN
--       non porta piu' una riga fuori dal perimetro (test 14-15, che prima la usavano
--       per COSTRUIRE quella riga). Il test 22 passa da K a C: il kit non ha piu' due
--       fonti nella stessa erogazione.
--
-- ⭐ TUTTO COSTRUITO: cliente ENE (la prima utility: ammette CONSUMO, QUOTA_FISSA,
--   IMPOSTA, ONERE_SISTEMA), listino, articoli. Gli articoli prendono qui la
--   classificazione che il caso vuole:
--     M, M2  MERCE senza tipologia          UNA_TANTUM/FISSA*, UNA_TANTUM/MANUALE
--     R, R2  SERVIZIO_RICORRENTE            CANONE/FISSA* (INIZIO_PERIODO), CONSUMO/MANUALE
--     C      tipologia CONSUMO, natura SERVIZIO_RICORRENTE   (vince la tipologia)
--     P      tipologia PRODOTTI, che ENE non prevede
--     K      composito, SERVIZIO_RICORRENTE  solo le FISSA: CANONE/FISSA* (I-D6)
-- ⚠️ I codici si leggono dai canali dell'eccezione (CONSTRAINT = codice, COLUMN = campo),
--   non dalla frase. Il test 20 legge il catalogo dei codici: rosso nella prova
--   pre-apply (il CSV si carica in 80_data), verde dopo l'apply.
-- ⚠️ Dal 20261007-28/-30 (§D.4 punto 2) con una fonte a valle la riga non porta
--   quantita': le righe che nascono MANUALE (6, 7, 22) si scrivono senza
--   qta_operativa, e il 12 la svuota insieme al cambio d'erogazione.
--
-- Indice test (1..22):
--   La sede unica (vendite.fn_articolo_erogazioni)
--    1) tipologia: vince sulla natura (C: solo CONSUMO)
--    2) senza tipologia: la natura (M: MERCE)
--    3) composito: solo le combinazioni FISSA (I-D6; niente DERIVATA_COMPONENTI)
--    4) articolo inesistente: nessuna riga
--   L'eredita' (INSERT)
--    5) niente erogazione ne' fonte: il default dell'articolo, con la generazione_canone
--    6) erogazione senza fonte: la fonte che l'articolo ammette per QUELLA erogazione
--    7) fonte senza erogazione: un'erogazione che l'articolo ammette con QUELLA fonte
--   Il perimetro (guard)
--    8) erogazione fuori perimetro: E_RIGA_EROGAZIONE_FUORI_PERIMETRO / tipo_erogazione
--    9) erogazione ammessa, fonte no: … / fonte_quantita_attesa
--   10) tipologia fuori utility: E_RIGA_TIPOLOGIA_FUORI_UTILITY / articolo_id
--   11) l'ESCLUSIONE non si giudica sul perimetro (parla solo il listino, A-5)
--   L'UPDATE
--   12) cambia la sola erogazione: la fonte si riallinea a quella dell'articolo
--   13) cambiano erogazione E fonte: la scelta non si tocca, la giudica il guard
--   14) la porta SUPER_ADMIN non porta una riga fuori perimetro (rev 2026-10-21)
--   15) …e la riga resta com'era
--   La lettura per il form (B4)
--   16) le combinazioni dell'articolo, col default in testa
--   17) tipologia fuori utility: nessuna combinazione
--   Il push (B-R5) e la forma
--   18) offerta → contratto: la riga porta i valori ereditati
--   19) l'ordine dei trigger sulle due tabelle gemelle
--   20) i due codici a catalogo, DATO_ERRATO
--   L'ordine delle combinazioni (§D.4 punto 1, 20261007-66 … -68)
--   21) il form sul composito: la sola CANONE/FISSA, di default
--   22) la prima fonte che il form propone per un'erogazione e' quella che il DB eredita (C)
-- ------------------------------------------------------------

BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(22);

-- Scopo: canali strutturati di uno statement che deve fallire: «codice / campo».
CREATE OR REPLACE FUNCTION pg_temp.canali(p_sql text)
RETURNS text LANGUAGE plpgsql AS $fx$
DECLARE v_cst text; v_col text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN ERRORE';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME, v_col = COLUMN_NAME;
        RETURN coalesce(nullif(v_cst, ''), '-') || ' / ' || coalesce(nullif(v_col, ''), '-');
    END;
END;
$fx$;

-- Scopo: le combinazioni di un articolo come testo ordinato, «EROG/FONTE[*]».
CREATE OR REPLACE FUNCTION pg_temp.combo(p_articolo uuid)
RETURNS text LANGUAGE sql STABLE AS $fx$
    SELECT string_agg(e.tipo_erogazione || '/' || e.fonte_quantita_attesa
                      || CASE WHEN e.e_default THEN '*' ELSE '' END,
                      ' ' ORDER BY e.tipo_erogazione, e.fonte_quantita_attesa)
      FROM vendite.fn_articolo_erogazioni(p_articolo) e;
$fx$;

-- ============================================================
-- Fixture COSTRUITA
-- ============================================================
CREATE TEMP TABLE tmp_eda_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'erogazione da articolo',
    (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_eda_art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGTAP-EDA-' || v.sigla,
           p_listino_tipologia_id => (SELECT t.id FROM config.listini_tipologie t
                                       WHERE t.codice = CASE v.sigla WHEN 'C' THEN 'CONSUMO'
                                                                     WHEN 'P' THEN 'PRODOTTI' END),
           p_is_composito         => v.sigla = 'K',
           p_natura_vendita_id    => CASE WHEN v.sigla IN ('R', 'R2', 'C', 'K', 'RP')
                                          THEN (SELECT n.id FROM config.nature_vendita n
                                                 WHERE n.codice_interno = 'SERVIZIO_RICORRENTE')
                                     END) AS id
  FROM (VALUES ('M'), ('M2'), ('R'), ('R2'), ('C'), ('P'), ('K'), ('RP'), ('KC')) AS v(sigla);

CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
    SELECT id FROM tmp_eda_art WHERE sigla = p_sigla;
$fx$;

-- rev 2026-10-14 (D-7, 20261014-06 di brief-db-articoli-ammessi-per-documento): un kit
--   senza nessun componente attivo non sta piu' in una riga (E_ARTICOLO_KIT_SENZA_COMPONENTI).
--   K riceve il suo componente KC: la fixture costruiva un kit vuoto.
INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
VALUES (pg_temp.art('K'), pg_temp.art('KC'), 1, '2020-01-01');

-- Contratto DRAFT senza listino: ogni AGGIUNTA e' ammessa dal guard del listino.
CREATE TEMP TABLE tmp_eda_ctr AS
WITH ins AS (
    INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
           stato_doc_contratto_id, emittente_fiscale_id)
    SELECT 'PGT-EDA-' || substr(md5(clock_timestamp()::text), 1, 6),
           c.billing_account_id, c.istanza_utility_id, c.utility_id,
           (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),
           script.fn_pgtap_emittente_operatore()
      FROM tmp_eda_cli c
    RETURNING id)
SELECT id FROM ins;

-- Scopo: l'INSERT di un'AGGIUNTA sul contratto, come testo (NULL = colonna vuota).
CREATE OR REPLACE FUNCTION pg_temp.agg(p_sigla text, p_erog text, p_fonte text,
                                       p_tipo text DEFAULT 'AGGIUNTA',
                                       p_qta numeric DEFAULT 1)
RETURNS text LANGUAGE sql STABLE AS $fx$
    SELECT CASE WHEN p_tipo = 'ESCLUSIONE' THEN
        format($$INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione)
                 VALUES (%s, %L, 'ESCLUSIONE')$$,
               (SELECT id FROM tmp_eda_ctr), pg_temp.art(p_sigla))
    ELSE
        format($$INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione,
                       prezzo_unitario, qta_operativa, tipo_erogazione, fonte_quantita_attesa)
                 VALUES (%s, %L, 'AGGIUNTA', 10, %L, %L, %L)$$,
               (SELECT id FROM tmp_eda_ctr), pg_temp.art(p_sigla), p_qta, p_erog, p_fonte)
    END;
$fx$;

-- Scopo: la riga del contratto per l'articolo, «EROG/FONTE/GENERAZIONE».
CREATE OR REPLACE FUNCTION pg_temp.riga(p_sigla text)
RETURNS text LANGUAGE sql STABLE AS $fx$
    SELECT r.tipo_erogazione || '/' || r.fonte_quantita_attesa || '/'
           || coalesce(r.generazione_canone, '-')
      FROM vendite.contratti_righe r
     WHERE r.contratto_id = (SELECT id FROM tmp_eda_ctr) AND r.articolo_id = pg_temp.art(p_sigla);
$fx$;

-- ============================================================
-- 1-4) La sede unica
-- ============================================================
SELECT is(pg_temp.combo(pg_temp.art('C')), 'CONSUMO/LETTURE* CONSUMO/MANUALE',
    '1) tipologia CONSUMO, natura SERVIZIO_RICORRENTE: vince la tipologia (niente CANONE)');

SELECT is(pg_temp.combo(pg_temp.art('M')), 'UNA_TANTUM/FISSA* UNA_TANTUM/MANUALE',
    '2) senza tipologia decide la natura (MERCE)');

SELECT is(pg_temp.combo(pg_temp.art('K')),
    'CANONE/FISSA*',
    '3) composito: solo le combinazioni FISSA della natura (I-D6), niente DERIVATA_COMPONENTI (I-D1)');

SELECT is((SELECT count(*)::int FROM vendite.fn_articolo_erogazioni(gen_random_uuid())), 0,
    '4) articolo inesistente: nessuna combinazione');

-- ============================================================
-- 5-7) L'eredita'
-- ============================================================
DO $fx$ BEGIN PERFORM pg_temp.canali(pg_temp.agg('R', NULL, NULL)); END $fx$;
SELECT is(pg_temp.riga('R'), 'CANONE/FISSA/INIZIO_PERIODO',
    '5) niente erogazione ne'' fonte: il default dell''articolo, con la generazione_canone');

-- Nasce MANUALE: senza quantita' (fonte a valle, 20261007-28).
DO $fx$ BEGIN PERFORM pg_temp.canali(pg_temp.agg('R2', 'CONSUMO', NULL, 'AGGIUNTA', NULL)); END $fx$;
SELECT is(pg_temp.riga('R2'), 'CONSUMO/MANUALE/-',
    '6) erogazione senza fonte: la fonte che l''articolo ammette per CONSUMO (MANUALE, non le LETTURE del vocabolario)');

DO $fx$ BEGIN PERFORM pg_temp.canali(pg_temp.agg('M', NULL, 'MANUALE', 'AGGIUNTA', NULL)); END $fx$;
SELECT is(pg_temp.riga('M'), 'UNA_TANTUM/MANUALE/-',
    '7) fonte senza erogazione: un''erogazione che l''articolo ammette con QUELLA fonte');

-- ============================================================
-- 8-11) Il perimetro
-- ============================================================
SELECT is(pg_temp.canali(pg_temp.agg('M2', 'CANONE', 'FISSA')),
    'E_RIGA_EROGAZIONE_FUORI_PERIMETRO / tipo_erogazione',
    '8) erogazione che l''articolo non ammette: rifiutata, campo tipo_erogazione');

SELECT is(pg_temp.canali(pg_temp.agg('C', 'CONSUMO', 'FISSA')),
    'E_RIGA_EROGAZIONE_FUORI_PERIMETRO / fonte_quantita_attesa',
    '9) erogazione ammessa con un''altra fonte: rifiutata, campo fonte_quantita_attesa');

SELECT is(pg_temp.canali(pg_temp.agg('P', NULL, NULL)),
    'E_RIGA_TIPOLOGIA_FUORI_UTILITY / articolo_id',
    '10) tipologia (PRODOTTI) che la utility (ENE) non prevede: rifiutata, campo articolo_id');

-- ⛔ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3b, A-5):
--   l'ESCLUSIONE modifica una riga del listino, e questo contratto un listino
--   non l'ha: parla E_RIGA_ECCEZIONE_SENZA_LISTINO. Il soggetto del test resta
--   vero, e si vede dal PRIMO motivo: P ha una tipologia che la utility non
--   prevede, e non e' quella a parlare — sul perimetro l'esclusione non si giudica.
SELECT is(pg_temp.canali(pg_temp.agg('P', NULL, NULL, 'ESCLUSIONE')),
    'E_RIGA_ECCEZIONE_SENZA_LISTINO / articolo_id',
    '11) l''ESCLUSIONE non si giudica sul perimetro: parla solo il listino (A-5), qui assente');

-- ============================================================
-- 12-15) L'UPDATE
-- ============================================================
-- R e' CANONE/FISSA (test 5). Cambia l'erogazione (non la fonte); la quantita'
-- si svuota, perche' la fonte riallineata (MANUALE) e' a valle.
UPDATE vendite.contratti_righe SET tipo_erogazione = 'CONSUMO', qta_operativa = NULL, quantita = NULL
 WHERE contratto_id = (SELECT id FROM tmp_eda_ctr) AND articolo_id = pg_temp.art('R');
SELECT is(split_part(pg_temp.riga('R'), '/', 2), 'MANUALE',
    '12) cambia la sola erogazione: la fonte si riallinea a quella che l''articolo ammette');

-- M e' UNA_TANTUM/MANUALE (test 7). L'operatore cambia erogazione E fonte.
SELECT is(pg_temp.canali(format(
    $$UPDATE vendite.contratti_righe SET tipo_erogazione = 'CONSUMO', fonte_quantita_attesa = 'LETTURE'
       WHERE contratto_id = %s AND articolo_id = %L$$,
    (SELECT id FROM tmp_eda_ctr), pg_temp.art('M'))),
    'E_RIGA_EROGAZIONE_FUORI_PERIMETRO / tipo_erogazione',
    '13) cambiano erogazione e fonte: la scelta non si corregge in silenzio, la giudica il guard');

-- RP e' SERVIZIO_RICORRENTE e la sua riga nasce CANONE/FISSA. Fino al 2026-10-21
-- qui la porta amministratore (catalogo.fn_articolo_correggi_struttura) faceva
-- diventare MERCE l'articolo gia' usato, e la riga restava fuori dal nuovo
-- perimetro (B-D6). Da 20261021-55 la porta confronta la riga INTERA
-- (script.fn_check_riga_documento_su_contesto): la correzione che porterebbe la
-- riga fuori dal perimetro d'erogazione si ferma, e la riga resta com'e'.
DO $fx$ BEGIN PERFORM pg_temp.canali(pg_temp.agg('RP', NULL, NULL)); END $fx$;
CREATE TEMP TABLE tmp_eda_rp AS SELECT pg_temp.riga('RP') AS prima;

SELECT is(pg_temp.canali(format(
    $$SELECT dbops.fn_pgtap_articolo_correggi_struttura(%L, %L::jsonb)$$,
    pg_temp.art('RP'),
    jsonb_build_object('natura_vendita_id',
        (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE')))),
    'E_ARTICOLO_STRUTTURA_RIGHE_APERTE / -',
    '14) la porta SUPER_ADMIN non porta una riga fuori dal perimetro d''erogazione: la correzione si ferma');

-- ⚠️ La riga deve esistere: due NULL uguali sarebbero un verde per sottrazione.
SELECT ok((SELECT prima IS NOT NULL AND prima LIKE 'CANONE/FISSA/%'
                  AND pg_temp.riga('RP') = prima
             FROM tmp_eda_rp),
    '15) …e la riga resta com''era (CANONE/FISSA)');

-- ============================================================
-- 16-17) La lettura per il form (B4)
-- ============================================================
SELECT is(
    (SELECT string_agg(e.tipo_erogazione || '/' || e.fonte_quantita_attesa
                       || CASE WHEN e.e_default THEN '*' ELSE '' END, ' ' ORDER BY e.n)
       FROM vendite.fn_documento_riga_erogazioni('CONTRATTO', (SELECT id FROM tmp_eda_ctr),
                                                 pg_temp.art('R2'))
            WITH ORDINALITY AS e(tipo_erogazione, fonte_quantita_attesa, e_default,
                                 generazione_canone, origine, n)),
    'CANONE/FISSA* CONSUMO/MANUALE',
    '16) il form legge le combinazioni dell''articolo, col default in testa');

SELECT is(
    (SELECT count(*)::int FROM vendite.fn_documento_riga_erogazioni(
        'CONTRATTO', (SELECT id FROM tmp_eda_ctr), pg_temp.art('P'))),
    0,
    '17) tipologia fuori utility: nessuna combinazione proposta');

-- ============================================================
-- 18) Il push offerta → contratto porta i valori ereditati (B-R5)
-- ============================================================
-- ⚠️ Un altro cliente: il contratto del push non deve incontrare quello sopra.
CREATE TEMP TABLE tmp_eda_cli2 AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'erogazione da articolo push',
    (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_eda_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_eda_cli2), 'erogazione da articolo');

CREATE TEMP TABLE tmp_eda_off AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, validita_dal, stato_doc_offerta_id)
    SELECT script.fn_pgtap_emittente_operatore(), c.billing_account_id, c.istanza_utility_id,
           c.utility_id, (SELECT listino_id FROM tmp_eda_listino), script.fn_data_operativa(),
           (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')
      FROM tmp_eda_cli2 c
    RETURNING id)
SELECT id FROM ins;

INSERT INTO vendite.offerte_commerciali_utilities (offerta_id, istanza_utility_id, utility_id)
SELECT o.id, c.istanza_utility_id, c.utility_id FROM tmp_eda_off o, tmp_eda_cli2 c;

INSERT INTO vendite.offerte_commerciali_eccezioni
       (offerta_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa)
VALUES ((SELECT id FROM tmp_eda_off), pg_temp.art('R2'), 'AGGIUNTA', 10, 1);

UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')
 WHERE id = (SELECT id FROM tmp_eda_off);
UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ACCETTATA')
 WHERE id = (SELECT id FROM tmp_eda_off);

CREATE TEMP TABLE tmp_eda_push AS
SELECT vendite.fn_push_offerta_a_contratto((SELECT id FROM tmp_eda_off), NULL::bigint, false) AS contratto_id;

SELECT is(
    (SELECT r.tipo_erogazione || '/' || r.fonte_quantita_attesa || '/' || coalesce(r.generazione_canone, '-')
       FROM vendite.contratti_righe r
      WHERE r.contratto_id = (SELECT contratto_id FROM tmp_eda_push)
        AND r.articolo_id = pg_temp.art('R2')),
    'CANONE/FISSA/INIZIO_PERIODO',
    '18) push offerta → contratto: la riga porta erogazione, fonte e generazione ereditate sull''offerta');

-- ============================================================
-- 19-20) La forma
-- ============================================================
SELECT is(
    (SELECT string_agg(split_part(t.tgname, '_a10_', 2), ' ' ORDER BY t.tgname)
       FROM pg_trigger t
      WHERE t.tgrelid IN ('vendite.contratti_righe'::regclass,
                          'vendite.offerte_commerciali_eccezioni'::regclass)
        AND NOT t.tgisinternal
        AND t.tgname ~ '_a10_(default_erogazione|default_fonte|guard_erogazione)'),
    'default_erogazione_articolo_ins_upd default_fonte_qta_ins_upd guard_erogazione_obbligatoria_ins_upd guard_erogazione_perimetro_ins guard_erogazione_perimetro_upd '
    || 'default_erogazione_articolo_ins_upd default_fonte_qta_ins_upd guard_erogazione_obbligatoria_ins_upd guard_erogazione_perimetro_ins guard_erogazione_perimetro_upd',
    '19) sulle due tabelle: prima si eredita, poi la fonte generica, poi l''obbligo, poi il perimetro');

SELECT is(
    (SELECT string_agg(ce.codice || '=' || ce.classe, ' ' ORDER BY ce.codice)
       FROM config.codici_errore ce
      WHERE ce.codice IN ('E_RIGA_EROGAZIONE_FUORI_PERIMETRO', 'E_RIGA_TIPOLOGIA_FUORI_UTILITY')),
    'E_RIGA_EROGAZIONE_FUORI_PERIMETRO=DATO_ERRATO E_RIGA_TIPOLOGIA_FUORI_UTILITY=DATO_ERRATO',
    '20) i due codici nuovi a catalogo, DATO_ERRATO');

-- ============================================================
-- 21-22) L'ordine delle combinazioni (§D.4 punto 1)
-- ============================================================
-- K composito SERVIZIO_RICORRENTE: della natura (CANONE/FISSA*, CONSUMO/MANUALE)
-- tiene la sola FISSA (I-D6). Fino al 2026-10-21 c'erano in piu' le DERIVATA, e
-- l'ordine «DERIVATA per ultima» era il difetto segnalato dal giro BE/FE.
SELECT is(
    (SELECT string_agg(e.tipo_erogazione || '/' || e.fonte_quantita_attesa
                       || CASE WHEN e.e_default THEN '*' ELSE '' END, ' ' ORDER BY e.n)
       FROM vendite.fn_documento_riga_erogazioni('CONTRATTO', (SELECT id FROM tmp_eda_ctr),
                                                 pg_temp.art('K'))
            WITH ORDINALITY AS e(tipo_erogazione, fonte_quantita_attesa, e_default,
                                 generazione_canone, origine, n)),
    'CANONE/FISSA*',
    '21) il form sul composito: la sola CANONE/FISSA, di default (I-D6)');

-- L'erogazione CONSUMO senza fonte: la riga eredita la fonte, e il form propone
-- per prima la stessa. Fino al 2026-10-21 il caso era K, che aveva in piu' la
-- DERIVATA; ora e' C (CONSUMO: LETTURE di default, poi MANUALE), che non ha
-- ancora una riga (il test 9 e' un rifiuto).
DO $fx$ BEGIN PERFORM pg_temp.canali(pg_temp.agg('C', 'CONSUMO', NULL, 'AGGIUNTA', NULL)); END $fx$;
SELECT is(
    split_part(pg_temp.riga('C'), '/', 2),
    (SELECT e.fonte_quantita_attesa
       FROM vendite.fn_documento_riga_erogazioni('CONTRATTO', (SELECT id FROM tmp_eda_ctr),
                                                 pg_temp.art('C'))
            WITH ORDINALITY AS e(tipo_erogazione, fonte_quantita_attesa, e_default,
                                 generazione_canone, origine, n)
      WHERE e.tipo_erogazione = 'CONSUMO'
      ORDER BY e.n
      LIMIT 1)::text,
    '22) la prima fonte che il form propone per CONSUMO e'' quella che il DB eredita (LETTURE)');

SELECT * FROM finish();
ROLLBACK;
