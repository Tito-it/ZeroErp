-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: emissione mirata per GRUPPO FATTURABILE
--       (chiave, persistenza del criterio, filtri su pull e select)
-- Brief: brief-db-emissione-fattura-per-documento-sorgente PARTE A (step A10)
-- Changeset coperti: 20260727-10..15
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima il
--   preventivo nasceva gia' ACCETTATO).
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): il mondo si
--   COSTRUISCE (azienda col suo operatore, contesto su di lui, cliente, articolo
--   servizio) invece di pescare «il primo BA / articolo / emittente per id»; il
--   contratto del gruppo C nasce DRAFT da dbops.fn_pgtap_crea_contratto.
--   L'articolo-onere resta del catalogo seminato (uno per causale, UNIQUE): si
--   legge per la causale SPESE_TRASFERTA, non «il primo per id».
-- rev 2026-10-24 (brief-modello-documento-vendita R-2/R-9): azienda,
--   operatore, contesto e cliente nascono da dbops.fn_pgtap_crea_mondo_cliente;
--   il contratto del gruppo C nasce DRAFT col periodo 2080 dal builder.
-- rev 2026-10-24 (brief-modello-documento-vendita §4-octies): le 4 righe
--   documentali le scrive dbops.fn_pgtap_crea_commessa_attivita con la
--   sorgente (chiave dal dominio, script.fn_segment_key) invece della madre
--   chiamata a mano con la chiave inventata SEG-GR-*.
-- ------------------------------------------------------------
-- Indice test (1..17):
--  1) fn_build_gruppo_fatturabile_key: forma documento '<codice_interno>:<uid>'
--  2) fn_build_gruppo_fatturabile_key: forma oneri 'MAN:<commessa_id>'
--  3) guard: sorgente_tipo_id <= 0 -> errore (no normalizzazione silenziosa)
--  4) G1: fn_emit SENZA p_gruppi emette tutte e 5 le righe (non-regressione)
--  5) G2: fn_emit con il gruppo del preventivo -> solo le sue 2 righe
--  6) G13: le righe degli altri gruppi restano stato_emissione='NON_EMESSA'
--  7) G3: nessuna AF creata per contratto e oneri
--  8) G4: fn_emit con il gruppo MAN -> solo la riga ONERE
--  9) G5: fn_emit con DUE gruppi -> tutte e sole le loro righe
-- 10) G6: chiave inesistente -> zero righe, nessun errore
-- 11) G12 ⭐ fn_select con p_gruppi NON consuma le AF residue di altri gruppi
-- 12) G1: fn_select SENZA p_gruppi le vede tutte (non-regressione)
-- 13) fn_list_emittibili_lane con p_gruppi -> solo le terne dei gruppi
-- 14) fn_list_commesse_emittibili con p_gruppi -> solo le commesse coinvolte
-- 15) G7: due emissioni mirate successive con gruppi diversi -> entrambe ok
-- 16) fatturazione_lotti_gruppi: UNIQUE respinge il duplicato
-- 17) G1/G11: lotto senza righe di perimetro = nessuna restrizione
-- ------------------------------------------------------------
-- ⭐ IL TEST 11 E' IL PIU' IMPORTANTE DEL FILE. E' l'unico che copre la falla
--    F8: fn_select_attivita_fatturabili non ha alcun criterio che sappia della
--    sorgente, quindi senza il filtro un giro mirato rastrellerebbe le AF gia'
--    esistenti di altri gruppi (residui di un giro interrotto, di un reset a
--    bozza o del giro schedulato). E' il test che si romperebbe se qualcuno
--    "semplificasse" filtrando solo il pull.
-- ------------------------------------------------------------
-- FIXTURE: una commessa MULTI-SORGENTE con TRE gruppi, come nel caso d'uso
--    reale del brief (stesso cliente, stesso mese, origini diverse):
--      gruppo P  = preventivo REALE (2 righe)   -> 'PREVENTIVO:<uid>'
--      gruppo C  = contratto     (2 righe)      -> 'CONTRATTO:<uuid>'
--      gruppo M  = onere         (1 riga)       -> 'MAN:<commessa_id>'
--    Il preventivo e' un documento vero perche' serve come ROOT source
--    (fn_emit la pretende) e il guard polimorfo ne verifica l'esistenza.
--    ⛔ rev 2026-10-13: anche il gruppo C e' un contratto VERO (testata in
--    bozza, stesso billing account). Prima bastava un uuid inventato, perche'
--    commesse_attivita non aveva guard polimorfo; dal 20261012-46 la madre
--    fn_upsert_commessa_attivita aggancia il documento alla commessa con
--    fn_link_commessa_sorgente, che ne pretende l'esistenza (E_SORG_*).
--    ⚠️ sorgente_uid porta l'UID anche per CONTRATTO (key_selector='id'): e'
--    la convenzione del push, decisione D-9 (il link lo traduce in id).
--    Vedi guida sorgente-polimorfa §4a.
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
-- ⭐ rev 2026-10-24 (Q-4): l'azienda e il suo operatore si costruiscono PRIMA
--   del contesto, e il contesto si apre su di lui: il cliente che nasce dopo
--   il trigger z90 lo lega a lei.
-- rev 2026-10-24 (R-9): il mondo del builder fa i tre passi nell'ordine giusto.
CREATE TEMP TABLE tmp_gr_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('gruppi fatturabili');

-- Il contesto l'ha gia' aperto il mondo sul suo operatore: la riga lo rende
-- esplicito (ed e' cio' che legge scripts/guardrail_pgtap_preambolo.py).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_gr_mondo)); END $ctx$;

SELECT plan(17);

CREATE TEMP TABLE tmp_gr_cli AS
SELECT billing_account_id, istanza_utility_id, utility_id FROM tmp_gr_mondo;

-- ============================================================
-- Riferimenti minimi (il mondo costruito sopra, e il catalogo di sistema)
-- ============================================================
CREATE TEMP TABLE tmp_gr_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_gr_cli)       AS billing_account_id,
  (SELECT utility_id FROM tmp_gr_cli)               AS utility_id,
  (SELECT istanza_utility_id FROM tmp_gr_cli)       AS istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGT-GR-SERV', false,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                               WHERE codice_interno = 'SERVIZIO_UNA_TANTUM')) AS articolo_id,
  (SELECT a.id FROM catalogo.articoli a
     JOIN config.causali_onere co ON co.id = a.causale_onere_id
    WHERE co.codice_interno = 'SPESE_TRASFERTA' AND a.attivo IS TRUE) AS articolo_onere_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT emittente_fiscale_id FROM tmp_gr_mondo) AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1) AS stato_prev_accettato_id,
  -- rev 2026-10-24 (§4-octies): il tipo del perimetro e' quello che la
  --   madre da' alle righe del preventivo; si legge dalle righe scritte,
  --   sotto (prima «il primo tipo con un registro», passato a mano).
  NULL::bigint                                      AS tipo_doc_fiscale_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO' LIMIT 1)  AS src_preventivo_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'CONTRATTO' LIMIT 1)   AS src_contratto_id,
  (SELECT s.id FROM config.stati_doc_contratti s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE LIMIT 1)                AS stato_contr_draft_id;

-- Preventivo REALE: serve come ROOT source della commessa.
-- ⚠️ rev 2026-10-24: nasce in bozza (lo stato non si scrive: lo mette il
--   trigger della nascita) e va ad ACCETTATO con dbops.fn_pgtap_porta_a_stato,
--   sotto i guard veri: senza righe non hanno motivi da sollevare.
CREATE TEMP TABLE tmp_gr_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-GRUPPI', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope', 'pgtap_gruppi'), r.emittente_fiscale_id
  FROM tmp_gr_refs r
  RETURNING id, uid)
SELECT * FROM ins;

DO $porta$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_gr_prev), 'ACCETTATO');
END $porta$;

-- Contratto VERO per il gruppo C (rev 2026-10-13): basta la testata in bozza.
--   La madre lo aggancia alla commessa (20261012-46) e il link ne verifica
--   l'esistenza: un uuid inventato non passa piu'.
-- rev 2026-10-24 (Q-2): nasce dal builder, dalla madre di produzione, sul
--   cliente del test.
-- rev 2026-10-24 (R-2): il periodo e la data 2080 li prende dal builder.
CREATE TEMP TABLE tmp_gr_k AS
SELECT * FROM dbops.fn_pgtap_crea_contratto(
                 'gruppi fatturabili', 'DRAFT', (SELECT billing_account_id FROM tmp_gr_refs), NULL,
                 DATE '2080-01-01', DATE '2080-12-31', DATE '2080-01-01');

CREATE TEMP TABLE tmp_gr_contr AS
SELECT k.id, k.uid FROM vendite.contratti k WHERE k.id = (SELECT contratto_id FROM tmp_gr_k);

-- Commessa dedicata (force_new: non riusare commesse di altri test).
CREATE TEMP TABLE tmp_gr_comm AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_gr_refs),
  p_utility_id => (SELECT utility_id FROM tmp_gr_refs),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2080-01-01',
  p_competenza_al => DATE '2080-01-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_gruppi'),
  p_force_new => true
) AS commessa_id;

-- ROOT source: il preventivo reale. fn_link_commessa_sorgente normalizza la
-- chiave secondo key_selector ('uid' per PREVENTIVO -> resta l'uuid).
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_id FROM tmp_gr_comm),
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_gr_refs),
  p_sorgente_uid     => (SELECT uid::text FROM tmp_gr_prev),
  p_meta             => jsonb_build_object('test_scope', 'pgtap_gruppi')
);

-- Le tre chiavi attese, calcolate dalla funzione stessa: il test verifica il
-- comportamento del filtro, non ri-implementa la forma della chiave.
CREATE TEMP TABLE tmp_gr_key AS
SELECT
  vendite.fn_build_gruppo_fatturabile_key(
    (SELECT src_preventivo_id FROM tmp_gr_refs),
    (SELECT uid::text FROM tmp_gr_prev),
    (SELECT commessa_id FROM tmp_gr_comm))                       AS k_prev,
  vendite.fn_build_gruppo_fatturabile_key(
    (SELECT src_contratto_id FROM tmp_gr_refs),
    (SELECT uid::text FROM tmp_gr_contr),
    (SELECT commessa_id FROM tmp_gr_comm))                       AS k_contr,
  vendite.fn_build_gruppo_fatturabile_key(
    NULL, NULL, (SELECT commessa_id FROM tmp_gr_comm))           AS k_man;

-- ------------------------------------------------------------
-- Helper fixture: 4 righe documentali (2 preventivo + 2 contratto)
-- ------------------------------------------------------------
-- rev 2026-10-24 (§4-octies): le scrive il builder, la chiave la compone il
--   dominio (<sorgente>:<uid>:R:<n>). Il numero di riga e' un ordinale del
--   test (le testate non hanno righe): basta a tenere distinte le chiavi.
--   Tipo documento fiscale e valuta non si passano: li deriva la madre
--   (il tipo dalla sorgente, come prima con il NULL del catalogo).
CREATE TEMP TABLE tmp_gr_righe AS
SELECT r.attivita_id, x.g AS gruppo
FROM (
  VALUES ('P', 1), ('P', 2), ('C', 1), ('C', 2)
) AS x(g, n)
CROSS JOIN LATERAL dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id      => (SELECT commessa_id FROM tmp_gr_comm),
    p_prezzo_snapshot  => 100.0000000000,
    p_articolo_id      => (SELECT articolo_id FROM tmp_gr_refs),
    p_sorgente_codice  => CASE WHEN x.g = 'P' THEN 'PREVENTIVO' ELSE 'CONTRATTO' END,
    -- ⚠️ UID anche per CONTRATTO (key_selector='id'): e' la convenzione del
    -- push, cioe' cio' che commesse_attivita contiene davvero (D-9).
    p_sorgente_uid     => CASE WHEN x.g = 'P'
                               THEN (SELECT uid::text FROM tmp_gr_prev)
                               ELSE (SELECT uid::text FROM tmp_gr_contr) END,
    p_sorgente_riga_id => x.n,
    p_quantita         => 1.000000,
    p_competenza_dal   => DATE '2080-01-01',
    p_competenza_al    => DATE '2080-01-31') r;

-- Le righe scritte davvero (niente verde per sottrazione): un controllo,
-- non un test, per non cambiare il piano.
DO $chk$ BEGIN
  IF (SELECT count(*) FROM vendite.commesse_attivita ca
        JOIN tmp_gr_righe t ON t.attivita_id = ca.id
       WHERE ca.stato_approvazione = 'APPROVATA' AND ca.stato_emissione = 'NON_EMESSA'
         AND ca.segment_key LIKE CASE t.gruppo WHEN 'P' THEN 'PREVENTIVO:%:R:_'
                                               ELSE 'CONTRATTO:%:R:_' END) <> 4 THEN
    RAISE EXCEPTION 'fixture: attese 4 righe documentali dal builder';
  END IF;
END $chk$;

-- Il tipo documento fiscale del perimetro: quello delle righe del preventivo
-- (lo deriva la madre dalla sorgente). L'onere e le letture 11, 12 e 16 lo
-- usano: il test prova il filtro per gruppo dentro un perimetro solo.
UPDATE tmp_gr_refs SET tipo_doc_fiscale_id = (
  SELECT DISTINCT ca.tipo_doc_fiscale_id FROM vendite.commesse_attivita ca
    JOIN tmp_gr_righe t ON t.attivita_id = ca.id
   WHERE t.gruppo = 'P');
-- Riga ONERE dalla porta manuale: sourceless per costruzione.
CREATE TEMP TABLE tmp_gr_onere AS
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_gr_comm),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_gr_refs),
  p_articolo_onere_id => (SELECT articolo_onere_id FROM tmp_gr_refs),
  p_importo => 500.00,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_gr_refs),
  p_motivo => 'pgtap gruppi fatturabili',
  p_data_attivita => DATE '2080-01-20'
) AS attivita_id;

-- ============================================================
-- TEST 1-3: la funzione chiave (A1)
-- ============================================================
SELECT is(
  (SELECT k_prev FROM tmp_gr_key),
  'PREVENTIVO:' || (SELECT uid::text FROM tmp_gr_prev),
  '1) chiave documento = <codice_interno>:<uid>'
);

SELECT is(
  (SELECT k_man FROM tmp_gr_key),
  'MAN:' || (SELECT commessa_id::text FROM tmp_gr_comm),
  '2) chiave oneri = MAN:<commessa_id>'
);

SELECT throws_ok(
  $$ SELECT vendite.fn_build_gruppo_fatturabile_key(0, 'x', 1) $$,
  'P0001', NULL,
  '3) guard: sorgente_tipo_id <= 0 -> errore'
);

-- ============================================================
-- TEST 4 (G1): senza criterio, il pull vede tutte e 5 le righe.
--   dry_run: conta senza scrivere, cosi' i test successivi partono puliti.
-- ============================================================
SELECT is(
  (SELECT total_candidate FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
      p_commessa_id => (SELECT commessa_id FROM tmp_gr_comm),
      p_dry_run => true)),
  5,
  '4) G1: senza p_gruppi il pull vede tutte e 5 le righe'
);

-- ============================================================
-- TEST 5-7 (G2, G13, G3): emissione del solo gruppo preventivo.
-- ============================================================
SELECT is(
  (SELECT inserted_rows FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
      p_commessa_id => (SELECT commessa_id FROM tmp_gr_comm),
      p_gruppi => ARRAY[(SELECT k_prev FROM tmp_gr_key)])),
  2,
  '5) G2: chiedendo il preventivo vengono emesse solo le sue 2 righe'
);

SELECT is(
  (SELECT count(*)::int FROM vendite.commesse_attivita ca
    WHERE ca.commessa_id = (SELECT commessa_id FROM tmp_gr_comm)
      AND ca.stato_emissione = 'NON_EMESSA'),
  3,
  '6) G13: le 3 righe non richieste restano NON_EMESSA'
);

SELECT is(
  (SELECT count(*)::int FROM vendite.attivita_fatturabili af
     JOIN vendite.commesse_attivita ca ON ca.id = af.commessa_attivita_id
    WHERE ca.commessa_id = (SELECT commessa_id FROM tmp_gr_comm)
      AND vendite.fn_build_gruppo_fatturabile_key(
            ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id)
          <> (SELECT k_prev FROM tmp_gr_key)),
  0,
  '7) G3: nessuna AF creata per contratto e oneri'
);

-- ============================================================
-- TEST 8 (G4): gli oneri sono raggiungibili dal criterio.
--   E' il caso che giustifica l'esistenza del concetto di "gruppo":
--   sono righe sourceless, senza questa forma sarebbero conteggiate
--   nella card ma non azionabili.
-- ============================================================
SELECT is(
  (SELECT inserted_rows FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
      p_commessa_id => (SELECT commessa_id FROM tmp_gr_comm),
      p_gruppi => ARRAY[(SELECT k_man FROM tmp_gr_key)])),
  1,
  '8) G4: chiedendo gli oneri viene emessa solo la riga ONERE'
);

SELECT is(
  (SELECT af.tipo_movimento FROM vendite.attivita_fatturabili af
     JOIN vendite.commesse_attivita ca ON ca.id = af.commessa_attivita_id
    WHERE ca.id = (SELECT attivita_id FROM tmp_gr_onere)),
  'ONERE'::varchar,
  '9) G5-pre: la riga emessa dal gruppo MAN e'' quella ONERE'
);

-- ============================================================
-- TEST 10 (G6): criterio che non corrisponde a nulla.
-- ============================================================
SELECT is(
  (SELECT total_candidate FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
      p_commessa_id => (SELECT commessa_id FROM tmp_gr_comm),
      p_gruppi => ARRAY['PREVENTIVO:00000000-0000-4000-8000-999999999999'])),
  0,
  '10) G6: chiave inesistente -> zero righe, nessun errore'
);

-- ============================================================
-- TEST 11 ⭐ (G12): IL TEST CHE CONTA.
--   Situazione: esistono AF del gruppo preventivo E del gruppo oneri
--   (emesse ai test 5 e 8), tutte non fatturate e non lockate — cioe'
--   esattamente i "residui" che un giro precedente lascerebbe.
--   Un giro mirato al solo preventivo NON deve toccare quelle degli oneri.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM vendite.fn_select_attivita_fatturabili(
      p_competenza_mese => DATE '2080-01-01',
      p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_gr_refs),
      p_billing_account_id => (SELECT billing_account_id FROM tmp_gr_refs),
      p_gruppi => ARRAY[(SELECT k_prev FROM tmp_gr_key)])),
  2,
  '11) G12: fn_select con p_gruppi ritorna SOLO le 2 AF del preventivo, non i residui degli oneri'
);

-- ============================================================
-- TEST 12 (G1): senza criterio le vede tutte e 3 (2 prev + 1 onere).
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM vendite.fn_select_attivita_fatturabili(
      p_competenza_mese => DATE '2080-01-01',
      p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_gr_refs),
      p_billing_account_id => (SELECT billing_account_id FROM tmp_gr_refs))),
  3,
  '12) G1: fn_select senza p_gruppi vede tutte le AF del perimetro'
);

-- ============================================================
-- TEST 13-14: le due discovery filtrate.
--   ⚠️ Entrambe richiedono che la commessa sia in uno stato EMITTIBILE
--   (stati_commessa.emittibile = true): e' il criterio 1 di entrambe le
--   funzioni, prima ancora dei filtri di perimetro. Senza questa
--   transizione tornerebbero zero righe per il motivo sbagliato, e i
--   test passerebbero/fallirebbero senza dire nulla sul filtro gruppi.
--   La transizione e' ammessa perche' restano righe APPROVATA+NON_EMESSA
--   (le 2 del gruppo contratto).
-- ============================================================
SELECT vendite.fn_cambia_stato_commessa(
  (SELECT commessa_id FROM tmp_gr_comm), 'PRONTA_FATTURAZIONE');

SELECT is(
  (SELECT COALESCE(sum(total_candidate), 0)::int
     FROM vendite.fn_list_emittibili_lane(
       p_competenza_mese => DATE '2080-01-01',
       p_billing_account_id => (SELECT billing_account_id FROM tmp_gr_refs),
       p_gruppi => ARRAY[(SELECT k_contr FROM tmp_gr_key)])),
  2,
  '13) fn_list_emittibili_lane con p_gruppi -> solo le righe del gruppo contratto'
);

-- Confronto FILTRATO vs NON FILTRATO sulla stessa commessa: un test che
-- si limitasse a "gruppo inesistente -> 0" passerebbe anche se il filtro
-- non funzionasse affatto (basterebbe che la commessa non fosse
-- emittibile). Qui si verifica che il filtro DISCRIMINA davvero.
SELECT is(
  ARRAY(
    SELECT COALESCE(sum(x.total_non_emesse), 0)::int FROM (
      SELECT total_non_emesse FROM vendite.fn_list_commesse_emittibili(
        p_competenza_mese => DATE '2080-01-01',
        p_billing_account_id => (SELECT billing_account_id FROM tmp_gr_refs))
      WHERE commessa_id = (SELECT commessa_id FROM tmp_gr_comm)
    ) x
    UNION ALL
    SELECT COALESCE(sum(x.total_non_emesse), 0)::int FROM (
      SELECT total_non_emesse FROM vendite.fn_list_commesse_emittibili(
        p_competenza_mese => DATE '2080-01-01',
        p_billing_account_id => (SELECT billing_account_id FROM tmp_gr_refs),
        p_gruppi => ARRAY['PREVENTIVO:00000000-0000-4000-8000-999999999999'])
      WHERE commessa_id = (SELECT commessa_id FROM tmp_gr_comm)
    ) x
  ),
  ARRAY[2, 0],
  '14) fn_list_commesse_emittibili: senza filtro 2 righe, con gruppo inesistente 0'
);

-- ============================================================
-- TEST 15 (G7): ripetibilita'. La seconda emissione mirata sullo stesso
--   perimetro, con un gruppo diverso, deve riuscire senza interferenze.
-- ============================================================
SELECT is(
  (SELECT inserted_rows FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
      p_commessa_id => (SELECT commessa_id FROM tmp_gr_comm),
      p_gruppi => ARRAY[(SELECT k_contr FROM tmp_gr_key)])),
  2,
  '15) G7: emissione successiva con gruppo diverso -> riesce, 2 righe'
);

-- ============================================================
-- TEST 16: la tabella del perimetro (A2).
-- ============================================================
CREATE TEMP TABLE tmp_gr_lotto AS
SELECT vendite.fn_get_or_create_lotto(
  p_competenza_mese => DATE '2080-01-01',
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_gr_refs),
  p_billing_account_id => (SELECT billing_account_id FROM tmp_gr_refs)
) AS lotto_id;

INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
SELECT (SELECT lotto_id FROM tmp_gr_lotto), (SELECT k_prev FROM tmp_gr_key);

SELECT throws_ok(
  format($$ INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
            VALUES (%s, %L) $$,
         (SELECT lotto_id FROM tmp_gr_lotto), (SELECT k_prev FROM tmp_gr_key)),
  '23505', NULL,
  '16) UNIQUE (lotto_id, gruppo_key) respinge il duplicato'
);

-- ============================================================
-- TEST 17 (G1/G11): la convenzione portante — nessuna riga di perimetro
--   per un lotto significa NESSUNA restrizione, cioe' il comportamento
--   odierno. Non esiste un flag "lotto mirato" da valorizzare.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM vendite.fatturazione_lotti_gruppi g
    WHERE g.lotto_id = (SELECT lotto_id FROM tmp_gr_lotto) + 999999),
  0,
  '17) G1/G11: lotto senza righe di perimetro = nessuna restrizione'
);

SELECT * FROM finish();
ROLLBACK;
