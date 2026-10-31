-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- rev 2026-10-28 (brief-modello-documento-vendita §16, giro 12): la versione nasce
--   senza stato (BOZZA) e diventa ATTIVA da dbops.fn_pgtap_porta_a_stato, non da un
--   UPDATE dello stato (la colonna non c'e' piu').
--
-- Test: le righe del contratto escono nell'UdM della RIGA, e portano ordine e
--   uom_operativa_id della riga di contratti_righe — vendite.fn_contratto_righe_preview.
--   Brief: brief-db-liste-righe-documento §9.11 (R-D1, R-D2).
--   changeSet: 20261004-01.
--
-- ⭐ TUTTO COSTRUITO: azienda, cliente, listino, articoli, UdM operative,
--   distinta del bundle, contratto e righe nascono qui. Dal catalogo si leggono
--   solo due unita' di misura del seed (80_data): vale anche su un DB
--   ricostruito da zero, come in CI.
-- ⚠️ Fatto datato (2026-09-30, dev): nessuna AGGIUNTA con un'UdM diversa dalla
--   base. Non e' un argomento: il form lo ammette, e un test che iterasse su
--   cio' che c'e' passerebbe a vuoto. Qui il caso si fabbrica.
--
-- LA FIXTURE — U1 e' l'UdM base di tutti gli articoli, U2 un'UdM operativa:
--   A  dal listino, nessuna eccezione                  -> DA_LISTINO
--   X  AGGIUNTA standalone quotata in U2, ordine 30     -> UdM U2
--   Y  AGGIUNTA a consumo (MANUALE), nessuna quantita', ordine 40
--        -> uom_operativa_id NULL: ricade sulla base U1
--   P  AGGIUNTA bundle in U1, ordine 50, componente K quotato in U2
--
-- Indice test (1..9):
--    1) precondizione: A, X, Y, P
--    2) R-D1: X esce in U2 (id e codice), non nell'UdM dell'articolo
--    3) R-D1: Y senza UdM operativa ricade sulla base dell'articolo
--    4) R-D1: il componente K del bundle esce nella SUA UdM operativa
--    5) R-D2: ordine e uom_operativa_id della riga su X
--    6) R-D2: su Y uom_operativa_id resta NULL (il dato della riga, non il ripiego)
--    7) R-D2: sulle eccezioni del listino (OVERRIDE) ci sono anche loro
--    8) R-D2: sulla riga DA_LISTINO sono vuote
--    9) la firma: 26 colonne, in coda periodicita e generazione_canone (D-7, 20261031-42;
--       prima 24, con ordine e uom_operativa_id in coda)
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo): il builder del
-- mondo lo riapre poi sul suo operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE tmp_cru_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('uom riga contratto');

-- Due UdM del seed: U1 la base, U2 l'operativa.
CREATE TEMP TABLE tmp_cru_uom AS
SELECT (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo ORDER BY u.id LIMIT 1)          AS u1,
       (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo ORDER BY u.id LIMIT 1 OFFSET 1) AS u2;

-- Il listino (prima degli articoli: la sua tipologia serve alla loro nascita).
-- ⚠️ La versione del builder nasce ATTIVA, con una riga d'appoggio sua. La si fa
--    finire nel 2020, e la versione che copre OGGI si costruisce qui: BOZZA,
--    righe, poi ATTIVA dal verbo (come test-contratto-righe-lista-v1).
CREATE TEMP TABLE tmp_cru_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_cru_mondo), 'uom riga contratto',
    '2020-01-01'::date, '2020-12-31'::date);

CREATE TEMP TABLE tmp_cru_ver AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
    SELECT listino_id, 'PGTAP_CRU_V2', '2021-01-01'::date FROM tmp_cru_listino
    RETURNING id
)
SELECT id FROM ins;

-- La struttura si sceglie alla nascita:
--   A, B  nella tipologia del listino (un listino TIPIZZATO accetta solo quella);
--   P     il bundle, composito (K e' il suo componente in distinta);
--   Y     servizio una tantum (vedi le righe, rev 2026-10-07).
CREATE TEMP TABLE tmp_cru_art AS
SELECT v.sigla,
       dbops.fn_pgtap_crea_articolo('PGTAP-CRU-' || v.sigla, true, false, false,
                                    (SELECT u1 FROM tmp_cru_uom),
           p_listino_tipologia_id => CASE WHEN v.sigla IN ('A', 'B') THEN
               (SELECT tipologia_id FROM tmp_cru_listino) END,
           p_is_composito         => v.sigla = 'P',
           p_natura_vendita_id    => CASE WHEN v.sigla = 'Y' THEN
               (SELECT id FROM config.nature_vendita
                 WHERE codice_interno = 'SERVIZIO_UNA_TANTUM') END) AS id
  FROM (VALUES ('A'), ('B'), ('X'), ('Y'), ('P'), ('K')) AS v(sigla);

-- Scopo: id di un articolo della fixture per sigla.
CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
  SELECT id FROM tmp_cru_art WHERE sigla = p_sigla;
$fx$;

-- U2 e' un'UdM operativa di X e del componente K (1 U2 = 6 U1).
INSERT INTO catalogo.articoli_uom_operativa (articolo_id, uom_id, is_base, factor_to_base, attivo, valido_dal)
SELECT a.id, (SELECT u2 FROM tmp_cru_uom), false, 6, true, '2020-01-01'::date
  FROM tmp_cru_art a WHERE a.sigla IN ('X', 'K');

-- Il bundle: P composito, con K come componente in distinta.
INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
VALUES (pg_temp.art('P'), pg_temp.art('K'), 1, '2020-01-01');

-- Il listino: A e B, nella loro UdM base.
INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT (SELECT id FROM tmp_cru_ver), a.id, (SELECT u1 FROM tmp_cru_uom), 100.00
  FROM tmp_cru_art a WHERE a.sigla IN ('A', 'B');

SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', (SELECT id FROM tmp_cru_ver), 'ATTIVA');

-- Il contratto in bozza sul listino.
CREATE TEMP TABLE tmp_cru_contratto AS
WITH ins AS (
    INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
           stato_doc_contratto_id, listino_id, valido_dal, valido_al)
    SELECT 'PGTAP-CRU-' || substr(gen_random_uuid()::text, 1, 8),
           m.billing_account_id, m.istanza_utility_id, m.utility_id,
           (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),
           (SELECT listino_id FROM tmp_cru_listino),
           script.fn_data_operativa(), script.fn_data_operativa() + 365
      FROM tmp_cru_mondo m
    RETURNING id
)
SELECT id FROM ins;

-- Scopo: una riga di contratto, con UdM operativa e ordine scelti dal test.
CREATE OR REPLACE FUNCTION pg_temp.riga(
    p_sigla text, p_tipo text, p_prezzo numeric, p_erogazione text, p_fonte text,
    p_qta numeric, p_uom bigint, p_ordine smallint)
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione, prezzo_unitario,
         tipo_erogazione, fonte_quantita_attesa, qta_operativa, uom_operativa_id, ordine)
  VALUES ((SELECT id FROM tmp_cru_contratto), pg_temp.art(p_sigla),
          p_tipo::vendite.tipo_eccezione_contratto, p_prezzo,
          p_erogazione, p_fonte, p_qta, p_uom, p_ordine)
  RETURNING id;
$fx$;

-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): le righe
--   stanno nel PERIMETRO dell'articolo. B (OVERRIDE, nel listino) eredita l'erogazione
--   dalla tipologia del listino; X e P (MERCE del builder) sono UNA_TANTUM; Y diventa un
--   servizio una tantum a consumo MANUALE (la natura gliela da' il builder, alla nascita):
--   la quantita' la scrive l'operatore, come con le LETTURE che una natura non ammette.
--   Prima erano CANONE/FISSA e CONSUMO/LETTURE, scritte a mano.

-- ⚠️ Rev 2026-10-07 (§D.4 punto 2, 20261007-28/-30): B eredita la combinazione di
--   default della tipologia del listino (quella del builder). La quantita' solo se la
--   fonte ereditata la porta (FISSA): con una fonte a valle resta vuota. Si chiede
--   alla sede unica; l'UdM operativa, soggetto del test, resta U1 in ogni caso.
CREATE TEMP TABLE tmp_cru_righe AS
SELECT 'B' AS sigla, pg_temp.riga('B', 'OVERRIDE', 80.00, NULL, NULL,
                                  (SELECT 1 FROM vendite.fn_articolo_erogazioni(pg_temp.art('B')) e
                                    WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA'),
                                  (SELECT u1 FROM tmp_cru_uom), 20::smallint) AS id
UNION ALL
SELECT 'X', pg_temp.riga('X', 'AGGIUNTA', 40.00, 'UNA_TANTUM', 'FISSA', 2,
                         (SELECT u2 FROM tmp_cru_uom), 30::smallint)
UNION ALL
SELECT 'Y', pg_temp.riga('Y', 'AGGIUNTA', 0.15, 'CONSUMO', 'MANUALE', NULL, NULL, 40::smallint)
UNION ALL
SELECT 'P', pg_temp.riga('P', 'AGGIUNTA', 90.00, 'UNA_TANTUM', 'FISSA', 1,
                         (SELECT u1 FROM tmp_cru_uom), 50::smallint);

-- Il componente K del bundle P, quotato in U2.
INSERT INTO vendite.contratti_righe_componenti (riga_contratto_id, articolo_componente_id,
       componente_id, coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id)
SELECT (SELECT id FROM tmp_cru_righe WHERE sigla = 'P'), ac.id, ac.componente_id,
       1, 1, 5.00, 'MANUALE', (SELECT u2 FROM tmp_cru_uom)
  FROM catalogo.articoli_componenti ac
 WHERE ac.prodotto_id = pg_temp.art('P') AND ac.componente_id = pg_temp.art('K');

CREATE TEMP TABLE tmp_cru_lista AS
SELECT * FROM vendite.fn_contratto_righe_preview((SELECT id FROM tmp_cru_contratto));

-- ============================================================
-- 1..4 — R-D1: l'UdM della riga
-- ============================================================
SELECT is((SELECT string_agg(origine || ':' || r.sigla, ',' ORDER BY r.sigla)
             FROM tmp_cru_lista l JOIN tmp_cru_art r ON r.id = l.articolo_id),
    'DA_LISTINO:A,OVERRIDE:B,AGGIUNTA:P,AGGIUNTA:X,AGGIUNTA:Y',
    '1) precondizione: A dal listino, B forzato, le aggiunte P, X e Y');

SELECT ok(
    (SELECT l.uom_id = (SELECT u2 FROM tmp_cru_uom)
        AND l.uom_codice = (SELECT codice FROM catalogo.unita_misura WHERE id = (SELECT u2 FROM tmp_cru_uom))
       FROM tmp_cru_lista l WHERE l.articolo_id = pg_temp.art('X')),
    '2) X esce nell''UdM della riga (U2), non in quella dell''articolo');

SELECT is(
    (SELECT uom_id FROM tmp_cru_lista WHERE articolo_id = pg_temp.art('Y')),
    (SELECT u1 FROM tmp_cru_uom),
    '3) Y senza UdM operativa ricade sulla base dell''articolo');

SELECT ok(
    (SELECT (c ->> 'uom_id')::bigint = (SELECT u2 FROM tmp_cru_uom)
        AND c ->> 'uom_codice' = (SELECT codice FROM catalogo.unita_misura WHERE id = (SELECT u2 FROM tmp_cru_uom))
       FROM tmp_cru_lista l, jsonb_array_elements(l.componenti) c
      WHERE l.articolo_id = pg_temp.art('P')
        AND (c ->> 'componente_id')::uuid = pg_temp.art('K')),
    '4) il componente K del bundle esce nella SUA UdM operativa (U2)');

-- ============================================================
-- 5..8 — R-D2: ordine e uom_operativa_id della riga
-- ============================================================
SELECT ok(
    (SELECT ordine = 30 AND uom_operativa_id = (SELECT u2 FROM tmp_cru_uom)
       FROM tmp_cru_lista WHERE articolo_id = pg_temp.art('X')),
    '5) X porta ordine e uom_operativa_id della sua riga');

SELECT ok(
    (SELECT ordine = 40 AND uom_operativa_id IS NULL
       FROM tmp_cru_lista WHERE articolo_id = pg_temp.art('Y')),
    '6) Y: uom_operativa_id resta NULL, il dato della riga e non il ripiego');

SELECT ok(
    (SELECT ordine = 20 AND uom_operativa_id = (SELECT u1 FROM tmp_cru_uom)
       FROM tmp_cru_lista WHERE articolo_id = pg_temp.art('B') AND origine = 'OVERRIDE'),
    '7) B (eccezione del listino) porta ordine e uom_operativa_id della sua riga');

SELECT ok(
    (SELECT ordine IS NULL AND uom_operativa_id IS NULL
       FROM tmp_cru_lista WHERE articolo_id = pg_temp.art('A') AND origine = 'DA_LISTINO'),
    '8) A dal listino: nessuna riga di contratto, colonne vuote');

-- ============================================================
-- 9 — la firma
-- ============================================================
-- ⚠️ La posizione si legge dagli argomenti OUT, non da un insieme di nomi.
SELECT is(
    (SELECT array_to_string(p.proargnames[array_length(p.proargnames, 1) - 1:], ',')
            || '/' || (array_length(p.proargnames, 1) - 1)::text
       FROM pg_proc p
      WHERE p.oid = 'vendite.fn_contratto_righe_preview(bigint)'::regprocedure),
    'periodicita,generazione_canone/26',
    '9) 26 colonne, periodicita e generazione_canone in coda (D-7)');

SELECT * FROM finish();
ROLLBACK;
