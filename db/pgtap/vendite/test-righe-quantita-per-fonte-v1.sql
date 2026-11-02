-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-11-01 (20261101-04/-06, brief-db-contratto-righe-periodiche-in-commessa passo 4): la
--   riga a canone vuole la periodicita'. La AGGIUNTA a canone la scrive (MENSILE): non e' il soggetto di questo test. Nessuna attesa
--   cambiata.
-- pgTAP test per Zero ERP
--
-- Test: la quantita' di una riga di contratto o di offerta la porta la sua FONTE.
--       Solo FISSA (la quantita' della riga) ha quantita e qta_operativa; con una
--       fonte a valle (MANUALE, LETTURE, TIMESHEET) restano vuote.
--       Brief brief-db-offerta-emissione-ed-erogazione §D.4 punto 2, §E (decisione di
--       Tid del 2026-10-07: «DB, rifiuto»), changeSet 20261007-28 … -30.
--       Terzo giro (§F.1, decisione di Tid del 2026-10-08, changeSet 20261008-10 … -12):
--       quantita e' CALCOLATA. Con una fonte a valle la porta a NULL il DB
--       (trgfn_qta_from_operativa); il rifiuto resta sull'input, qta_operativa.
--       Prima la regola la applicava solo il backend, solo sul contratto, azzerando
--       in silenzio (`_apply_fonte_quantita_logic`).
--       ⚠️ rev 2026-10-21 (§I.1, I-D1 di Tid; changeSet 20261021-44 … -51):
--       DERIVATA_COMPONENTI ritirata. Diceva «la quantita' la scrive il DB dai
--       componenti», ma i componenti seguono la quantita' del padre e nessuno la
--       calcolava. Il test 5 prova il composito con la FISSA, il 13 che la DERIVATA
--       e' fuori dal perimetro, il 10 che CHECK e funzione dicono la sola FISSA.
--
-- ⭐ TUTTO COSTRUITO: cliente sulla prima utility, contratto DRAFT senza listino,
--   offerta in BOZZA su un listino costruito, articoli senza tipologia (decide la
--   natura):
--     M  MERCE                 UNA_TANTUM/FISSA*, UNA_TANTUM/MANUALE
--     R  SERVIZIO_RICORRENTE   CANONE/FISSA*, CONSUMO/MANUALE
--     K  MERCE, composito      come M (dal 2026-10-21 niente DERIVATA_COMPONENTI)
--     N  MERCE                 come M (una riga sola per articolo: uq AGGIUNTA)
-- ⚠️ I codici si leggono dai canali dell'eccezione (CONSTRAINT = codice, COLUMN =
--   campo), non dalla frase. Il test 12 legge il catalogo dei codici: rosso nella
--   prova pre-apply (il CSV si carica in 80_data), verde dopo l'apply.
--
-- Indice test (1..15):
--   L'INSERT
--    1) fonte a valle con qta_operativa: rifiutata, campo qta_operativa
--    2) fonte a valle con la sola quantita: ammessa, quantita la svuota il DB (F-1.2)
--    3) fonte a valle senza quantita': ammessa
--    4) FISSA con la quantita': ammessa
--    5) il composito con la FISSA e la quantita': ammessa (i componenti la seguono)
--    6) l'offerta, stessa regola (il push copia le righe 1:1)
--   L'UPDATE
--    7) cambia l'erogazione e un altro trigger riallinea la fonte a MANUALE: la
--       quantita' rimasta e' rifiutata (UPDATE senza colonne)
--    8) una fonte fuori perimetro: parla prima il perimetro, non la quantita'
--    9) FISSA → MANUALE con la quantita': rifiutata; mandando la sola
--       qta_operativa = NULL (come il form): ammessa, e quantita resta NULL (F-1.4)
--   La forma
--   10) i due CHECK (la rete) dicono le fonti di script.fn_fonte_porta_quantita, e
--       il guard e il calcolo della quantita' la chiamano (F-1.3)
--   11) il guard sulle due tabelle: BEFORE INSERT OR UPDATE, senza colonne, dopo
--       il perimetro
--   12) il codice a catalogo, DATO_ERRATO
--   Il terzo giro (§F.1)
--   13) DERIVATA_COMPONENTI e' ritirata: la riga che la chiede e' fuori perimetro
--   14) l'offerta: FISSA → MANUALE con la sola qta_operativa = NULL, quantita NULL
--   15) MANUALE con qta_operativa sull'UPDATE: rifiutata col campo qta_operativa
-- ------------------------------------------------------------

BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(15);

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

-- ============================================================
-- Fixture COSTRUITA
-- ============================================================
CREATE TEMP TABLE tmp_qpf_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'quantita per fonte',
    (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_qpf_art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGTAP-QPF-' || v.sigla,
           p_is_composito      => v.sigla = 'K',
           p_natura_vendita_id => CASE WHEN v.sigla = 'R'
                                       THEN (SELECT n.id FROM config.nature_vendita n
                                              WHERE n.codice_interno = 'SERVIZIO_RICORRENTE')
                                  END) AS id
  FROM (VALUES ('M'), ('R'), ('K'), ('N'), ('KC')) AS v(sigla);

CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
    SELECT id FROM tmp_qpf_art WHERE sigla = p_sigla;
$fx$;

-- rev 2026-10-14 (D-7, 20261014-06 di brief-db-articoli-ammessi-per-documento): un kit
--   senza nessun componente attivo non sta piu' in una riga (E_ARTICOLO_KIT_SENZA_COMPONENTI).
--   K riceve il suo componente KC: la fixture costruiva un kit vuoto.
INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
VALUES (pg_temp.art('K'), pg_temp.art('KC'), 1, '2020-01-01');

-- Contratto DRAFT senza listino: ogni AGGIUNTA e' ammessa dal guard del listino.
CREATE TEMP TABLE tmp_qpf_ctr AS
WITH ins AS (
    INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
           stato_doc_contratto_id, emittente_fiscale_id)
    SELECT 'PGT-QPF-' || substr(md5(clock_timestamp()::text), 1, 6),
           c.billing_account_id, c.istanza_utility_id, c.utility_id,
           (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),
           script.fn_pgtap_emittente_operatore()
      FROM tmp_qpf_cli c
    RETURNING id)
SELECT id FROM ins;

-- Scopo: l'INSERT di un'AGGIUNTA sul contratto, come testo (NULL = colonna vuota).
CREATE OR REPLACE FUNCTION pg_temp.agg(p_sigla text, p_erog text, p_fonte text,
                                       p_qta_op numeric, p_qta numeric DEFAULT NULL)
RETURNS text LANGUAGE sql STABLE AS $fx$
    SELECT format($$INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione,
                         prezzo_unitario, qta_operativa, quantita, tipo_erogazione, fonte_quantita_attesa,
                         periodicita)
                   VALUES (%s, %L, 'AGGIUNTA', 10, %L, %L, %L, %L, %L)$$,
                  (SELECT id FROM tmp_qpf_ctr), pg_temp.art(p_sigla), p_qta_op, p_qta, p_erog, p_fonte,
                  CASE WHEN p_erog = 'CANONE' THEN 'MENSILE' END);
$fx$;

-- Scopo: la riga del contratto per l'articolo, «EROG/FONTE/QTA_OPERATIVA/QUANTITA».
CREATE OR REPLACE FUNCTION pg_temp.riga(p_sigla text)
RETURNS text LANGUAGE sql STABLE AS $fx$
    SELECT r.tipo_erogazione || '/' || r.fonte_quantita_attesa || '/' || coalesce(r.qta_operativa::text, '-')
           || '/' || coalesce(r.quantita::text, '-')
      FROM vendite.contratti_righe r
     WHERE r.contratto_id = (SELECT id FROM tmp_qpf_ctr) AND r.articolo_id = pg_temp.art(p_sigla);
$fx$;

-- ============================================================
-- 1-6) L'INSERT
-- ============================================================
SELECT is(pg_temp.canali(pg_temp.agg('M', 'UNA_TANTUM', 'MANUALE', 1)),
    'E_RIGA_QUANTITA_CON_FONTE_A_VALLE / qta_operativa',
    '1) fonte a valle (MANUALE) con qta_operativa: rifiutata, campo qta_operativa');

-- quantita e' calcolata: chi la manda con una fonte a valle non viene rifiutato,
-- la svuota il DB (F-1.2). La lettura in un'istruzione a parte (snapshot).
CREATE TEMP TABLE tmp_qpf_2 AS
SELECT pg_temp.canali(pg_temp.agg('M', 'UNA_TANTUM', 'MANUALE', NULL, 1)) AS esito;

SELECT is((SELECT esito FROM tmp_qpf_2) || ' | ' || pg_temp.riga('M'),
    'NESSUN ERRORE | UNA_TANTUM/MANUALE/-/-',
    '2) fonte a valle con la sola quantita: ammessa, la quantita'' la svuota il DB');

SELECT is(pg_temp.canali(pg_temp.agg('N', 'UNA_TANTUM', 'MANUALE', NULL)), 'NESSUN ERRORE',
    '3) fonte a valle senza quantita'': ammessa');

SELECT is(pg_temp.canali(pg_temp.agg('R', 'CANONE', 'FISSA', 2)), 'NESSUN ERRORE',
    '4) FISSA con la quantita'': ammessa');

SELECT is(pg_temp.canali(pg_temp.agg('K', 'UNA_TANTUM', 'FISSA', 1)), 'NESSUN ERRORE',
    '5) il composito con la FISSA e la quantita'': ammessa (i componenti la seguono)');

-- L'offerta: stessa regola, perche' fn_push_offerta_a_contratto copia le righe 1:1.
CREATE TEMP TABLE tmp_qpf_cli2 AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'quantita per fonte offerta',
    (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_qpf_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_qpf_cli2), 'quantita per fonte');

CREATE TEMP TABLE tmp_qpf_off AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, validita_dal, stato_doc_offerta_id)
    SELECT script.fn_pgtap_emittente_operatore(), c.billing_account_id, c.istanza_utility_id,
           c.utility_id, (SELECT listino_id FROM tmp_qpf_listino), script.fn_data_operativa(),
           (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')
      FROM tmp_qpf_cli2 c
    RETURNING id)
SELECT id FROM ins;

INSERT INTO vendite.offerte_commerciali_utilities (offerta_id, istanza_utility_id, utility_id)
SELECT o.id, c.istanza_utility_id, c.utility_id FROM tmp_qpf_off o, tmp_qpf_cli2 c;

SELECT is(pg_temp.canali(format(
    $$INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id, tipo_eccezione,
             prezzo_unitario, qta_operativa, tipo_erogazione, fonte_quantita_attesa)
      VALUES (%s, %L, 'AGGIUNTA', 10, 1, 'CONSUMO', 'MANUALE')$$,
    (SELECT id FROM tmp_qpf_off), pg_temp.art('R'))),
    'E_RIGA_QUANTITA_CON_FONTE_A_VALLE / qta_operativa',
    '6) l''offerta: fonte a valle con qta_operativa, rifiutata come sul contratto');

-- ============================================================
-- 7-9) L'UPDATE
-- ============================================================
-- R e' CANONE/FISSA con qta_operativa 2 (test 4). Cambia la sola erogazione: la
-- fonte la riallinea trgfn_righe_default_erogazione_da_articolo (MANUALE), e la
-- quantita' rimasta e' di troppo. Un UPDATE OF fonte non l'avrebbe visto.
SELECT is(pg_temp.canali(format(
    $$UPDATE vendite.contratti_righe SET tipo_erogazione = 'CONSUMO'
       WHERE contratto_id = %s AND articolo_id = %L$$,
    (SELECT id FROM tmp_qpf_ctr), pg_temp.art('R'))),
    'E_RIGA_QUANTITA_CON_FONTE_A_VALLE / qta_operativa',
    '7) cambia l''erogazione, la fonte si riallinea a MANUALE: la quantita'' rimasta e'' rifiutata');

SELECT is(pg_temp.canali(format(
    $$UPDATE vendite.contratti_righe SET fonte_quantita_attesa = 'MANUALE'
       WHERE contratto_id = %s AND articolo_id = %L AND fonte_quantita_attesa = 'FISSA'$$,
    (SELECT id FROM tmp_qpf_ctr), pg_temp.art('R'))),
    'E_RIGA_EROGAZIONE_FUORI_PERIMETRO / fonte_quantita_attesa',
    '8) CANONE/MANUALE e'' fuori perimetro per R: parla prima il perimetro («guard_e» < «guard_q»)');

-- M ha una riga UNA_TANTUM/MANUALE senza quantita' (test 2): si porta a FISSA con
-- la quantita', poi di nuovo a MANUALE.
UPDATE vendite.contratti_righe SET fonte_quantita_attesa = 'FISSA', qta_operativa = 3
 WHERE contratto_id = (SELECT id FROM tmp_qpf_ctr) AND articolo_id = pg_temp.art('M');

-- ⚠️ Gli UPDATE in un'istruzione, la lettura in un'altra: una funzione STABLE
--   chiamata nella stessa istruzione vede la fotografia presa prima degli UPDATE.
CREATE TEMP TABLE tmp_qpf_89 AS
SELECT pg_temp.canali(format(
           $$UPDATE vendite.contratti_righe SET fonte_quantita_attesa = 'MANUALE'
              WHERE contratto_id = %s AND articolo_id = %L$$,
           (SELECT id FROM tmp_qpf_ctr), pg_temp.art('M'))) AS solo_fonte;
ALTER TABLE tmp_qpf_89 ADD COLUMN svuotata text;
-- ⭐ Come il form (F-1.4): la sola qta_operativa = NULL, quantita non si manda.
UPDATE tmp_qpf_89 SET svuotata = pg_temp.canali(format(
           $$UPDATE vendite.contratti_righe
                SET fonte_quantita_attesa = 'MANUALE', qta_operativa = NULL
              WHERE contratto_id = %s AND articolo_id = %L$$,
           (SELECT id FROM tmp_qpf_ctr), pg_temp.art('M')));

SELECT is(
    (SELECT solo_fonte || ' | ' || svuotata FROM tmp_qpf_89) || ' | ' || pg_temp.riga('M'),
    'E_RIGA_QUANTITA_CON_FONTE_A_VALLE / qta_operativa | NESSUN ERRORE | UNA_TANTUM/MANUALE/-/-',
    '9) FISSA → MANUALE con la quantita'': rifiutata; con la sola qta_operativa = NULL: ammessa, quantita NULL');

-- ============================================================
-- 10-12) La forma
-- ============================================================
-- L'elenco delle fonti che portano la quantita' sta in script.fn_fonte_porta_quantita
-- (F-1.3). I CHECK (la rete) ne tengono una copia: i loro letterali devono essere
-- le fonti del vocabolario per cui la funzione dice true. Il guard e il calcolo
-- della quantita' la CHIAMANO (commenti tolti: un nome nella prosa non conta).
SELECT is(
    (SELECT string_agg(DISTINCT x.elenco, ' | ')
       FROM (SELECT (SELECT string_agg(m[1], ',' ORDER BY m[1])
                       FROM regexp_matches(pg_get_constraintdef(c.oid), '''([A-Z_]+)''', 'g') AS m) AS elenco
               FROM pg_constraint c
              WHERE c.conname IN ('chk_contrighe_quantita_per_fonte',
                                  'chk_offerte_eccezioni_quantita_per_fonte')
             UNION ALL
             SELECT string_agg(DISTINCT ef.fonte_quantita_attesa, ',' ORDER BY ef.fonte_quantita_attesa)
               FROM config.erogazioni_fonti ef
              WHERE script.fn_fonte_porta_quantita(ef.fonte_quantita_attesa)) x)
    || ' #' || (SELECT count(*) FROM pg_constraint c
                 WHERE c.conname IN ('chk_contrighe_quantita_per_fonte',
                                     'chk_offerte_eccezioni_quantita_per_fonte')
                   AND c.contype = 'c' AND c.convalidated)
    || ' ' || (SELECT string_agg(p.proname || '=' ||
                         (regexp_replace(p.prosrc, '--[^\n]*', '', 'g')
                            ~ 'script\.fn_fonte_porta_quantita\s*\(')::text
                         || (CASE WHEN p.prosrc ~ 'c_fonti_con_quantita' THEN '+costante' ELSE '' END),
                         ' ' ORDER BY p.proname)
                 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'script'
                  AND p.proname IN ('trgfn_righe_guard_quantita_per_fonte', 'trgfn_qta_from_operativa')),
    'FISSA #2 trgfn_qta_from_operativa=true trgfn_righe_guard_quantita_per_fonte=true',
    '10) i due CHECK (validati) dicono le fonti di fn_fonte_porta_quantita; guard e calcolo la chiamano');

-- tgtype: bit 1 ROW, bit 2 BEFORE, bit 4 INSERT, bit 16 UPDATE; tgattr vuoto = nessun OF.
SELECT is(
    (SELECT string_agg(split_part(t.tgname, '_a10_', 2) || ':' ||
                       (t.tgtype & 2 = 2 AND t.tgtype & 4 = 4 AND t.tgtype & 16 = 16
                        AND cardinality(t.tgattr::int2[]) = 0)::text, ' ' ORDER BY t.tgname)
       FROM pg_trigger t
      WHERE t.tgrelid IN ('vendite.contratti_righe'::regclass,
                          'vendite.offerte_commerciali_eccezioni'::regclass)
        AND NOT t.tgisinternal
        AND t.tgname ~ '_a10_guard_(erogazione_perimetro_upd|quantita)'),
    'guard_erogazione_perimetro_upd:false guard_quantita_per_fonte_ins_upd:true '
    || 'guard_erogazione_perimetro_upd:false guard_quantita_per_fonte_ins_upd:true',
    '11) il guard sulle due tabelle: BEFORE INSERT OR UPDATE senza colonne, dopo il perimetro');

SELECT is(
    (SELECT ce.codice || '=' || ce.classe FROM config.codici_errore ce
      WHERE ce.codice = 'E_RIGA_QUANTITA_CON_FONTE_A_VALLE'),
    'E_RIGA_QUANTITA_CON_FONTE_A_VALLE=DATO_ERRATO',
    '12) il codice a catalogo, DATO_ERRATO');

-- ============================================================
-- 13-15) Il terzo giro (§F.1): quantita e' calcolata
-- ============================================================
-- K e' il composito FISSA con qta_operativa 1 (test 5). Fino al 2026-10-21 il
-- composito ammetteva in piu' DERIVATA_COMPONENTI (B-D5); ritirata (§I.1), la
-- riga che la chiede e' fuori dal perimetro dell'articolo, e resta com'era.
CREATE TEMP TABLE tmp_qpf_13 AS
SELECT pg_temp.riga('K') AS prima,
       pg_temp.canali(format(
           $$UPDATE vendite.contratti_righe SET fonte_quantita_attesa = 'DERIVATA_COMPONENTI'
              WHERE contratto_id = %s AND articolo_id = %L$$,
           (SELECT id FROM tmp_qpf_ctr), pg_temp.art('K'))) AS esito;

SELECT is(
    (SELECT prima || ' | ' || esito FROM tmp_qpf_13) || ' | ' || pg_temp.riga('K'),
    'UNA_TANTUM/FISSA/1.000000/1.000000 | E_RIGA_EROGAZIONE_FUORI_PERIMETRO / fonte_quantita_attesa | UNA_TANTUM/FISSA/1.000000/1.000000',
    '13) DERIVATA_COMPONENTI e'' ritirata: la riga che la chiede e'' fuori perimetro, e resta FISSA');

-- L'offerta: stessa regola. M nasce FISSA con la quantita', poi passa a MANUALE
-- mandando la sola qta_operativa = NULL, come il form.
INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id, tipo_eccezione,
       prezzo_unitario, qta_operativa, tipo_erogazione, fonte_quantita_attesa)
VALUES ((SELECT id FROM tmp_qpf_off), pg_temp.art('M'), 'AGGIUNTA', 10, 2, 'UNA_TANTUM', 'FISSA');

CREATE TEMP TABLE tmp_qpf_14 AS
SELECT pg_temp.canali(format(
           $$UPDATE vendite.offerte_commerciali_eccezioni
                SET fonte_quantita_attesa = 'MANUALE', qta_operativa = NULL
              WHERE offerta_id = %s AND articolo_id = %L$$,
           (SELECT id FROM tmp_qpf_off), pg_temp.art('M'))) AS esito;

SELECT is(
    (SELECT esito FROM tmp_qpf_14) || ' | ' ||
    (SELECT e.fonte_quantita_attesa || '/' || coalesce(e.qta_operativa::text, '-') || '/'
            || coalesce(e.quantita::text, '-')
       FROM vendite.offerte_commerciali_eccezioni e
      WHERE e.offerta_id = (SELECT id FROM tmp_qpf_off) AND e.articolo_id = pg_temp.art('M')),
    'NESSUN ERRORE | MANUALE/-/-',
    '14) l''offerta: FISSA → MANUALE con la sola qta_operativa = NULL, ammessa e quantita NULL');

-- Il rifiuto resta sull'input: una qta_operativa su una riga MANUALE.
SELECT is(pg_temp.canali(format(
    $$UPDATE vendite.offerte_commerciali_eccezioni SET qta_operativa = 4
       WHERE offerta_id = %s AND articolo_id = %L$$,
    (SELECT id FROM tmp_qpf_off), pg_temp.art('M'))),
    'E_RIGA_QUANTITA_CON_FONTE_A_VALLE / qta_operativa',
    '15) MANUALE con qta_operativa sull''UPDATE: rifiutata col campo qta_operativa');

SELECT * FROM finish();
ROLLBACK;
