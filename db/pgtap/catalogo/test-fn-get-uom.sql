-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Funzioni: catalogo.fn_get_uom_base, catalogo.fn_get_uom_factor
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. In testa e non in coda apposta:
--   in coda scatterebbero tutti insieme DOPO il cleanup, su righe ormai
--   cancellate. Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(9);

-- =========================================================
-- Fixture: il mondo si COSTRUISCE, non si cerca
-- =========================================================
-- ⛔ Fino al 2026-09-23 questo file pescava `ART_TEST_BASE` e
--   `ART_TEST_FALLBACK` e asseriva fattori scritti a mano (6, 2, 0.25) che
--   dipendevano da righe esistenti SOLO su questa macchina: i due articoli non
--   stanno in nessun changelog (UUID …101 e …102, messi a mano) e in CI
--   `catalogo.unita_misura_conversioni` e' VUOTA. Il file misurava la
--   configurazione di un computer, non le due funzioni.
-- ⭐ Ora la fixture scrive le conversioni con i fattori che il test dichiara:
--   l'asserzione dice «la funzione risponde il fattore che il catalogo
--   dichiara», che e' una proprieta' del prodotto.
-- ⚠️ Le tre UoM devono stare nella STESSA tipologia: le conversioni globali
--   fra tipologie diverse le rifiuta `trgfn_uom_conversioni_guard_tipo`. E la
--   base si sceglie alla nascita dell'articolo (`uom_id` e' loccata), da cui
--   il quinto parametro di `fn_pgtap_crea_articolo` (rev 20260923-01).
-- ⛔ Fino al 2026-11-09 le tre unita' si sceglievano fra quelle esistenti
--   (la prima tipologia con tre unita' attive). Su una macchina che fra due di
--   loro ha gia' una conversione, la fixture non si scrive piu': dal
--   2026-11-09 le conversioni sono una per coppia di unita' nei due versi
--   (ex_unita_misura_conversioni_coppia_no_overlap, brief-db-revisione-catalogo
--   giro 2). Le unita' ora le costruisce il test, nella tipologia MASSA (scelta
--   per codice_interno, bloccato).
CREATE FUNCTION pg_temp.uom(p_codice text)
 RETURNS bigint
 LANGUAGE sql
AS $f$
    INSERT INTO catalogo.unita_misura (codice, descrizione, tipo_uom_id)
    SELECT p_codice, p_codice, t.id
      FROM catalogo.uom_tipi t
     WHERE t.codice_interno = 'MASSA'
    RETURNING id;
$f$;

CREATE TEMP TABLE tmp_uom AS
SELECT pg_temp.uom('PGTU-GU-BASE') AS uom_base_id,
       pg_temp.uom('PGTU-GU-OPER') AS uom_operativa_id,
       pg_temp.uom('PGTU-GU-CONV') AS uom_conv_id;

CREATE TEMP TABLE tmp_seed AS
SELECT
  dbops.fn_pgtap_crea_articolo('PGT-UOM-BASE', true, false, false,
                               (SELECT uom_base_id FROM tmp_uom))     AS art_base_id,
  dbops.fn_pgtap_crea_articolo('PGT-UOM-FALLBACK', true, false, false,
                               (SELECT uom_base_id FROM tmp_uom))     AS art_fallback_id;

-- La mappatura operativa del solo articolo BASE: fattore 6, da oggi.
-- ⚠️ 2026-11-10 (brief-db-revisione-catalogo, giro 2-bis, Q28): una mappatura con
--   giorni passati non si spegne piu' (catalogo.trgfn_uom_guard_storia). I test 8-9
--   la spengono: comincia oggi, cioe' non ha giorni passati.
INSERT INTO catalogo.articoli_uom_operativa
    (articolo_id, uom_id, is_base, factor_to_base, valido_dal, attivo)
SELECT (SELECT art_base_id FROM tmp_seed), uom_operativa_id, false, 6, script.fn_data_operativa(), true
  FROM tmp_uom;

-- Le due conversioni globali, nei due VERSI: la diretta (uom_conv -> base,
-- fattore 2) e quella che la funzione deve leggere ALL'INCONTRARIO
-- (base -> uom_operativa, fattore 4, quindi risposta 0.25).
-- ⚠️ `valido_dal` e' NOT NULL e `validita` e' GENERATED: la prima si scrive,
--   la seconda non si nomina.
INSERT INTO catalogo.unita_misura_conversioni
    (uom_from_id, uom_to_id, fattore, valido_dal, attivo)
SELECT uom_conv_id, uom_base_id, 2, script.fn_data_operativa(), true FROM tmp_uom
UNION ALL
SELECT uom_base_id, uom_operativa_id, 4, script.fn_data_operativa(), true FROM tmp_uom;

-- =========================================================
-- 1-2) fn_get_uom_base risponde la UoM dell'articolo
-- =========================================================
SELECT is(
  catalogo.fn_get_uom_base((SELECT art_base_id FROM tmp_seed)),
  (SELECT uom_base_id FROM tmp_uom),
  'UoM base articolo base'
);

SELECT is(
  catalogo.fn_get_uom_base((SELECT art_fallback_id FROM tmp_seed)),
  (SELECT uom_base_id FROM tmp_uom),
  'UoM base articolo fallback'
);

-- =========================================================
-- 3-7) I quattro rami di fn_get_uom_factor
-- =========================================================
SELECT is(
  catalogo.fn_get_uom_factor((SELECT art_base_id FROM tmp_seed),
                             (SELECT uom_base_id FROM tmp_uom), script.fn_data_operativa()),
  1::numeric,
  'Fattore base = 1'
);

SELECT is(
  catalogo.fn_get_uom_factor((SELECT art_base_id FROM tmp_seed),
                             (SELECT uom_operativa_id FROM tmp_uom), script.fn_data_operativa()),
  6::numeric,
  'Fattore da articoli_uom_operativa'
);

SELECT is(
  catalogo.fn_get_uom_factor((SELECT art_fallback_id FROM tmp_seed),
                             (SELECT uom_conv_id FROM tmp_uom), script.fn_data_operativa()),
  2::numeric,
  'Fallback conversione diretta'
);

-- ⭐ Stessa coppia (articolo fallback, UoM operativa) che per l'articolo BASE
--   vale 6: qui la mappatura operativa non c'e', quindi si legge la
--   conversione globale al contrario. E' la PRECEDENZA fra i due rami, ed e'
--   la ragione per cui i due articoli sono due.
SELECT is(
  catalogo.fn_get_uom_factor((SELECT art_fallback_id FROM tmp_seed),
                             (SELECT uom_operativa_id FROM tmp_uom), script.fn_data_operativa()),
  0.25::numeric,
  'Fallback conversione inversa'
);

SELECT is(
  catalogo.fn_get_uom_factor((SELECT art_fallback_id FROM tmp_seed), 9999, script.fn_data_operativa()),
  NULL,
  'Nessuna conversione trovata: NULL'
);

-- =========================================================
-- 8-9) Il ramo che nessuno guardava: `attivo = false`
-- =========================================================
-- ⭐ Al posto delle due asserzioni che dicevano solo «il seed c'e'» (ora la
--   presenza e' una precondizione COSTRUITA, non una scoperta), si pinna il
--   ramo che la funzione ha sempre avuto e che nessun test percorreva: una
--   mappatura operativa spenta non conta, e si ricade sulla conversione.
SELECT lives_ok($$
    UPDATE catalogo.articoli_uom_operativa
       SET attivo = false
     WHERE articolo_id = (SELECT art_base_id FROM tmp_seed)
$$, 'La mappatura operativa che comincia oggi si puo'' disattivare');

SELECT is(
  catalogo.fn_get_uom_factor((SELECT art_base_id FROM tmp_seed),
                             (SELECT uom_operativa_id FROM tmp_uom), script.fn_data_operativa()),
  0.25::numeric,
  'Mappatura operativa spenta: la funzione ricade sulla conversione globale inversa'
);

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
