-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture cambia il vocabolario del perimetro (config.nature_vendita_erogazioni), un seed che nessun operatore scrive, per far uscire dal perimetro righe gia' scritte: e' la strada che il modello lascia aperta, e il caso da provare
-- rev 2026-11-01 (20261101-04/-06, brief-db-contratto-righe-periodiche-in-commessa passo 4): la
--   riga a canone vuole la periodicita'. La riga dell'offerta la scrive (MENSILE) quando e' a
--   canone (SERV): non e' il soggetto di questo test. Nessuna attesa cambiata.
-- pgTAP test per Zero ERP
--
-- Test: le righe gia' scritte le intercetta il primo passo che le usa; «Genera
--       ordine» e' un verbo DB; da ACCETTATA si esce anche annullando.
--       Brief: brief-db-offerta-emissione-ed-erogazione §I (decisioni I-D2…I-D5 di
--       Tid del 2026-10-21; H-R1…H-R4 del §H), changeSet 20261021-52 … -61.
-- rev 2026-10-26 (brief-modello-documento-vendita §11): l'attivazione del contratto (22) dal verbo vendite.fn_cambia_stato_contratto, non piu' con l'UPDATE diretto dello stato che la porta ora rifiuta; prima del 21 si concede emetti_contratto, senza la quale la capability nasconde «Attiva». Nessuna attesa cambiata.
-- rev 2026-10-26 (brief-modello-documento-vendita §13, giro 9): lo stato dell'offerta dal verbo — accettazione della fixture con dbops.fn_pgtap_porta_a_stato, emissione (8) con vendite.fn_cambia_stato_offerta, annullo (18, 20) con vendite.fn_annulla_offerta, invece degli UPDATE di stato che la porta ora rifiuta; si concede emetti_offerta, senza la quale la capability nasconde «Emetti» (7) e «Annulla» da ACCETTATA (17, 19). Nessuna attesa cambiata.
--
-- ⭐ Il caso del §H.1, costruito: righe scritte quando erano ammesse, che escono
--   dal perimetro per un dato che sta FUORI dalla riga (qui il vocabolario della
--   natura). I guard di riga non se ne accorgono (scattano solo quando la riga si
--   scrive); l'emissione, il push, l'attivazione e la correzione di un articolo si'.
--
-- ⚠️ Fixture COSTRUITA: cliente e BA da dbops.fn_pgtap_crea_cliente_ba, listino da
--   dbops.fn_pgtap_crea_listino (versione in vigore da oggi con la sola riga
--   d'appoggio della fixture: rev 2026-10-28, una versione si attiva solo con un
--   prezzo; le righe espanse dell'offerta sono quella e le sue eccezioni),
--   articoli senza tipologia:
--     R  SERVIZIO_RICORRENTE   CANONE/FISSA*, CONSUMO/MANUALE (dalla natura)
--     M  MERCE                 UNA_TANTUM/FISSA*, UNA_TANTUM/MANUALE
--   Poi la combinazione CONSUMO/MANUALE esce dal vocabolario della natura
--   SERVIZIO_RICORRENTE: le righe R CONSUMO/MANUALE gia' scritte restano fuori.
-- ⚠️ I codici si leggono dal canale CONSTRAINT dell'eccezione (pg_temp.codice), non
--   dalla frase: la frase la cambia il CSV dei messaggi.
-- ⚠️ I test 24-25 leggono i seed (codici d'errore, transizioni): rossi nella prova
--   pre-apply senza gli effetti dei CSV (si caricano in 80_data), verdi dopo l'apply.
--
-- Indice test (1..25):
--   Struttura
--    1) le quattro check STABLE e il verbo VOLATILE, tutte SECURITY INVOKER
--   La riga intera (script.fn_check_riga_documento_su_contesto)
--    2) offerta, R CONSUMO/MANUALE fuori dal vocabolario: E_RIGA_EROGAZIONE_FUORI_PERIMETRO
--    3) offerta, R CANONE/FISSA: ammessa
--    4) ordine, R: un motivo solo, la natura (nessuna erogazione da giudicare)
--   Le righe di un documento (script.fn_check_righe_documento)
--    5) l'offerta in bozza: un motivo E_DOC_RIGA_NON_AMMESSA, con la riga e il suo motivo
--    6) un documento che non e' offerta ne' contratto: E_DOC_TIPO_NON_GESTITO
--   Emissione (H-R1)
--    7) «Emetti» spento col motivo RIGA_NON_AMMESSA
--    8) …e l'emissione e' rifiutata con E_DOC_RIGA_NON_AMMESSA
--   Push (H-R2)
--    9) «Genera contratto» proposto e spento: can_push_contratto false, reason RIGA_NON_AMMESSA
--   10) …e il push lo ferma il guard di riga del contratto (la rete)
--   Genera ordine (I-D2)
--   11) un servizio: «Genera ordine» spento (RIGA_NON_AMMESSA), «Genera contratto» acceso
--   12) …e il verbo rifiuta con E_DOC_RIGA_NON_AMMESSA prima di scrivere
--   13) la merce: il verbo genera l'ordine DRAFT, con la provenienza e le righe espanse
--   14) …una seconda volta: E_ORD_OFFERTA_GIA_CONVERTITA
--   15) …e il push dopo l'ordine: E_OFFERTA_ORDINE_GIA_GENERATO
--   16) da un'offerta non ACCETTATA: E_ORD_ORIGINE_NON_CONVERTIBILE
--   Annullo da ACCETTATA (H-R3)
--   17) con l'ordine vivo: «Annulla» spento col motivo DOCUMENTI_VIVI
--   18) …e l'annullo e' rifiutato con E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI
--   19) annullato l'ordine, «Annulla» si accende
--   20) …e l'offerta si annulla
--   Attivazione del contratto (H-R4)
--   21) «Attiva» spento col motivo RIGA_NON_AMMESSA
--   22) …e l'attivazione e' rifiutata con E_DOC_RIGA_NON_AMMESSA
--   La correzione di un articolo (il buco del §I.2, punto 3)
--   23) catalogo.fn_articolo_righe_vive_non_ammesse vede la riga fuori perimetro d'erogazione
--   I seed
--   24) i due codici nuovi a catalogo, con la classe
--   25) la transizione ACCETTATA -> ANNULLATA, manuale, con la motivazione
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga i DEFERRABLE INITIALLY DEFERRED non
--   scatterebbero mai (il file si chiude in ROLLBACK).
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(25);

-- ⚠️ rev 2026-10-26 (giro 9): «Emetti» (da BOZZA) e «Annulla» (da ACCETTATA)
--   sono dell'azione emetti_offerta: senza, la capability li nasconde e il verbo
--   risponde E_PERMESSO_NEGATO. Il test prova i motivi di stato (7, 17, 19), non
--   il permesso: l'azione si concede all'utente del contesto.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_offerta');

-- Scopo: esegue uno statement che deve essere rifiutato e ne rende il codice,
--   dal canale CONSTRAINT dell'eccezione ('NESSUN ERRORE' se passa).
CREATE OR REPLACE FUNCTION pg_temp.codice(p_sql text)
RETURNS text LANGUAGE plpgsql AS $fx$
DECLARE v_cst text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN ERRORE';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME;
        RETURN coalesce(nullif(v_cst, ''), '-');
    END;
END;
$fx$;

-- Scopo: l'azione di una capability per chiave, come jsonb.
CREATE OR REPLACE FUNCTION pg_temp.azione(p_blob jsonb, p_key text)
RETURNS jsonb LANGUAGE sql IMMUTABLE AS $fx$
    SELECT a FROM jsonb_array_elements(p_blob -> 'available_actions') a
     WHERE a ->> 'key' = p_key;
$fx$;

-- ============================================================
-- Fixture COSTRUITA
-- ============================================================
CREATE TEMP TABLE tmp_ra_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'righe ammesse ai passi',
    (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_ra_lis AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_ra_cli), 'righe ammesse ai passi');

CREATE TEMP TABLE tmp_ra_art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGTAP-RA-' || v.sigla,
           p_natura_vendita_id => (SELECT n.id FROM config.nature_vendita n
                                    WHERE n.codice_interno = v.natura)) AS id
  FROM (VALUES ('R', 'SERVIZIO_RICORRENTE'), ('M', 'MERCE')) AS v(sigla, natura);

CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
    SELECT id FROM tmp_ra_art WHERE sigla = p_sigla;
$fx$;

CREATE TEMP TABLE tmp_ra_ctx AS
SELECT c.billing_account_id, c.istanza_utility_id, c.utility_id,
       script.fn_pgtap_emittente_operatore()  AS emittente_fiscale_id,
       (SELECT listino_id FROM tmp_ra_lis)     AS listino_id,
       (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')     AS st_bozza,
       (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')    AS st_emessa,
       (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ACCETTATA') AS st_accettata,
       (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ANNULLATA') AS st_annullata,
       (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT')   AS st_draft,
       (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO')  AS st_attivo
  FROM tmp_ra_cli c;

CREATE TEMP TABLE tmp_ra_doc (slot text PRIMARY KEY, id bigint, riga_id bigint);

-- Scopo: un'offerta in BOZZA sul listino, con un'AGGIUNTA dell'articolo dato.
CREATE OR REPLACE FUNCTION pg_temp.offerta(p_slot text, p_sigla text, p_erog text,
                                           p_fonte text, p_qta numeric)
RETURNS bigint LANGUAGE plpgsql AS $fx$
DECLARE v_id bigint; v_riga bigint;
BEGIN
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, validita_dal, stato_doc_offerta_id)
    SELECT c.emittente_fiscale_id, c.billing_account_id, c.istanza_utility_id, c.utility_id,
           c.listino_id, script.fn_data_operativa(), c.st_bozza
      FROM tmp_ra_ctx c
    RETURNING id INTO v_id;

    INSERT INTO vendite.offerte_commerciali_eccezioni (
        offerta_id, articolo_id, tipo_eccezione, prezzo_unitario,
        qta_operativa, tipo_erogazione, fonte_quantita_attesa, periodicita)
    VALUES (v_id, pg_temp.art(p_sigla), 'AGGIUNTA', 10, p_qta, p_erog, p_fonte,
            CASE WHEN p_erog = 'CANONE' THEN 'MENSILE' END)
    RETURNING id INTO v_riga;

    INSERT INTO tmp_ra_doc VALUES (p_slot, v_id, v_riga);
    RETURN v_id;
END;
$fx$;

CREATE OR REPLACE FUNCTION pg_temp.doc(p_slot text)
RETURNS bigint LANGUAGE sql STABLE AS $fx$
    SELECT id FROM tmp_ra_doc WHERE slot = p_slot;
$fx$;

-- Scopo: porta un'offerta da BOZZA ad ACCETTATA (le righe sono ancora ammesse).
-- rev 2026-10-26 (giro 9): dal verbo, con la fixture della matrice, non piu' con
--   due UPDATE di stato che la porta ora rifiuta.
CREATE OR REPLACE FUNCTION pg_temp.accetta(p_slot text)
RETURNS void LANGUAGE sql AS $fx$
    SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', pg_temp.doc(p_slot), 'ACCETTATA');
$fx$;

-- Le offerte. EM resta in bozza; PUSH, SERV e ORD vanno in ACCETTATA mentre le
-- righe sono ancora ammesse.
SELECT pg_temp.offerta('EM',   'R', 'CONSUMO',    'MANUALE', NULL);
SELECT pg_temp.offerta('PUSH', 'R', 'CONSUMO',    'MANUALE', NULL);
SELECT pg_temp.offerta('SERV', 'R', 'CANONE',     'FISSA',   1);
SELECT pg_temp.offerta('ORD',  'M', 'UNA_TANTUM', 'FISSA',   2);
SELECT pg_temp.accetta('PUSH');
SELECT pg_temp.accetta('SERV');
SELECT pg_temp.accetta('ORD');

-- Il contratto in DRAFT, senza listino, con la stessa riga R CONSUMO/MANUALE.
WITH ins AS (
    INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
           stato_doc_contratto_id, emittente_fiscale_id)
    SELECT 'PGT-RA-' || substr(md5(clock_timestamp()::text), 1, 6),
           c.billing_account_id, c.istanza_utility_id, c.utility_id, c.st_draft,
           c.emittente_fiscale_id
      FROM tmp_ra_ctx c
    RETURNING id)
INSERT INTO tmp_ra_doc (slot, id) SELECT 'CTR', id FROM ins;

WITH ins AS (
    INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione,
           prezzo_unitario, tipo_erogazione, fonte_quantita_attesa)
    VALUES (pg_temp.doc('CTR'), pg_temp.art('R'), 'AGGIUNTA', 10, 'CONSUMO', 'MANUALE')
    RETURNING id)
UPDATE tmp_ra_doc SET riga_id = (SELECT id FROM ins) WHERE slot = 'CTR';

-- ⭐ Il dato che sta FUORI dalla riga: CONSUMO/MANUALE esce dal vocabolario della
--   natura SERVIZIO_RICORRENTE. Le righe R CONSUMO/MANUALE restano scritte.
DELETE FROM config.nature_vendita_erogazioni ne
 USING config.nature_vendita n
 WHERE n.id = ne.natura_vendita_id
   AND n.codice_interno = 'SERVIZIO_RICORRENTE'
   AND ne.tipo_erogazione = 'CONSUMO'
   AND ne.fonte_quantita_attesa = 'MANUALE';

-- ============================================================
-- 1) Struttura
-- ============================================================
SELECT is(
    (SELECT string_agg(p.proname || ':' || p.provolatile::text || ':' || p.prosecdef::text, ' '
                       ORDER BY p.proname)
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE (n.nspname, p.proname) IN (
                ('script', 'fn_check_riga_documento_su_contesto'),
                ('script', 'fn_check_righe_documento'),
                ('script', 'fn_check_righe_offerta_in_ordine'),
                ('script', 'fn_check_offerta_annullabile'),
                ('vendite', 'fn_genera_ordine_da_offerta'))),
    'fn_check_offerta_annullabile:s:false fn_check_riga_documento_su_contesto:s:false '
    'fn_check_righe_documento:s:false fn_check_righe_offerta_in_ordine:s:false '
    'fn_genera_ordine_da_offerta:v:false',
    '1) le quattro check STABLE e il verbo VOLATILE, tutte SECURITY INVOKER');

-- ============================================================
-- 2-4) La riga intera
-- ============================================================
SELECT is(
    script.fn_check_riga_documento_su_contesto(
        script.fn_articolo_riga_contesto('OFFERTA_COMMERCIALE', pg_temp.doc('EM'), 'AGGIUNTA'),
        pg_temp.art('R'), NULL, 'CONSUMO', 'MANUALE') -> 0 ->> 'codice',
    'E_RIGA_EROGAZIONE_FUORI_PERIMETRO',
    '2) offerta, R CONSUMO/MANUALE fuori dal vocabolario: il motivo d''erogazione');

SELECT is(
    script.fn_check_riga_documento_su_contesto(
        script.fn_articolo_riga_contesto('OFFERTA_COMMERCIALE', pg_temp.doc('EM'), 'AGGIUNTA'),
        pg_temp.art('R'), NULL, 'CANONE', 'FISSA'),
    '[]'::jsonb,
    '3) offerta, R CANONE/FISSA: ammessa');

SELECT is(
    (SELECT jsonb_array_length(m) || ' ' || (m -> 0 ->> 'codice')
       FROM (SELECT script.fn_check_riga_documento_su_contesto(
                        script.fn_articolo_riga_contesto('ORDINE_VENDITA', NULL),
                        pg_temp.art('R'), NULL, 'CONSUMO', 'MANUALE') AS m) x),
    '1 E_RIGA_NATURA_NON_AMMESSA',
    '4) ordine, R: un motivo solo, la natura (l''ordine non ha erogazione)');

-- ============================================================
-- 5-6) Le righe di un documento
-- ============================================================
SELECT is(
    (SELECT jsonb_array_length(m) || ' ' || (m -> 0 ->> 'codice') || ' ' || (m -> 0 ->> 'reason')
            || ' ' || ((m -> 0 -> 'dettaglio' ->> 'riga_id')::bigint
                       = (SELECT riga_id FROM tmp_ra_doc WHERE slot = 'EM'))::text
            || ' ' || (m -> 0 -> 'dettaglio' -> 'motivo_riga' ->> 'codice')
            || ' ' || (m -> 0 -> 'valori' ->> 1)
       FROM (SELECT script.fn_check_righe_documento('OFFERTA_COMMERCIALE', pg_temp.doc('EM')) AS m) x),
    '1 E_DOC_RIGA_NON_AMMESSA RIGA_NON_AMMESSA true E_RIGA_EROGAZIONE_FUORI_PERIMETRO PGTAP-RA-R',
    '5) l''offerta in bozza: un motivo, con la riga, il suo motivo e il codice dell''articolo');

SELECT is(
    pg_temp.codice($$SELECT script.fn_check_righe_documento('ORDINE_VENDITA', 1)$$),
    'E_DOC_TIPO_NON_GESTITO',
    '6) un documento che non e'' offerta ne'' contratto: E_DOC_TIPO_NON_GESTITO');

-- ============================================================
-- 7-8) Emissione
-- ============================================================
SELECT ok(
    (SELECT (a ->> 'enabled')::boolean IS FALSE
            AND a -> 'reasons' @> '[{"reason": "RIGA_NON_AMMESSA"}]'::jsonb
       FROM (SELECT a FROM jsonb_array_elements(
                 script.fn_available_actions_offerta(pg_temp.doc('EM')) -> 'available_actions') a
              WHERE a ->> 'target_state' = 'EMESSA') x),
    '7) «Emetti» spento col motivo RIGA_NON_AMMESSA');

-- rev 2026-10-26 (giro 9): l'emissione si chiede al verbo, non con un UPDATE.
SELECT is(
    pg_temp.codice(format(
        $q$SELECT * FROM vendite.fn_cambia_stato_offerta(%s, 'EMESSA', NULL)$q$,
        pg_temp.doc('EM'))),
    'E_DOC_RIGA_NON_AMMESSA',
    '8) …e l''emissione e'' rifiutata con E_DOC_RIGA_NON_AMMESSA');

-- ============================================================
-- 9-10) Push
-- ============================================================
SELECT is(
    (SELECT (b ->> 'can_push_contratto') || ' ' || (b ->> 'can_push_contratto_reason')
            || ' ' || (pg_temp.azione(b, 'push_contratto') ->> 'enabled')
       FROM (SELECT script.fn_available_actions_offerta(pg_temp.doc('PUSH')) AS b) x),
    'false RIGA_NON_AMMESSA false',
    '9) «Genera contratto» proposto e spento: can_push_contratto false, reason RIGA_NON_AMMESSA');

SELECT is(
    pg_temp.codice(format($$SELECT vendite.fn_push_offerta_a_contratto(%s, NULL)$$,
                          pg_temp.doc('PUSH'))),
    'E_RIGA_EROGAZIONE_FUORI_PERIMETRO',
    '10) …e il push lo ferma il guard di riga del contratto (la rete)');

-- ============================================================
-- 11-16) Genera ordine
-- ============================================================
SELECT is(
    (SELECT (b ->> 'can_genera_ordine') || ' ' || (b ->> 'can_genera_ordine_reason')
            || ' ' || (pg_temp.azione(b, 'genera_ordine') ->> 'enabled')
            || ' ' || (b ->> 'can_push_contratto')
       FROM (SELECT script.fn_available_actions_offerta(pg_temp.doc('SERV')) AS b) x),
    'false RIGA_NON_AMMESSA false true',
    '11) un servizio: «Genera ordine» spento (RIGA_NON_AMMESSA), «Genera contratto» acceso');

SELECT is(
    pg_temp.codice(format($$SELECT vendite.fn_genera_ordine_da_offerta(%s)$$, pg_temp.doc('SERV'))),
    'E_DOC_RIGA_NON_AMMESSA',
    '12) …e il verbo rifiuta con E_DOC_RIGA_NON_AMMESSA prima di scrivere');

INSERT INTO tmp_ra_doc (slot, id)
SELECT 'ORDINE', vendite.fn_genera_ordine_da_offerta(pg_temp.doc('ORD'));

SELECT is(
    (SELECT s.codice_interno || ' ' || o.documento_origine_tipo || ' '
            || (o.documento_origine_id = pg_temp.doc('ORD'))::text || ' '
            || (SELECT count(*) || ' ' || max(r.riga_nr) || ' ' || max(r.qta_operativa)::numeric(10,2)
                       || ' ' || max(r.prezzo_unitario)::numeric(10,2)
                  FROM vendite.ordini_righe r
                 WHERE r.ordine_id = o.id AND r.articolo_id = pg_temp.art('M'))
       FROM vendite.ordini o
       JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
      WHERE o.id = pg_temp.doc('ORDINE')),
    -- ⚠️ rev 2026-10-28 (brief-modello-documento-vendita §16): la riga della
    --   merce e' la 2, perche' la 1 e' la riga d'appoggio del listino della
    --   fixture, espansa nell'ordine (una versione in vigore ha un prezzo).
    'DRAFT OFFERTA_COMMERCIALE true 1 2 2.00 10.00',
    '13) la merce: l''ordine DRAFT, con la provenienza e la riga espansa al prezzo negoziato');

SELECT is(
    pg_temp.codice(format($$SELECT vendite.fn_genera_ordine_da_offerta(%s)$$, pg_temp.doc('ORD'))),
    'E_ORD_OFFERTA_GIA_CONVERTITA',
    '14) …una seconda volta: E_ORD_OFFERTA_GIA_CONVERTITA');

SELECT is(
    pg_temp.codice(format($$SELECT vendite.fn_push_offerta_a_contratto(%s, NULL)$$,
                          pg_temp.doc('ORD'))),
    'E_OFFERTA_ORDINE_GIA_GENERATO',
    '15) …e il push dopo l''ordine: E_OFFERTA_ORDINE_GIA_GENERATO');

SELECT is(
    pg_temp.codice(format($$SELECT vendite.fn_genera_ordine_da_offerta(%s)$$, pg_temp.doc('EM'))),
    'E_ORD_ORIGINE_NON_CONVERTIBILE',
    '16) da un''offerta non ACCETTATA: E_ORD_ORIGINE_NON_CONVERTIBILE');

-- ============================================================
-- 17-20) Annullo da ACCETTATA
-- ============================================================
SELECT is(
    (SELECT (a ->> 'enabled') || ' ' || (a ->> 'reason') || ' ' || (a ->> 'requires_motivazione')
       FROM (SELECT a FROM jsonb_array_elements(
                 script.fn_available_actions_offerta(pg_temp.doc('ORD')) -> 'available_actions') a
              WHERE a ->> 'target_state' = 'ANNULLATA') x),
    'false DOCUMENTI_VIVI true',
    '17) con l''ordine vivo: «Annulla» proposto e spento col motivo DOCUMENTI_VIVI');

-- rev 2026-10-26 (giro 9): l'annullo dal verbo vendite.fn_annulla_offerta, con
--   la motivazione (nessun legame: l'offerta non e' una revisione).
SELECT is(
    pg_temp.codice(format(
        $q$SELECT vendite.fn_annulla_offerta(%s, 'pgtap', NULL)$q$, pg_temp.doc('ORD'))),
    'E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI',
    '18) …e l''annullo e'' rifiutato con E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI');

-- L'ordine nato dall'offerta ha UN legame, l'offerta stessa (lineage): l'annullo
-- lo conferma (brief-db-annullo-documento-con-legami). Ritirato, l'offerta torna
-- trasformabile e annullabile.
SELECT vendite.fn_annulla_ordine(pg_temp.doc('ORDINE'), 1);

SELECT is(
    (SELECT a ->> 'enabled'
       FROM (SELECT a FROM jsonb_array_elements(
                 script.fn_available_actions_offerta(pg_temp.doc('ORD')) -> 'available_actions') a
              WHERE a ->> 'target_state' = 'ANNULLATA') x),
    'true',
    '19) annullato l''ordine, «Annulla» si accende');

SELECT is(
    pg_temp.codice(format(
        $q$SELECT vendite.fn_annulla_offerta(%s, 'pgtap', NULL)$q$, pg_temp.doc('ORD'))),
    'NESSUN ERRORE',
    '20) …e l''offerta si annulla');

-- ============================================================
-- 21-22) Attivazione del contratto
-- ============================================================
-- ⚠️ «Attiva» e' dell'azione emetti_contratto: senza, la capability lo
--   nasconde e il verbo risponde E_PERMESSO_NEGATO (giro 8).
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_contratto');

SELECT ok(
    (SELECT (a ->> 'enabled')::boolean IS FALSE
            AND a -> 'reasons' @> '[{"reason": "RIGA_NON_AMMESSA"}]'::jsonb
       FROM (SELECT a FROM jsonb_array_elements(
                 script.fn_available_actions_contratto(pg_temp.doc('CTR')) -> 'available_actions') a
              WHERE a ->> 'target_state' = 'ATTIVO') x),
    '21) «Attiva» spento col motivo RIGA_NON_AMMESSA');

SELECT is(
    pg_temp.codice(format(
        $q$SELECT * FROM vendite.fn_cambia_stato_contratto(%s, 'ATTIVO')$q$, pg_temp.doc('CTR'))),
    'E_DOC_RIGA_NON_AMMESSA',
    '22) …e l''attivazione e'' rifiutata con E_DOC_RIGA_NON_AMMESSA');

-- ============================================================
-- 23) La correzione di un articolo
-- ============================================================
SELECT is(
    (SELECT v.motivo ->> 'codice'
       FROM catalogo.fn_articolo_righe_vive_non_ammesse(pg_temp.art('R')) v
      WHERE v.documento = 'OFFERTA_COMMERCIALE'
        AND v.riga_id = (SELECT riga_id FROM tmp_ra_doc WHERE slot = 'EM')),
    'E_RIGA_EROGAZIONE_FUORI_PERIMETRO',
    '23) catalogo.fn_articolo_righe_vive_non_ammesse vede la riga fuori perimetro d''erogazione');

-- ============================================================
-- 24-25) I seed
-- ============================================================
SELECT is(
    (SELECT string_agg(ce.codice || '=' || ce.classe, ' ' ORDER BY ce.codice)
       FROM config.codici_errore ce
      WHERE ce.codice IN ('E_DOC_RIGA_NON_AMMESSA', 'E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI')),
    'E_DOC_RIGA_NON_AMMESSA=DATO_ERRATO E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI=CONFLITTO_STATO',
    '24) i due codici nuovi a catalogo, con la classe');

SELECT is(
    (SELECT (t.meta ->> 'action_key') || ' ' || (t.meta ->> 'manuale')
            || ' ' || (t.meta ->> 'requires_motivazione')
       FROM config.stati_doc_offerte_transizioni t
      WHERE t.stato_da_id = (SELECT st_accettata FROM tmp_ra_ctx)
        AND t.stato_a_id  = (SELECT st_annullata FROM tmp_ra_ctx)
        AND t.attivo),
    'annulla true true',
    '25) la transizione ACCETTATA -> ANNULLATA, manuale, con la motivazione');

SELECT * FROM finish();
ROLLBACK;
