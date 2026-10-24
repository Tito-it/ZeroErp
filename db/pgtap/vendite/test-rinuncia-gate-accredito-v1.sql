-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; resta scritto a mano il reso (giro 2), la rinuncia e la commessa con la fattura, che sono il caso del test.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: script.fn_check_rinuncia_reversibile — il gate NC si e' svegliato
--       (P-3 / passo 4, changeset 20260819-02)
-- ------------------------------------------------------------
-- ⛔ Prima di 20260819-02 questo file NON arriva in fondo, ed e' il difetto che
--    misura. Corsa del 2026-08-19, senza il changeset:
--      1, 2   verdi  (la fixture regge: rinuncia creata, riga in coda)
--      3      have NULL, want E_RESO_RINUNCIA_ACCREDITO_ESEGUITO|...
--      4      «no exception thrown»  <- ⭐ il difetto in tre parole: la madre
--             non si oppone, e la rinuncia SI RIAPRE davvero
--      5..8   non eseguiti: avendo riaperto per davvero al test 4, il test 6
--             trova E_RESO_NESSUNA_RICONSEGNA_PENDENTE e la transazione muore
--             («Bad plan. You planned 8 tests but ran 5»)
--    ⚠️ La cascata NON e' un difetto del test: e' la conseguenza diretta del
--    fatto che al test 4 il divieto non morde. Con il changeset applicato il
--    test 4 solleva, non riapre niente, e 5-8 girano.
--
-- Indice test (1..8):
--   1) fixture: la riga e' in coda accrediti e la ri-consegna e' stata chiusa
--   2) PRIMA dell'accredito il gate e' vuoto: la rinuncia si puo' riaprire
--   3) ⭐ dopo l'accredito il gate produce ACCREDITO_ESEGUITO, col codice giusto
--   4) ⭐ e la MADRE lo solleva da se': fn_riapri_riconsegna_reso rifiuta —
--      e' il pezzo che dimostra che il gate non e' decorativo
--   5) ⭐⭐ dopo l'ANNULLO il gate torna vuoto: l'auto-riparazione di C-3
--   6) ⭐ e la madre RIESCE davvero: la rinuncia si riapre
--   7) il ramo storico non e' stato rotto: riga inesistente -> RIGA_INESISTENTE
--   8) guard sul parametro: id nullo -> errore di dominio (P0001)
--
-- ⭐ PERCHE' SI PASSA DALLA MADRE (test 4 e 6) E NON SOLO DAL GATE.
--    Il gate e' una funzione PURA: da sola produce un elenco che nessuno e'
--    obbligato a leggere. Che il divieto MORDA lo dice solo
--    vendite.fn_riapri_riconsegna_reso, che solleva il primo motivo prodotto.
--    Un test sul solo gate direbbe «l'elenco contiene la voce giusta», non
--    «la rinuncia non si riapre».
--
-- ⚠️ NOTA DI CONTRATTO, verificata: la madre solleva
--    `v_motivi -> 0 ->> 'codice'` passando UN SOLO valore (resi_riga_id). Ogni
--    codice prodotto da questo gate deve quindi avere arita' <= 1, o
--    l'errore di dominio sparirebbe in un 22023.
--
-- ⚠️ Il tipo di reso e' RESO_PER_RICONSEGNA (riapre_residuo = true): senza,
--    trgfn_resi_rinunce_guard rifiuta la rinuncia e la fixture non arriva
--    nemmeno al soggetto del test.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti): azienda + operatore + cliente BA, e il builder apre
--   da se' il contesto su quell'operatore. Niente utente 1 inchiodato.
CREATE TEMP TABLE tmp_mondo_acc AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP rinuncia gate');
-- Il mondo ha gia' aperto il contesto sul suo operatore: la riga lo
--   dichiara (e il guardrail del preambolo la cerca).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_mondo_acc)); END $ctx$;

SELECT plan(10);

-- Dal 2026-09-28 conferma e annullo del reso sono verbi che applicano
-- l'azione conferma_reso (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-f):
-- l'operatore di fixture non ha azioni, si concede qui.
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione(
        NULLIF(current_setting('app.current_user_id', true), '')::integer, 'conferma_reso');
END $az$;

CREATE TEMP TABLE tmp_refs_rin AS
SELECT
  ba.id                                        AS billing_account_id,
  ba.utility_id                                AS utility_id,
  ba.istanza_utility_id                        AS istanza_utility_id,
  script.fn_pgtap_emittente_sr_operatore()     AS emittente_sr_id,
  -- ⛔ rev 2026-10-13: l'articolo si COSTRUISCE (merce non solo-componente, non
  --   gestito: il test non misura il magazzino) — da zero il catalogo ha solo ONERE_*.
  dbops.fn_pgtap_crea_articolo('PGTAP-RIN-GATE', false)                  AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)            AS iva_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='DDT_VENDITA' AND s.attivo ORDER BY s.id LIMIT 1)            AS sorgente_ddt_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA'    AND s.attivo ORDER BY s.id LIMIT 1)            AS sorgente_root_id,
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='DRAFT' AND s.attivo ORDER BY s.id LIMIT 1)            AS stato_reso_draft_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_PER_RICONSEGNA' AND t.attivo ORDER BY t.id LIMIT 1)        AS tipo_reso_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)                               AS tipo_doc_fiscale_id,
  (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno='DRAFT' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1) AS stato_fatt_draft_id,
  script.fn_pgtap_registro_fattura()                         AS registro_id,
  config.fn_get_natura_doc_fiscale_id('NOTA_CREDITO')                                                                     AS natura_nc_id
-- ⛔ rev 2026-10-13: il BA e' quello del mondo costruito, non il primo del database.
FROM tmp_mondo_acc m
JOIN anagrafiche.billing_account ba ON ba.id = m.billing_account_id;

-- ============================================================
-- Helper di fixture (stessa forma di test-fn-accredita-riga-reso-v1)
-- ⚠️ Padre e figlio in DUE istruzioni, mai in una CTE sola: le CTE che
--    scrivono condividono la stessa snapshot e una policy che risolve il
--    perimetro dal padre non lo trova, negando fail-closed.
-- La partita (bolla CONSEGNATA da ordine) e' del builder
-- dbops.fn_pgtap_crea_ddt_da_ordine.
-- ============================================================

-- La merce viene FATTURATA per intero: e' la catena che la madre risale per
-- copiare il prezzo. Senza `fattura_riga_id` l'accredito e' impossibile.
CREATE OR REPLACE FUNCTION pg_temp.rin_fattura(p_segment varchar, p_qta numeric, p_prezzo numeric)
RETURNS bigint AS $$
DECLARE r RECORD; v_af bigint; v_fatt bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_rin;

  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id                   => (SELECT commessa_id FROM tmp_com_rin),
    -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
    p_sorgente_uid => ((SELECT commessa_id FROM tmp_com_rin))::text,
    p_segment_key                   => p_segment,
    p_articolo_id                   => r.articolo_id,
    p_istanza_utility_id            => r.istanza_utility_id,
    p_data_attivita                 => DATE '2026-07-15',
    p_uom_id                        => r.uom_id,
    p_quantita                      => p_qta,
    p_competenza_mese               => DATE '2026-07-01',
    p_competenza_dal                => DATE '2026-07-01',
    p_competenza_al                 => DATE '2026-07-31',
    p_prezzo_snapshot               => p_prezzo,
    p_prezzo_base_snapshot          => NULL,
    p_origine_prezzo                => NULL,
    p_tipo_variazione_applicata     => NULL,
    p_valore_variazione_applicata   => NULL,
    p_promo_id                      => NULL,
    p_contratto_id                  => NULL,
    p_categoria_cliente_id_snapshot => NULL,
    p_classe_utenza_id_snapshot     => NULL,
    p_tipo_doc_fiscale_id           => r.tipo_doc_fiscale_id,
    p_valuta_id                     => r.valuta_id,
    p_stato_approvazione            => 'APPROVATA',
    p_stato_emissione               => 'NON_EMESSA',
    p_tipo_movimento                => 'NORMALE');

  PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa(
      (SELECT commessa_id FROM tmp_com_rin), true, false);

  SELECT af.id INTO v_af
    FROM vendite.attivita_fatturabili af
    JOIN vendite.commesse_attivita ca ON ca.id = af.commessa_attivita_id
   WHERE ca.segment_key = p_segment
   ORDER BY af.id DESC LIMIT 1;

  INSERT INTO vendite.fatture (registro_id, data, tipo_doc_fiscale_id, stato_doc_fiscale_id,
      emittente_soggetto_ruolo_id, billing_account_id, utility_id, valuta_id, tasso_cambio, meta)
  VALUES (r.registro_id, DATE '2026-07-31', r.tipo_doc_fiscale_id, r.stato_fatt_draft_id,
      r.emittente_sr_id, r.billing_account_id, r.utility_id, r.valuta_id, 1,
      jsonb_build_object('test_scope','pgtap_rinuncia_gate'))
  RETURNING id INTO v_fatt;

  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione,
      uom_id, qta, prezzo_unitario, iva_id, imponibile_riga, competenza_dal, competenza_al)
  VALUES (v_fatt, 1, r.articolo_id, 'Riga fattura pgTAP', r.uom_id, p_qta, p_prezzo,
      r.iva_id, p_qta * p_prezzo, script.fn_data_operativa(), script.fn_data_operativa())
  RETURNING id INTO v_riga;

  UPDATE vendite.attivita_fatturabili
     SET fattura_riga_id = v_riga
   WHERE id = v_af;

  RETURN v_riga;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pg_temp.rin_mk_reso(p_ddt_riga bigint, p_ddt_uid uuid, p_qta numeric)
RETURNS bigint AS $$
DECLARE r RECORD; v_reso bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_rin;
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  VALUES (r.stato_reso_draft_id, r.sorgente_ddt_id, p_ddt_uid, false,
          jsonb_build_object('test_scope','pgtap_rinuncia_gate'))
  RETURNING id INTO v_reso;

  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
      articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base,
      tipo_reso_id, storicizza)
  SELECT v_reso, 1, dr.id,
         (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f
           WHERE f.ddt_riga_id = dr.id ORDER BY f.id LIMIT 1),
         dr.articolo_id, dr.descrizione, p_qta, dr.uom_operativa_id, dr.factor_to_base,
         r.tipo_reso_id, false
    FROM vendite.ddt_righe dr WHERE dr.id = p_ddt_riga
  RETURNING id INTO v_riga;

  PERFORM vendite.fn_conferma_reso(v_reso);
  RETURN v_riga;
END $$ LANGUAGE plpgsql;

-- Il reset del lotto, nella forma esatta in cui lo fa
-- vendite.fn_cleanup_fatture_by_ids (RD-4): l'attivita' torna NON_EMESSA e
-- l'attivita_fatturabili SOPRAVVIVE, sbloccata e senza fattura_riga_id.
-- ⭐ E' proprio questa sopravvivenza che il test 17 mette alla prova.
CREATE OR REPLACE FUNCTION pg_temp.ann_reset_lotto(p_ca_id bigint)
RETURNS void AS $$
BEGIN
  UPDATE vendite.attivita_fatturabili
     SET lock_in_fatturazione = false, lock_batch_id = NULL,
         fattura_riga_id = NULL
   WHERE commessa_attivita_id = p_ca_id;
  UPDATE vendite.commesse_attivita
     SET stato_emissione = 'NON_EMESSA'
   WHERE id = p_ca_id;
END $$ LANGUAGE plpgsql;


-- ============================================================
-- FIXTURE: consegnati 10 a 25, fatturati 10, resi 3 per RI-CONSEGNA,
--   poi la ri-consegna viene CHIUSA -> nasce la rinuncia.
-- ============================================================
CREATE TEMP TABLE tmp_com_rin AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_rin),
  p_utility_id             => (SELECT utility_id FROM tmp_refs_rin),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-07-01',
  p_competenza_al          => DATE '2026-07-31',
  p_meta                   => '{}'::jsonb,
  p_force_new              => true) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_id FROM tmp_com_rin),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs_rin),
  p_sorgente_uid     => (SELECT commessa_id FROM tmp_com_rin)::text,
  p_sorgente_riga    => 1,
  p_meta             => '{}'::jsonb);

CREATE TEMP TABLE tmp_pr AS
SELECT b.ordine_riga_id, b.ddt_id, b.ddt_uid, b.ddt_riga_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('rinuncia gate',
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs_rin),
           p_quantita             => 10,
           p_prezzo               => 25,
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs_rin),
           p_fatturazione_trigger => 'CONSEGNATO') b;
CREATE TEMP TABLE tmp_pr_fattura AS
SELECT pg_temp.rin_fattura(
    script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_pr)::text, (SELECT ddt_riga_id FROM tmp_pr)),
    10, 25) AS fattura_riga_id;
CREATE TEMP TABLE tmp_pr_reso AS
SELECT pg_temp.rin_mk_reso((SELECT ddt_riga_id FROM tmp_pr), (SELECT ddt_uid FROM tmp_pr), 3) AS resi_riga_id;
CREATE TEMP TABLE tmp_pr_reso_id AS
SELECT rr.reso_id FROM vendite.resi_righe rr WHERE rr.id = (SELECT resi_riga_id FROM tmp_pr_reso);

-- La ri-consegna si chiude: la quota diventa definitivamente non ri-spedibile
-- e nasce la riga in vendite.resi_righe_rinunce, che e' il soggetto del gate.
SELECT vendite.fn_chiudi_riconsegna_reso((SELECT reso_id FROM tmp_pr_reso_id));

SELECT is(
  (SELECT count(*)::int FROM vendite.resi_righe_rinunce x
     WHERE x.resi_riga_id = (SELECT resi_riga_id FROM tmp_pr_reso))::text
  || '|' ||
  (SELECT count(*)::int FROM vendite.vw_resi_da_accreditare q
     WHERE q.resi_riga_id = (SELECT resi_riga_id FROM tmp_pr_reso))::text,
  '1|1',
  '1) fixture: la ri-consegna e'' chiusa (una rinuncia) e la riga e'' in coda accrediti'
);

SELECT is(
  script.fn_check_rinuncia_reversibile((SELECT resi_riga_id FROM tmp_pr_reso)),
  '[]'::jsonb,
  '2) PRIMA dell''accredito il gate e'' vuoto: la rinuncia si puo'' riaprire'
);

-- ============================================================
-- IL VERBO
-- ============================================================
CREATE TEMP TABLE tmp_acc_rin AS
SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_pr_reso));

SELECT is(
  (SELECT script.fn_check_rinuncia_reversibile((SELECT resi_riga_id FROM tmp_pr_reso)) -> 0 ->> 'codice'
   || '|' ||
   (script.fn_check_rinuncia_reversibile((SELECT resi_riga_id FROM tmp_pr_reso)) -> 0 ->> 'reason')),
  'E_RESO_RINUNCIA_ACCREDITO_ESEGUITO|ACCREDITO_ESEGUITO',
  '3) dopo l''accredito il gate produce il motivo, col codice e la reason giusti'
);

-- ⭐ P-1 — LA FRASE RESA. E' l'unica verifica che vede l'ORDINE dei valori:
--   il ramo C di test-catalogo-messaggi-errore-completo.sql prova che sono
--   TANTI QUANTI i segnaposto, non che siano quelli giusti al posto giusto.
--   Il precedente e' del 2026-09-01 su E_REGISTRO_SERIE_NON_AMMESSA — due
--   valori, due segnaposto, «Registro X1» a video con la serie al posto della
--   famiglia — e nel 2026-09-09 lo stesso difetto e' stato trovato VIVO su due
--   siti di questo cantiere.
-- ⚠️ Si confronta con la frase composta dai valori letti dalla TABELLA: se la
--   check li emettesse invertiti, le due stringhe divergerebbero. Un `matches`
--   su un pezzo di frase non lo vedrebbe.
-- ⚠️ Il CASE con `coalesce` non e' pignoleria: senza, una check che smettesse
--   di emettere `valori` farebbe alzare 22023 a format() e ABORTIREBBE il file.
--   E scritto con un `<>` nudo non guarderebbe niente: `jsonb_typeof(NULL) <>
--   'array'` vale NULL, non vero.
SELECT is(
  (WITH v AS (SELECT script.fn_check_rinuncia_reversibile((SELECT resi_riga_id FROM tmp_pr_reso)) -> 0 AS motivo)
   SELECT CASE
            WHEN coalesce(jsonb_typeof(v.motivo -> 'valori'), 'assente') <> 'array'
              THEN '(la check non emette valori)'
            ELSE format(
                   (SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_RESO_RINUNCIA_ACCREDITO_ESEGUITO' AND m.lingua = 'it'),
                   VARIADIC ARRAY(SELECT jsonb_array_elements_text(v.motivo -> 'valori')))
          END
     FROM v),
  (SELECT format((SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_RESO_RINUNCIA_ACCREDITO_ESEGUITO' AND m.lingua = 'it'),
                 (SELECT resi_riga_id FROM tmp_pr_reso)::text)),
  '3-bis) la frase resa nomina la RIGA DI RESO');

-- ⭐ IL CASO A ZERO SEGNAPOSTO, e vale la riga a se': «Reso non trovato.» non
--   ha `%s`, quindi il suo `valori` e' un array VUOTO — che e' un valore, non
--   una dimenticanza. Con zero valori fn_log_and_raise_error salta il ramo
--   format() e il testo arriva intero.
--   ⛔ Il difetto da vedere qui e' l'opposto degli altri: un `%s` che resta a
--   video LETTERALE perche' nessuno lo riempie (test 4 del catalogo messaggi).
--   ⚠️ Le due arita' diverse sulla stessa check (0 e 1) sono il caso che il
--   chiamante a valori FISSI non poteva servire: e' la ragione per cui questa
--   check e' entrata nel cantiere.
SELECT is(
  (WITH v AS (SELECT script.fn_check_rinuncia_reversibile(999999999) -> 0 AS motivo)
   SELECT CASE
            WHEN coalesce(jsonb_typeof(v.motivo -> 'valori'), 'assente') <> 'array'
              THEN '(la check non emette valori)'
            ELSE format(
                   (SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_RESO_NOT_FOUND' AND m.lingua = 'it'),
                   VARIADIC ARRAY(SELECT jsonb_array_elements_text(v.motivo -> 'valori')))
          END
     FROM v),
  (SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_RESO_NOT_FOUND' AND m.lingua = 'it'),
  '3-ter) il motivo a ZERO segnaposto rende il testo intero, senza %s a video');

-- ⭐ Che il divieto MORDA lo dice solo la madre: il gate da solo produce un
--    elenco che nessuno e' obbligato a leggere.
SELECT throws_like(
  format($$ SELECT vendite.fn_riapri_riconsegna_reso(%s) $$,
         (SELECT reso_id FROM tmp_pr_reso_id)),
  '%accredito e'' gia'' stato eseguito%',
  '4) e la MADRE lo solleva da se'': la rinuncia NON si riapre'
);

-- ============================================================
-- 5-6) ⭐⭐ L'AUTO-RIPARAZIONE DI C-3, nei due versi.
--   Il gate non sa nulla dell'annullo: torna vuoto solo perche' l'annullo
--   CANCELLA le righe di ponte. Se un giorno diventasse un soft-delete,
--   questi due test diventerebbero rossi — ed e' esattamente il loro scopo.
-- ============================================================
SELECT vendite.fn_annulla_accredito_riga_reso(
    (SELECT resi_riga_id FROM tmp_pr_reso), 'ci ho ripensato, pgTAP');

SELECT is(
  script.fn_check_rinuncia_reversibile((SELECT resi_riga_id FROM tmp_pr_reso)),
  '[]'::jsonb,
  '5) dopo l''ANNULLO il gate torna vuoto: si auto-ripara senza sapere nulla dell''annullo'
);

SELECT is(
  (SELECT vendite.fn_riapri_riconsegna_reso((SELECT reso_id FROM tmp_pr_reso_id)))::int,
  1,
  '6) e la madre RIESCE davvero: la rinuncia si riapre, il round-trip si chiude'
);

-- ============================================================
-- I rami che c'erano prima, non rotti
-- ============================================================
SELECT is(
  script.fn_check_rinuncia_reversibile(999999999) -> 0 ->> 'reason',
  'RIGA_INESISTENTE',
  '7) il ramo storico regge: una riga inesistente resta RIGA_INESISTENTE'
);

SELECT throws_ok(
  $$ SELECT script.fn_check_rinuncia_reversibile(NULL) $$,
  'P0001', NULL,
  '8) guard sul parametro: id nullo -> errore di dominio, mai normalizzazione silenziosa'
);

SELECT * FROM finish();
ROLLBACK;
