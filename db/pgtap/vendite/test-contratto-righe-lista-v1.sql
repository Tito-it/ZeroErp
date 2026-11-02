-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- rev 2026-10-29 (brief-db-contratto-righe-periodiche-in-commessa §6.10, G-0-ter; 20261029-39): la riga
--   di listino ha anche l'azione ADERISCI (test 3).
-- rev 2026-10-28 (brief-modello-documento-vendita §16, giro 12): la versione nasce
--   senza stato (BOZZA) e diventa ATTIVA da dbops.fn_pgtap_porta_a_stato, non da un
--   UPDATE dello stato (la colonna non c'e' piu').
--
-- Test: le righe del contratto come LISTA — vendite.fn_contratto_righe_preview
--   con chiave di riga, azioni per origine e «Escludi» spento col motivo; la
--   check script.fn_check_esclusione_articolo_documento e il guard che la chiama
--   (rev 2026-10-04, brief-db-righe-esclusione-solo-non-si-vende: check e guard
--   generici per contratto e offerta; la lista e' l'involucro di
--   vendite.fn_documento_righe_preview; le esclusioni nascono vuote).
--   Brief: brief-db-liste-righe-documento §8.4 (D-8.4), §8.13.
--   changeSet: 20260928-29 (check), -31 (guard), -32 (anteprima).
--
-- ⭐ TUTTO COSTRUITO: azienda, cliente, listino, articoli, distinta del bundle,
--   contratto e righe nascono qui (builder dbops.fn_pgtap_crea_*). Nessuna riga
--   letta dal database: vale anche su un DB ricostruito da zero, come in CI.
--
-- LA FIXTURE — un listino con quattro articoli standalone e un bundle:
--   A  dal listino, nessuna eccezione          -> DA_LISTINO
--   B  dal listino, prezzo forzato             -> OVERRIDE
--   C  dal listino, escluso                    -> ESCLUSIONE
--   F  dal listino E componente del bundle P   -> DA_LISTINO, «Escludi» SPENTO
--   P  il bundle (composito, figlio F)          -> DA_LISTINO dal core
--   X  fuori listino, aggiunto                  -> AGGIUNTA
--
-- ⛔ COSA PRESIDIA:
--   · la chiave che il frontend inventava ora la da' il DB, ed e' unica;
--   · la mappa origine -> azioni, che stava nel drawer;
--   · ⭐ «Escludi» spento sulla riga di F con lo STESSO motivo con cui il guard
--     rifiuterebbe: e il guard non contiene piu' il predicato (§12.5.2).
--
-- Indice test (1..12):
--    1) precondizione: l'anteprima restituisce le sei righe della fixture
--    2) ogni riga ha una chiave, e sono tutte diverse
--    3) A: chiave L:<articolo>:<uom>, azioni sovrascrivi/escludi, nessun blocco
--    4) B (OVERRIDE): modifica / ripristina il listino
--    5) C (ESCLUSIONE): il solo ripristina l'articolo (rev 2026-10-04)
--    6) X (AGGIUNTA): chiave A:<id della riga>, modifica / rimuovi
--    7) ⭐ F: «Escludi» spento con FIGLIO_DI_BUNDLE
--    8) la check su F: codice a catalogo, reason, reason_key
--    9) la check su A: nessun motivo
--   10) il guard rifiuta l'esclusione di F
--   11) il guard lascia passare l'esclusione di A
--   12) il guard non contiene piu' il predicato: chiama la check
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo): il builder del
-- mondo lo riapre poi sul suo operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- FIXTURE
-- ============================================================
-- Il mondo apre anche il contesto applicativo (azienda + operatore).
CREATE TEMP TABLE tmp_crl_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('righe contratto');

-- ⚠️ La versione del builder nasce ATTIVA, e i componenti di un bundle non si
--    scrivono su una versione ATTIVA (guard di immutabilita'). La si fa finire
--    nel 2020, e la versione che copre OGGI si costruisce qui: BOZZA, righe,
--    poi ATTIVA — la strada di un listino vero.
CREATE TEMP TABLE tmp_crl_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_crl_mondo), 'righe contratto',
    '2020-01-01'::date, '2020-12-31'::date);

CREATE TEMP TABLE tmp_crl_ver AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
    SELECT listino_id, 'PGTAP_CRL_V2', '2021-01-01'::date FROM tmp_crl_listino
    RETURNING id
)
SELECT id FROM ins;

-- Un listino TIPIZZATO accetta solo articoli della sua tipologia: nascono in quella;
-- il bundle P nasce composito.
CREATE TEMP TABLE tmp_crl_art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGTAP-CRL-' || v.sigla,
           p_listino_tipologia_id => (SELECT tipologia_id FROM tmp_crl_listino),
           p_is_composito         => v.sigla = 'P') AS id
  FROM (VALUES ('A'), ('B'), ('C'), ('F'), ('P'), ('X')) AS v(sigla);

-- Scopo: id di un articolo della fixture per sigla.
CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
  SELECT id FROM tmp_crl_art WHERE sigla = p_sigla;
$fx$;

-- Il bundle: P composito, con F come componente in distinta.
INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
VALUES (pg_temp.art('P'), pg_temp.art('F'), 1, '2020-01-01');

-- Le righe del listino: A, B, C, F standalone, ciascuno nella sua UoM.
INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT (SELECT id FROM tmp_crl_ver), a.id, ar.uom_id, 100.00
  FROM tmp_crl_art a JOIN catalogo.articoli ar ON ar.id = a.id
 WHERE a.sigla IN ('A', 'B', 'C', 'F');

-- Il bundle P nel listino, col suo componente F.
INSERT INTO vendite.listini_righe_componenti (listino_versione_id, articolo_componente_id,
       articolo_padre_id, articolo_figlio_id, prezzo, valido_dal)
SELECT (SELECT id FROM tmp_crl_ver), ac.id,
       pg_temp.art('P'), pg_temp.art('F'), 50.00, '2021-01-01'
  FROM catalogo.articoli_componenti ac
 WHERE ac.prodotto_id = pg_temp.art('P') AND ac.componente_id = pg_temp.art('F');

SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', (SELECT id FROM tmp_crl_ver), 'ATTIVA');

-- Il contratto in bozza sul listino (versione operativa: la ATTIVA di oggi).
CREATE TEMP TABLE tmp_crl_contratto AS
WITH ins AS (
    INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
           stato_doc_contratto_id, listino_id, valido_dal, valido_al)
    SELECT 'PGTAP-CRL-' || substr(gen_random_uuid()::text, 1, 8),
           m.billing_account_id, m.istanza_utility_id, m.utility_id,
           (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),
           (SELECT listino_id FROM tmp_crl_listino),
           script.fn_data_operativa(), script.fn_data_operativa() + 365
      FROM tmp_crl_mondo m
    RETURNING id
)
SELECT id FROM ins;

-- Scopo: la fonte che la riga eredita dall'articolo (la combinazione di default).
CREATE OR REPLACE FUNCTION pg_temp.fonte_default(p_articolo uuid)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT e.fonte_quantita_attesa::text FROM vendite.fn_articolo_erogazioni(p_articolo) e WHERE e.e_default;
$fx$;

-- Scopo: una riga di contratto (eccezione) sull'articolo della sigla.
CREATE OR REPLACE FUNCTION pg_temp.riga(p_sigla text, p_tipo text, p_prezzo numeric)
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione, prezzo_unitario,
         tipo_erogazione, fonte_quantita_attesa, quantita, qta_operativa, uom_operativa_id)
  SELECT (SELECT id FROM tmp_crl_contratto), a.id, p_tipo::vendite.tipo_eccezione_contratto,
         p_prezzo,
         -- rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende): un'ESCLUSIONE
         -- nasce vuota, senza dati di vendita; le altre righe coi dati di una riga
         -- che si fattura.
         -- rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3):
         -- erogazione e fonte VUOTE, la riga le eredita dall'articolo (la tipologia
         -- del listino del test). Erano CANONE/FISSA scritte a mano, fuori dal
         -- perimetro di un articolo CONSUMO.
         -- rev 2026-10-07 (§D.4 punto 2, 20261007-28/-30): la quantita' solo se la
         -- fonte ereditata la porta (FISSA); con una fonte a valle resta vuota.
         -- Si chiede alla sede unica, perche' la tipologia e' quella del builder.
         NULL,
         NULL,
         CASE WHEN p_tipo <> 'ESCLUSIONE' AND pg_temp.fonte_default(a.id) = 'FISSA' THEN 1 END,
         CASE WHEN p_tipo <> 'ESCLUSIONE' AND pg_temp.fonte_default(a.id) = 'FISSA' THEN 1 END,
         CASE WHEN p_tipo <> 'ESCLUSIONE' THEN a.uom_id END
    FROM catalogo.articoli a WHERE a.id = pg_temp.art(p_sigla)
  RETURNING id;
$fx$;

SELECT pg_temp.riga('B', 'OVERRIDE', 80.00);
SELECT pg_temp.riga('C', 'ESCLUSIONE', NULL);
CREATE TEMP TABLE tmp_crl_x AS SELECT pg_temp.riga('X', 'AGGIUNTA', 40.00) AS id;

CREATE TEMP TABLE tmp_crl_lista AS
SELECT * FROM vendite.fn_contratto_righe_preview((SELECT id FROM tmp_crl_contratto));

-- ============================================================
-- 1..2 — perimetro e chiave
-- ============================================================
SELECT is((SELECT count(*)::integer FROM tmp_crl_lista), 6,
    '1) precondizione: A, B, C, F, il bundle P e l''aggiunta X');

SELECT ok(
    (SELECT count(*) = count(DISTINCT riga_key) AND count(riga_key) = count(*) FROM tmp_crl_lista),
    '2) ogni riga ha una chiave, e sono tutte diverse');

-- ============================================================
-- 3..6 — la mappa origine -> azioni
-- ============================================================
SELECT ok(
    (SELECT riga_key = 'L:' || l.articolo_id::text || ':' || l.uom_id::text
        AND origine = 'DA_LISTINO'
        AND azioni = ARRAY['SOVRASCRIVI_PREZZO', 'ESCLUDI', 'ADERISCI']
        AND escludi_blocco_codice IS NULL
       FROM tmp_crl_lista l WHERE l.articolo_id = pg_temp.art('A')),
    '3) A dal listino: chiave L:<articolo>:<uom>, sovrascrivi/escludi/aderisci, nessun blocco');

SELECT is(
    (SELECT azioni FROM tmp_crl_lista WHERE articolo_id = pg_temp.art('B') AND origine = 'OVERRIDE'),
    ARRAY['MODIFICA', 'RIPRISTINA_LISTINO'],
    '4) B col prezzo forzato: modifica / ripristina il prezzo di listino');

SELECT is(
    (SELECT azioni FROM tmp_crl_lista WHERE articolo_id = pg_temp.art('C') AND origine = 'ESCLUSIONE'),
    -- rev 2026-10-04 (brief-db-contratto-esclusione-non-modificabile, R1): un'esclusione
    -- si crea e si cancella, non si modifica. Il rifiuto dell'UPDATE lo prova
    -- test-contratto-esclusione-non-modificabile-v1.
    ARRAY['RIPRISTINA_ARTICOLO'],
    '5) C escluso: il solo ripristina l''articolo, niente modifica');

SELECT ok(
    (SELECT riga_key = 'A:' || (SELECT id FROM tmp_crl_x)::text
        AND azioni = ARRAY['MODIFICA', 'RIMUOVI']
       FROM tmp_crl_lista WHERE articolo_id = pg_temp.art('X') AND origine = 'AGGIUNTA'),
    '6) X aggiunto: chiave A:<id della riga>, modifica / rimuovi');

-- ============================================================
-- 7..9 — «Escludi» spento, e la check che lo decide
-- ============================================================
-- ⭐ Il caso per cui la check esiste: il pulsante si spegne PRIMA, col motivo.
SELECT is(
    (SELECT escludi_blocco_codice FROM tmp_crl_lista
      WHERE articolo_id = pg_temp.art('F') AND origine = 'DA_LISTINO'),
    'FIGLIO_DI_BUNDLE',
    '7) F e'' un componente del bundle: «Escludi» spento con il motivo');

SELECT ok(
    (SELECT m -> 0 ->> 'codice' = 'E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA'
        AND m -> 0 ->> 'reason' = 'FIGLIO_DI_BUNDLE'
        AND m -> 0 ->> 'reason_key' = 'vendite.contratti.escludi_blocco.figlio_di_bundle'
        AND jsonb_array_length(m) = 1
       FROM (SELECT script.fn_check_esclusione_articolo_documento(
                 'CONTRATTO', (SELECT id FROM tmp_crl_contratto), pg_temp.art('F')) AS m) x),
    '8) la check su F: il codice a catalogo, il reason e la sua chiave');

SELECT is(
    script.fn_check_esclusione_articolo_documento('CONTRATTO', (SELECT id FROM tmp_crl_contratto), pg_temp.art('A')),
    '[]'::jsonb,
    '9) la check su A: nessun motivo');

-- ============================================================
-- 10..12 — il guard, che ora chiama la check
-- ============================================================
-- ⚠️ Sul TESTO del messaggio a catalogo, non su «un errore qualsiasi»: un
--    rifiuto di altra natura (un vincolo, un altro guard) non deve passare per
--    questo. Il testo e' quello di config.messaggi_errore, non il codice.
SELECT throws_like(
    $$SELECT pg_temp.riga('F', 'ESCLUSIONE', NULL)$$,
    '%componente figlio di un bundle%',
    '10) il guard rifiuta l''esclusione di F col messaggio del codice a catalogo');

SELECT lives_ok(
    $$SELECT pg_temp.riga('A', 'ESCLUSIONE', NULL)$$,
    '11) il guard lascia passare l''esclusione di A');

-- ⭐ Il presidio della §12.5.2: non «gli esiti coincidono», ma «la madre non
--    contiene piu' il predicato». Commenti tolti prima di cercare.
-- ⛔ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3b): il
--   guard dedicato (script.trgfn_righe_guard_esclusione_figlio_bundle) e'
--   ritirato; il figlio di bundle e' ora il primo motivo dell'ESCLUSIONE nella
--   check per tipo di riga, script.fn_check_articolo_riga, che lo COMPONE dalla
--   stessa check. Il presidio resta lo stesso, sulla nuova sede.
-- rev 2026-10-14 (Lotto 4, 20261014-02): i motivi della check stanno in
--   script.fn_check_articolo_riga_su_contesto (la firma di sempre la compone
--   col contesto del documento): la sede e' quella.
SELECT ok(
    (SELECT regexp_replace(prosrc, '--[^\n]*', '', 'g') ~ 'fn_check_esclusione_articolo_documento\s*\('
        AND regexp_replace(prosrc, '--[^\n]*', '', 'g') !~ 'listini_righe_componenti'
       FROM pg_proc
      WHERE oid = 'script.fn_check_articolo_riga_su_contesto(jsonb,uuid,bigint)'::regprocedure),
    '12) la check di riga chiama la check dell''esclusione e non contiene il predicato');

SELECT * FROM finish();
ROLLBACK;
