-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: porta oneri — onere → emissione → attività fatturabile → lotto.
-- Brief: brief-db-immutabilita-quantita-e-porta-oneri §4c.7 (step 9).
--
-- Verifica che una riga onere (sourceless, tipo_movimento='ONERE') faccia il
-- "giro normale da APPROVATA in poi": emissione (fn_emit) crea l'attività
-- fatturabile propagando ONERE + qta=1 + prezzo + l'articolo-onere, e la riga
-- entra nel lotto. PAYOFF: l'AF porta l'articolo-onere, e con esso la SUA IVA
-- (penale = fuori campo art.15) → il modello articolo↔causale porta l'IVA
-- per-onere fino al confine della fatturazione.
--
-- fn_emit esige una ROOT source sulla COMMESSA (non sulla riga): la si crea con
-- fn_link_commessa_sorgente.
--
-- ⚠️ PERIMETRO — perché il test si ferma alla AF e non arriva alla riga di
-- fattura. Fino al 2026-07-28 questo file proseguiva invocando
-- vendite.fn_generate_fatture_righe (3 asserzioni: riga generata, qta/prezzo,
-- IVA sulla riga). Quella funzione NON era in esercizio dal 2026-02-03 — il task
-- della pipeline esegue apps/vendite/services/fatture_righe_service.py — ed è
-- stata rimossa dal changeset 20260728-21. Le 3 asserzioni erano quindi verdi su
-- codice che nessuno eseguiva: toglierle non riduce la copertura reale, la
-- dichiara. Il tratto AF → riga di fattura va coperto da uno smoke sul percorso
-- Python (brief-db-ritiro-generatore-righe-fattura-sql §5 passo 5), che è dove
-- quel codice vive davvero.
-- ------------------------------------------------------------
-- Indice test (1..9):
--   1  onere creato (CA ONERE)
--   2  commessa con ROOT source
--   3  fn_emit: 1 AF inserita
--   4  AF: tipo_movimento='ONERE' propagato
--   5  AF: quantita=1 e prezzo_unitario=importo
--   6  AF: articolo = articolo-onere passato
--   7  AF: approvato=true + link commessa_attivita_id
--   8  AF: una sola per la riga di commessa dell'onere (pull idempotente)
--   9  lotto creato
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

SELECT plan(9);

-- rev 2026-10-27 (lotto 4 di D7): via il vecchio «SET LOCAL app.current_user_id
--   = '1'» (con ruolo OPERATORE): l'utente 1 da zero non esiste, e su dev e' un
--   super admin senza azienda. Chi agisce e' l'operatore del contesto qui sopra
--   (le madri/viste sono SECURITY INVOKER: il ruolo applicativo lo da' lui).
--   Il cliente si COSTRUISCE con dbops.fn_pgtap_crea_cliente_ba (BA legato
--   all'azienda di chi agisce): prima si pescava il primo BA con emittente, e
--   da zero non c'era. L'emittente si deriva dal BA costruito. Restano letture
--   di catalogo di SEED: tipi_doc_fiscale, sorgenti, articoli-onere.
CREATE TEMP TABLE tmp_cli_ogc AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('porta oneri giro completo');

-- ===== riferimenti =====
CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_ogc) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_ogc) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cli_ogc) AS istanza_utility_id,
  (SELECT anagrafiche.fn_get_emittente_fiscale_id(billing_account_id) FROM tmp_cli_ogc) AS emittente_soggetto_ruolo_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
  -- Sorgente ROOT: COMMESSA (target vendite.commesse, key_selector='id') con uid =
  -- id della commessa stessa -> la riga esiste per costruzione (passa il guard
  -- sorgente polimorfa: formato id::text + esistenza nel target). fn_emit richiede
  -- solo che esista una ROOT in commesse_sorgenti, non ne dereferenzia il tipo.
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA' AND s.attivo LIMIT 1) AS sorgente_root_id,
  (SELECT id FROM catalogo.articoli WHERE codice='ONERE_PENALE') AS articolo_onere_id,
  (SELECT iva_id FROM catalogo.articoli WHERE codice='ONERE_PENALE') AS iva_onere_id;

-- ===== commessa + ROOT source (richiesta da fn_emit) =====
CREATE TEMP TABLE tmp_com AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO', p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false, p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01', p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope','pgtap_onere_giro'), p_force_new => true
) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_com),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs),
  p_sorgente_chiave => (SELECT commessa_id FROM tmp_com)::text,
  p_sorgente_riga => NULL, p_meta => '{}'::jsonb);

-- ===== onere (penale 150,00) =====
CREATE TEMP TABLE tmp_onere AS
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id        => (SELECT commessa_id FROM tmp_com),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs),
  p_articolo_onere_id  => (SELECT articolo_onere_id FROM tmp_refs),
  p_importo            => 150.00,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs),
  p_motivo             => 'Ritardo consegna — pgtap giro completo',
  p_data_attivita      => DATE '2026-07-15'
) AS commessa_attivita_id;

SELECT ok((SELECT commessa_attivita_id IS NOT NULL FROM tmp_onere), '1) onere creato (CA ONERE)');

SELECT ok(
  (SELECT count(*) = 1 FROM vendite.commesse_sorgenti cs
    WHERE cs.commessa_id = (SELECT commessa_id FROM tmp_com) AND cs.ruolo_link = 'ROOT'),
  '2) commessa con ROOT source');

-- ===== emissione: PRONTA_FATTURAZIONE + pull =====
-- rev 2026-10-27: il verbo della commessa chiede cambia_stato_commessa
-- all'operatore del test (giro 10); senza, su un db dove l'operatore non ce l'ha,
-- si ferma qui con E_PERMESSO_NEGATO.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'cambia_stato_commessa');
SELECT vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_com), 'PRONTA_FATTURAZIONE');
CREATE TEMP TABLE tmp_emit AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com));

SELECT is((SELECT inserted_rows FROM tmp_emit), 1, '3) fn_emit: 1 AF inserita');

-- AF dell'onere
CREATE TEMP TABLE tmp_af AS
SELECT a.*
FROM vendite.attivita_fatturabili a
WHERE a.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_onere);

SELECT is((SELECT tipo_movimento FROM tmp_af), 'ONERE'::varchar, '4) AF: tipo_movimento=ONERE propagato');

SELECT ok(
  (SELECT quantita = 1 AND prezzo_unitario = 150.00 FROM tmp_af),
  '5) AF: quantita=1 e prezzo_unitario=importo');

SELECT is((SELECT articolo_id FROM tmp_af), (SELECT articolo_onere_id FROM tmp_refs),
  '6) AF: articolo = articolo-onere passato');

SELECT ok(
  (SELECT approvato IS TRUE AND commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_onere) FROM tmp_af),
  '7) AF: approvato=true + link commessa_attivita_id');

-- rev 2026-11-07 (lotto C, giro C.1 di brief-db-sorgente-documento-e-riga): l'AF
--   non porta piu' una copia della provenienza (sorgente COMMESSA): la sua
--   provenienza e' la riga di commessa, e il pull la ritrova per
--   commessa_attivita_id. Un secondo pull non crea una seconda AF per l'onere.
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_com));
SELECT is(
  (SELECT count(*)::int FROM vendite.attivita_fatturabili af
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_onere)),
  1,
  '8) AF: una sola per la riga di commessa dell''onere (pull idempotente)');

-- ===== lotto =====
CREATE TEMP TABLE tmp_lotto AS
SELECT vendite.fn_create_fatturazione_lotto(
  p_competenza_mese => DATE '2026-07-01',
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs)::integer,
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_lock_batch_id => '11111111-1111-1111-1111-111111111111'::uuid,
  p_meta => jsonb_build_object('test_scope','pgtap_onere_giro'),
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs)
) AS lotto_id;

SELECT ok((SELECT lotto_id IS NOT NULL FROM tmp_lotto), '9) lotto creato');

-- Qui finiva il tratto verso la riga di fattura: emulazione del lock
-- select_attivita + fn_generate_fatture_righe + 3 asserzioni. Rimosso col
-- changeset 20260728-21 (funzione ritirata, mai in esercizio) — vedi il
-- ⚠️ PERIMETRO in testa al file. Anche l'emulazione del lock è sparita con
-- l'unico consumatore che ne aveva bisogno: era setup, non copertura.

SELECT * FROM finish();
ROLLBACK;
