-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: fn_resolve_prezzo_listino_v2 — logica bundle-prioritario
-- Fix bug 2026-05-13 sera: bundle (listini_righe_componenti) deve
-- avere PRIORITA' su standalone (listini_righe) quando padre_contesto
-- e' fornito. Verifica anche E_LISTINO_VERSIONE_NON_ATTIVA (448).
--
-- ⭐ TUTTO COSTRUITO (rev 2026-10-05, brief-db-erogazione-obbligatoria-righe-fatturate
--   §5.5): azienda, cliente, categoria, listino, articoli, distinta, matrice e
--   contratto nascono qui. Prima il file CERCAVA composito, BA e listino nel
--   database: da zero non trovava niente e i sette test andavano in skip — verde
--   per sottrazione. E la versione restava in BOZZA, che il resolver non legge
--   (fn_listino_versione_in_vigore: ATTIVA o CHIUSA).
--
-- LA FIXTURE — il bundle P con due figli in distinta:
--   F1: solo riga di bundle (75), nessuna riga standalone;
--   F2: riga di bundle (75) E riga standalone (100).
--   Una categoria cliente PROPRIA, mappata sul listino: sulla terna
--   categoria x utility x emittente la matrice ha un'esclusione sulle date, e
--   su dbdev l'azienda di contesto e' vera — la sua riga potrebbe esserci gia'.
--
-- Indice test (1..7):
--   1) Precondizione: la versione costruita e' quella in vigore oggi
--   2) Bundle-only (F1, solo lrc): padre_contesto fornito
--      -> LISTINO_BUNDLE [CORE FIX]
--   3) Versione listino non attiva alla data (matrice OK, versione NO)
--      -> E_LISTINO_VERSIONE_NON_ATTIVA (448)
--   4) Bundle + standalone presenti (F2): padre_contesto -> bundle vince
--      (prezzo bundle=75, standalone=100)
--   5) F2 + padre_contesto fake (nessuna lrc match) -> fallback CATEGORIA
--   6) Ne' bundle ne' standalone (articolo fake, padre_contesto reale)
--      -> E_PREZZO_LISTINO_RIGA_NON_TROVATA
--   7) CONTRATTO_OVERRIDE + padre_contesto -> vince CONTRATTO_OVERRIDE
--
-- ⚠️ 3 e 6 leggono l'esito dal NUCLEO (fn_resolve_prezzo_listino_v2_esito):
--   un throws_ok sul guscio con P0001 e messaggio NULL passerebbe con
--   QUALUNQUE rifiuto, anche quello di una fixture rotta.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- =========================================================
-- FIXTURE
-- =========================================================
CREATE TEMP TABLE tmp_bnd_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('bundle prioritario');

-- La categoria del cliente: propria, senza promo (l'overlay promo non e' il
-- caso del test). Il BA nasce con la prima del seed e la cambia qui, prima
-- del contratto, che ne fotografa la categoria.
CREATE TEMP TABLE tmp_bnd_categoria AS
WITH ins AS (
    INSERT INTO anagrafiche.categorie_clienti (codice, codice_interno, descrizione, partecipa_promo)
    SELECT s.sigla, s.sigla, 'Fixture pgTAP: bundle prioritario', FALSE
      FROM (SELECT 'PGTAP-BND-' || substr(md5(clock_timestamp()::text || random()::text), 1, 12) AS sigla) s
    RETURNING id
)
SELECT id FROM ins;

UPDATE anagrafiche.billing_account
   SET categoria_cliente_id = (SELECT id FROM tmp_bnd_categoria)
 WHERE id = (SELECT billing_account_id FROM tmp_bnd_mondo);

-- ⚠️ La versione del builder nasce ATTIVA, e i componenti di un bundle non si
--    scrivono su una versione ATTIVA. La si fa finire nel 2020, e la versione
--    che copre OGGI si costruisce qui: BOZZA, righe, poi ATTIVA. Finisce a
--    +400 giorni: il test 3 chiede una data dove nessuna versione e' in vigore.
CREATE TEMP TABLE tmp_bnd_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_bnd_mondo), 'bundle prioritario',
    '2020-01-01'::date, '2020-12-31'::date);

CREATE TEMP TABLE tmp_bnd_ver AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, stato)
    SELECT listino_id, 'PGTAP_BND_V2', script.fn_data_operativa(), script.fn_data_operativa() + 400, 'BOZZA' FROM tmp_bnd_listino
    RETURNING id
)
SELECT id FROM ins;

-- Un listino TIPIZZATO accetta solo articoli della sua tipologia: la si
-- sceglie alla nascita. Il bundle: P composito, con F1 e F2 in distinta.
CREATE TEMP TABLE tmp_bnd_art AS
SELECT v.sigla,
       dbops.fn_pgtap_crea_articolo('PGTAP-BND-' || v.sigla, false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM tmp_bnd_listino),
           p_is_composito         => v.composito) AS id
  FROM (VALUES ('P', true), ('F1', false), ('F2', false)) AS v(sigla, composito);

-- Scopo: id di un articolo della fixture per sigla.
CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
  SELECT id FROM tmp_bnd_art WHERE sigla = p_sigla;
$fx$;

-- Scopo: UoM base di un articolo della fixture.
CREATE OR REPLACE FUNCTION pg_temp.uom(p_sigla text)
RETURNS bigint LANGUAGE sql STABLE AS $fx$
  SELECT a.uom_id FROM catalogo.articoli a WHERE a.id = pg_temp.art(p_sigla);
$fx$;

-- La distinta del bundle P.
INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
SELECT pg_temp.art('P'), pg_temp.art(f.sigla), 1, '2020-01-01'
  FROM (VALUES ('F1'), ('F2')) AS f(sigla);

INSERT INTO vendite.listini_righe_componenti (listino_versione_id, articolo_componente_id,
       articolo_padre_id, articolo_figlio_id, prezzo, valido_dal, valido_al)
-- La validita' della riga sta dentro quella della versione (guard coerenza BoM).
SELECT (SELECT id FROM tmp_bnd_ver), ac.id, ac.prodotto_id, ac.componente_id, 75.00,
       script.fn_data_operativa(), script.fn_data_operativa() + 400
  FROM catalogo.articoli_componenti ac
 WHERE ac.prodotto_id = pg_temp.art('P');

-- Solo F2 ha anche la riga standalone: F1 e' il caso «bundle-only».
INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
VALUES ((SELECT id FROM tmp_bnd_ver), pg_temp.art('F2'), pg_temp.uom('F2'), 100.00);

UPDATE vendite.listini_versioni SET stato = 'ATTIVA' WHERE id = (SELECT id FROM tmp_bnd_ver);

-- La matrice categoria -> listino (valido_al NULL = aperta): e' lo stadio
-- CATEGORIA, quello che i test 2..6 attraversano (nessun contratto ancora).
INSERT INTO anagrafiche.categorie_clienti_listini (
    categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
    classe_utenza_id, listino_id, valido_dal)
SELECT (SELECT id FROM tmp_bnd_categoria), m.utility_id, m.emittente_soggetto_ruolo_id,
       NULL, (SELECT listino_id FROM tmp_bnd_listino), script.fn_data_operativa()
  FROM tmp_bnd_mondo m;

-- Scopo: la chiamata al GUSCIO del resolver sul mondo della fixture.
CREATE OR REPLACE FUNCTION pg_temp.risolvi(p_articolo uuid, p_uom bigint, p_data date, p_padre uuid)
RETURNS TABLE(origine text, prezzo_finale numeric) LANGUAGE sql AS $fx$
  SELECT r.origine::text, r.prezzo_finale
    FROM tmp_bnd_mondo m,
         vendite.fn_resolve_prezzo_listino_v2(
             p_articolo, p_uom, p_data, m.billing_account_id, m.utility_id,
             m.emittente_soggetto_ruolo_id, NULL, p_padre) r;
$fx$;

-- Scopo: l'esito del NUCLEO, per i casi di rifiuto (codice esatto, niente log).
CREATE OR REPLACE FUNCTION pg_temp.esito(p_articolo uuid, p_uom bigint, p_data date, p_padre uuid)
RETURNS text LANGUAGE sql AS $fx$
  SELECT r.esito_codice
    FROM tmp_bnd_mondo m,
         vendite.fn_resolve_prezzo_listino_v2_esito(
             p_articolo, p_uom, p_data, m.billing_account_id, m.utility_id,
             m.emittente_soggetto_ruolo_id, NULL, p_padre) r;
$fx$;

-- =========================================================
-- 1) Precondizione: i test sotto leggono la versione costruita
-- =========================================================
SELECT is(
    vendite.fn_listino_versione_in_vigore((SELECT listino_id FROM tmp_bnd_listino), script.fn_data_operativa()),
    (SELECT id FROM tmp_bnd_ver),
    '1) Precondizione: la versione costruita (bundle + standalone) e'' quella in vigore oggi');

-- =========================================================
-- 2) Bundle-only: F1 ha solo la lrc, nessuna listini_righe
--    padre_contesto fornito -> LISTINO_BUNDLE [CORE FIX]
-- =========================================================
SELECT is(
    (SELECT origine FROM pg_temp.risolvi(pg_temp.art('F1'), pg_temp.uom('F1'), script.fn_data_operativa(), pg_temp.art('P'))),
    'LISTINO_BUNDLE',
    '2) Bundle-only + padre_contesto -> LISTINO_BUNDLE (core fix bug bi-layer)');

-- =========================================================
-- 3) Versione non attiva alla data script.fn_data_operativa()+500
--    La versione copre solo script.fn_data_operativa()..script.fn_data_operativa()+400.
--    La matrice e' aperta (valido_al NULL) -> matrice trovata.
--    -> E_LISTINO_VERSIONE_NON_ATTIVA (448)
-- =========================================================
SELECT is(
    pg_temp.esito(pg_temp.art('F1'), pg_temp.uom('F1'), script.fn_data_operativa() + 500, pg_temp.art('P')),
    'E_LISTINO_VERSIONE_NON_ATTIVA',
    '3) Versione non attiva alla data -> E_LISTINO_VERSIONE_NON_ATTIVA');

-- =========================================================
-- 4) Bundle + standalone presenti (F2): padre_contesto -> bundle vince
--    (prezzo bundle=75, standalone=100)
-- =========================================================
SELECT is(
    (SELECT prezzo_finale FROM pg_temp.risolvi(pg_temp.art('F2'), pg_temp.uom('F2'), script.fn_data_operativa(), pg_temp.art('P'))),
    75.00::numeric,
    '4) Bundle + standalone: padre_contesto -> bundle vince (prezzo=75 non 100)');

-- =========================================================
-- 5) F2 + padre_contesto fake: nessuna lrc per il padre fake
--    -> fallback CATEGORIA, prezzo=100
-- =========================================================
SELECT is(
    (SELECT origine FROM pg_temp.risolvi(pg_temp.art('F2'), pg_temp.uom('F2'), script.fn_data_operativa(),
                                          '00000000-0000-0000-0000-000000000099'::uuid)),
    'CATEGORIA',
    '5) padre_contesto fake (nessuna lrc) + standalone presente -> CATEGORIA');

-- =========================================================
-- 6) Ne' bundle ne' standalone: articolo UUID fake
--    padre_contesto = reale -> bundle tentato ma non trovato
--    standalone non trovato (articolo fake non ha righe)
--    -> E_PREZZO_LISTINO_RIGA_NON_TROVATA
-- =========================================================
SELECT is(
    pg_temp.esito('00000000-0000-0000-0000-000000000098'::uuid, pg_temp.uom('F2'), script.fn_data_operativa(),
                  pg_temp.art('P')),
    'E_PREZZO_LISTINO_RIGA_NON_TROVATA',
    '6) Articolo fake + padre_contesto reale: ne'' bundle ne'' standalone -> E_PREZZO_LISTINO_RIGA_NON_TROVATA');

-- =========================================================
-- Setup test 7: contratto con OVERRIDE prezzo=999 su F2
--   La strada di un contratto vero: in DRAFT con la riga, poi ATTIVO (il
--   rifiuto «fuori bozza» non ammette righe nuove su un contratto attivo).
-- =========================================================
CREATE TEMP TABLE tmp_bnd_contratto AS
WITH ins AS (
    INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
           stato_doc_contratto_id, listino_id, valido_dal, valido_al)
    SELECT 'PGTAP-BND-' || substr(gen_random_uuid()::text, 1, 8),
           m.billing_account_id, m.istanza_utility_id, m.utility_id,
           (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),
           (SELECT listino_id FROM tmp_bnd_listino),
           script.fn_data_operativa(), script.fn_data_operativa() + 365
      FROM tmp_bnd_mondo m
    RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione, prezzo_unitario,
       tipo_erogazione, fonte_quantita_attesa, quantita, qta_operativa, uom_operativa_id)
-- rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): erogazione e
--   fonte VUOTE, la riga le eredita dalla tipologia del listino (era CANONE/FISSA, fuori
--   dal perimetro di un articolo del listino del test).
-- rev 2026-10-07 (§D.4 punto 2, 20261007-28/-30): la quantita' solo se la fonte
--   ereditata la porta (FISSA); con una fonte a valle resta vuota. Si chiede alla sede
--   unica: il soggetto del test e' il prezzo forzato, non la quantita'.
SELECT (SELECT id FROM tmp_bnd_contratto), pg_temp.art('F2'), 'OVERRIDE', 999.00,
       NULL, NULL, q.qta, q.qta, pg_temp.uom('F2')
  FROM (SELECT (SELECT 1 FROM vendite.fn_articolo_erogazioni(pg_temp.art('F2')) e
                 WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA') AS qta) q;

UPDATE vendite.contratti
   SET stato_doc_contratto_id = (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO')
 WHERE id = (SELECT id FROM tmp_bnd_contratto);

-- =========================================================
-- 7) CONTRATTO_OVERRIDE + padre_contesto: override batte bundle
--    STADIO 1a (CONTRATTO_OVERRIDE) precede bundle -> prezzo=999.
-- =========================================================
SELECT is(
    (SELECT origine || ' a 999: ' || (prezzo_finale = 999.00)
       FROM pg_temp.risolvi(pg_temp.art('F2'), pg_temp.uom('F2'), script.fn_data_operativa(), pg_temp.art('P'))),
    'CONTRATTO_OVERRIDE a 999: true',
    '7) CONTRATTO_OVERRIDE + padre_contesto -> vince override a 999 (bundle ignorato)');

SELECT * FROM finish();
ROLLBACK;
