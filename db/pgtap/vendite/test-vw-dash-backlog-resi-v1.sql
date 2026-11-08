-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-26 (brief-modello-documento-vendita §14, giro 10): la commessa passa a PRONTA_FATTURAZIONE dal verbo vendite.fn_cambia_stato_commessa, che ora chiede l'azione cambia_stato_commessa: il test prova la vista, non il permesso, e la concede all'utente del contesto (dbops.fn_pgtap_concedi_azione). Attese invariate.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): i resi dal builder dbops.fn_pgtap_crea_reso (pg_temp.mk_reso ritirata); resta la chiamata diretta al verbo fn_genera_ddt_riconsegna del 4 (la generazione e' il caso: la bolla resta in bozza).
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine (pg_temp.mk_partita ritirata); il reso (pg_temp.mk_reso) e la fatturazione restano scritti a mano (giro 2, e il caso del test).
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2d): l'area della dashboard e' il codice della sorgente (RESO_VENDITA).
-- pgTAP test per Zero ERP
-- Test: ramo resi sul Backlog (vw_dash_backlog_documenti come union) — step 9,
--       brief-db-fatturazione-ddt-resi §4d / DL-24.
-- (changeset 20260718-14 + seed motivi_fermo 13/14)
-- ------------------------------------------------------------
-- Indice test (1..7):
--   1) security_invoker=on sul backlog (regressione V-1)
--   2) reso PER RICONSEGNA confermato, copertura incompleta -> riga backlog
--      area RESI, motivo RICONSEGNA_NON_ESEGUITA, RECUPERABILE, con azione
--   3) misura a conteggi (DL-11): valore_fermo NULL (mai 0), unita_ferme=1
--   4) ri-consegna generata (copertura completa) -> la riga SPARISCE
--   5) reso A CREDITO su merce FATTURATA -> in coda accrediti come DOVUTA
--      (sanity: la fixture morde davvero)
--   6) ⭐ ...ed E' in backlog, RECUPERABILE con azione: dal 2026-08-18 il
--      rimedio esiste (il verbo di accredito), quindi il motivo cambia voce
--      (nessuna azione esiste: niente NC, quantita' immutabile). Il ramo lo
--      EMETTE e il filtro di classe lo esclude -> la classe e' VIVA: con la
--      slice NC basta promuovere una cella di seed
--   7) i resi NON entrano nella union pre-commessa (REVERSE_FLOW):
--      "resi solo nel backlog"
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

SET LOCAL app.ruolo_applicativo = 'OPERATORE';
-- ⛔ rev 2026-10-13: niente app.current_user_id = '1' (in CI l'utente 1 non
--   esiste): l'operatore e' quello del contesto aperto qui sopra.

-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti): cliente fatturabile legato all'azienda di chi agisce,
--   articolo merce non gestito a magazzino (il test non misura il magazzino).
CREATE TEMP TABLE tmp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP backlog resi');
CREATE TEMP TABLE tmp_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-BLR-V1', false) AS id;

-- ============================================================
-- Riferimenti + helper (fixture consolidata della slice)
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  -- ⛔ rev 2026-10-13: BA, utility, istanza e articolo dal
  --   mondo costruito (prima: il primo BA del database e l'ultimo articolo).
  (SELECT m.billing_account_id FROM tmp_mondo m)                         AS billing_account_id,
  (SELECT m.utility_id FROM tmp_mondo m)                                 AS utility_id,
  (SELECT m.istanza_utility_id FROM tmp_mondo m)                         AS istanza_utility_id,
  (SELECT t.id FROM tmp_art t)                                           AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA' AND s.attivo LIMIT 1)        AS sorgente_root_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id;

-- Commessa + AF per la partita "fatturata" (caso 5-6)
CREATE TEMP TABLE tmp_com AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO', p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false, p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01', p_competenza_al => DATE '2026-07-31',
  p_meta => '{}'::jsonb, p_force_new => true) AS commessa_id;
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_com),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs),
  -- ROOT: sorgente COMMESSA (key_selector='id') con uid = id della commessa
  -- stessa. La riga esiste per costruzione, quindi passa il guard sorgente
  -- polimorfa su entrambi i fronti: formato (id::text) ed esistenza nel
  -- target. fn_emit pretende solo che una ROOT esista, non ne dereferenzia
  -- il tipo. rev 2026-07-27 (bonifica: prima era una stringa inventata su
  -- sorgente PREVENTIVO, illegale dal guard del 2026-07-18).
  p_sorgente_chiave => (SELECT commessa_id FROM tmp_com)::text,
  p_sorgente_riga => NULL, p_meta => '{}'::jsonb);

CREATE OR REPLACE FUNCTION pg_temp.mk_af(p_segment varchar, p_qta numeric)
RETURNS void AS $$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com),
    -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    -- La provenienza e' il documento che la chiave nomina (come nel push).
    p_sorgente_tipo_id => (SELECT k.sorgente_tipo_id FROM dbops.fn_pgtap_provenienza_da_chiave(p_segment) k),
    p_sorgente_chiave => (SELECT k.sorgente_chiave FROM dbops.fn_pgtap_provenienza_da_chiave(p_segment) k),
    p_sorgente_riga => (SELECT k.sorgente_riga FROM dbops.fn_pgtap_provenienza_da_chiave(p_segment) k),
    p_segment_key => p_segment,
    p_articolo_id => r.articolo_id, p_istanza_utility_id => r.istanza_utility_id,
    p_data_attivita => DATE '2026-07-15', p_uom_id => r.uom_id, p_quantita => p_qta,
    p_competenza_mese => DATE '2026-07-01', p_competenza_dal => DATE '2026-07-01', p_competenza_al => DATE '2026-07-31',
    p_prezzo_snapshot => 10.0, p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
    p_tipo_variazione_applicata => NULL, p_valore_variazione_applicata => NULL,
    p_promo_id => NULL, p_contratto_id => NULL, p_categoria_cliente_id_snapshot => NULL, p_classe_utenza_id_snapshot => NULL,
    p_tipo_doc_fiscale_id => r.tipo_doc_fiscale_id, p_stato_approvazione => 'APPROVATA', p_stato_emissione => 'NON_EMESSA',
    p_tipo_movimento => 'NORMALE', p_meta => '{}'::jsonb);
END $$ LANGUAGE plpgsql;

-- ============================================================
-- FIXTURE
--   A: reso 3 PER RICONSEGNA (merce non fatturata) -> coda ri-consegna
--   B: fatturata 10 + reso 3 A CREDITO -> accredito dovuto 3
--   La partita: ordine 10 @25 trigger CONSEGNATO, bolla CONSEGNATA dal builder.
-- ============================================================
CREATE TEMP TABLE tmp_a AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('backlog resi A', 'CONSEGNATO',
    (SELECT billing_account_id FROM tmp_refs), p_quantita => 10, p_prezzo => 25,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONSEGNATO');
-- La grana del backlog e' reso x motivo: si legge la testata (reso_id).
CREATE TEMP TABLE tmp_a_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('backlog resi A', (SELECT ddt_id FROM tmp_a), 3,
         'RESO_PER_RICONSEGNA');

CREATE TEMP TABLE tmp_b AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('backlog resi B', 'CONSEGNATO',
    (SELECT billing_account_id FROM tmp_refs), p_quantita => 10, p_prezzo => 25,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONSEGNATO');
SELECT pg_temp.mk_af(script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_b)::text, (SELECT ddt_riga_id FROM tmp_b)), 10);
-- Il test prova la vista, non il permesso: l'azione «rendi pronta» all'utente del contesto.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'cambia_stato_commessa');
SELECT vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_com), 'PRONTA_FATTURAZIONE');
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com));
CREATE TEMP TABLE tmp_b_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('backlog resi B', (SELECT ddt_id FROM tmp_b), 3);

-- ============================================================
-- ASSERZIONI
-- ============================================================
-- Copre anche vw_resi_da_riconsegnare, che non aveva un'asserzione sua
-- (le altre viste resi sono gia' coperte dai rispettivi test): tutta la
-- catena del ramo resi legge vendite.resi sotto scope emittente.
SELECT ok(
  (SELECT bool_and('security_invoker=on' = ANY(c.reloptions))
     FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='vendite'
      AND c.relname IN ('vw_dash_backlog_documenti',
                        'vw_resi_da_riconsegnare',
                        'vw_resi_da_accreditare')),
  '1) security_invoker=on su backlog E code resi della catena (no bypass RLS)');

-- 2) A in backlog: RICONSEGNA_NON_ESEGUITA, RECUPERABILE, con azione
SELECT is(
  (SELECT (b.motivo_fermo, b.classe, b.azione) FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area='RESO_VENDITA' AND b.documento_id=(SELECT reso_id FROM tmp_a_reso)),
  ('RICONSEGNA_NON_ESEGUITA'::varchar, 'RECUPERABILE'::varchar, 'Genera il DDT di ri-consegna'::varchar),
  '2) reso per ri-consegna senza copertura -> backlog RESI, RECUPERABILE, azione presente');

-- 3) misura a conteggi (DL-11): NULL, mai 0
SELECT is(
  (SELECT (b.valore_fermo IS NULL, b.unita_ferme) FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area='RESO_VENDITA' AND b.documento_id=(SELECT reso_id FROM tmp_a_reso)),
  (true, 1), '3) misura a conteggi: valore_fermo NULL (mai 0), unita_ferme = 1 riga');

-- 4) ri-consegna completa -> la riga sparisce
SELECT vendite.fn_genera_ddt_riconsegna((SELECT reso_id FROM tmp_a_reso));
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area='RESO_VENDITA' AND b.documento_id=(SELECT reso_id FROM tmp_a_reso)),
  0, '4) ri-consegna generata (copertura completa) -> fuori dal backlog');

-- 5) B: l'accredito dovuto esiste (sanity sulla fixture)
SELECT is(
  (SELECT (a.accredito_dovuto, a.etichetta) FROM vendite.vw_resi_da_accreditare a
    WHERE a.reso_id=(SELECT reso_id FROM tmp_b_reso)),
  (3::numeric, 'DOVUTA'::varchar),
  '5) merce fatturata 10, resa 3 a credito -> coda accrediti: dovuto 3, DOVUTA');

-- 6) ⭐ E ORA E' IN BACKLOG. rev 2026-08-18 (brief-design-note-credito-resi
--    N11, §6.1). Questo test asseriva il contrario, ed era giusto: il motivo
--    era classificato FISIOLOGICO e l'ultimo filtro della vista
--    (`classe <> 'FISIOLOGICO'`) lo teneva fuori. Il Backlog elenca cio' che e'
--    fermo e RECUPERABILE, e un motivo senza rimedio non e' arretrato — e'
--    uno stato di fatto.
--
--    ⚠️ Il rimedio adesso esiste: `vendite.fn_accredita_riga_reso`. Nel
--    momento in cui il verbo c'e', «merce resa gia' fatturata» smette di
--    essere una constatazione e diventa un arretrato con azione — e i TRE
--    posti che dicevano «fatto senza rimedio» devono cambiare voce insieme,
--    o l'applicazione si contraddice (§9-bis). Cambiarne uno solo e' il
--    difetto che nessun test intercetta, perche' ognuno resta coerente con se'
--    stesso.
--
--    ⭐ E non e' costato una riga di SQL: DUE CELLE DI SEED su
--    config.motivi_fermo (classe FISIOLOGICO -> RECUPERABILE, azione da NULL
--    alla frase). La vista e la union non sono state toccate.
SELECT is(
  (SELECT (b.classe, b.azione IS NOT NULL) FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area='RESO_VENDITA' AND b.documento_id=(SELECT reso_id FROM tmp_b_reso)),
  ('RECUPERABILE'::varchar, true),
  '6) MERCE_RESA_GIA_FATTURATA e'' RECUPERABILE con azione: il rimedio esiste, la riga entra in backlog');

-- 7) i resi non stanno nella union pre-commessa (REVERSE_FLOW)
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.vw_dash_fatturazione_documenti WHERE area='RESO_VENDITA'),
  0, '7) resi SOLO nel backlog: mai in vw_dash_fatturazione_documenti (REVERSE_FLOW)');

SELECT * FROM finish();
ROLLBACK;
