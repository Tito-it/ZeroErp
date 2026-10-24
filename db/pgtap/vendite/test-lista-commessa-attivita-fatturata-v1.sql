-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: colonna 'fatturata' in vendite.fn_list_commessa_attivita.
-- Brief: brief-db-flag-fatturata-lista-attivita.md (2026-07-24).
--
-- PERCHE' ESISTE: il drawer di gestione commessa offre le azioni prezzo per
-- riga; il BE le rifiuta su riga fatturata (_assert_non_fatturata legge
-- af.fattura_riga_id), ma il FE non puo' nasconderle prima del click finche' la
-- lista non espone il dato. 'fatturata' e' lo SPECCHIO ESATTO del guard BE:
-- EXISTS di un'attivita_fatturabili della riga con fattura_riga_id valorizzato.
--
-- CRITERIO: fattura_riga_id IS NOT NULL, NON la colonna denormalizzata
-- attivita_fatturabili.fatturato. La relazione CA<->AF e' 1:1
-- (uq_attivita_fatturabili_commessa_attivita).
--
-- Il caso 3 e' il DISCRIMINANTE del brief: riga con AF ma fattura_riga_id NULL
-- (lotto resettato) -> EMESSA ma prezzo ancora modificabile. E' dove
-- stato_emissione sbaglierebbe e fattura_riga_id no.
--
-- Nota fixture: le righe si creano via fn_upsert_commessa_attivita (sourceless);
-- le AF via INSERT diretto (no fn_emit, che esige una ROOT source reale).
-- ⚠️ fattura_riga_id HA una FK dal 20260728-11 (prima no): non basta piu' un id
-- fittizio, serve una riga di fattura vera — la crea il fixture qui sotto.
-- Le righe APPROVATA+NON_EMESSA esigono tipo_doc (guard tipo_doc_emittibile):
-- si passa sempre tipo_doc all'upsert.
-- ------------------------------------------------------------
-- Indice test (1..4):
--   1  fn_list_commessa_attivita dichiara la colonna fatturata boolean
--   2  fatturata = false su riga senza attivita_fatturabili
--   3  fatturata = false su riga con AF ma fattura_riga_id NULL (reset-lotto)
--   4  fatturata = true  su riga con AF e fattura_riga_id valorizzato
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

SELECT plan(4);

-- ============================================================
-- 1 — STRUTTURA
-- ============================================================
-- ⚠️ La firma NON si scrive a mano. Questa asserzione inchiodava
--    `(bigint,varchar,varchar,date,integer,integer)` in un `::regprocedure`, e
--    si e' rotta il 2026-08-02 quando la funzione ha preso `p_order_by`/
--    `p_order_dir` (changeset 20260802-26, 7o lotto liste configurabili): la
--    firma e' diventata a 8 parametri e il cast non ha piu' trovato nulla.
--    Il test moriva alla prima riga, quindi le altre 3 asserzioni — che sono
--    il vero contenuto del file — non venivano nemmeno eseguite.
--
--    Cio' che qui interessa e' che la funzione DICHIARI la colonna, non con
--    quali parametri: si risolve per NOME. Se qualcuno creasse un overload per
--    sbaglio, la subquery scalare troverebbe due righe e fallirebbe
--    rumorosamente — che e' esattamente il segnale che si vuole.
SELECT ok(
  (SELECT pg_get_function_result(p.oid) LIKE '%fatturata boolean%'
     FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_commessa_attivita'),
  '1) fn_list_commessa_attivita dichiara la colonna fatturata boolean');

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE tmp_refs_lcf AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS billing_account_id,
  (SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS utility_id,
  (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1) AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE
    ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id;

-- Commessa isolata (force_new), nasce in BOZZA.
CREATE TEMP TABLE tmp_commessa_lcf AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_lcf),
  p_utility_id             => (SELECT utility_id FROM tmp_refs_lcf),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-10-01',
  p_competenza_al          => DATE '2026-10-31',
  p_meta                   => jsonb_build_object('test_scope', 'pgtap_lista_fatturata'),
  p_force_new              => true
) AS commessa_id;

-- Scopo: aggiunge una riga alla commessa negli stati richiesti; ritorna l'id.
CREATE OR REPLACE FUNCTION pg_temp.fx_riga_lcf(
  p_seg  vendite.commesse_attivita.segment_key%TYPE,
  p_appr vendite.commesse_attivita.stato_approvazione%TYPE,
  p_emis vendite.commesse_attivita.stato_emissione%TYPE)
RETURNS vendite.commesse_attivita.id%TYPE LANGUAGE sql AS $fx$
  SELECT r.attivita_id
    FROM vendite.fn_upsert_commessa_attivita(
      p_commessa_id                   => (SELECT commessa_id FROM tmp_commessa_lcf),
      -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
      p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
      p_sorgente_uid => ((SELECT commessa_id FROM tmp_commessa_lcf))::text,
      p_segment_key                   => p_seg,
      p_articolo_id                   => (SELECT articolo_id FROM tmp_refs_lcf),
      p_istanza_utility_id            => (SELECT istanza_utility_id FROM tmp_refs_lcf),
      p_data_attivita                 => DATE '2026-10-15',
      p_uom_id                        => (SELECT uom_id FROM tmp_refs_lcf),
      p_quantita                      => 1.000000,
      p_competenza_mese               => DATE '2026-10-01',
      p_competenza_dal                => DATE '2026-10-01',
      p_competenza_al                 => DATE '2026-10-31',
      p_prezzo_snapshot               => 10.0000000000,
      p_prezzo_base_snapshot          => NULL,
      p_origine_prezzo                => NULL,
      p_tipo_variazione_applicata     => NULL,
      p_valore_variazione_applicata   => NULL,
      p_promo_id                      => NULL,
      p_contratto_id                  => NULL,
      p_categoria_cliente_id_snapshot => NULL,
      p_classe_utenza_id_snapshot     => NULL,
      p_tipo_doc_fiscale_id           => (SELECT tipo_doc_fiscale_id FROM tmp_refs_lcf),
      p_stato_approvazione            => p_appr,
      p_stato_emissione               => p_emis,
      p_tipo_movimento                => 'NORMALE',
      p_meta                          => jsonb_build_object('case', 'LCF')
    ) r;
$fx$;

-- Tre righe: senza AF / AF non fatturata / AF fatturata.
CREATE TEMP TABLE tmp_att_lcf AS
SELECT
  pg_temp.fx_riga_lcf('SEG-LCF-1', 'APPROVATA', 'NON_EMESSA') AS id_senza_af,
  pg_temp.fx_riga_lcf('SEG-LCF-2', 'APPROVATA', 'EMESSA')     AS id_af_non_fatt,
  pg_temp.fx_riga_lcf('SEG-LCF-3', 'APPROVATA', 'EMESSA')     AS id_af_fatt;

-- AF per la riga 2: esiste ma fattura_riga_id NULL (caso reset-lotto).
INSERT INTO vendite.attivita_fatturabili (
  articolo_id, istanza_utility_id, data_attivita, quantita,
  competenza_mese, competenza_dal, competenza_al,
  uom_id, prezzo_unitario, tipo_doc_fiscale_id,
  commessa_id, commessa_attivita_id, fattura_riga_id,
  -- ⭐ billing_account_id: NOT NULL dal changeSet 20260910-25. Si deriva
  --   dalla COMMESSA, che e' la rotta portante (commessa_id NOT NULL ->
  --   commesse.billing_account_id NOT NULL): la fixture non lo inventa.
  billing_account_id)
SELECT r.articolo_id, r.istanza_utility_id, DATE '2026-10-15', 1,
       DATE '2026-10-01', DATE '2026-10-01', DATE '2026-10-31',
       r.uom_id, 10.000000, r.tipo_doc_fiscale_id,
       (SELECT commessa_id FROM tmp_commessa_lcf),
       (SELECT id_af_non_fatt FROM tmp_att_lcf), NULL,
       (SELECT c.billing_account_id FROM vendite.commesse c
         WHERE c.id = (SELECT commessa_id FROM tmp_commessa_lcf))
       FROM tmp_refs_lcf r;

-- ⚠️ 2026-07-28: serve una riga di fattura VERA.
--   Prima qui c'era `fattura_riga_id = 999999` con la nota «id fittizio, nessuna
--   FK»: sfruttava letteralmente l'assenza del vincolo. Dal 20260728-11 la FK
--   esiste (ON UPDATE CASCADE ON DELETE SET NULL), perche' con l'aggregazione
--   quel puntatore diventa la struttura portante della fattura — e un puntatore
--   pendente non sarebbe piu' un dettaglio.
--   L'importo della riga lo calcola il trigger a20.
-- ⚠️ 2026-08-07: testata e righe in DUE statement, non in una CTE sola.
--   La policy rls_fatture_righe_ef_whitelist risolve l'emittente passando da
--   vendite.fatture (script.fn_scope_ef_whitelist_via_fattura, STABLE). Dentro
--   una CTE che scrive, tutti i rami condividono la stessa snapshot: la fattura
--   appena inserita NON e' ancora visibile, l'SR risolve a NULL e il WITH CHECK
--   nega fail-closed. Misurato: stessi dati, stesso operatore — in due statement
--   passa, in una CTE no. L'applicazione scrive sempre in due tempi (il BE crea
--   la fattura in uno step e le righe in quello dopo), quindi la forma qui sotto
--   e' anche la piu' fedele.
CREATE TEMP TABLE tmp_fattura_lcf AS
WITH f AS (
  INSERT INTO vendite.fatture (registro_id, data, emittente_soggetto_ruolo_id,
                               billing_account_id, utility_id, meta)
  -- ⛔ Il registro dev'essere quello dell'emittente della riga sotto, non
  --   «il primo che c'e'»: dal 2026-08-30 il guard non ammette piu' la
  --   coincidenza (vendite.trgfn_fatture_guard_registro_emittente).
  SELECT script.fn_pgtap_registro_fattura(
           anagrafiche.fn_get_emittente_fiscale_id((SELECT billing_account_id FROM tmp_refs_lcf))),
         script.fn_data_operativa(),
         anagrafiche.fn_get_emittente_fiscale_id((SELECT billing_account_id FROM tmp_refs_lcf)),
         (SELECT billing_account_id FROM tmp_refs_lcf),
         -- utility dal BA, come la testata vera (R-3, 20261021-15)
         (SELECT ba.utility_id FROM anagrafiche.billing_account ba
           WHERE ba.id = (SELECT billing_account_id FROM tmp_refs_lcf)),
         jsonb_build_object('test_scope', 'pgtap_lista_commessa_attivita_fatturata')
  RETURNING id
)
SELECT (SELECT id FROM f) AS fattura_id, NULL::bigint AS riga_id;

WITH r AS (
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta,
                                     prezzo_unitario, meta, competenza_dal, competenza_al)
  SELECT (SELECT fattura_id FROM tmp_fattura_lcf), 1, 'Riga di test',
         1::numeric, 10::numeric,
         jsonb_build_object('test_scope', 'pgtap_lista_commessa_attivita_fatturata'), script.fn_data_operativa(), script.fn_data_operativa()
  RETURNING id
)
UPDATE tmp_fattura_lcf SET riga_id = (SELECT id FROM r);

-- AF per la riga 3: fattura_riga_id valorizzato con una riga esistente.
INSERT INTO vendite.attivita_fatturabili (
  articolo_id, istanza_utility_id, data_attivita, quantita,
  competenza_mese, competenza_dal, competenza_al,
  uom_id, prezzo_unitario, tipo_doc_fiscale_id,
  commessa_id, commessa_attivita_id, fattura_riga_id,
  -- ⭐ billing_account_id: NOT NULL dal changeSet 20260910-25. Si deriva
  --   dalla COMMESSA, che e' la rotta portante (commessa_id NOT NULL ->
  --   commesse.billing_account_id NOT NULL): la fixture non lo inventa.
  billing_account_id)
SELECT r.articolo_id, r.istanza_utility_id, DATE '2026-10-15', 1,
       DATE '2026-10-01', DATE '2026-10-01', DATE '2026-10-31',
       r.uom_id, 10.000000, r.tipo_doc_fiscale_id,
       (SELECT commessa_id FROM tmp_commessa_lcf),
       (SELECT id_af_fatt FROM tmp_att_lcf), (SELECT riga_id FROM tmp_fattura_lcf),
       (SELECT c.billing_account_id FROM vendite.commesse c
         WHERE c.id = (SELECT commessa_id FROM tmp_commessa_lcf))
       FROM tmp_refs_lcf r;

-- ============================================================
-- 2..4 — VALORI
-- ============================================================
SELECT is(
  (SELECT l.fatturata
     FROM vendite.fn_list_commessa_attivita((SELECT commessa_id FROM tmp_commessa_lcf)) l
    WHERE l.id = (SELECT id_senza_af FROM tmp_att_lcf)),
  false,
  '2) fatturata = false su riga senza attivita_fatturabili');

SELECT is(
  (SELECT l.fatturata
     FROM vendite.fn_list_commessa_attivita((SELECT commessa_id FROM tmp_commessa_lcf)) l
    WHERE l.id = (SELECT id_af_non_fatt FROM tmp_att_lcf)),
  false,
  '3) fatturata = false su riga con AF ma fattura_riga_id NULL (reset-lotto)');

SELECT is(
  (SELECT l.fatturata
     FROM vendite.fn_list_commessa_attivita((SELECT commessa_id FROM tmp_commessa_lcf)) l
    WHERE l.id = (SELECT id_af_fatt FROM tmp_att_lcf)),
  true,
  '4) fatturata = true su riga con AF e fattura_riga_id valorizzato');

SELECT * FROM finish();
ROLLBACK;
