-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il listino di un contratto o di un'offerta e' della SUA utility e del SUO
--       emittente. Brief brief-db-offerta-emissione-ed-erogazione §F.2 (decisione
--       F-2 di Tid del 2026-10-08), changeSet 20261008-13 … -16.
--
-- ⭐ TUTTO COSTRUITO: due aziende (MIA, il contesto; ALTRUI, il listino fuori
--   perimetro) con dbops.fn_pgtap_crea_emittente_operatore, prima del contesto;
--   il cliente di MIA sulla utility U1; tre listini:
--     L_MIO     U1, emittente MIA                     → ammesso
--     L_ALTRA_U U2, emittente MIA                     → utility diversa
--     L_ALTRUI  U1, emittente ALTRUI (lo crea ALTRUI) → emittente diverso
-- ⚠️ Runner APPLICATIVO: L_ALTRUI per MIA non si legge (RLS di vendite.listini), e
--   la check lo dice «emittente diverso». Da owner si legge e l'emittente e'
--   diverso: stesso motivo, stesso esito. Nessun test dipende dal runner.
-- ⚠️ I codici si leggono dai canali dell'eccezione (CONSTRAINT = codice, COLUMN =
--   campo), non dalla frase. Il test 12 legge il catalogo: rosso nella prova
--   pre-apply (il CSV si carica in 80_data), verde dopo l'apply.
-- rev 2026-10-26 (brief-modello-documento-vendita §13, giro 9): lo stato
--   dell'offerta del push dalla fixture dbops.fn_pgtap_porta_a_stato (il verbo),
--   non piu' con due UPDATE diretti: la porta li rifiuta.
--
-- Indice test (1..12):
--   La check, sui valori (F-2.1)
--    1) listino della utility e dell'emittente del documento: nessun motivo
--    2) utility diversa, emittente diverso, listino NULL, valori NULL
--   Il guard (F-2.2)
--    3) offerta con L_MIO: ammessa
--    4) offerta con L_ALTRA_U: rifiutata, E_DOC_LISTINO_UTILITY_DIVERSA, campo listino_id
--    5) offerta con L_ALTRUI: rifiutata, E_DOC_LISTINO_EMITTENTE_DIVERSO, campo listino_id
--    6) contratto senza listino (negoziato puro): ammesso; con L_ALTRA_U: rifiutato
--    7) UPDATE del listino del contratto: L_ALTRUI rifiutato, L_MIO ammesso
--    8) UPDATE di un'altra colonna: il guard non giudica (F-2.4, la WHEN)
--   La lettura per il form (F-2.3)
--    9) propone L_MIO, non L_ALTRA_U ne' L_ALTRUI; con l'emittente NULL niente
--   Il push (F-2.5)
--   10) offerta → contratto: il contratto porta il listino dell'offerta, coerente
--   La forma
--   11) i quattro trigger: INSERT senza WHEN, UPDATE con la WHEN sulle tre colonne,
--       dopo il default dell'emittente e il guard emittente/cliente
--   12) i due codici a catalogo, DATO_ERRATO
-- ------------------------------------------------------------

BEGIN;

-- Le due aziende si costruiscono PRIMA del contesto (fn_pgtap_crea_mondo_cliente:
-- «una seconda azienda si costruisce coi builder atomici, prima del contesto»).
CREATE TEMP TABLE tmp_dl_mondi AS
SELECT 'MIA'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'ALTRUI' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Due utility che ammettono una tipologia di listino (fn_pgtap_crea_listino la
-- pretende): U1 la prima, U2 un'altra.
CREATE TEMP TABLE tmp_dl_u AS
SELECT (array_agg(u.id ORDER BY u.id))[1] AS u1,
       (array_agg(u.id ORDER BY u.id))[2] AS u2
  FROM config.utilities u
 WHERE EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                WHERE ltu.utility_id = u.id AND ltu.attivo);

-- Il listino di ALTRUI lo crea ALTRUI (il guard emittente_scope di
-- vendite.listini non ne accetta un altro).
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM tmp_dl_mondi WHERE lato = 'ALTRUI'));
END $ctx$;

CREATE TEMP TABLE tmp_dl_l_altrui AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT u1 FROM tmp_dl_u), 'listino documento altrui');

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM tmp_dl_mondi WHERE lato = 'MIA'));
END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

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

-- Il cliente di MIA (a contesto aperto: il trigger z90 lega il BA a chi agisce).
CREATE TEMP TABLE tmp_dl_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('listino documento', (SELECT u1 FROM tmp_dl_u));

CREATE TEMP TABLE tmp_dl_l_mio AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT u1 FROM tmp_dl_u), 'listino documento mio');

CREATE TEMP TABLE tmp_dl_l_altra_u AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT u2 FROM tmp_dl_u), 'listino documento altra utility');

-- Scopo: l'id di un listino del fixture per sigla.
CREATE OR REPLACE FUNCTION pg_temp.lst(p_sigla text)
RETURNS bigint LANGUAGE sql STABLE AS $fx$
    SELECT CASE p_sigla
             WHEN 'MIO'     THEN (SELECT listino_id FROM tmp_dl_l_mio)
             WHEN 'ALTRA_U' THEN (SELECT listino_id FROM tmp_dl_l_altra_u)
             WHEN 'ALTRUI'  THEN (SELECT listino_id FROM tmp_dl_l_altrui)
           END;
$fx$;

-- Scopo: i reason della check, in ordine, «A,B» ('' = nessun motivo).
CREATE OR REPLACE FUNCTION pg_temp.motivi(p_listino bigint, p_utility integer, p_ef bigint)
RETURNS text LANGUAGE sql STABLE AS $fx$
    SELECT coalesce(string_agg(m ->> 'reason', ',' ORDER BY n), '')
      FROM jsonb_array_elements(script.fn_check_listino_documento(p_listino, p_utility, p_ef))
           WITH ORDINALITY AS x(m, n);
$fx$;

-- Scopo: l'INSERT di un'offerta in BOZZA del cliente di MIA col listino dato.
CREATE OR REPLACE FUNCTION pg_temp.offerta(p_sigla text)
RETURNS text LANGUAGE sql STABLE AS $fx$
    SELECT format($$INSERT INTO vendite.offerte_commerciali (
                        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
                        listino_id, validita_dal, stato_doc_offerta_id)
                    VALUES (%s, %s, %s, %s, %s, script.fn_data_operativa(),
                            (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA'))$$,
                  script.fn_pgtap_emittente_operatore(), c.billing_account_id, c.istanza_utility_id,
                  c.utility_id, pg_temp.lst(p_sigla))
      FROM tmp_dl_cli c;
$fx$;

-- Scopo: l'INSERT di un contratto DRAFT del cliente di MIA (listino NULL = negoziato).
CREATE OR REPLACE FUNCTION pg_temp.contratto(p_sigla text, p_numero text)
RETURNS text LANGUAGE sql STABLE AS $fx$
    SELECT format($$INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id,
                        utility_id, stato_doc_contratto_id, emittente_fiscale_id, listino_id)
                    VALUES (%L, %s, %s, %s,
                            (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),
                            %s, %s)$$,
                  p_numero, c.billing_account_id, c.istanza_utility_id, c.utility_id,
                  script.fn_pgtap_emittente_operatore(), coalesce(pg_temp.lst(p_sigla)::text, 'NULL'))
      FROM tmp_dl_cli c;
$fx$;

-- ============================================================
-- 1-2) La check, sui valori
-- ============================================================
SELECT is(pg_temp.motivi(pg_temp.lst('MIO'), (SELECT u1 FROM tmp_dl_u), script.fn_pgtap_emittente_operatore()),
    '',
    '1) listino della utility e dell''emittente del documento: nessun motivo');

SELECT is(
    pg_temp.motivi(pg_temp.lst('ALTRA_U'), (SELECT u1 FROM tmp_dl_u), script.fn_pgtap_emittente_operatore())
    || ' | ' ||
    pg_temp.motivi(pg_temp.lst('ALTRUI'), (SELECT u1 FROM tmp_dl_u), script.fn_pgtap_emittente_operatore())
    || ' | ' ||
    pg_temp.motivi(NULL, (SELECT u1 FROM tmp_dl_u), script.fn_pgtap_emittente_operatore())
    || ' | ' ||
    pg_temp.motivi(pg_temp.lst('MIO'), NULL, NULL),
    'LISTINO_UTILITY_DIVERSA | LISTINO_EMITTENTE_DIVERSO |  | LISTINO_UTILITY_DIVERSA,LISTINO_EMITTENTE_DIVERSO',
    '2) utility diversa; emittente diverso; listino NULL nessun motivo; valori NULL diversi per costruzione');

-- ============================================================
-- 3-8) Il guard
-- ============================================================
-- L'offerta buona resta: serve al push (test 10).
CREATE TEMP TABLE tmp_dl_esiti AS
SELECT pg_temp.canali(pg_temp.offerta('MIO')) AS mio;

SELECT is((SELECT mio FROM tmp_dl_esiti), 'NESSUN ERRORE',
    '3) offerta con un listino della sua utility e del suo emittente: ammessa');

SELECT is(pg_temp.canali(pg_temp.offerta('ALTRA_U')),
    'E_DOC_LISTINO_UTILITY_DIVERSA / listino_id',
    '4) offerta con un listino di un''altra utility: rifiutata col campo listino_id');

SELECT is(pg_temp.canali(pg_temp.offerta('ALTRUI')),
    'E_DOC_LISTINO_EMITTENTE_DIVERSO / listino_id',
    '5) offerta con un listino di un altro emittente: rifiutata col campo listino_id');

CREATE TEMP TABLE tmp_dl_ctr AS
SELECT pg_temp.canali(pg_temp.contratto(NULL, 'PGT-DL-' || substr(md5(clock_timestamp()::text), 1, 8))) AS negoziato;

SELECT is(
    (SELECT negoziato FROM tmp_dl_ctr) || ' | ' ||
    pg_temp.canali(pg_temp.contratto('ALTRA_U', 'PGT-DL-' || substr(md5(clock_timestamp()::text || 'u'), 1, 8))),
    'NESSUN ERRORE | E_DOC_LISTINO_UTILITY_DIVERSA / listino_id',
    '6) contratto senza listino (negoziato puro): ammesso; con un listino di un''altra utility: rifiutato');

-- Il contratto negoziato del test 6 prende un listino.
CREATE OR REPLACE FUNCTION pg_temp.ctr_listino(p_sigla text)
RETURNS text LANGUAGE sql STABLE AS $fx$
    SELECT format($$UPDATE vendite.contratti SET listino_id = %s
                     WHERE billing_account_id = %s AND numero LIKE 'PGT-DL-%%'$$,
                  pg_temp.lst(p_sigla), (SELECT billing_account_id FROM tmp_dl_cli));
$fx$;

SELECT is(
    pg_temp.canali(pg_temp.ctr_listino('ALTRUI')) || ' | ' || pg_temp.canali(pg_temp.ctr_listino('MIO')),
    'E_DOC_LISTINO_EMITTENTE_DIVERSO / listino_id | NESSUN ERRORE',
    '7) UPDATE del listino del contratto: di un altro emittente rifiutato, il suo ammesso');

-- F-2.4: un UPDATE che non tocca listino, utility ne' emittente non passa dal
-- guard. Lo si prova sulla WHEN: con il guard spento per le colonne giudicate,
-- la riga non verrebbe giudicata comunque. Qui basta che un cambio di data passi.
SELECT is(pg_temp.canali(format(
    $$UPDATE vendite.offerte_commerciali SET validita_al = script.fn_data_operativa() + 30
       WHERE billing_account_id = %s AND listino_id = %s$$,
    (SELECT billing_account_id FROM tmp_dl_cli), pg_temp.lst('MIO'))),
    'NESSUN ERRORE',
    '8) UPDATE di un''altra colonna dell''offerta: il guard non scatta');

-- ============================================================
-- 9) La lettura per il form
-- ============================================================
SELECT is(
    (SELECT string_agg(s.sigla || '=' || EXISTS (
                SELECT 1 FROM vendite.fn_listini_selezionabili(
                    (SELECT u1 FROM tmp_dl_u), script.fn_pgtap_emittente_operatore()) f
                 WHERE f.id = pg_temp.lst(s.sigla))::text, ' ' ORDER BY s.sigla)
       FROM (VALUES ('ALTRA_U'), ('ALTRUI'), ('MIO')) AS s(sigla))
    || ' #' || (SELECT count(*) FROM vendite.fn_listini_selezionabili((SELECT u1 FROM tmp_dl_u), NULL)),
    'ALTRA_U=false ALTRUI=false MIO=true #0',
    '9) il form: il listino della utility e dell''emittente sì, gli altri no; emittente NULL nessuno');

-- ============================================================
-- 10) Il push offerta → contratto
-- ============================================================
-- ⚠️ Un altro cliente: il contratto del push non deve incontrare quello sopra.
CREATE TEMP TABLE tmp_dl_cli2 AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('listino documento push', (SELECT u1 FROM tmp_dl_u));

CREATE TEMP TABLE tmp_dl_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGTAP-DL-M') AS id;

CREATE TEMP TABLE tmp_dl_off AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, validita_dal, stato_doc_offerta_id)
    SELECT script.fn_pgtap_emittente_operatore(), c.billing_account_id, c.istanza_utility_id,
           c.utility_id, pg_temp.lst('MIO'), script.fn_data_operativa(),
           (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')
      FROM tmp_dl_cli2 c
    RETURNING id)
SELECT id FROM ins;

INSERT INTO vendite.offerte_commerciali_utilities (offerta_id, istanza_utility_id, utility_id)
SELECT o.id, c.istanza_utility_id, c.utility_id FROM tmp_dl_off o, tmp_dl_cli2 c;

-- Un articolo MERCE senza tipologia: eredita UNA_TANTUM/FISSA (la natura).
INSERT INTO vendite.offerte_commerciali_eccezioni
       (offerta_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa)
VALUES ((SELECT id FROM tmp_dl_off), (SELECT id FROM tmp_dl_art), 'AGGIUNTA', 10, 1);

-- Lo stato dell'offerta dal verbo (la porta rifiuta l'UPDATE diretto): la
-- fixture cammina BOZZA → EMESSA → ACCETTATA e concede da se' emetti_offerta.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', (SELECT id FROM tmp_dl_off), 'ACCETTATA');

CREATE TEMP TABLE tmp_dl_push AS
SELECT vendite.fn_push_offerta_a_contratto((SELECT id FROM tmp_dl_off), NULL::bigint, false) AS contratto_id;

SELECT is(
    (SELECT (c.listino_id = pg_temp.lst('MIO'))::text || '/' || (c.utility_id = o.utility_id)::text
            || '/' || (c.emittente_fiscale_id = o.emittente_fiscale_id)::text
       FROM vendite.contratti c, vendite.offerte_commerciali o
      WHERE c.id = (SELECT contratto_id FROM tmp_dl_push)
        AND o.id = (SELECT id FROM tmp_dl_off)),
    'true/true/true',
    '10) push offerta → contratto: il contratto nasce col listino, la utility e l''emittente dell''offerta');

-- ============================================================
-- 11-12) La forma
-- ============================================================
-- tgtype: bit 2 BEFORE, bit 4 INSERT, bit 16 UPDATE. La WHEN si legge dalla
-- definizione: deve nominare le tre colonne. L'ordine per nome rispetto ai vicini.
SELECT is(
    (SELECT string_agg(
                split_part(t.tgname, '_a10_', 2) || ':'
                || CASE WHEN t.tgtype & 4 = 4 THEN 'I' ELSE '' END
                || CASE WHEN t.tgtype & 16 = 16 THEN 'U' ELSE '' END
                || CASE WHEN t.tgqual IS NULL THEN ''
                        ELSE '(' || (pg_get_triggerdef(t.oid) ~* 'old\.listino_id'
                                     AND pg_get_triggerdef(t.oid) ~* 'old\.utility_id'
                                     AND pg_get_triggerdef(t.oid) ~* 'old\.emittente_fiscale_id')::text || ')' END,
                ' ' ORDER BY c.relname, t.tgname)
       FROM pg_trigger t
       JOIN pg_class c ON c.oid = t.tgrelid
      WHERE t.tgrelid IN ('vendite.contratti'::regclass, 'vendite.offerte_commerciali'::regclass)
        AND NOT t.tgisinternal
        AND t.tgname ~ '_a10_(default_emittente|guard_emittente_ba|guard_listino_documento)'),
    'default_emittente_ins:I guard_emittente_ba_ins_upd:IU guard_listino_documento_ins:I guard_listino_documento_upd:U(true) '
    || 'default_emittente_ins:I guard_emittente_ba_ins_upd:IU guard_listino_documento_ins:I guard_listino_documento_upd:U(true)',
    '11) i trigger: INSERT senza WHEN, UPDATE con la WHEN sulle tre colonne, dopo default emittente e guard emittente/cliente');

SELECT is(
    (SELECT string_agg(ce.codice || '=' || ce.classe, ' ' ORDER BY ce.codice)
       FROM config.codici_errore ce
      WHERE ce.codice IN ('E_DOC_LISTINO_UTILITY_DIVERSA', 'E_DOC_LISTINO_EMITTENTE_DIVERSO')),
    'E_DOC_LISTINO_EMITTENTE_DIVERSO=DATO_ERRATO E_DOC_LISTINO_UTILITY_DIVERSA=DATO_ERRATO',
    '12) i due codici a catalogo, DATO_ERRATO');

SELECT * FROM finish();
ROLLBACK;
